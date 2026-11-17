# Aplicacion Flask: API, archivos del frontend y manejo de errores.
#
# La API se publica bajo /api y el frontend se sirve desde /frontend. El
# backend no devuelve HTML de la interfaz: solo JSON, salvo los archivos
# estaticos que solicita explicitamente el navegador.
import os
import secrets

from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory, session
from sqlalchemy.exc import IntegrityError

from backend.errores import ErrorConflicto, ErrorDatosInvalidos, ErrorNoEncontrado
from backend.migracion import preparar_base
from backend.modelos import db
from backend.rutas import api, leer_json, obtener_campo, respuesta
from backend.usuarios import (
    Usuario, autenticar, cambiar_estado_usuario, crear_usuario, hay_usuarios,
    listar_usuarios,
)


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_FRONTEND = RAIZ_PROYECTO / "frontend"


def cargar_clave_secreta(ruta_clave):
    ruta = Path(ruta_clave)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ruta.open("x", encoding="utf-8") as archivo:
            archivo.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    clave = ruta.read_text(encoding="utf-8").strip()
    if len(clave) != 64:
        raise RuntimeError("La clave de sesión guardada no es válida.")
    return clave


def crear_aplicacion(ruta_base=None, configuracion_extra=None):
    if ruta_base is None:
        ruta_base = os.environ.get("BIBLIOTECA_DB")
    if ruta_base is None:
        ruta_base = RAIZ_PROYECTO / "biblioteca.db"
    ruta = Path(ruta_base).resolve()
    ruta.parent.mkdir(parents=True, exist_ok=True)

    aplicacion = Flask(__name__, static_folder=None,
                       instance_path=str(RAIZ_PROYECTO / "instance"))
    aplicacion.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + ruta.as_posix()
    aplicacion.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    aplicacion.config["RUTA_BASE"] = str(ruta)
    aplicacion.config["PROBLEMAS_BASE"] = []
    aplicacion.config["RESPALDO_BASE"] = None
    aplicacion.config["CAMBIOS_BASE"] = []
    aplicacion.config["RUTA_CLAVE_SECRETA"] = str(Path(aplicacion.instance_path) / "clave_secreta")
    aplicacion.config["SESSION_COOKIE_HTTPONLY"] = True
    aplicacion.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if configuracion_extra is not None:
        for clave in configuracion_extra:
            aplicacion.config[clave] = configuracion_extra[clave]
    if not aplicacion.config.get("SECRET_KEY"):
        aplicacion.config["SECRET_KEY"] = cargar_clave_secreta(
            aplicacion.config["RUTA_CLAVE_SECRETA"]
        )

    db.init_app(aplicacion)
    aplicacion.register_blueprint(api)
    aplicacion.json.sort_keys = False

    with aplicacion.app_context():
        resultado = preparar_base(str(ruta))
        aplicacion.config["PROBLEMAS_BASE"] = resultado["problemas"]
        aplicacion.config["RESPALDO_BASE"] = resultado["respaldo"]
        aplicacion.config["CAMBIOS_BASE"] = resultado["cambios"]

    @aplicacion.before_request
    def comprobar_acceso():
        if request.path != "/api" and request.path.startswith("/api/") == False:
            return None
        g.usuario = None
        identificador = session.get("usuario_id")
        if isinstance(identificador, int) and isinstance(identificador, bool) == False:
            cuenta = db.session.get(Usuario, identificador, populate_existing=True)
            if cuenta is not None and cuenta.activa:
                g.usuario = cuenta
        if g.usuario is None:
            session.clear()
        if request.endpoint in ("ver_sesion", "iniciar_sesion", "primer_usuario"):
            return None
        if g.usuario is None:
            return _respuesta_error("Iniciá sesión para acceder al sistema.", 401)
        return None

    @aplicacion.get("/api/sesion")
    def ver_sesion():
        cuenta = None
        if g.usuario is not None:
            cuenta = g.usuario.a_diccionario()
        return respuesta({"usuario": cuenta, "requiere_configuracion": not hay_usuarios()})

    @aplicacion.post("/api/login")
    def iniciar_sesion():
        datos = leer_json()
        cuenta = autenticar(datos.get("usuario"), datos.get("contrasena"))
        session.clear()
        if cuenta is None:
            return _respuesta_error("Usuario o contraseña incorrectos", 401)
        session["usuario_id"] = cuenta.id
        return respuesta(cuenta.a_diccionario(), "Sesión iniciada.")

    @aplicacion.post("/api/primer-usuario")
    def primer_usuario():
        if hay_usuarios():
            return _respuesta_error("La primera cuenta ya fue creada.", 403)
        datos = leer_json()
        cuenta = crear_usuario(obtener_campo(datos, "usuario"),
                               obtener_campo(datos, "nombre"),
                               obtener_campo(datos, "contrasena"), primero=True)
        session.clear()
        session["usuario_id"] = cuenta.id
        return respuesta(cuenta.a_diccionario(), "Primera cuenta creada.", 201)

    @aplicacion.post("/api/logout")
    def cerrar_sesion():
        session.clear()
        return respuesta(None, "Sesión cerrada.")

    @aplicacion.get("/api/usuarios")
    def consultar_usuarios():
        cuentas = []
        for cuenta in listar_usuarios():
            cuentas.append(cuenta.a_diccionario())
        return respuesta(cuentas)

    @aplicacion.post("/api/usuarios")
    def agregar_usuario():
        datos = leer_json()
        cuenta = crear_usuario(obtener_campo(datos, "usuario"),
                               obtener_campo(datos, "nombre"),
                               obtener_campo(datos, "contrasena"))
        return respuesta(cuenta.a_diccionario(), "Cuenta creada.", 201)

    @aplicacion.post("/api/usuarios/<int:identificador>/estado")
    def estado_usuario(identificador):
        datos = leer_json()
        cuenta = cambiar_estado_usuario(identificador, obtener_campo(datos, "activa"),
                                        g.usuario.id)
        return respuesta(cuenta.a_diccionario(), "Estado de la cuenta actualizado.")

    @aplicacion.get("/")
    def inicio():
        return send_from_directory(str(CARPETA_FRONTEND), "index.html")

    @aplicacion.get("/<path:archivo>")
    def archivo_frontend(archivo):
        if archivo.startswith("api/"):
            abort(404)
        return send_from_directory(str(CARPETA_FRONTEND), archivo)

    @aplicacion.errorhandler(ErrorDatosInvalidos)
    def manejar_datos_invalidos(error):
        db.session.rollback()
        return _respuesta_error(str(error), 400)

    @aplicacion.errorhandler(ErrorNoEncontrado)
    def manejar_no_encontrado(error):
        db.session.rollback()
        return _respuesta_error(str(error), 404)

    @aplicacion.errorhandler(ErrorConflicto)
    def manejar_conflicto(error):
        db.session.rollback()
        return _respuesta_error(str(error), 409)

    @aplicacion.errorhandler(IntegrityError)
    def manejar_integridad(error):
        db.session.rollback()
        return _respuesta_error(
            "La operación no respeta una relación o una restricción de la base de datos.", 409
        )

    @aplicacion.errorhandler(404)
    def manejar_404(error):
        if request.path.startswith("/api"):
            return _respuesta_error("No existe la ruta solicitada.", 404)
        return "No encontrado", 404

    @aplicacion.errorhandler(405)
    def manejar_405(error):
        if request.path.startswith("/api"):
            return _respuesta_error("Método no permitido para esta ruta.", 405)
        return "Método no permitido", 405

    @aplicacion.errorhandler(403)
    def manejar_prohibido(error):
        db.session.rollback()
        return _respuesta_error(error.description, 403)

    @aplicacion.errorhandler(500)
    def manejar_error_interno(error):
        db.session.rollback()
        if request.path.startswith("/api"):
            return _respuesta_error("Ocurrió un error interno en el servidor.", 500)
        return "Error interno", 500

    return aplicacion


def _respuesta_error(mensaje, codigo):
    return jsonify({"error": mensaje}), codigo
