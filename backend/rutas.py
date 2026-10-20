# Rutas HTTP de la API.
#
# Cada ruta recibe datos, llama a una operacion de RedBibliotecas y devuelve
# JSON. Las reglas de negocio no se repiten aca: viven en el dominio.
import datetime

from flask import Blueprint, current_app, jsonify, request

from backend.errores import ErrorDatosInvalidos, ErrorNoEncontrado
from backend.red import RedBibliotecas
from backend.reportes import (
    FabricaReporteActivosVencidos,
    FabricaReporteDisponibilidad,
    FabricaReporteLibrosSolicitados,
    FabricaReporteMovimientoEnvios,
)
from backend.serializadores import (
    ejemplar_a_diccionario,
    libro_a_diccionario,
    prestamo_a_diccionario,
    remito_a_diccionario,
    reserva_a_diccionario,
    sede_a_diccionario,
    socio_a_diccionario,
    solicitud_a_diccionario,
)
from backend.validaciones import validar_entero


api = Blueprint("api", __name__, url_prefix="/api")
red = RedBibliotecas()


# ---------- Lectura y validacion de peticiones ----------

def leer_json():
    datos = request.get_json(silent=True)
    if datos is None or isinstance(datos, dict) == False:
        raise ErrorDatosInvalidos("El cuerpo de la peticion debe ser un objeto JSON valido.")
    return datos


def obtener_campo(datos, nombre):
    if nombre not in datos:
        raise ErrorDatosInvalidos("Falta el campo obligatorio: " + nombre)
    return datos[nombre]


def obtener_texto(datos, nombre):
    valor = obtener_campo(datos, nombre)
    if isinstance(valor, str) == False:
        raise ErrorDatosInvalidos("El campo " + nombre + " debe ser un texto.")
    return valor


def obtener_entero(datos, nombre, minimo=0):
    valor = obtener_campo(datos, nombre)
    return validar_entero(valor, nombre, minimo)


def obtener_fecha(datos, nombre):
    valor = obtener_campo(datos, nombre)
    return parsear_fecha(valor, nombre)


def parsear_fecha(valor, nombre):
    if isinstance(valor, str) == False:
        raise ErrorDatosInvalidos("El campo " + nombre + " debe ser una fecha AAAA-MM-DD.")
    if len(valor) != 10 or valor[4] != "-" or valor[7] != "-":
        raise ErrorDatosInvalidos("El campo " + nombre + " debe tener formato AAAA-MM-DD.")
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError:
        raise ErrorDatosInvalidos("El campo " + nombre + " no es una fecha existente: " + valor)


def obtener_momento_opcional(datos, nombre):
    if nombre not in datos:
        return None
    valor = datos[nombre]
    if valor is None or valor == "":
        return None
    return parsear_momento(valor, nombre)


def parsear_momento(valor, nombre):
    if isinstance(valor, str) == False:
        raise ErrorDatosInvalidos("El campo " + nombre + " debe ser una fecha y hora.")
    if len(valor) == 10:
        return parsear_fecha(valor, nombre)
    try:
        return datetime.datetime.fromisoformat(valor)
    except ValueError:
        raise ErrorDatosInvalidos("El campo " + nombre + " no es una fecha y hora valida: " + valor)


def argumento(nombre):
    valor = request.args.get(nombre)
    if valor is None:
        return None
    valor = valor.strip()
    if valor == "":
        return None
    return valor


def respuesta(datos, mensaje=None, codigo=200):
    cuerpo = {"datos": datos}
    if mensaje is not None:
        cuerpo["mensaje"] = mensaje
    return jsonify(cuerpo), codigo


# ---------- Salud y resumen ----------

@api.get("/salud")
def salud():
    problemas = current_app.config.get("PROBLEMAS_BASE", [])
    return respuesta({
        "estado": "ok",
        "base_de_datos": current_app.config.get("RUTA_BASE"),
        "problemas_datos": problemas,
    })


@api.get("/resumen")
def resumen():
    return respuesta(red.resumen())


# ---------- Sedes ----------

@api.get("/sedes")
def listar_sedes():
    datos = []
    for sede in red.sedes:
        datos.append(sede_a_diccionario(sede))
    return respuesta(datos)


@api.post("/sedes")
def crear_sede():
    datos = leer_json()
    sede = red.agregar_sede(
        obtener_texto(datos, "codigo"),
        obtener_texto(datos, "nombre"),
        obtener_texto(datos, "direccion"),
        obtener_texto(datos, "telefono"),
        obtener_texto(datos, "horario"),
    )
    return respuesta(sede_a_diccionario(sede), "Sede creada.", 201)


@api.get("/sedes/<codigo>")
def obtener_sede(codigo):
    sede = red.buscar_sede(codigo)
    if sede is None:
        raise ErrorNoEncontrado("No existe la sede: " + codigo)
    return respuesta(sede_a_diccionario(sede))


@api.put("/sedes/<codigo>")
def modificar_sede(codigo):
    datos = leer_json()
    sede = red.modificar_sede(
        codigo,
        obtener_texto(datos, "nombre"),
        obtener_texto(datos, "direccion"),
        obtener_texto(datos, "telefono"),
        obtener_texto(datos, "horario"),
    )
    return respuesta(sede_a_diccionario(sede), "Sede modificada.")


@api.post("/sedes/<codigo>/baja")
def dar_baja_sede(codigo):
    sede = red.dar_baja_sede(codigo)
    return respuesta(sede_a_diccionario(sede), "Sede dada de baja.")


@api.post("/sedes/<codigo>/reactivacion")
def reactivar_sede(codigo):
    sede = red.reactivar_sede(codigo)
    return respuesta(sede_a_diccionario(sede), "Sede reactivada.")


# ---------- Socios ----------

@api.get("/socios")
def listar_socios():
    datos = []
    for socio in red.socios:
        datos.append(socio_a_diccionario(socio))
    return respuesta(datos)


@api.post("/socios")
def crear_socio():
    datos = leer_json()
    socio = red.agregar_socio(
        obtener_entero(datos, "numero", 1),
        obtener_texto(datos, "nombre"),
        obtener_texto(datos, "email"),
        obtener_texto(datos, "telefono"),
    )
    return respuesta(socio_a_diccionario(socio), "Socio creado.", 201)


@api.get("/socios/<int:numero>")
def obtener_socio(numero):
    socio = red.buscar_socio(numero)
    if socio is None:
        raise ErrorNoEncontrado("No existe el socio: " + str(numero))
    return respuesta(socio_a_diccionario(socio))


@api.put("/socios/<int:numero>")
def modificar_socio(numero):
    datos = leer_json()
    socio = red.modificar_socio(
        numero,
        obtener_texto(datos, "nombre"),
        obtener_texto(datos, "email"),
        obtener_texto(datos, "telefono"),
    )
    return respuesta(socio_a_diccionario(socio), "Socio modificado.")


@api.post("/socios/<int:numero>/habilitar")
def habilitar_socio(numero):
    socio = red.habilitar_socio(numero)
    return respuesta(socio_a_diccionario(socio), "Socio habilitado.")


@api.post("/socios/<int:numero>/inhabilitar")
def inhabilitar_socio(numero):
    socio = red.inhabilitar_socio(numero)
    return respuesta(socio_a_diccionario(socio), "Socio inhabilitado.")


# ---------- Libros ----------

@api.get("/libros")
def listar_libros():
    datos = []
    for libro in red.libros:
        datos.append(libro_a_diccionario(libro))
    return respuesta(datos)


@api.post("/libros")
def crear_libro():
    datos = leer_json()
    libro = red.agregar_libro(
        obtener_texto(datos, "isbn"),
        obtener_texto(datos, "titulo"),
        obtener_texto(datos, "autor"),
        obtener_entero(datos, "anio", 1000),
        obtener_texto(datos, "genero"),
    )
    return respuesta(libro_a_diccionario(libro), "Libro creado.", 201)


@api.get("/libros/<isbn>")
def obtener_libro(isbn):
    libro = red.buscar_libro(isbn)
    if libro is None:
        raise ErrorNoEncontrado("No existe el libro: " + isbn)
    return respuesta(libro_a_diccionario(libro))


@api.put("/libros/<isbn>")
def modificar_libro(isbn):
    datos = leer_json()
    libro = red.modificar_libro(
        isbn,
        obtener_texto(datos, "titulo"),
        obtener_texto(datos, "autor"),
        obtener_entero(datos, "anio", 1000),
        obtener_texto(datos, "genero"),
    )
    return respuesta(libro_a_diccionario(libro), "Libro modificado.")


# ---------- Ejemplares y disponibilidad ----------

@api.get("/ejemplares")
def listar_ejemplares():
    isbn = argumento("isbn")
    sede = argumento("sede")
    datos = []
    for ejemplar in red.disponibilidad_detallada(isbn, sede):
        datos.append(ejemplar_a_diccionario(ejemplar, red))
    return respuesta(datos)


@api.post("/ejemplares")
def crear_ejemplar():
    datos = leer_json()
    ejemplar = red.agregar_ejemplar(
        obtener_texto(datos, "codigo"),
        obtener_texto(datos, "libro_isbn"),
        obtener_texto(datos, "sede_pertenencia"),
    )
    return respuesta(ejemplar_a_diccionario(ejemplar, red), "Ejemplar creado.", 201)


@api.get("/ejemplares/<codigo>")
def obtener_ejemplar(codigo):
    ejemplar = red.buscar_ejemplar(codigo)
    if ejemplar is None:
        raise ErrorNoEncontrado("No existe el ejemplar: " + codigo)
    return respuesta(ejemplar_a_diccionario(ejemplar, red))


@api.post("/ejemplares/<codigo>/reparar")
def reparar_ejemplar(codigo):
    ejemplar = red.reparar_ejemplar(codigo)
    return respuesta(ejemplar_a_diccionario(ejemplar, red), "Ejemplar reparado.")


# ---------- Solicitudes ----------

@api.get("/solicitudes")
def listar_solicitudes():
    estado = argumento("estado")
    datos = []
    for solicitud in red.solicitudes:
        if estado is not None and solicitud.estado != estado:
            continue
        datos.append(solicitud_a_diccionario(solicitud, red))
    return respuesta(datos)


@api.get("/solicitudes/<int:numero>")
def obtener_solicitud(numero):
    solicitud = red.buscar_solicitud(numero)
    if solicitud is None:
        raise ErrorNoEncontrado("No existe la solicitud: " + str(numero))
    return respuesta(solicitud_a_diccionario(solicitud, red))


@api.post("/solicitudes")
def crear_solicitud():
    datos = leer_json()
    solicitud = red.registrar_solicitud(
        obtener_entero(datos, "socio_numero", 1),
        obtener_texto(datos, "libro_isbn"),
        obtener_texto(datos, "ejemplar_codigo"),
        obtener_texto(datos, "sede_origen"),
        obtener_texto(datos, "sede_destino"),
        obtener_fecha(datos, "fecha_solicitud"),
        obtener_texto(datos, "tipo"),
    )
    return respuesta(solicitud_a_diccionario(solicitud, red), "Solicitud registrada.", 201)


@api.post("/solicitudes/<int:numero>/cancelar")
def cancelar_solicitud(numero):
    solicitud = red.cancelar_solicitud(numero)
    return respuesta(solicitud_a_diccionario(solicitud, red), "Solicitud cancelada.")


@api.post("/solicitudes/<int:numero>/entregar")
def entregar_solicitud(numero):
    datos = leer_json()
    prestamo = red.entregar_solicitud(numero, obtener_fecha(datos, "fecha_prestamo"))
    solicitud = red.buscar_solicitud(numero)
    return respuesta({
        "solicitud": solicitud_a_diccionario(solicitud, red),
        "prestamo": prestamo_a_diccionario(prestamo, red),
    }, "Prestamo entregado.", 201)


# ---------- Reservas ----------

@api.get("/reservas")
def listar_reservas():
    datos = []
    for reserva in red.reservas:
        datos.append(reserva_a_diccionario(reserva, red))
    return respuesta(datos)


@api.post("/reservas")
def crear_reserva():
    datos = leer_json()
    reserva = red.registrar_reserva(
        obtener_entero(datos, "socio_numero", 1),
        obtener_texto(datos, "libro_isbn"),
        obtener_texto(datos, "codigo_sede"),
        obtener_fecha(datos, "fecha_reserva"),
    )
    return respuesta(reserva_a_diccionario(reserva, red), "Reserva registrada.", 201)


@api.post("/reservas/<int:numero>/cancelar")
def cancelar_reserva(numero):
    reserva = red.cancelar_reserva(numero)
    return respuesta(reserva_a_diccionario(reserva, red), "Reserva cancelada.")


# ---------- Prestamos y devoluciones ----------

@api.get("/prestamos")
def listar_prestamos():
    estado = argumento("estado")
    datos = []
    for prestamo in red.prestamos:
        if estado is not None and prestamo.estado != estado:
            continue
        datos.append(prestamo_a_diccionario(prestamo, red))
    return respuesta(datos)


@api.get("/prestamos/<int:numero>")
def obtener_prestamo(numero):
    prestamo = red.buscar_prestamo(numero)
    if prestamo is None:
        raise ErrorNoEncontrado("No existe el prestamo: " + str(numero))
    return respuesta(prestamo_a_diccionario(prestamo, red))


@api.post("/prestamos/<int:numero>/devolucion")
def registrar_devolucion(numero):
    datos = leer_json()
    prestamo = red.registrar_devolucion(
        numero,
        obtener_fecha(datos, "fecha_devolucion"),
        obtener_texto(datos, "sede_devolucion"),
        obtener_texto(datos, "estado_fisico"),
    )
    return respuesta(prestamo_a_diccionario(prestamo, red), "Devolucion registrada.")


# ---------- Remitos ----------

@api.get("/remitos")
def listar_remitos():
    estado = argumento("estado")
    motivo = argumento("motivo")
    datos = []
    for remito in red.remitos:
        if estado is not None and remito.estado_actual != estado:
            continue
        if motivo is not None and remito.motivo != motivo:
            continue
        datos.append(remito_a_diccionario(remito))
    return respuesta(datos)


@api.get("/remitos/<codigo>")
def obtener_remito(codigo):
    remito = red.buscar_remito(codigo)
    if remito is None:
        raise ErrorNoEncontrado("No existe el remito: " + codigo)
    return respuesta(remito_a_diccionario(remito))


@api.get("/remitos/<codigo>/historial")
def historial_remito(codigo):
    remito = red.buscar_remito(codigo)
    if remito is None:
        raise ErrorNoEncontrado("No existe el remito: " + codigo)
    return respuesta(remito_a_diccionario(remito)["historial"])


@api.post("/remitos/prestamo")
def crear_remito_prestamo():
    datos = leer_json()
    solicitud_numero = obtener_entero(datos, "solicitud_numero", 1)
    momento = obtener_momento_opcional(datos, "fecha_creacion")
    if momento is None:
        momento = datetime.datetime.now()
    remito = red.crear_remito_para_solicitud(solicitud_numero, momento)
    return respuesta(remito_a_diccionario(remito), "Remito de prestamo creado.", 201)


@api.post("/remitos/retorno")
def crear_remito_retorno():
    datos = leer_json()
    ejemplar_codigo = obtener_texto(datos, "ejemplar_codigo")
    momento = obtener_momento_opcional(datos, "fecha_creacion")
    if momento is None:
        momento = datetime.datetime.now()
    remito = red.crear_remito_retorno(ejemplar_codigo, momento)
    return respuesta(remito_a_diccionario(remito), "Remito de retorno creado.", 201)


@api.post("/remitos/<codigo>/empaquetar")
def empaquetar_remito(codigo):
    datos = leer_json()
    remito = red.empaquetar_remito(codigo, obtener_momento_opcional(datos, "momento"))
    return respuesta(remito_a_diccionario(remito), "Remito empaquetado.")


@api.post("/remitos/<codigo>/despachar")
def despachar_remito(codigo):
    datos = leer_json()
    remito = red.despachar_remito(codigo, obtener_momento_opcional(datos, "momento"))
    return respuesta(remito_a_diccionario(remito), "Remito despachado.")


@api.post("/remitos/<codigo>/recibir")
def recibir_remito(codigo):
    datos = leer_json()
    remito = red.recibir_remito(codigo, obtener_momento_opcional(datos, "momento"))
    return respuesta(remito_a_diccionario(remito), "Remito recibido.")


# ---------- Reportes ----------

@api.get("/reportes/activos-vencidos")
def reporte_activos_vencidos():
    fecha_texto = argumento("fecha_referencia")
    fecha = None
    if fecha_texto is not None:
        fecha = parsear_fecha(fecha_texto, "fecha_referencia")
    fabrica = FabricaReporteActivosVencidos()
    reporte = fabrica.crear_reporte()
    filas = reporte.generar(red, {"fecha_referencia": fecha})
    return respuesta({"reporte": reporte.nombre(), "filas": filas})


@api.get("/reportes/disponibilidad")
def reporte_disponibilidad():
    fabrica = FabricaReporteDisponibilidad()
    reporte = fabrica.crear_reporte()
    filas = reporte.generar(red, {"sede": argumento("sede"), "isbn": argumento("isbn")})
    return respuesta({"reporte": reporte.nombre(), "filas": filas})


@api.get("/reportes/libros-solicitados")
def reporte_libros_solicitados():
    desde_texto = argumento("desde")
    hasta_texto = argumento("hasta")
    desde = None
    hasta = None
    if desde_texto is not None:
        desde = parsear_fecha(desde_texto, "desde")
    if hasta_texto is not None:
        hasta = parsear_fecha(hasta_texto, "hasta")
    if desde is not None and hasta is not None and hasta < desde:
        raise ErrorDatosInvalidos("La fecha 'hasta' no puede ser anterior a 'desde'.")
    fabrica = FabricaReporteLibrosSolicitados()
    reporte = fabrica.crear_reporte()
    filas = reporte.generar(red, {
        "fecha_desde": desde,
        "fecha_hasta": hasta,
        "sede_origen": argumento("sede_origen"),
        "sede_destino": argumento("sede_destino"),
    })
    return respuesta({"reporte": reporte.nombre(), "filas": filas})


@api.get("/reportes/movimiento")
def reporte_movimiento():
    fabrica = FabricaReporteMovimientoEnvios()
    reporte = fabrica.crear_reporte()
    filas = reporte.generar(red, {})
    return respuesta({"reporte": reporte.nombre(), "filas": filas})


# ---------- Listados para formularios ----------

@api.get("/listados")
def listados():
    sedes = []
    for sede in red.sedes:
        sedes.append(sede_a_diccionario(sede))
    socios = []
    for socio in red.socios:
        socios.append(socio_a_diccionario(socio))
    libros = []
    for libro in red.libros:
        libros.append(libro_a_diccionario(libro))
    ejemplares = []
    for ejemplar in red.ejemplares:
        ejemplares.append(ejemplar_a_diccionario(ejemplar, red))
    solicitudes = []
    for solicitud in red.solicitudes:
        solicitudes.append(solicitud_a_diccionario(solicitud, red))
    prestamos = []
    for prestamo in red.prestamos:
        prestamos.append(prestamo_a_diccionario(prestamo, red))
    reservas = []
    for reserva in red.reservas:
        reservas.append(reserva_a_diccionario(reserva, red))
    remitos = []
    for remito in red.remitos:
        remitos.append(remito_a_diccionario(remito))
    return respuesta({
        "sedes": sedes,
        "socios": socios,
        "libros": libros,
        "ejemplares": ejemplares,
        "solicitudes": solicitudes,
        "prestamos": prestamos,
        "reservas": reservas,
        "remitos": remitos,
        "resumen": red.resumen(),
    })
