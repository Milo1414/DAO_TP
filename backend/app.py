# Aplicacion Flask: API, archivos del frontend y manejo de errores.
#
# La API se publica bajo /api y el frontend se sirve desde /frontend. El
# backend no devuelve HTML de la interfaz: solo JSON, salvo los archivos
# estaticos que solicita explicitamente el navegador.
import os

from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory
from sqlalchemy.exc import IntegrityError

from backend.errores import ErrorConflicto, ErrorDatosInvalidos, ErrorNoEncontrado
from backend.migracion import preparar_base
from backend.modelos import db
from backend.rutas import api


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_FRONTEND = RAIZ_PROYECTO / "frontend"


def crear_aplicacion(ruta_base=None, configuracion_extra=None):
    if ruta_base is None:
        ruta_base = os.environ.get("BIBLIOTECA_DB")
    if ruta_base is None:
        ruta_base = RAIZ_PROYECTO / "biblioteca.db"
    ruta = Path(ruta_base).resolve()
    ruta.parent.mkdir(parents=True, exist_ok=True)

    aplicacion = Flask(__name__, static_folder=None)
    aplicacion.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + ruta.as_posix()
    aplicacion.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    aplicacion.config["RUTA_BASE"] = str(ruta)
    aplicacion.config["PROBLEMAS_BASE"] = []
    aplicacion.config["RESPALDO_BASE"] = None
    aplicacion.config["CAMBIOS_BASE"] = []
    if configuracion_extra is not None:
        for clave in configuracion_extra:
            aplicacion.config[clave] = configuracion_extra[clave]

    db.init_app(aplicacion)
    aplicacion.register_blueprint(api)
    aplicacion.json.sort_keys = False

    with aplicacion.app_context():
        resultado = preparar_base(str(ruta))
        aplicacion.config["PROBLEMAS_BASE"] = resultado["problemas"]
        aplicacion.config["RESPALDO_BASE"] = resultado["respaldo"]
        aplicacion.config["CAMBIOS_BASE"] = resultado["cambios"]

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
            "La operacion no respeta una relacion o una restriccion de la base de datos.", 409
        )

    @aplicacion.errorhandler(404)
    def manejar_404(error):
        if request.path.startswith("/api"):
            return _respuesta_error("No existe la ruta solicitada.", 404)
        return "No encontrado", 404

    @aplicacion.errorhandler(405)
    def manejar_405(error):
        if request.path.startswith("/api"):
            return _respuesta_error("Metodo no permitido para esta ruta.", 405)
        return "Metodo no permitido", 405

    @aplicacion.errorhandler(500)
    def manejar_error_interno(error):
        db.session.rollback()
        if request.path.startswith("/api"):
            return _respuesta_error("Ocurrio un error interno en el servidor.", 500)
        return "Error interno", 500

    return aplicacion


def _respuesta_error(mensaje, codigo):
    return jsonify({"error": mensaje}), codigo
