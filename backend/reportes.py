# Reportes con patron Factory Method.
#
# FabricaReportes define el contrato de creacion. Cada fabrica concreta
# instancia un reporte distinto. La API y la web usan las fabricas y luego
# ejecutan generar() de forma polimorfica.
import datetime

from abc import ABC, abstractmethod


class Reporte(ABC):
    @abstractmethod
    def nombre(self):
        pass

    @abstractmethod
    def generar(self, red, parametros):
        pass


class ReporteActivosVencidos(Reporte):
    # Cantidad de prestamos activos y vencidos por sede de destino, con la
    # proporcion de vencidos, el atraso promedio y la multa acumulada.
    def nombre(self):
        return "Prestamos activos y vencidos por sede"

    def generar(self, red, parametros):
        fecha = parametros.get("fecha_referencia")
        if fecha is None:
            fecha = datetime.date.today()
        filas = []
        for sede in red.sedes:
            cantidad_activos = 0
            cantidad_vencidos = 0
            suma_atraso = 0
            multa_total = 0
            for prestamo in red.prestamos:
                if prestamo.esta_activo() == False:
                    continue
                if prestamo.sede_destino != sede.codigo:
                    continue
                cantidad_activos = cantidad_activos + 1
                if prestamo.esta_vencido(fecha):
                    cantidad_vencidos = cantidad_vencidos + 1
                    dias = prestamo.dias_atraso(fecha)
                    suma_atraso = suma_atraso + dias
                    multa_total = multa_total + prestamo.multa_acumulada(fecha, red.multa_por_dia)
            proporcion = 0
            promedio_atraso = 0
            if cantidad_activos > 0:
                proporcion = cantidad_vencidos / cantidad_activos
            if cantidad_vencidos > 0:
                promedio_atraso = suma_atraso / cantidad_vencidos
            fila = {}
            fila["sede"] = sede.codigo
            fila["sede_nombre"] = sede.nombre
            fila["activos"] = cantidad_activos
            fila["vencidos"] = cantidad_vencidos
            fila["proporcion_vencidos"] = round(proporcion, 2)
            fila["promedio_dias_atraso"] = round(promedio_atraso, 2)
            fila["multa_total"] = multa_total
            filas.append(fila)
        return filas


class ReporteDisponibilidad(Reporte):
    # Inventario por sede fisica y libro. Cada copia se cuenta una sola vez.
    # Una copia en transito no esta en ninguna sede: se atribuye al origen de
    # su remito activo. Una copia sin ubicacion ni remito activo se atribuye
    # a su sede de pertenencia para no perderla del inventario.
    def nombre(self):
        return "Disponibilidad del catalogo por sede y libro"

    def generar(self, red, parametros):
        filtro_sede = parametros.get("sede")
        filtro_isbn = parametros.get("isbn")
        filas = []
        for sede in red.sedes:
            if filtro_sede is not None and sede.codigo != filtro_sede:
                continue
            for libro in red.libros:
                if filtro_isbn is not None and libro.isbn != filtro_isbn:
                    continue
                total = 0
                disponibles = 0
                prestados = 0
                en_transito = 0
                en_reparacion = 0
                apartados = 0
                pendientes_retorno = 0
                for ejemplar in red.ejemplares:
                    if ejemplar.libro_isbn != libro.isbn:
                        continue
                    sede_efectiva = ejemplar.ubicacion_actual
                    if sede_efectiva is None:
                        activo = red.remito_activo_por_ejemplar(ejemplar.codigo)
                        if activo is not None:
                            sede_efectiva = activo.sede_origen
                        else:
                            sede_efectiva = ejemplar.sede_pertenencia
                    if sede_efectiva != sede.codigo:
                        continue
                    total = total + 1
                    if ejemplar.ubicacion_actual is None:
                        en_transito = en_transito + 1
                    elif ejemplar.estado_disponibilidad == "disponible":
                        disponibles = disponibles + 1
                    elif ejemplar.estado_disponibilidad == "prestado":
                        prestados = prestados + 1
                    elif ejemplar.estado_disponibilidad == "en_transito":
                        en_transito = en_transito + 1
                    elif ejemplar.estado_disponibilidad == "en_reparacion":
                        en_reparacion = en_reparacion + 1
                    elif ejemplar.estado_disponibilidad == "apartado":
                        apartados = apartados + 1
                    elif ejemplar.estado_disponibilidad == "pendiente_retorno":
                        pendientes_retorno = pendientes_retorno + 1
                reservas = 0
                for reserva in red.reservas:
                    if reserva.libro_isbn != libro.isbn:
                        continue
                    if reserva.codigo_sede != sede.codigo:
                        continue
                    if reserva.esta_activa() == False:
                        continue
                    reservas = reservas + 1
                if total == 0 and reservas == 0:
                    continue
                fila = {}
                fila["sede"] = sede.codigo
                fila["isbn"] = libro.isbn
                fila["titulo"] = libro.titulo
                fila["total"] = total
                fila["disponibles"] = disponibles
                fila["prestados"] = prestados
                fila["en_transito"] = en_transito
                fila["en_reparacion"] = en_reparacion
                fila["apartados"] = apartados
                fila["pendientes_retorno"] = pendientes_retorno
                fila["reservas_activas"] = reservas
                filas.append(fila)
        return filas


class ReporteLibrosSolicitados(Reporte):
    # Ranking de libros con solicitudes interbibliotecarias. Filtra por
    # periodo y, opcionalmente, por sede de origen o destino.
    def nombre(self):
        return "Libros mas solicitados entre sedes"

    def generar(self, red, parametros):
        fecha_desde = parametros.get("fecha_desde")
        fecha_hasta = parametros.get("fecha_hasta")
        sede_origen = parametros.get("sede_origen")
        sede_destino = parametros.get("sede_destino")
        conteo = {}
        for solicitud in red.solicitudes:
            if solicitud.es_interbibliotecaria() == False:
                continue
            if fecha_desde is not None and solicitud.fecha_solicitud < fecha_desde:
                continue
            if fecha_hasta is not None and solicitud.fecha_solicitud > fecha_hasta:
                continue
            if sede_origen is not None and solicitud.sede_origen != sede_origen:
                continue
            if sede_destino is not None and solicitud.sede_destino != sede_destino:
                continue
            if solicitud.libro_isbn in conteo:
                conteo[solicitud.libro_isbn] = conteo[solicitud.libro_isbn] + 1
            else:
                conteo[solicitud.libro_isbn] = 1
        filas = []
        for isbn in conteo:
            libro = red.buscar_libro(isbn)
            titulo = isbn
            if libro is not None:
                titulo = libro.titulo
            fila = {}
            fila["isbn"] = isbn
            fila["titulo"] = titulo
            fila["cantidad"] = conteo[isbn]
            filas.append(fila)
        # Orden descendente por cantidad y, ante empate, por ISBN.
        ordenadas = []
        pendientes = list(filas)
        while len(pendientes) > 0:
            mayor = pendientes[0]
            for candidata in pendientes:
                if candidata["cantidad"] > mayor["cantidad"]:
                    mayor = candidata
                elif candidata["cantidad"] == mayor["cantidad"] and candidata["isbn"] < mayor["isbn"]:
                    mayor = candidata
            ordenadas.append(mayor)
            pendientes.remove(mayor)
        return ordenadas


class ReporteMovimientoEnvios(Reporte):
    # Movimientos agrupados por sede origen y destino. Distingue remitos de
    # prestamo y de retorno, pendientes y recibidos. Calcula el tiempo de
    # transito (recepcion - despacho) y el tiempo total (recepcion -
    # creacion) en horas y dias sin truncar. La incidencia de danio usa el
    # estado fisico registrado al recibir, no el estado actual de la copia.
    def nombre(self):
        return "Movimiento y tiempo de envio entre sedes"

    def generar(self, red, parametros):
        grupos = {}
        for remito in red.remitos:
            clave = remito.sede_origen + "->" + remito.sede_destino
            if clave not in grupos:
                grupo = {}
                grupo["origen"] = remito.sede_origen
                grupo["destino"] = remito.sede_destino
                grupo["remitos"] = []
                grupos[clave] = grupo
            grupos[clave]["remitos"].append(remito)

        filas = []
        for clave in grupos:
            grupo = grupos[clave]
            lista = grupo["remitos"]
            total = 0
            pendientes = 0
            recibidos = 0
            prestamos = 0
            retornos = 0
            copias_danadas_recepcion = 0
            suma_horas_transito = 0
            suma_horas_total = 0
            cantidad_con_duracion = 0
            for remito in lista:
                total = total + 1
                if remito.es_retorno():
                    retornos = retornos + 1
                else:
                    prestamos = prestamos + 1
                if remito.nombre_estado() == "recibido":
                    recibidos = recibidos + 1
                    creacion = remito.fecha_de("pendiente_empaque")
                    despacho = remito.fecha_de("despachado")
                    recepcion = remito.fecha_de("recibido")
                    if creacion is not None and despacho is not None and recepcion is not None:
                        horas_transito = (recepcion - despacho).total_seconds() / 3600
                        horas_total = (recepcion - creacion).total_seconds() / 3600
                        suma_horas_transito = suma_horas_transito + horas_transito
                        suma_horas_total = suma_horas_total + horas_total
                        cantidad_con_duracion = cantidad_con_duracion + 1
                    for asignacion in remito.asignaciones:
                        if asignacion.estado_fisico_recepcion == "requiere_reparacion":
                            copias_danadas_recepcion = copias_danadas_recepcion + 1
                else:
                    pendientes = pendientes + 1
            promedio_horas_transito = 0
            promedio_horas_total = 0
            if cantidad_con_duracion > 0:
                promedio_horas_transito = suma_horas_transito / cantidad_con_duracion
                promedio_horas_total = suma_horas_total / cantidad_con_duracion
            promedio_dias_transito = promedio_horas_transito / 24
            promedio_dias_total = promedio_horas_total / 24
            tasa_exito = 0
            if total > 0:
                tasa_exito = recibidos / total
            fila = {}
            fila["origen"] = grupo["origen"]
            fila["destino"] = grupo["destino"]
            fila["total"] = total
            fila["prestamos"] = prestamos
            fila["retornos"] = retornos
            fila["recibidos"] = recibidos
            fila["pendientes"] = pendientes
            fila["copias_danadas_recepcion"] = copias_danadas_recepcion
            fila["tasa_exito"] = round(tasa_exito, 2)
            fila["promedio_horas_transito"] = round(promedio_horas_transito, 2)
            fila["promedio_dias_transito"] = round(promedio_dias_transito, 2)
            fila["promedio_horas_total"] = round(promedio_horas_total, 2)
            fila["promedio_dias_total"] = round(promedio_dias_total, 2)
            filas.append(fila)

        # Orden por origen y destino para que el resultado sea estable.
        ordenadas = []
        pendientes = list(filas)
        while len(pendientes) > 0:
            menor = pendientes[0]
            for candidata in pendientes:
                if candidata["origen"] < menor["origen"]:
                    menor = candidata
                elif candidata["origen"] == menor["origen"] and candidata["destino"] < menor["destino"]:
                    menor = candidata
            ordenadas.append(menor)
            pendientes.remove(menor)
        return ordenadas


class FabricaReportes(ABC):
    @abstractmethod
    def crear_reporte(self):
        pass


class FabricaReporteActivosVencidos(FabricaReportes):
    def crear_reporte(self):
        return ReporteActivosVencidos()


class FabricaReporteDisponibilidad(FabricaReportes):
    def crear_reporte(self):
        return ReporteDisponibilidad()


class FabricaReporteLibrosSolicitados(FabricaReportes):
    def crear_reporte(self):
        return ReporteLibrosSolicitados()


class FabricaReporteMovimientoEnvios(FabricaReportes):
    def crear_reporte(self):
        return ReporteMovimientoEnvios()
