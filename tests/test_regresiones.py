# Regresiones de la revision final: operaciones completas con API y ORM reales.
import datetime
import math
import unittest
from unittest.mock import patch

from sqlalchemy import text

from backend.errores import ErrorDatosInvalidos
from backend.migracion import preparar_base
from backend.modelos import Configuracion, db
from backend.prestamos import Prestamo
from tests.apoyo import PruebaBase


class PruebaCorrecciones(PruebaBase):
    def preparar_envio(self, recibir=False):
        self.datos_basicos(dos_sedes=True)
        self.solicitud_interbibliotecaria()
        remito = self.crear_remito()
        if recibir:
            self.mover_remito(remito["codigo"])
        return remito["codigo"]

    def test_cancelar_antes_del_despacho_conserva_historial_y_libera_copia(self):
        codigo = self.preparar_envio()
        self.red.empaquetar_remito(codigo, datetime.datetime(2026, 1, 10, 11))
        respuesta = self.pedir("POST", "/api/solicitudes/1/cancelar", {})
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        db.session.remove()
        remito = self.red.buscar_remito(codigo)
        self.assertEqual(remito.estado_actual, "cancelado")
        self.assertEqual(len(remito.historial), 3)
        self.assertEqual(remito.historial[-1].nombre_estado, "cancelado")
        self.assertTrue(self.red.buscar_ejemplar("E2").esta_disponible())
        self.assertIsNone(self.red.remito_activo_por_ejemplar("E2"))
        self.assertEqual(self.red.resumen()["remitos_activos"], 0)
        fila = self.pedir("GET", "/api/reportes/movimiento").get_json()["datos"]["filas"][0]
        self.assertEqual(fila["cancelados"], 1)
        self.assertEqual(fila["pendientes"], 0)
        self.assertEqual(preparar_base(self.ruta_base)["problemas"], [])

    def test_cancelar_remito_sin_empaquetar(self):
        codigo = self.preparar_envio()
        self.red.cancelar_solicitud(1)
        self.assertEqual(self.red.buscar_remito(codigo).estado_actual, "cancelado")
        self.assertEqual(len(self.red.buscar_remito(codigo).historial), 2)
        self.assertEqual(preparar_base(self.ruta_base)["problemas"], [])

    def test_cancelacion_en_transito_no_muta_y_luego_permite_retornar(self):
        codigo = self.preparar_envio()
        self.red.empaquetar_remito(codigo, datetime.datetime(2026, 1, 10, 11))
        self.red.despachar_remito(codigo, datetime.datetime(2026, 1, 10, 12))
        respuesta = self.pedir("POST", "/api/solicitudes/1/cancelar", {})
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(self.red.buscar_solicitud(1).estado, "pendiente")
        self.assertEqual(self.red.buscar_remito(codigo).estado_actual, "despachado")
        self.red.recibir_remito(codigo, datetime.datetime(2026, 1, 10, 13), "bueno")
        self.verificar_cancelacion_y_retorno()

    def verificar_cancelacion_y_retorno(self):
        self.red.inhabilitar_socio(2)
        respuesta = self.pedir("POST", "/api/solicitudes/1/entregar", {"fecha_prestamo": "2026-01-11"})
        self.assertEqual(respuesta.status_code, 409)
        respuesta = self.pedir("POST", "/api/solicitudes/1/cancelar", {})
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        ejemplar = self.red.buscar_ejemplar("E2")
        self.assertEqual(ejemplar.estado_disponibilidad, "pendiente_retorno")
        self.assertIsNone(ejemplar.solicitud_asignada)
        retorno = self.red.crear_remito_retorno("E2", datetime.datetime(2026, 1, 11, 9))
        self.mover_remito(retorno.codigo, ("2026-01-11T10:00:00", "2026-01-11T11:00:00", "2026-01-11T12:00:00"))
        db.session.remove()
        self.assertTrue(self.red.buscar_ejemplar("E2").esta_disponible())
        self.assertEqual(self.red.buscar_ejemplar("E2").ubicacion_actual, "S2")
        self.assertEqual(len(self.red.prestamos), 0)
        self.assertEqual(preparar_base(self.ruta_base)["problemas"], [])

    def test_socio_inhabilitado_tras_recepcion_no_bloquea_la_copia(self):
        self.preparar_envio(recibir=True)
        self.verificar_cancelacion_y_retorno()

    def test_no_se_acepta_una_solicitud_anterior_a_la_ultima_devolucion(self):
        self.datos_basicos()
        self.solicitud_local()
        self.entregar_local()
        self.devolver(1)
        with self.assertRaises(ErrorDatosInvalidos):
            self.red.registrar_solicitud(1, "L1", "E1", "S1", "S1", datetime.date(2026, 1, 5), "local")
        db.session.remove()
        self.assertEqual(len(self.red.solicitudes), 1)
        self.assertTrue(self.red.buscar_ejemplar("E1").esta_disponible())
        self.red.registrar_solicitud(1, "L1", "E1", "S1", "S1", datetime.date(2026, 1, 20), "local")

    def test_no_se_acepta_una_solicitud_anterior_a_la_recepcion_del_retorno(self):
        self.preparar_envio(recibir=True)
        self.verificar_cancelacion_y_retorno()
        with self.assertRaises(ErrorDatosInvalidos):
            self.red.registrar_solicitud(1, "L1", "E2", "S2", "S2", datetime.date(2026, 1, 10), "local")

    def test_configuracion_invalida_no_modifica_una_entrega_directa(self):
        self.datos_basicos()
        self.solicitud_local()
        db.session.get(Configuracion, "plazo_dias").valor = "invalido"
        db.session.commit()
        with self.assertRaises(ErrorDatosInvalidos):
            self.red.entregar_solicitud(1, datetime.date(2026, 1, 10))
        self.assertEqual(self.red.buscar_solicitud(1).estado, "pendiente")
        self.assertEqual(self.red.buscar_ejemplar("E1").solicitud_asignada, 1)
        db.session.commit()
        db.session.remove()
        self.assertEqual(len(self.red.prestamos), 0)
        self.assertEqual(self.red.buscar_ejemplar("E1").estado_disponibilidad, "apartado")

    def test_fallo_despues_de_mutar_la_devolucion_revierte_toda_la_operacion(self):
        self.datos_basicos()
        self.solicitud_local()
        self.entregar_local()
        with patch.object(self.red, "atender_cola_reservas", side_effect=ErrorDatosInvalidos("Fallo de prueba")):
            with self.assertRaises(ErrorDatosInvalidos):
                self.red.registrar_devolucion(1, datetime.date(2026, 1, 20), "S1", "bueno")
        db.session.commit()
        db.session.remove()
        self.assertEqual(self.red.buscar_prestamo(1).estado, "activo")
        self.assertIsNone(self.red.buscar_prestamo(1).fecha_devolucion)
        self.assertEqual(self.red.buscar_ejemplar("E1").estado_disponibilidad, "prestado")

    def test_recepcion_exige_revision_y_rechaza_datos_sin_mutar(self):
        codigo = self.preparar_envio()
        self.red.empaquetar_remito(codigo, datetime.datetime(2026, 1, 10, 11))
        self.red.despachar_remito(codigo, datetime.datetime(2026, 1, 10, 12))
        for datos in ({}, {"estado_fisico": "invalido"}):
            respuesta = self.pedir("POST", "/api/remitos/" + codigo + "/recibir", datos)
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(self.red.buscar_remito(codigo).estado_actual, "despachado")
            self.assertEqual(len(self.red.buscar_remito(codigo).historial), 3)
        respuesta = self.pedir("POST", "/api/remitos/" + codigo + "/recibir", {
            "momento": "2026-01-10T13:00:00", "estado_fisico": "requiere_reparacion",
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        db.session.remove()
        self.assertEqual(self.red.buscar_remito(codigo).asignaciones[0].estado_fisico_recepcion, "requiere_reparacion")
        self.assertEqual(self.red.buscar_solicitud(1).estado, "cancelada")
        self.assertEqual(self.red.buscar_ejemplar("E2").estado_disponibilidad, "pendiente_retorno")
        retorno = self.red.crear_remito_retorno("E2", datetime.datetime(2026, 1, 11))
        self.red.empaquetar_remito(retorno.codigo, datetime.datetime(2026, 1, 11, 1))
        self.red.despachar_remito(retorno.codigo, datetime.datetime(2026, 1, 11, 2))
        self.red.recibir_remito(retorno.codigo, datetime.datetime(2026, 1, 11, 3), "requiere_reparacion")
        self.red.reparar_ejemplar("E2")
        fila = self.pedir("GET", "/api/reportes/movimiento").get_json()["datos"]["filas"][1]
        self.assertEqual(fila["copias_danadas_recepcion"], 1)
        self.assertEqual(preparar_base(self.ruta_base)["problemas"], [])

    def test_momentos_con_zona_horaria_se_rechazan_como_400(self):
        codigo = self.preparar_envio()
        respuesta = self.pedir("POST", "/api/remitos/" + codigo + "/empaquetar", {"momento": "2026-01-10T11:00:00+00:00"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.red.buscar_remito(codigo).estado_actual, "pendiente_empaque")
        self.red.cancelar_solicitud(1)
        self.solicitud_interbibliotecaria(fecha="2026-01-11")
        respuesta = self.pedir("POST", "/api/remitos/prestamo", {"solicitud_numero": 2, "fecha_creacion": "2026-01-11T10:00:00Z"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(len(self.red.remitos), 1)

    def test_datos_recuperados_invalidos_no_se_usan_en_el_dominio(self):
        self.datos_basicos()
        self.solicitud_local()
        self.entregar_local()
        db.session.execute(text("UPDATE prestamos SET fecha_vencimiento = '2026-01-01' WHERE numero = 1"))
        db.session.commit()
        db.session.remove()
        with self.assertRaises(ErrorDatosInvalidos):
            self.red.buscar_prestamo(1)
        respuesta = self.pedir("GET", "/api/prestamos")
        self.assertEqual(respuesta.status_code, 400)
        problemas = preparar_base(self.ruta_base)["problemas"]
        self.assertIn("vencimiento es anterior", "\n".join(problemas))

    def test_revision_heredada_detecta_historial_incompleto_y_cronologia(self):
        codigo = self.preparar_envio(recibir=True)
        db.session.execute(text("DELETE FROM remito_historial WHERE nombre_estado = 'empaquetado'"))
        db.session.commit()
        db.session.remove()
        problemas = preparar_base(self.ruta_base)["problemas"]
        self.assertIn("historial", "\n".join(problemas))
        with self.assertRaises(ErrorDatosInvalidos):
            self.red.buscar_remito(codigo)

    def test_revision_heredada_detecta_fecha_invalida_del_historial(self):
        self.preparar_envio(recibir=True)
        db.session.execute(text("UPDATE remito_historial SET momento = 'no-es-fecha' WHERE nombre_estado = 'recibido'"))
        db.session.commit()
        db.session.remove()
        problemas = preparar_base(self.ruta_base)["problemas"]
        self.assertTrue(problemas)
        self.assertIn("Remito", "\n".join(problemas))

    def test_revision_heredada_detecta_eventos_fuera_de_orden_temporal(self):
        self.preparar_envio(recibir=True)
        db.session.execute(text("UPDATE remito_historial SET momento = '2026-01-09 10:00:00' WHERE nombre_estado = 'recibido'"))
        db.session.commit()
        db.session.remove()
        problemas = preparar_base(self.ruta_base)["problemas"]
        self.assertIn("cronologia", "\n".join(problemas))

    def test_revision_heredada_detecta_asignaciones_cruzadas(self):
        self.datos_basicos()
        self.solicitud_local()
        self.crear_ejemplar("E3")
        db.session.execute(text("UPDATE ejemplares SET solicitud_asignada = 1, estado_disponibilidad = 'apartado' WHERE codigo = 'E3'"))
        db.session.commit()
        db.session.remove()
        problemas = preparar_base(self.ruta_base)["problemas"]
        self.assertIn("solicitud asignada no corresponde", "\n".join(problemas))

    def test_devolucion_rechaza_multa_no_finita_sin_modificar(self):
        prestamo = Prestamo(1, 1, 1, "E1", "S1", "S1", datetime.date(2026, 1, 10), datetime.date(2026, 1, 24))
        for multa in (math.nan, math.inf, -1, "100"):
            with self.assertRaises(ErrorDatosInvalidos):
                prestamo.registrar_devolucion(datetime.date(2026, 1, 20), "S1", "bueno", multa)
            self.assertTrue(prestamo.esta_activo())
            self.assertIsNone(prestamo.fecha_devolucion)


if __name__ == "__main__":
    unittest.main()
