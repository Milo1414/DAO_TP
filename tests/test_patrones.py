# Pruebas de los patrones Factory Method y Observer.
import datetime
import unittest

from backend.errores import ErrorDatosInvalidos
from backend.reportes import (
    FabricaReporteActivosVencidos,
    FabricaReporteDisponibilidad,
    FabricaReporteLibrosSolicitados,
    FabricaReporteMovimientoEnvios,
    FabricaReportes,
    Reporte,
    ReporteActivosVencidos,
    ReporteDisponibilidad,
    ReporteLibrosSolicitados,
    ReporteMovimientoEnvios,
)
from backend.remito import RegistradorHistorial, Remito
from tests.apoyo import PruebaBase


class ObservadorDePrueba:
    def __init__(self):
        self.eventos = []

    def actualizar(self, remito, nombre_estado, momento):
        self.eventos.append((remito.codigo, nombre_estado, momento))


class PruebaFactory(PruebaBase):
    def test_clases_abstractas_no_se_instancian(self):
        with self.assertRaises(TypeError):
            Reporte()
        with self.assertRaises(TypeError):
            FabricaReportes()

    def test_cada_fabrica_crea_su_reporte(self):
        casos = (
            (FabricaReporteActivosVencidos(), ReporteActivosVencidos),
            (FabricaReporteDisponibilidad(), ReporteDisponibilidad),
            (FabricaReporteLibrosSolicitados(), ReporteLibrosSolicitados),
            (FabricaReporteMovimientoEnvios(), ReporteMovimientoEnvios),
        )
        for fabrica, clase in casos:
            reporte = fabrica.crear_reporte()
            self.assertIsInstance(reporte, clase)
            self.assertEqual(reporte.nombre(), reporte.nombre())

    def test_reportes_vacios(self):
        fabricas = (
            FabricaReporteActivosVencidos(),
            FabricaReporteDisponibilidad(),
            FabricaReporteLibrosSolicitados(),
            FabricaReporteMovimientoEnvios(),
        )
        for fabrica in fabricas:
            reporte = fabrica.crear_reporte()
            self.assertEqual(reporte.generar(self.red, {}), [])


class PruebaObserver(PruebaBase):
    def test_alta_registra_estado_inicial(self):
        remito = Remito("R-1", "S1", "S2", datetime.datetime(2026, 1, 10, 9, 0))
        self.assertEqual(len(remito.historial), 1)
        self.assertEqual(remito.historial[0].nombre_estado, Remito.ESTADO_PENDIENTE_EMPAQUE)
        self.assertIsInstance(remito.observadores[0], RegistradorHistorial)

    def test_transiciones_validas_notifican_y_guardan_historial(self):
        remito = Remito("R-1", "S1", "S2", datetime.datetime(2026, 1, 10, 9, 0))
        observador = ObservadorDePrueba()
        remito.suscribir(observador)

        remito.empaquetar(datetime.datetime(2026, 1, 10, 10, 0))
        remito.despachar(datetime.datetime(2026, 1, 10, 11, 0))
        remito.recibir(datetime.datetime(2026, 1, 10, 12, 0))

        self.assertEqual(len(observador.eventos), 3)
        self.assertEqual(len(remito.historial), 4)
        self.assertEqual(remito.nombre_estado(), Remito.ESTADO_RECIBIDO)
        self.assertEqual(observador.eventos[0][1], Remito.ESTADO_EMPAQUETADO)

    def test_desuscripcion(self):
        remito = Remito("R-1", "S1", "S2", datetime.datetime(2026, 1, 10, 9, 0))
        observador = ObservadorDePrueba()
        remito.suscribir(observador)
        remito.desuscribir(observador)
        remito.empaquetar(datetime.datetime(2026, 1, 10, 10, 0))
        self.assertEqual(observador.eventos, [])

    def test_transicion_invalida_no_muta_ni_notifica(self):
        remito = Remito("R-1", "S1", "S2", datetime.datetime(2026, 1, 10, 9, 0))
        observador = ObservadorDePrueba()
        remito.suscribir(observador)
        with self.assertRaises(ErrorDatosInvalidos):
            remito.despachar(datetime.datetime(2026, 1, 10, 10, 0))
        self.assertEqual(remito.nombre_estado(), Remito.ESTADO_PENDIENTE_EMPAQUE)
        self.assertEqual(len(remito.historial), 1)
        self.assertEqual(observador.eventos, [])

    def test_cronologia_invalida_no_muta_ni_notifica(self):
        remito = Remito("R-1", "S1", "S2", datetime.datetime(2026, 1, 10, 9, 0))
        with self.assertRaises(ErrorDatosInvalidos):
            remito.empaquetar(datetime.datetime(2026, 1, 10, 8, 0))
        self.assertEqual(remito.nombre_estado(), Remito.ESTADO_PENDIENTE_EMPAQUE)
        self.assertEqual(len(remito.historial), 1)

    def test_remito_no_acepta_dos_ejemplares(self):
        remito = Remito("R-1", "S1", "S2", datetime.datetime(2026, 1, 10, 9, 0))
        remito.agregar_ejemplar("E1", 1)
        with self.assertRaises(ErrorDatosInvalidos):
            remito.agregar_ejemplar("E2", 2)


if __name__ == "__main__":
    unittest.main()
