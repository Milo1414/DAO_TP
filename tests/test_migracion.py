# Pruebas de preparacion de la base, respaldo y lectura de datos heredados.
import os
import sqlite3
import tempfile
import unittest

from backend.app import crear_aplicacion
from backend.modelos import db


class PruebaMigracion(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "heredada.db")
        self.aplicacion = None

    def tearDown(self):
        if self.aplicacion is not None:
            with self.aplicacion.app_context():
                db.session.remove()
                db.engine.dispose()
        self.carpeta.cleanup()

    def crear_tabla_vieja_remito_ejemplares(self):
        conexion = sqlite3.connect(self.ruta)
        conexion.execute(
            "CREATE TABLE remito_ejemplares ("
            "remito_codigo TEXT NOT NULL, "
            "ejemplar_codigo TEXT NOT NULL, "
            "numero_solicitud INTEGER, "
            "PRIMARY KEY (remito_codigo, ejemplar_codigo))"
        )
        conexion.commit()
        conexion.close()

    def crear_tabla_vieja_sedes(self):
        conexion = sqlite3.connect(self.ruta)
        conexion.execute(
            "CREATE TABLE sedes ("
            "codigo TEXT PRIMARY KEY, "
            "nombre TEXT NOT NULL, "
            "direccion TEXT NOT NULL, "
            "telefono TEXT NOT NULL, "
            "horario TEXT NOT NULL, "
            "activa INTEGER NOT NULL)"
        )
        conexion.execute(
            "INSERT INTO sedes VALUES ('123', 'HOla', 'Angel', '1234a', 'sd', 1)"
        )
        conexion.commit()
        conexion.close()

    def test_agrega_columna_y_crea_respaldo(self):
        self.crear_tabla_vieja_remito_ejemplares()
        aplicacion = crear_aplicacion(self.ruta)
        self.aplicacion = aplicacion
        respaldo = aplicacion.config["RESPALDO_BASE"]
        self.assertIsNotNone(respaldo)
        self.assertTrue(os.path.exists(respaldo))
        self.assertEqual(len(aplicacion.config["CAMBIOS_BASE"]), 1)
        self.assertIn("estado_fisico_recepcion", aplicacion.config["CAMBIOS_BASE"][0])

        conexion = sqlite3.connect(self.ruta)
        columnas = conexion.execute("PRAGMA table_info(remito_ejemplares)").fetchall()
        conexion.close()
        nombres = []
        for columna in columnas:
            nombres.append(columna[1])
        self.assertIn("estado_fisico_recepcion", nombres)

    def test_segunda_apertura_no_repite_el_respaldo(self):
        self.crear_tabla_vieja_remito_ejemplares()
        primera = crear_aplicacion(self.ruta)
        self.aplicacion = primera
        self.assertIsNotNone(primera.config["RESPALDO_BASE"])
        with primera.app_context():
            db.session.remove()
            db.engine.dispose()
        segunda = crear_aplicacion(self.ruta)
        self.aplicacion = segunda
        self.assertIsNone(segunda.config["RESPALDO_BASE"])
        self.assertEqual(segunda.config["CAMBIOS_BASE"], [])

    def test_informa_datos_heredados_sin_corregirlos(self):
        self.crear_tabla_vieja_sedes()
        aplicacion = crear_aplicacion(self.ruta)
        self.aplicacion = aplicacion
        problemas = aplicacion.config["PROBLEMAS_BASE"]
        texto = "\n".join(problemas)
        self.assertIn("telefono de sede", texto)
        self.assertIn("horario de sede", texto)

        cliente = aplicacion.test_client()
        respuesta = cliente.get("/api/salud")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.get_json()["datos"]["problemas_datos"]), 2)

        conexion = sqlite3.connect(self.ruta)
        fila = conexion.execute(
            "SELECT telefono, horario FROM sedes WHERE codigo = '123'"
        ).fetchone()
        conexion.close()
        self.assertEqual(fila[0], "1234a")
        self.assertEqual(fila[1], "sd")

    def test_base_nueva_queda_con_configuracion(self):
        aplicacion = crear_aplicacion(self.ruta)
        self.aplicacion = aplicacion
        self.assertIsNone(aplicacion.config["RESPALDO_BASE"])
        self.assertEqual(aplicacion.config["PROBLEMAS_BASE"], [])
        conexion = sqlite3.connect(self.ruta)
        claves = conexion.execute("SELECT clave FROM configuracion ORDER BY clave").fetchall()
        conexion.close()
        nombres = []
        for fila in claves:
            nombres.append(fila[0])
        self.assertIn("plazo_dias", nombres)
        self.assertIn("multa_por_dia", nombres)


if __name__ == "__main__":
    unittest.main()
