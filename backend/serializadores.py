# Conversion de entidades a diccionarios para la API JSON.
#
# La API usa JSON para transportar datos; esto no tiene relacion con la
# persistencia, que se hace exclusivamente en SQLite mediante el ORM.
import datetime


def _fecha_texto(valor):
    if valor is None:
        return None
    return valor.isoformat()


def _momento_texto(valor):
    if valor is None:
        return None
    return valor.isoformat(sep=" ", timespec="seconds")


def sede_a_diccionario(sede):
    return {
        "codigo": sede.codigo,
        "nombre": sede.nombre,
        "direccion": sede.direccion,
        "telefono": sede.telefono,
        "horario": sede.horario,
        "activa": sede.activa,
    }


def socio_a_diccionario(socio):
    return {
        "numero": socio.numero,
        "nombre": socio.nombre,
        "email": socio.email,
        "telefono": socio.telefono,
        "habilitado": socio.habilitado,
    }


def libro_a_diccionario(libro):
    return {
        "isbn": libro.isbn,
        "titulo": libro.titulo,
        "autor": libro.autor,
        "anio": libro.anio,
        "genero": libro.genero,
    }


def ejemplar_a_diccionario(ejemplar, red):
    libro = red.buscar_libro(ejemplar.libro_isbn)
    titulo = ejemplar.libro_isbn
    if libro is not None:
        titulo = libro.titulo
    disponible = ejemplar.esta_disponible()
    if ejemplar.ubicacion_actual != ejemplar.sede_pertenencia:
        disponible = False
    return {
        "codigo": ejemplar.codigo,
        "libro_isbn": ejemplar.libro_isbn,
        "libro_titulo": titulo,
        "sede_pertenencia": ejemplar.sede_pertenencia,
        "ubicacion_actual": ejemplar.ubicacion_actual,
        "estado_disponibilidad": ejemplar.estado_disponibilidad,
        "estado_fisico": ejemplar.estado_fisico,
        "solicitud_asignada": ejemplar.solicitud_asignada,
        "reserva_asignada": ejemplar.reserva_asignada,
        "disponible": disponible,
        "motivo": red.motivo_no_disponible(ejemplar),
    }


def solicitud_a_diccionario(solicitud, red):
    socio = red.buscar_socio(solicitud.socio_numero)
    libro = red.buscar_libro(solicitud.libro_isbn)
    socio_nombre = str(solicitud.socio_numero)
    libro_titulo = solicitud.libro_isbn
    if socio is not None:
        socio_nombre = socio.nombre
    if libro is not None:
        libro_titulo = libro.titulo
    remito = red.buscar_remito_por_solicitud(solicitud.numero)
    codigo_remito = None
    if remito is not None:
        codigo_remito = remito.codigo
    return {
        "numero": solicitud.numero,
        "socio_numero": solicitud.socio_numero,
        "socio_nombre": socio_nombre,
        "libro_isbn": solicitud.libro_isbn,
        "libro_titulo": libro_titulo,
        "ejemplar_codigo": solicitud.ejemplar_codigo,
        "sede_origen": solicitud.sede_origen,
        "sede_destino": solicitud.sede_destino,
        "fecha_solicitud": _fecha_texto(solicitud.fecha_solicitud),
        "tipo": solicitud.tipo,
        "estado": solicitud.estado,
        "remito_codigo": codigo_remito,
    }


def prestamo_a_diccionario(prestamo, red):
    socio = red.buscar_socio(prestamo.socio_numero)
    ejemplar = red.buscar_ejemplar(prestamo.ejemplar_codigo)
    socio_nombre = str(prestamo.socio_numero)
    if socio is not None:
        socio_nombre = socio.nombre
    libro_titulo = None
    if ejemplar is not None:
        libro = red.buscar_libro(ejemplar.libro_isbn)
        if libro is not None:
            libro_titulo = libro.titulo
    hoy = datetime.date.today()
    dias_atraso = prestamo.dias_atraso(hoy)
    multa_estimada = prestamo.multa_acumulada(hoy, red.multa_por_dia)
    return {
        "numero": prestamo.numero,
        "solicitud_numero": prestamo.solicitud_numero,
        "socio_numero": prestamo.socio_numero,
        "socio_nombre": socio_nombre,
        "ejemplar_codigo": prestamo.ejemplar_codigo,
        "libro_titulo": libro_titulo,
        "sede_origen": prestamo.sede_origen,
        "sede_destino": prestamo.sede_destino,
        "fecha_prestamo": _fecha_texto(prestamo.fecha_prestamo),
        "fecha_vencimiento": _fecha_texto(prestamo.fecha_vencimiento),
        "fecha_devolucion": _fecha_texto(prestamo.fecha_devolucion),
        "sede_devolucion": prestamo.sede_devolucion,
        "estado_fisico_devolucion": prestamo.estado_fisico_devolucion,
        "multa": prestamo.multa,
        "estado": prestamo.estado,
        "dias_atraso": dias_atraso,
        "multa_estimada": multa_estimada,
    }


def reserva_a_diccionario(reserva, red):
    socio = red.buscar_socio(reserva.socio_numero)
    libro = red.buscar_libro(reserva.libro_isbn)
    socio_nombre = str(reserva.socio_numero)
    libro_titulo = reserva.libro_isbn
    if socio is not None:
        socio_nombre = socio.nombre
    if libro is not None:
        libro_titulo = libro.titulo
    return {
        "numero": reserva.numero,
        "socio_numero": reserva.socio_numero,
        "socio_nombre": socio_nombre,
        "libro_isbn": reserva.libro_isbn,
        "libro_titulo": libro_titulo,
        "codigo_sede": reserva.codigo_sede,
        "fecha_reserva": _fecha_texto(reserva.fecha_reserva),
        "estado": reserva.estado,
        "ejemplar_codigo": reserva.ejemplar_codigo,
        "solicitud_numero": reserva.solicitud_numero,
    }


def remito_a_diccionario(remito, incluir_historial=True):
    asignaciones = []
    for asignacion in remito.asignaciones:
        asignaciones.append({
            "ejemplar_codigo": asignacion.ejemplar_codigo,
            "numero_solicitud": asignacion.numero_solicitud,
            "estado_fisico_recepcion": asignacion.estado_fisico_recepcion,
        })
    historial = []
    if incluir_historial:
        for registro in remito.historial:
            historial.append({
                "orden": registro.orden,
                "estado": registro.nombre_estado,
                "momento": _momento_texto(registro.momento),
            })
    return {
        "codigo": remito.codigo,
        "sede_origen": remito.sede_origen,
        "sede_destino": remito.sede_destino,
        "fecha_creacion": _momento_texto(remito.fecha_creacion),
        "motivo": remito.motivo,
        "estado_actual": remito.estado_actual,
        "asignaciones": asignaciones,
        "historial": historial,
    }
