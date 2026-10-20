# Pruebas de la API HTTP y de las operaciones principales.
import unittest

from backend.catalogo import Ejemplar
from backend.prestamos import Reserva, SolicitudPrestamo
from tests.apoyo import PruebaBase


class PruebaApiBasica(PruebaBase):
    def test_salud_y_resumen_inicial(self):
        respuesta = self.pedir("GET", "/api/salud")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()["datos"]
        self.assertEqual(datos["estado"], "ok")
        self.assertEqual(datos["problemas_datos"], [])

        respuesta = self.pedir("GET", "/api/resumen")
        self.assertEqual(respuesta.status_code, 200)
        resumen = respuesta.get_json()["datos"]
        self.assertEqual(resumen["sedes"], 0)
        self.assertEqual(resumen["socios"], 0)
        self.assertEqual(resumen["prestamos_activos"], 0)

    def test_ruta_inexistente_devuelve_json(self):
        respuesta = self.pedir("GET", "/api/no-existe")
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("error", respuesta.get_json())

    def test_crud_de_sede(self):
        self.crear_sede("S1")
        respuesta = self.pedir("GET", "/api/sedes/S1")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.get_json()["datos"]["activa"])

        respuesta = self.pedir("PUT", "/api/sedes/S1", {
            "nombre": "Sede modificada",
            "direccion": "Otra calle 123",
            "telefono": "555-9876",
            "horario": "09:00-17:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["datos"]["nombre"], "Sede modificada")

        respuesta = self.pedir("POST", "/api/sedes/S1/baja", {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.get_json()["datos"]["activa"])
        respuesta = self.pedir("POST", "/api/sedes/S1/baja", {})
        self.assertEqual(respuesta.status_code, 409)

        respuesta = self.pedir("POST", "/api/sedes/S1/reactivacion", {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.get_json()["datos"]["activa"])

    def test_validaciones_de_sede(self):
        respuesta = self.pedir("POST", "/api/sedes", {
            "codigo": "S1",
            "nombre": "Sede",
            "direccion": "Calle",
            "telefono": "1234a",
            "horario": "08:00-18:00",
        })
        self.assertEqual(respuesta.status_code, 400)

        respuesta = self.pedir("POST", "/api/sedes", {
            "codigo": "S1",
            "nombre": "Sede",
            "direccion": "Calle",
            "telefono": "555-1234",
            "horario": "25:00-26:00",
        })
        self.assertEqual(respuesta.status_code, 400)

    def test_crud_de_socio(self):
        self.crear_sede("S1")
        self.crear_socio(1)
        respuesta = self.pedir("POST", "/api/socios", {
            "numero": 1,
            "nombre": "Otro",
            "email": "otro@mail.com",
            "telefono": "555-2222",
        })
        self.assertEqual(respuesta.status_code, 409)

        respuesta = self.pedir("POST", "/api/socios", {
            "numero": 2,
            "nombre": "Otro",
            "email": "socio1@mail.com",
            "telefono": "555-2222",
        })
        self.assertEqual(respuesta.status_code, 409)

        respuesta = self.pedir("POST", "/api/socios/1/inhabilitar", {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.get_json()["datos"]["habilitado"])
        respuesta = self.pedir("POST", "/api/socios/1/inhabilitar", {})
        self.assertEqual(respuesta.status_code, 409)
        respuesta = self.pedir("POST", "/api/socios/1/habilitar", {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.get_json()["datos"]["habilitado"])

    def test_catalogo_y_ejemplares(self):
        self.crear_sede("S1")
        self.crear_libro()
        self.crear_ejemplar("E1")
        respuesta = self.pedir("POST", "/api/ejemplares", {
            "codigo": "E1",
            "libro_isbn": "L1",
            "sede_pertenencia": "S1",
        })
        self.assertEqual(respuesta.status_code, 409)

        respuesta = self.pedir("POST", "/api/ejemplares", {
            "codigo": "E2",
            "libro_isbn": "NOEXISTE",
            "sede_pertenencia": "S1",
        })
        self.assertEqual(respuesta.status_code, 404)

        respuesta = self.pedir("GET", "/api/ejemplares?isbn=L1&sede=S1")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.get_json()["datos"]), 1)

        respuesta = self.pedir("POST", "/api/libros", {
            "isbn": "L2",
            "titulo": "Libro futuro",
            "autor": "Autor",
            "anio": 3000,
            "genero": "Genero",
        })
        self.assertEqual(respuesta.status_code, 400)


class PruebaPrestamos(PruebaBase):
    def test_prestamo_local_y_devolucion(self):
        self.datos_basicos()
        solicitud = self.solicitud_local()
        self.assertEqual(solicitud["estado"], "pendiente")

        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-10",
        })
        self.assertEqual(respuesta.status_code, 201)
        prestamo = respuesta.get_json()["datos"]["prestamo"]
        self.assertEqual(prestamo["estado"], "activo")
        self.assertEqual(prestamo["fecha_vencimiento"], "2026-01-24")

        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-10",
        })
        self.assertEqual(respuesta.status_code, 409)

        devolucion = self.devolver(1)
        self.assertEqual(devolucion["estado"], "devuelto")
        self.assertEqual(devolucion["multa"], 0)

        respuesta = self.pedir("GET", "/api/ejemplares/E1")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["datos"]["estado_disponibilidad"], "disponible")

    def test_multa_por_atraso(self):
        self.datos_basicos()
        self.solicitud_local()
        self.entregar_local(fecha="2026-01-10")
        devolucion = self.devolver(1, fecha="2026-01-30")
        self.assertEqual(devolucion["estado"], "devuelto")
        self.assertEqual(devolucion["multa"], 600)

    def test_no_se_presta_a_socio_inhabilitado(self):
        self.datos_basicos()
        self.solicitud_local()
        self.pedir("POST", "/api/socios/1/inhabilitar", {})
        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-10",
        })
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.red.buscar_solicitud(1).estado, SolicitudPrestamo.ESTADO_PENDIENTE)

    def test_rechazo_no_consume_identificadores(self):
        self.datos_basicos()
        respuesta = self.pedir("POST", "/api/solicitudes", {
            "socio_numero": 1,
            "libro_isbn": "L1",
            "ejemplar_codigo": "E1",
            "sede_origen": "S1",
            "sede_destino": "S1",
            "fecha_solicitud": "2026-01-10",
            "tipo": "interbibliotecario",
        })
        self.assertEqual(respuesta.status_code, 400)
        self.solicitud_local()
        self.assertEqual(self.red.buscar_solicitud(1).numero, 1)
        self.assertIsNone(self.red.buscar_solicitud(2))


class PruebaInterbibliotecaria(PruebaBase):
    def test_circuito_con_remito_y_retorno(self):
        self.datos_basicos(dos_sedes=True)
        solicitud = self.solicitud_interbibliotecaria()
        self.assertEqual(solicitud["tipo"], "interbibliotecario")

        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-12",
        })
        self.assertEqual(respuesta.status_code, 409)

        remito = self.crear_remito()
        self.assertEqual(remito["estado_actual"], "pendiente_empaque")
        self.assertEqual(len(remito["historial"]), 1)

        respuesta = self.pedir("GET", "/api/ejemplares/E2")
        self.assertEqual(respuesta.get_json()["datos"]["ubicacion_actual"], "S2")
        self.assertEqual(respuesta.get_json()["datos"]["estado_disponibilidad"], "apartado")

        respuesta = self.pedir("POST", "/api/remitos/" + remito["codigo"] + "/empaquetar", {
            "momento": "2026-01-10T11:00:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("POST", "/api/remitos/" + remito["codigo"] + "/despachar", {
            "momento": "2026-01-10T12:00:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("GET", "/api/ejemplares/E2")
        self.assertEqual(respuesta.get_json()["datos"]["ubicacion_actual"], None)
        self.assertEqual(respuesta.get_json()["datos"]["estado_disponibilidad"], "en_transito")

        respuesta = self.pedir("POST", "/api/remitos/" + remito["codigo"] + "/recibir", {
            "momento": "2026-01-10T13:00:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("GET", "/api/ejemplares/E2")
        datos = respuesta.get_json()["datos"]
        self.assertEqual(datos["ubicacion_actual"], "S1")
        self.assertEqual(datos["estado_disponibilidad"], "apartado")

        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-12",
        })
        self.assertEqual(respuesta.status_code, 201)
        prestamo_numero = respuesta.get_json()["datos"]["prestamo"]["numero"]

        respuesta = self.pedir("POST", "/api/prestamos/" + str(prestamo_numero) + "/devolucion", {
            "fecha_devolucion": "2026-01-20",
            "sede_devolucion": "S1",
            "estado_fisico": "requiere_reparacion",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("GET", "/api/ejemplares/E2")
        datos = respuesta.get_json()["datos"]
        self.assertEqual(datos["estado_disponibilidad"], "pendiente_retorno")
        self.assertEqual(datos["ubicacion_actual"], "S1")

        respuesta = self.pedir("POST", "/api/remitos/retorno", {
            "ejemplar_codigo": "E2",
            "fecha_creacion": "2026-01-21T09:00:00",
        })
        self.assertEqual(respuesta.status_code, 201)
        retorno = respuesta.get_json()["datos"]
        self.assertEqual(retorno["motivo"], "retorno")

        respuesta = self.pedir("POST", "/api/remitos/" + retorno["codigo"] + "/empaquetar", {
            "momento": "2026-01-21T10:00:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("POST", "/api/remitos/" + retorno["codigo"] + "/despachar", {
            "momento": "2026-01-21T11:00:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("POST", "/api/remitos/" + retorno["codigo"] + "/recibir", {
            "momento": "2026-01-21T12:00:00",
        })
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("GET", "/api/ejemplares/E2")
        datos = respuesta.get_json()["datos"]
        self.assertEqual(datos["ubicacion_actual"], "S2")
        self.assertEqual(datos["estado_disponibilidad"], "en_reparacion")

        respuesta = self.pedir("POST", "/api/ejemplares/E2/reparar", {})
        self.assertEqual(respuesta.status_code, 200)
        respuesta = self.pedir("GET", "/api/ejemplares/E2")
        self.assertEqual(respuesta.get_json()["datos"]["estado_disponibilidad"], "disponible")

    def test_no_se_entrega_antes_de_recibir(self):
        self.datos_basicos(dos_sedes=True)
        self.solicitud_interbibliotecaria()
        remito = self.crear_remito()
        self.pedir("POST", "/api/remitos/" + remito["codigo"] + "/empaquetar", {
            "momento": "2026-01-10T11:00:00",
        })
        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {
            "fecha_prestamo": "2026-01-12",
        })
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.red.buscar_solicitud(1).estado, SolicitudPrestamo.ESTADO_PENDIENTE)


class PruebaReservas(PruebaBase):
    def test_reserva_fifo_y_cancelacion(self):
        self.datos_basicos()
        self.crear_socio(2)
        respuesta = self.pedir("POST", "/api/reservas", {
            "socio_numero": 1,
            "libro_isbn": "L1",
            "codigo_sede": "S1",
            "fecha_reserva": "2026-01-10",
        })
        self.assertEqual(respuesta.status_code, 201)
        reserva_uno = respuesta.get_json()["datos"]
        self.assertEqual(reserva_uno["estado"], "asignada")
        self.assertEqual(reserva_uno["ejemplar_codigo"], "E1")

        respuesta = self.pedir("POST", "/api/reservas", {
            "socio_numero": 2,
            "libro_isbn": "L1",
            "codigo_sede": "S1",
            "fecha_reserva": "2026-01-11",
        })
        self.assertEqual(respuesta.status_code, 201)
        reserva_dos = respuesta.get_json()["datos"]
        self.assertEqual(reserva_dos["estado"], "pendiente")

        respuesta = self.pedir("POST", "/api/reservas/1/cancelar", {})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.red.buscar_reserva(2).estado, Reserva.ESTADO_ASIGNADA)
        self.assertEqual(self.red.buscar_ejemplar("E1").reserva_asignada, 2)

    def test_reserva_de_inhabilitado_pierde_el_turno(self):
        self.datos_basicos()
        self.pedir("POST", "/api/reservas", {
            "socio_numero": 1,
            "libro_isbn": "L1",
            "codigo_sede": "S1",
            "fecha_reserva": "2026-01-10",
        })
        self.pedir("POST", "/api/socios/1/inhabilitar", {})
        self.assertEqual(self.red.buscar_reserva(1).estado, Reserva.ESTADO_CANCELADA)
        self.assertEqual(self.red.buscar_ejemplar("E1").estado_disponibilidad, Ejemplar.DISPONIBLE)

    def test_nueva_copia_atiende_la_cola(self):
        self.datos_basicos()
        self.crear_socio(2)
        for socio in (1, 2):
            respuesta = self.pedir("POST", "/api/reservas", {
                "socio_numero": socio,
                "libro_isbn": "L1",
                "codigo_sede": "S1",
                "fecha_reserva": "2026-01-10",
            })
            self.assertEqual(respuesta.status_code, 201)
        self.crear_ejemplar("E3")
        self.assertEqual(self.red.buscar_reserva(2).estado, Reserva.ESTADO_ASIGNADA)
        self.assertEqual(self.red.buscar_reserva(2).ejemplar_codigo, "E3")


if __name__ == "__main__":
    unittest.main()
