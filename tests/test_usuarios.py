import os
import re
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import check_password_hash

from backend.app import cargar_clave_secreta, crear_aplicacion
from backend.modelos import db
from backend.usuarios import Usuario


class PruebaUsuarios(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "cuentas.db")
        self.aplicacion = crear_aplicacion(self.ruta, {
            "TESTING": True, "SECRET_KEY": "test-only-key",
        })
        self.cliente = self.aplicacion.test_client()

    def tearDown(self):
        with self.aplicacion.app_context():
            db.session.remove()
            db.engine.dispose()
        self.carpeta.cleanup()

    def registrar_primero(self):
        respuesta = self.cliente.post("/api/primer-usuario", json={
            "usuario": "personal", "nombre": "Personal", "contrasena": "prueba123",
        })
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.get_json()["datos"]

    def crear_auxiliar(self):
        respuesta = self.cliente.post("/api/usuarios", json={
            "usuario": "auxiliar", "nombre": "Auxiliar", "contrasena": "prueba123",
        })
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.get_json()["datos"]

    def test_solo_sesion_login_y_registro_inicial_son_publicos(self):
        sesion = self.cliente.get("/api/sesion").get_json()["datos"]
        self.assertEqual(sesion, {"usuario": None, "requiere_configuracion": True})
        publicos = {"ver_sesion", "iniciar_sesion", "primer_usuario"}
        for regla in self.aplicacion.url_map.iter_rules():
            if regla.rule.startswith("/api/") == False or regla.endpoint in publicos:
                continue
            ruta = re.sub(r"<[^>]+>", "1", regla.rule)
            for metodo in regla.methods:
                if metodo in ("HEAD", "OPTIONS"):
                    continue
                with self.subTest(ruta=ruta, metodo=metodo):
                    respuesta = self.cliente.open(ruta, method=metodo, json={})
                    self.assertEqual(respuesta.status_code, 401)
        pagina = self.cliente.get("/")
        self.assertEqual(pagina.status_code, 200)
        pagina.close()
        self.assertEqual(self.cliente.get("/api/reportes/movimiento?formato=pdf").status_code, 401)

    def test_primer_registro_abre_sesion_y_luego_devuelve_403(self):
        cuenta = self.registrar_primero()
        self.assertEqual(self.cliente.get("/api/listados").status_code, 200)
        sesion = self.cliente.get("/api/sesion").get_json()["datos"]
        self.assertEqual(sesion["usuario"], cuenta)
        self.assertFalse(sesion["requiere_configuracion"])
        otro = self.aplicacion.test_client()
        self.assertEqual(otro.post("/api/primer-usuario", json={}).status_code, 403)

    def test_doble_registro_inicial_no_crea_dos_cuentas(self):
        self.registrar_primero()
        otro = self.aplicacion.test_client()
        with patch("backend.app.hay_usuarios", return_value=False):
            with patch("backend.usuarios.hay_usuarios", return_value=False):
                respuesta = otro.post("/api/primer-usuario", json={
                    "usuario": "otra", "nombre": "Otra", "contrasena": "prueba123",
                })
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(len(self.cliente.get("/api/usuarios").get_json()["datos"]), 1)

    def test_hash_con_salt_y_respuestas_sin_contrasenas(self):
        primero = self.registrar_primero()
        auxiliar = self.crear_auxiliar()
        with self.aplicacion.app_context():
            cuenta = db.session.get(Usuario, primero["id"])
            otra = db.session.get(Usuario, auxiliar["id"])
            self.assertNotEqual(cuenta.password_hash, "prueba123")
            self.assertNotEqual(cuenta.password_hash, otra.password_hash)
            self.assertTrue(check_password_hash(cuenta.password_hash, "prueba123"))
        for datos in [primero, auxiliar] + self.cliente.get("/api/usuarios").get_json()["datos"]:
            self.assertEqual(set(datos), {"id", "usuario", "nombre", "activa"})

    def test_login_logout_cookie_y_mensaje_generico(self):
        self.registrar_primero()
        self.assertEqual(self.cliente.post("/api/logout").status_code, 200)
        mensajes = []
        for usuario, contrasena in [("desconocido", "prueba123"), ("personal", "incorrecta")]:
            respuesta = self.cliente.post("/api/login", json={
                "usuario": usuario, "contrasena": contrasena,
            })
            self.assertEqual(respuesta.status_code, 401)
            mensajes.append(respuesta.get_json()["error"])
        self.assertEqual(mensajes, ["Usuario o contraseña incorrectos"] * 2)
        respuesta = self.cliente.post("/api/login", json={
            "usuario": "PERSONAL", "contrasena": "prueba123",
        })
        self.assertEqual(respuesta.status_code, 200)
        cookie = respuesta.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        with self.cliente.session_transaction() as sesion:
            self.assertEqual(dict(sesion), {"usuario_id": 1})
        self.cliente.post("/api/logout")
        self.assertEqual(self.cliente.get("/api/listados").status_code, 401)

    def test_cuenta_desactivada_pierde_acceso_y_puede_reactivarse(self):
        self.registrar_primero()
        auxiliar = self.crear_auxiliar()
        otro = self.aplicacion.test_client()
        self.assertEqual(otro.post("/api/login", json={
            "usuario": "auxiliar", "contrasena": "prueba123",
        }).status_code, 200)
        ruta = "/api/usuarios/" + str(auxiliar["id"]) + "/estado"
        self.assertEqual(self.cliente.post(ruta, json={"activa": False}).status_code, 200)
        self.assertEqual(otro.get("/api/listados").status_code, 401)
        self.assertEqual(otro.get("/api/sesion").get_json()["datos"]["usuario"], None)
        respuesta = otro.post("/api/login", json={"usuario": "auxiliar", "contrasena": "prueba123"})
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.get_json()["error"], "Usuario o contraseña incorrectos")
        self.assertEqual(self.cliente.post(ruta, json={"activa": True}).status_code, 200)
        self.assertEqual(otro.post("/api/login", json={
            "usuario": "auxiliar", "contrasena": "prueba123",
        }).status_code, 200)

    def test_no_permite_desactivar_cuenta_propia_ni_estado_invalido(self):
        self.registrar_primero()
        self.assertEqual(self.cliente.post("/api/usuarios/1/estado", json={"activa": False}).status_code, 409)
        self.assertEqual(self.cliente.post("/api/usuarios/1/estado", json={"activa": "false"}).status_code, 400)
        self.assertEqual(self.cliente.get("/api/listados").status_code, 200)

    def test_validaciones_no_crean_cuentas_incompletas_y_evitan_duplicados(self):
        for contrasena in ["corta", None, 12345678]:
            respuesta = self.cliente.post("/api/primer-usuario", json={
                "usuario": "personal", "nombre": "Personal", "contrasena": contrasena,
            })
            self.assertEqual(respuesta.status_code, 400)
            self.assertTrue(self.cliente.get("/api/sesion").get_json()["datos"]["requiere_configuracion"])
        self.registrar_primero()
        respuesta = self.cliente.post("/api/usuarios", json={
            "usuario": "PERSONAL", "nombre": "Duplicada", "contrasena": "prueba123",
        })
        self.assertEqual(respuesta.status_code, 409)

    def test_persistencia_y_clave_estable_entre_reinicios(self):
        self.registrar_primero()
        with self.aplicacion.app_context():
            db.session.remove()
            db.engine.dispose()
        self.aplicacion = crear_aplicacion(self.ruta, {"TESTING": True, "SECRET_KEY": "test-only-key"})
        nuevo = self.aplicacion.test_client()
        self.assertEqual(nuevo.post("/api/login", json={
            "usuario": "personal", "contrasena": "prueba123",
        }).status_code, 200)
        ruta_clave = os.path.join(self.carpeta.name, "instance", "clave_secreta")
        clave = cargar_clave_secreta(ruta_clave)
        self.assertEqual(len(clave), 64)
        self.assertEqual(cargar_clave_secreta(ruta_clave), clave)
        self.assertIsNotNone(bytes.fromhex(clave))


if __name__ == "__main__":
    unittest.main()
