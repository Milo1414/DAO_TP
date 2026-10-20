# Apoyo comun para las pruebas de la API y del dominio.
#
# Cada prueba usa una base SQLite temporal distinta. La aplicacion se crea
# con crear_aplicacion, igual que en main.py, para probar tambien la
# migracion, la configuracion y el registro de las rutas.
import datetime
import os
import tempfile
import unittest

from backend.app import crear_aplicacion
from backend.modelos import db
from backend.red import RedBibliotecas


class PruebaBase(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta_base = os.path.join(self.carpeta.name, "prueba.db")
        self.aplicacion = crear_aplicacion(self.ruta_base)
        self.aplicacion.config["TESTING"] = True
        self.cliente = self.aplicacion.test_client()
        self.contexto = self.aplicacion.app_context()
        self.contexto.push()
        self.red = RedBibliotecas()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.contexto.pop()
        self.carpeta.cleanup()

    def pedir(self, metodo, ruta, datos=None):
        if datos is None:
            return self.cliente.open(ruta, method=metodo)
        return self.cliente.open(ruta, method=metodo, json=datos)

    def crear_sede(self, codigo, nombre=None, telefono="555-1234",
                   horario="08:00-18:00"):
        if nombre is None:
            nombre = "Sede " + codigo
        respuesta = self.pedir("POST", "/api/sedes", {
            "codigo": codigo,
            "nombre": nombre,
            "direccion": "Calle " + codigo,
            "telefono": telefono,
            "horario": horario,
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def crear_socio(self, numero, nombre=None, email=None):
        if nombre is None:
            nombre = "Socio " + str(numero)
        if email is None:
            email = "socio" + str(numero) + "@mail.com"
        respuesta = self.pedir("POST", "/api/socios", {
            "numero": numero,
            "nombre": nombre,
            "email": email,
            "telefono": "555-000" + str(numero),
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def crear_libro(self, isbn="L1", titulo="Libro de prueba"):
        respuesta = self.pedir("POST", "/api/libros", {
            "isbn": isbn,
            "titulo": titulo,
            "autor": "Autor de prueba",
            "anio": 2020,
            "genero": "Novela",
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def crear_ejemplar(self, codigo, libro_isbn="L1", sede="S1"):
        respuesta = self.pedir("POST", "/api/ejemplares", {
            "codigo": codigo,
            "libro_isbn": libro_isbn,
            "sede_pertenencia": sede,
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def datos_basicos(self, dos_sedes=False):
        self.crear_sede("S1")
        self.crear_socio(1)
        self.crear_libro()
        self.crear_ejemplar("E1")
        if dos_sedes:
            self.crear_sede("S2")
            self.crear_socio(2)
            self.crear_ejemplar("E2", "L1", "S2")

    def solicitud_local(self, fecha="2026-01-10"):
        respuesta = self.pedir("POST", "/api/solicitudes", {
            "socio_numero": 1,
            "libro_isbn": "L1",
            "ejemplar_codigo": "E1",
            "sede_origen": "S1",
            "sede_destino": "S1",
            "fecha_solicitud": fecha,
            "tipo": "local",
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def solicitud_interbibliotecaria(self, fecha="2026-01-10"):
        respuesta = self.pedir("POST", "/api/solicitudes", {
            "socio_numero": 2,
            "libro_isbn": "L1",
            "ejemplar_codigo": "E2",
            "sede_origen": "S2",
            "sede_destino": "S1",
            "fecha_solicitud": fecha,
            "tipo": "interbibliotecario",
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def entregar_local(self, numero=1, fecha="2026-01-10"):
        respuesta = self.pedir("POST", "/api/solicitudes/" + str(numero) + "/entregar", {
            "fecha_prestamo": fecha,
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def crear_remito(self, numero_solicitud=1, momento="2026-01-10T10:00:00"):
        respuesta = self.pedir("POST", "/api/remitos/prestamo", {
            "solicitud_numero": numero_solicitud,
            "fecha_creacion": momento,
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def mover_remito(self, codigo, momentos=("2026-01-10T11:00:00", "2026-01-10T12:00:00", "2026-01-10T13:00:00")):
        respuesta = self.pedir("POST", "/api/remitos/" + codigo + "/empaquetar", {
            "momento": momentos[0],
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        respuesta = self.pedir("POST", "/api/remitos/" + codigo + "/despachar", {
            "momento": momentos[1],
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        respuesta = self.pedir("POST", "/api/remitos/" + codigo + "/recibir", {
            "momento": momentos[2],
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def devolver(self, numero_prestamo, sede="S1", estado_fisico="bueno", fecha="2026-01-20"):
        respuesta = self.pedir("POST", "/api/prestamos/" + str(numero_prestamo) + "/devolucion", {
            "fecha_devolucion": fecha,
            "sede_devolucion": sede,
            "estado_fisico": estado_fisico,
        })
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        return respuesta.get_json()["datos"]

    def fecha(self, texto):
        return datetime.date.fromisoformat(texto)
