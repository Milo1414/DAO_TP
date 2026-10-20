# Pruebas de los cuatro reportes sobre datos reales de la API.
import unittest

from tests.apoyo import PruebaBase


class PruebaReportes(PruebaBase):
    def preparar_movimiento(self):
        self.crear_sede("S1")
        self.crear_sede("S2")
        self.crear_socio(1)
        self.crear_socio(2)
        self.crear_libro("L1", "Libro uno")
        self.crear_libro("L2", "Libro dos")
        self.crear_ejemplar("E1", "L1", "S1")
        self.crear_ejemplar("E2", "L1", "S1")
        self.crear_ejemplar("E3", "L2", "S2")

        respuesta = self.pedir("POST", "/api/solicitudes", {
            "socio_numero": 2,
            "libro_isbn": "L1",
            "ejemplar_codigo": "E1",
            "sede_origen": "S1",
            "sede_destino": "S2",
            "fecha_solicitud": "2026-01-10",
            "tipo": "interbibliotecario",
        })
        self.assertEqual(respuesta.status_code, 201)
        remito_uno = self.crear_remito(1)
        self.mover_remito(remito_uno["codigo"])
        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-12",
        })
        self.assertEqual(respuesta.status_code, 201)
        self.numero_prestamo = respuesta.get_json()["datos"]["prestamo"]["numero"]

        respuesta = self.pedir("POST", "/api/solicitudes", {
            "socio_numero": 1,
            "libro_isbn": "L2",
            "ejemplar_codigo": "E3",
            "sede_origen": "S2",
            "sede_destino": "S1",
            "fecha_solicitud": "2026-01-15",
            "tipo": "interbibliotecario",
        })
        self.assertEqual(respuesta.status_code, 201)
        self.crear_remito(2, "2026-01-15T10:00:00")

    def test_activos_y_vencidos(self):
        self.preparar_movimiento()
        respuesta = self.pedir("GET", "/api/reportes/activos-vencidos?fecha_referencia=2026-01-30")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()["datos"]
        self.assertEqual(datos["reporte"], "Prestamos activos y vencidos por sede")
        fila = None
        for candidata in datos["filas"]:
            if candidata["sede"] == "S2":
                fila = candidata
        self.assertIsNotNone(fila)
        self.assertEqual(fila["activos"], 1)
        self.assertEqual(fila["vencidos"], 1)
        self.assertEqual(fila["promedio_dias_atraso"], 4)
        self.assertEqual(fila["multa_total"], 400)

    def test_disponibilidad_no_duplica_copias(self):
        self.preparar_movimiento()
        respuesta = self.pedir("GET", "/api/reportes/disponibilidad?sede=S1&isbn=L1")
        self.assertEqual(respuesta.status_code, 200)
        filas = respuesta.get_json()["datos"]["filas"]
        self.assertEqual(len(filas), 1)
        fila = filas[0]
        self.assertEqual(fila["total"], 1)
        self.assertEqual(fila["disponibles"], 1)
        self.assertEqual(fila["prestados"], 0)
        self.assertEqual(fila["en_transito"], 0)

        respuesta = self.pedir("GET", "/api/reportes/disponibilidad?sede=S2&isbn=L1")
        filas = respuesta.get_json()["datos"]["filas"]
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["total"], 1)
        self.assertEqual(filas[0]["prestados"], 1)

    def test_libros_solicitados_filtra_y_ordena(self):
        self.preparar_movimiento()
        respuesta = self.pedir(
            "GET",
            "/api/reportes/libros-solicitados?sede_origen=S1&sede_destino=S2",
        )
        self.assertEqual(respuesta.status_code, 200)
        filas = respuesta.get_json()["datos"]["filas"]
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["isbn"], "L1")
        self.assertEqual(filas[0]["cantidad"], 1)

        respuesta = self.pedir(
            "GET",
            "/api/reportes/libros-solicitados?desde=2026-01-14&hasta=2026-01-16",
        )
        filas = respuesta.get_json()["datos"]["filas"]
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["isbn"], "L2")

    def test_movimiento_y_tiempos(self):
        self.preparar_movimiento()
        respuesta = self.pedir("GET", "/api/reportes/movimiento")
        self.assertEqual(respuesta.status_code, 200)
        filas = respuesta.get_json()["datos"]["filas"]
        self.assertEqual(len(filas), 2)
        recibido = None
        pendiente = None
        for fila in filas:
            if fila["origen"] == "S1" and fila["destino"] == "S2":
                recibido = fila
            if fila["origen"] == "S2" and fila["destino"] == "S1":
                pendiente = fila
        self.assertIsNotNone(recibido)
        self.assertEqual(recibido["recibidos"], 1)
        self.assertEqual(recibido["pendientes"], 0)
        self.assertEqual(recibido["copias_danadas_recepcion"], 0)
        self.assertEqual(recibido["promedio_horas_transito"], 1)
        self.assertEqual(recibido["promedio_horas_total"], 3)
        self.assertIsNotNone(pendiente)
        self.assertEqual(pendiente["pendientes"], 1)

    def test_filtros_invalidos(self):
        self.preparar_movimiento()
        respuesta = self.pedir("GET", "/api/reportes/activos-vencidos?fecha_referencia=no-es-fecha")
        self.assertEqual(respuesta.status_code, 400)
        respuesta = self.pedir("GET", "/api/reportes/libros-solicitados?desde=2026-02-01&hasta=2026-01-01")
        self.assertEqual(respuesta.status_code, 400)


if __name__ == "__main__":
    unittest.main()
