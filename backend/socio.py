# Socio de la biblioteca.
from backend.modelos import db
from backend.validaciones import validar_email, validar_entero, validar_telefono, validar_texto


class Socio(db.Model):
    __tablename__ = "socios"

    numero = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    telefono = db.Column(db.String(40), nullable=False)
    habilitado = db.Column(db.Boolean, nullable=False, default=True)

    def __init__(self, numero, nombre, email, telefono):
        self.numero = validar_entero(numero, "numero de socio", 1)
        self.nombre = validar_texto(nombre, "nombre del socio")
        self.email = validar_email(email, "email del socio")
        self.telefono = validar_telefono(telefono, "telefono del socio")
        self.habilitado = True

    def inhabilitar(self):
        self.habilitado = False

    def habilitar(self):
        self.habilitado = True

    def esta_habilitado(self):
        return self.habilitado

    def modificar_datos(self, nombre, email, telefono):
        nuevo_nombre = validar_texto(nombre, "nombre del socio")
        nuevo_email = validar_email(email, "email del socio")
        nuevo_telefono = validar_telefono(telefono, "telefono del socio")

        self.nombre = nuevo_nombre
        self.email = nuevo_email
        self.telefono = nuevo_telefono
