# Pruebas de persistencia real con SQLite, configuracion y validaciones atomicas.
import datetime
import unittest

from sqlalchemy import text

from backend.catalogo import Libro
from backend.errores import ErrorDatosInvalidos
from backend.modelos import Configuracion, db
from backend.remito import Remito
from backend.sede import Sede
from backend.socio import Socio
from tests.apoyo import PruebaBase


class PruebaOrm(PruebaBase):
    def test_configuracion_inicial(self):
        self.assertEqual(self.red.plazo_dias, 14)
        self.assertEqual(self.red.multa_por_dia, 100)
        self.assertEqual(db.session.get(Configuracion, "plazo_dias").valor, "14")

        self.red.plazo_dias = 7
        self.red.multa_por_dia = 50
        db.session.expire_all()
        self.assertEqual(self.red.plazo_dias, 7)
        self.assertEqual(self.red.multa_por_dia, 50)

    def test_claves_foraneas_activas(self):
        resultado = db.session.execute(text("PRAGMA foreign_keys")).scalar()
        self.assertEqual(resultado, 1)

    def test_los_datos_sobreviven_al_cierre_de_sesion(self):
        self.crear_sede("S1")
        self.crear_socio(1)
        self.crear_libro()
        self.crear_ejemplar("E1")
        db.session.remove()

        self.assertIsNotNone(self.red.buscar_sede("S1"))
        self.assertIsNotNone(self.red.buscar_socio(1))
        self.assertIsNotNone(self.red.buscar_libro("L1"))
        self.assertIsNotNone(self.red.buscar_ejemplar("E1"))

    def test_el_historial_se_recupera_y_el_observer_sigue_funcionando(self):
        self.datos_basicos(dos_sedes=True)
        self.solicitud_interbibliotecaria()
        remito = self.crear_remito()
        codigo = remito["codigo"]
        db.session.remove()

        recuperado = self.red.buscar_remito(codigo)
        self.assertIsNotNone(recuperado)
        self.assertEqual(len(recuperado.historial), 1)
        self.red.empaquetar_remito(codigo, datetime.datetime(2026, 1, 10, 11, 0))

        db.session.remove()
        recuperado = self.red.buscar_remito(codigo)
        self.assertEqual(len(recuperado.historial), 2)
        self.assertEqual(recuperado.estado_actual, Remito.ESTADO_EMPAQUETADO)
        self.assertEqual(recuperado.historial[1].nombre_estado, Remito.ESTADO_EMPAQUETADO)

    def test_modificacion_atomica_de_sede(self):
        sede = Sede("S1", "Sede uno", "Calle 1", "555-1234", "08:00-18:00")
        with self.assertRaises(ErrorDatosInvalidos):
            sede.modificar_datos("Sede dos", "Calle 2", "telefono con letras", "09:00-17:00")
        self.assertEqual(sede.nombre, "Sede uno")
        self.assertEqual(sede.direccion, "Calle 1")
        self.assertEqual(sede.telefono, "555-1234")
        self.assertEqual(sede.horario, "08:00-18:00")

    def test_modificacion_atomica_de_socio(self):
        socio = Socio(1, "Socio uno", "socio@mail.com", "555-1234")
        with self.assertRaises(ErrorDatosInvalidos):
            socio.modificar_datos("Socio dos", "email-invalido", "555-9876")
        self.assertEqual(socio.nombre, "Socio uno")
        self.assertEqual(socio.email, "socio@mail.com")
        self.assertEqual(socio.telefono, "555-1234")

    def test_modificacion_atomica_de_libro(self):
        libro = Libro("L1", "Titulo uno", "Autor uno", 2020, "Novela")
        with self.assertRaises(ErrorDatosInvalidos):
            libro.modificar_datos("Titulo dos", "Autor dos", 3000, "Cuento")
        self.assertEqual(libro.titulo, "Titulo uno")
        self.assertEqual(libro.autor, "Autor uno")
        self.assertEqual(libro.anio, 2020)


if __name__ == "__main__":
    unittest.main()
