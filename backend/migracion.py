# Preparacion y migracion de la base SQLite.
#
# La base existente se conserva. Si hace falta cambiar el esquema, primero
# se crea un respaldo. Los datos heredados no se corrigen solos: se revisan
# y los problemas se muestran en /api/salud para que una persona decida.
import datetime
import math
import os
import shutil
import sqlite3

from backend.catalogo import Ejemplar
from backend.modelos import Configuracion, db
from backend.prestamos import Prestamo, Reserva, SolicitudPrestamo
from backend.remito import Remito
from backend.validaciones import (
    validar_anio,
    validar_codigo,
    validar_email,
    validar_entero,
    validar_estado_fisico,
    validar_horario,
    validar_telefono,
    validar_texto,
    validar_tipo_solicitud,
    validar_momento,
    validar_historial_remito,
)


VALORES_CONFIGURACION = {
    "plazo_dias": "14",
    "multa_por_dia": "100",
}


def preparar_base(ruta_base):
    resultado = {"respaldo": None, "cambios": [], "problemas": []}
    if os.path.exists(ruta_base):
        resultado["respaldo"] = _migrar_columnas(ruta_base, resultado["cambios"])
    db.create_all()
    _sembrar_configuracion()
    conexion = sqlite3.connect(ruta_base)
    conexion.row_factory = sqlite3.Row
    try:
        resultado["problemas"] = revisar_datos_heredados(conexion)
    finally:
        conexion.close()
    return resultado


def _migrar_columnas(ruta_base, cambios):
    conexion = sqlite3.connect(ruta_base)
    conexion.row_factory = sqlite3.Row
    try:
        tablas = _nombres_de_tablas(conexion)
        if "remito_ejemplares" not in tablas:
            return None
        columnas = _nombres_de_columnas(conexion, "remito_ejemplares")
        if "estado_fisico_recepcion" in columnas:
            return None
        respaldo = _crear_respaldo(ruta_base)
        conexion.execute(
            "ALTER TABLE remito_ejemplares ADD COLUMN estado_fisico_recepcion TEXT"
        )
        conexion.commit()
        cambios.append("Se agrego estado_fisico_recepcion a remito_ejemplares.")
        return respaldo
    finally:
        conexion.close()


def _crear_respaldo(ruta_base):
    marca = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destino = ruta_base + ".respaldo-" + marca
    shutil.copy2(ruta_base, destino)
    return destino


def _sembrar_configuracion():
    for clave in VALORES_CONFIGURACION:
        if db.session.get(Configuracion, clave) is None:
            db.session.add(Configuracion(clave, VALORES_CONFIGURACION[clave]))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _nombres_de_tablas(conexion):
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    nombres = []
    for fila in filas:
        nombres.append(fila["name"])
    return nombres


def _nombres_de_columnas(conexion, tabla):
    filas = conexion.execute("PRAGMA table_info(" + tabla + ")").fetchall()
    nombres = []
    for fila in filas:
        nombres.append(fila["name"])
    return nombres


def _leer_tabla(conexion, tabla):
    if tabla not in _nombres_de_tablas(conexion):
        return []
    return conexion.execute("SELECT * FROM " + tabla).fetchall()


def _agregar(problemas, etiqueta, detalle):
    problemas.append(etiqueta + ": " + detalle)


def _probar(problemas, etiqueta, funcion, *argumentos):
    try:
        funcion(*argumentos)
    except Exception as error:
        _agregar(problemas, etiqueta, str(error))


def _fecha(valor):
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    if isinstance(valor, str) == False:
        raise ValueError("la fecha no es valida")
    return datetime.date.fromisoformat(valor)


def _momento(valor):
    if isinstance(valor, datetime.datetime):
        return validar_momento(valor, "momento")
    if isinstance(valor, datetime.date):
        return datetime.datetime.combine(valor, datetime.time(0, 0))
    if isinstance(valor, str) == False:
        raise ValueError("la fecha y hora no es valida")
    return validar_momento(datetime.datetime.fromisoformat(valor), "momento")


def revisar_datos_heredados(conexion):
    problemas = []
    sedes = _leer_tabla(conexion, "sedes")
    socios = _leer_tabla(conexion, "socios")
    libros = _leer_tabla(conexion, "libros")
    ejemplares = _leer_tabla(conexion, "ejemplares")
    solicitudes = _leer_tabla(conexion, "solicitudes")
    prestamos = _leer_tabla(conexion, "prestamos")
    reservas = _leer_tabla(conexion, "reservas")
    remitos = _leer_tabla(conexion, "remitos")
    remito_ejemplares = _leer_tabla(conexion, "remito_ejemplares")
    remito_historial = _leer_tabla(conexion, "remito_historial")
    configuracion = _leer_tabla(conexion, "configuracion")

    codigos_sede = _conjunto(sedes, "codigo")
    numeros_socio = _conjunto(socios, "numero")
    isbns = _conjunto(libros, "isbn")
    codigos_ejemplar = _conjunto(ejemplares, "codigo")
    numeros_solicitud = _conjunto(solicitudes, "numero")
    numeros_reserva = _conjunto(reservas, "numero")
    reservas_por_numero = {}
    for fila in reservas:
        reservas_por_numero[fila["numero"]] = fila
    codigos_remito = _conjunto(remitos, "codigo")

    emails = []
    for fila in sedes:
        _revisar_sede(fila, problemas)
    for fila in socios:
        _revisar_socio(fila, problemas)
        emails.append(str(fila["email"]).lower())
    _revisar_duplicados(emails, "email de socio", problemas)
    for fila in libros:
        _revisar_libro(fila, problemas)
    for fila in ejemplares:
        _revisar_ejemplar(
            fila, codigos_sede, isbns, numeros_solicitud, reservas_por_numero, problemas
        )
    for fila in solicitudes:
        _revisar_solicitud(
            fila, numeros_socio, isbns, codigos_ejemplar, codigos_sede, problemas
        )
    for fila in prestamos:
        _revisar_prestamo(
            fila, numeros_solicitud, numeros_socio, codigos_ejemplar, codigos_sede, problemas
        )
    for fila in reservas:
        _revisar_reserva(
            fila, numeros_socio, isbns, codigos_sede, codigos_ejemplar, numeros_solicitud, problemas
        )
    for fila in remitos:
        _revisar_remito(fila, codigos_sede, problemas)
    for fila in remito_ejemplares:
        _revisar_remito_ejemplar(
            fila, codigos_remito, codigos_ejemplar, numeros_solicitud, problemas
        )
    _revisar_historial(remito_historial, remitos, problemas)
    _revisar_relaciones(solicitudes, prestamos, ejemplares, reservas, problemas)
    _revisar_configuracion(configuracion, problemas)
    return problemas


def _conjunto(filas, columna):
    valores = set()
    for fila in filas:
        valores.add(fila[columna])
    return valores


def _revisar_sede(fila, problemas):
    etiqueta = "Sede '" + str(fila["codigo"]) + "'"
    _probar(problemas, etiqueta, validar_codigo, fila["codigo"], "codigo de sede")
    _probar(problemas, etiqueta, validar_texto, fila["nombre"], "nombre de sede")
    _probar(problemas, etiqueta, validar_texto, fila["direccion"], "direccion de sede")
    _probar(problemas, etiqueta, validar_telefono, fila["telefono"], "telefono de sede")
    _probar(problemas, etiqueta, validar_horario, fila["horario"], "horario de sede")
    if fila["activa"] not in (0, 1):
        _agregar(problemas, etiqueta, "el campo activa debe ser 0 o 1")


def _revisar_socio(fila, problemas):
    etiqueta = "Socio '" + str(fila["numero"]) + "'"
    _probar(problemas, etiqueta, validar_entero, fila["numero"], "numero de socio", 1)
    _probar(problemas, etiqueta, validar_texto, fila["nombre"], "nombre del socio")
    _probar(problemas, etiqueta, validar_email, fila["email"], "email del socio")
    _probar(problemas, etiqueta, validar_telefono, fila["telefono"], "telefono del socio")
    if fila["habilitado"] not in (0, 1):
        _agregar(problemas, etiqueta, "el campo habilitado debe ser 0 o 1")


def _revisar_libro(fila, problemas):
    etiqueta = "Libro '" + str(fila["isbn"]) + "'"
    _probar(problemas, etiqueta, validar_codigo, fila["isbn"], "ISBN")
    _probar(problemas, etiqueta, validar_texto, fila["titulo"], "titulo del libro")
    _probar(problemas, etiqueta, validar_texto, fila["autor"], "autor del libro")
    _probar(problemas, etiqueta, validar_anio, fila["anio"], "anio del libro")
    _probar(problemas, etiqueta, validar_texto, fila["genero"], "genero del libro")


def _revisar_ejemplar(fila, codigos_sede, isbns, numeros_solicitud, reservas_por_numero, problemas):
    etiqueta = "Ejemplar '" + str(fila["codigo"]) + "'"
    _probar(problemas, etiqueta, validar_codigo, fila["codigo"], "codigo de ejemplar")
    if fila["libro_isbn"] not in isbns:
        _agregar(problemas, etiqueta, "el libro no existe")
    if fila["sede_pertenencia"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de pertenencia no existe")
    if fila["ubicacion_actual"] is not None and fila["ubicacion_actual"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la ubicacion actual no existe")
    if fila["estado_disponibilidad"] not in Ejemplar.ESTADOS_DISPONIBILIDAD:
        _agregar(problemas, etiqueta, "estado de disponibilidad desconocido")
    _probar(problemas, etiqueta, validar_estado_fisico, fila["estado_fisico"])
    if fila["solicitud_asignada"] is not None:
        if fila["solicitud_asignada"] not in numeros_solicitud:
            _agregar(problemas, etiqueta, "la solicitud asignada no existe")
    if fila["reserva_asignada"] is not None:
        if fila["reserva_asignada"] not in reservas_por_numero:
            _agregar(problemas, etiqueta, "la reserva asignada no existe")
    if fila["solicitud_asignada"] is not None and fila["reserva_asignada"] is not None:
        reserva = reservas_por_numero.get(fila["reserva_asignada"])
        if reserva is None or reserva["solicitud_numero"] != fila["solicitud_asignada"]:
            _agregar(
                problemas,
                etiqueta,
                "tiene una solicitud y una reserva asignadas que no estan vinculadas",
            )
    if fila["estado_disponibilidad"] == Ejemplar.DISPONIBLE:
        if fila["solicitud_asignada"] is not None or fila["reserva_asignada"] is not None:
            _agregar(problemas, etiqueta, "esta disponible pero conserva una asignacion")
    if fila["estado_disponibilidad"] == Ejemplar.EN_TRANSITO and fila["ubicacion_actual"] is not None:
        _agregar(problemas, etiqueta, "esta en transito pero tiene ubicacion fisica")
    if fila["estado_disponibilidad"] != Ejemplar.EN_TRANSITO and fila["ubicacion_actual"] is None:
        _agregar(problemas, etiqueta, "esta fuera de transito pero no tiene ubicacion fisica")
    if fila["estado_disponibilidad"] == Ejemplar.DISPONIBLE:
        if fila["estado_fisico"] == Ejemplar.FISICO_REPARACION or fila["ubicacion_actual"] != fila["sede_pertenencia"]:
            _agregar(problemas, etiqueta, "esta disponible pero necesita reparacion o retorno")


def _revisar_solicitud(fila, numeros_socio, isbns, codigos_ejemplar, codigos_sede, problemas):
    etiqueta = "Solicitud '" + str(fila["numero"]) + "'"
    _probar(problemas, etiqueta, validar_entero, fila["numero"], "numero de solicitud", 1)
    if fila["socio_numero"] not in numeros_socio:
        _agregar(problemas, etiqueta, "el socio no existe")
    if fila["libro_isbn"] not in isbns:
        _agregar(problemas, etiqueta, "el libro no existe")
    if fila["ejemplar_codigo"] not in codigos_ejemplar:
        _agregar(problemas, etiqueta, "el ejemplar no existe")
    if fila["sede_origen"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de origen no existe")
    if fila["sede_destino"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de destino no existe")
    if fila["estado"] not in (
        SolicitudPrestamo.ESTADO_PENDIENTE,
        SolicitudPrestamo.ESTADO_ENTREGADA,
        SolicitudPrestamo.ESTADO_CANCELADA,
    ):
        _agregar(problemas, etiqueta, "estado desconocido")
    _probar(problemas, etiqueta, validar_tipo_solicitud, fila["tipo"])
    if (fila["tipo"] == SolicitudPrestamo.TIPO_LOCAL) != (fila["sede_origen"] == fila["sede_destino"]):
        _agregar(problemas, etiqueta, "el tipo no coincide con las sedes")
    _probar(problemas, etiqueta, _fecha, fila["fecha_solicitud"])


def _revisar_prestamo(fila, numeros_solicitud, numeros_socio, codigos_ejemplar, codigos_sede, problemas):
    etiqueta = "Prestamo '" + str(fila["numero"]) + "'"
    _probar(problemas, etiqueta, validar_entero, fila["numero"], "numero de prestamo", 1)
    if fila["solicitud_numero"] not in numeros_solicitud:
        _agregar(problemas, etiqueta, "la solicitud no existe")
    if fila["socio_numero"] not in numeros_socio:
        _agregar(problemas, etiqueta, "el socio no existe")
    if fila["ejemplar_codigo"] not in codigos_ejemplar:
        _agregar(problemas, etiqueta, "el ejemplar no existe")
    if fila["sede_origen"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de origen no existe")
    if fila["sede_destino"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de destino no existe")
    if fila["estado"] not in (Prestamo.ESTADO_ACTIVO, Prestamo.ESTADO_DEVUELTO):
        _agregar(problemas, etiqueta, "estado desconocido")
    _probar(problemas, etiqueta, _fecha, fila["fecha_prestamo"])
    _probar(problemas, etiqueta, _fecha, fila["fecha_vencimiento"])
    if fila["fecha_devolucion"] is not None:
        _probar(problemas, etiqueta, _fecha, fila["fecha_devolucion"])
    try:
        inicio = _fecha(fila["fecha_prestamo"])
        if _fecha(fila["fecha_vencimiento"]) < inicio:
            _agregar(problemas, etiqueta, "el vencimiento es anterior al prestamo")
        if fila["fecha_devolucion"] is not None and _fecha(fila["fecha_devolucion"]) < inicio:
            _agregar(problemas, etiqueta, "la devolucion es anterior al prestamo")
    except (ValueError, TypeError):
        pass  # Las fechas invalidas ya se informaron individualmente.
    if fila["estado"] == Prestamo.ESTADO_DEVUELTO:
        if (fila["fecha_devolucion"] is None or fila["sede_devolucion"] is None or
                fila["estado_fisico_devolucion"] is None):
            _agregar(problemas, etiqueta, "faltan datos de devolucion")
    elif fila["estado"] == Prestamo.ESTADO_ACTIVO:
        if (fila["fecha_devolucion"] is not None or fila["sede_devolucion"] is not None or
                fila["estado_fisico_devolucion"] is not None or fila["multa"] != 0):
            _agregar(problemas, etiqueta, "esta activo pero conserva datos de devolucion")
    try:
        multa = float(fila["multa"])
        if not math.isfinite(multa) or multa < 0:
            raise ValueError("la multa debe ser finita y no negativa")
    except (TypeError, ValueError) as error:
        _agregar(problemas, etiqueta, str(error))
    if fila["sede_devolucion"] is not None and fila["sede_devolucion"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de devolucion no existe")
    if fila["estado_fisico_devolucion"] is not None:
        _probar(problemas, etiqueta, validar_estado_fisico, fila["estado_fisico_devolucion"])


def _revisar_reserva(fila, numeros_socio, isbns, codigos_sede, codigos_ejemplar, numeros_solicitud, problemas):
    etiqueta = "Reserva '" + str(fila["numero"]) + "'"
    _probar(problemas, etiqueta, validar_entero, fila["numero"], "numero de reserva", 1)
    if fila["estado"] in (Reserva.ESTADO_ASIGNADA, Reserva.ESTADO_CUMPLIDA) and fila["ejemplar_codigo"] is None:
        _agregar(problemas, etiqueta, "la reserva atendida no tiene ejemplar")
    if fila["estado"] == Reserva.ESTADO_CUMPLIDA and fila["solicitud_numero"] is None:
        _agregar(problemas, etiqueta, "la reserva cumplida no tiene solicitud")
    if fila["socio_numero"] not in numeros_socio:
        _agregar(problemas, etiqueta, "el socio no existe")
    if fila["libro_isbn"] not in isbns:
        _agregar(problemas, etiqueta, "el libro no existe")
    if fila["codigo_sede"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede no existe")
    if fila["ejemplar_codigo"] is not None and fila["ejemplar_codigo"] not in codigos_ejemplar:
        _agregar(problemas, etiqueta, "el ejemplar no existe")
    if fila["solicitud_numero"] is not None and fila["solicitud_numero"] not in numeros_solicitud:
        _agregar(problemas, etiqueta, "la solicitud no existe")
    if fila["estado"] not in (
        Reserva.ESTADO_PENDIENTE,
        Reserva.ESTADO_ASIGNADA,
        Reserva.ESTADO_CUMPLIDA,
        Reserva.ESTADO_CANCELADA,
    ):
        _agregar(problemas, etiqueta, "estado desconocido")
    _probar(problemas, etiqueta, _fecha, fila["fecha_reserva"])


def _revisar_remito(fila, codigos_sede, problemas):
    etiqueta = "Remito '" + str(fila["codigo"]) + "'"
    _probar(problemas, etiqueta, validar_codigo, fila["codigo"], "codigo de remito")
    if fila["sede_origen"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de origen no existe")
    if fila["sede_destino"] not in codigos_sede:
        _agregar(problemas, etiqueta, "la sede de destino no existe")
    if fila["sede_origen"] == fila["sede_destino"]:
        _agregar(problemas, etiqueta, "origen y destino son iguales")
    if fila["motivo"] not in (Remito.MOTIVO_PRESTAMO, Remito.MOTIVO_RETORNO):
        _agregar(problemas, etiqueta, "motivo desconocido")
    if fila["estado_actual"] not in (
        Remito.ESTADO_PENDIENTE_EMPAQUE,
        Remito.ESTADO_EMPAQUETADO,
        Remito.ESTADO_DESPACHADO,
        Remito.ESTADO_RECIBIDO,
        Remito.ESTADO_CANCELADO,
    ):
        _agregar(problemas, etiqueta, "estado desconocido")
    _probar(problemas, etiqueta, _momento, fila["fecha_creacion"])


def _revisar_remito_ejemplar(fila, codigos_remito, codigos_ejemplar, numeros_solicitud, problemas):
    etiqueta = "Remito '" + str(fila["remito_codigo"]) + "', ejemplar '" + str(fila["ejemplar_codigo"]) + "'"
    if fila["remito_codigo"] not in codigos_remito:
        _agregar(problemas, etiqueta, "el remito no existe")
    if fila["ejemplar_codigo"] not in codigos_ejemplar:
        _agregar(problemas, etiqueta, "el ejemplar no existe")
    if fila["numero_solicitud"] is not None and fila["numero_solicitud"] not in numeros_solicitud:
        _agregar(problemas, etiqueta, "la solicitud no existe")
    if "estado_fisico_recepcion" in fila.keys():
        valor = fila["estado_fisico_recepcion"]
        if valor is not None:
            _probar(problemas, etiqueta, validar_estado_fisico, valor)


def _revisar_historial(historial, remitos, problemas):
    por_remito = {}
    for fila in historial:
        codigo = fila["remito_codigo"]
        if codigo not in por_remito:
            por_remito[codigo] = []
        por_remito[codigo].append(fila)
    for remito in remitos:
        codigo = remito["codigo"]
        registros = por_remito.get(codigo, [])
        etiqueta = "Remito '" + str(codigo) + "'"
        try:
            eventos = []
            for fila in registros:
                orden = validar_entero(fila["orden"], "orden del historial", 0)
                eventos.append((orden, fila["nombre_estado"], _momento(fila["momento"])))
            eventos.sort()
            validar_historial_remito(_momento(remito["fecha_creacion"]), remito["estado_actual"], eventos)
        except (ValueError, TypeError) as error:
            _agregar(problemas, etiqueta, str(error))
    codigos = _conjunto(remitos, "codigo")
    for fila in historial:
        if fila["remito_codigo"] not in codigos:
            _agregar(problemas, "Historial", "el remito no existe")


def _revisar_relaciones(solicitudes, prestamos, ejemplares, reservas, problemas):
    por_codigo = {}
    por_numero = {}
    for ejemplar in ejemplares:
        por_codigo[ejemplar["codigo"]] = ejemplar
    for solicitud in solicitudes:
        por_numero[solicitud["numero"]] = solicitud
        ejemplar = por_codigo.get(solicitud["ejemplar_codigo"])
        if ejemplar is not None:
            if (ejemplar["libro_isbn"] != solicitud["libro_isbn"] or
                    ejemplar["sede_pertenencia"] != solicitud["sede_origen"]):
                _agregar(problemas, "Solicitud '" + str(solicitud["numero"]) + "'", "el libro u origen no corresponde al ejemplar")
    for prestamo in prestamos:
        solicitud = por_numero.get(prestamo["solicitud_numero"])
        etiqueta = "Prestamo '" + str(prestamo["numero"]) + "'"
        if solicitud is not None:
            for campo in ("socio_numero", "ejemplar_codigo", "sede_origen", "sede_destino"):
                if prestamo[campo] != solicitud[campo]:
                    _agregar(problemas, etiqueta, "no coincide con su solicitud: " + campo)
            if solicitud["estado"] != SolicitudPrestamo.ESTADO_ENTREGADA:
                _agregar(problemas, etiqueta, "su solicitud no esta entregada")
        for otro in prestamos:
            if otro["numero"] <= prestamo["numero"] or otro["ejemplar_codigo"] != prestamo["ejemplar_codigo"]:
                continue
            try:
                inicio = _fecha(prestamo["fecha_prestamo"])
                otro_inicio = _fecha(otro["fecha_prestamo"])
                fin = datetime.date.max
                if prestamo["fecha_devolucion"] is not None:
                    fin = _fecha(prestamo["fecha_devolucion"])
                otro_fin = datetime.date.max
                if otro["fecha_devolucion"] is not None:
                    otro_fin = _fecha(otro["fecha_devolucion"])
                if inicio < otro_fin and otro_inicio < fin:
                    _agregar(problemas, etiqueta, "se superpone con el prestamo " + str(otro["numero"]))
            except (ValueError, TypeError):
                pass
    for ejemplar in ejemplares:
        numero = ejemplar["solicitud_asignada"]
        solicitud = por_numero.get(numero)
        if solicitud is not None:
            if (solicitud["ejemplar_codigo"] != ejemplar["codigo"] or
                    solicitud["estado"] != SolicitudPrestamo.ESTADO_PENDIENTE):
                _agregar(problemas, "Ejemplar '" + str(ejemplar["codigo"]) + "'", "la solicitud asignada no corresponde o no esta pendiente")
    for reserva in reservas:
        if reserva["estado"] != Reserva.ESTADO_ASIGNADA:
            continue
        ejemplar = por_codigo.get(reserva["ejemplar_codigo"])
        if ejemplar is not None and (
                ejemplar["reserva_asignada"] != reserva["numero"] or
                ejemplar["libro_isbn"] != reserva["libro_isbn"] or
                ejemplar["sede_pertenencia"] != reserva["codigo_sede"]):
            _agregar(problemas, "Reserva '" + str(reserva["numero"]) + "'", "el ejemplar asignado no corresponde a la reserva")


def _revisar_configuracion(filas, problemas):
    for fila in filas:
        clave = fila["clave"]
        valor = fila["valor"]
        if clave == "plazo_dias":
            _probar(problemas, "Configuracion 'plazo_dias'", validar_entero, valor, "plazo_dias", 1)
        elif clave == "multa_por_dia":
            try:
                monto = float(valor)
                if math.isfinite(monto) == False:
                    raise ValueError("debe ser un numero finito")
                if monto < 0:
                    raise ValueError("no puede ser negativa")
            except (TypeError, ValueError) as error:
                _agregar(problemas, "Configuracion 'multa_por_dia'", str(error))


def _revisar_duplicados(valores, descripcion, problemas):
    vistos = []
    for valor in valores:
        if valor in vistos:
            mensaje = "Hay mas de un registro con el mismo " + descripcion + ": " + str(valor)
            if mensaje not in problemas:
                problemas.append(mensaje)
        else:
            vistos.append(valor)
