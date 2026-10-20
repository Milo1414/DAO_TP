# Sede de la red de bibliotecas.
from backend.modelos import db
from backend.validaciones import validar_codigo, validar_horario, validar_telefono, validar_texto


class Sede(db.Model):
    __tablename__ = "sedes"

    codigo = db.Column(db.String(40), primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    telefono = db.Column(db.String(40), nullable=False)
    horario = db.Column(db.String(20), nullable=False)
    activa = db.Column(db.Boolean, nullable=False, default=True)

    def __init__(self, codigo, nombre, direccion, telefono, horario):
        self.codigo = validar_codigo(codigo, "codigo de sede")
        self.nombre = validar_texto(nombre, "nombre de sede")
        self.direccion = validar_texto(direccion, "direccion de sede")
        self.telefono = validar_telefono(telefono, "telefono de sede")
        self.horario = validar_horario(horario, "horario de sede")
        self.activa = True

    def dar_de_baja(self):
        # La baja no borra el historial: la sede conserva sus datos,
        # ejemplares y operaciones anteriores.
        self.activa = False

    def reactivar(self):
        self.activa = True

    def modificar_datos(self, nombre, direccion, telefono, horario):
        # Se validan todos los datos nuevos antes de modificar cualquier
        # atributo. Si uno falla, la sede conserva sus valores anteriores.
        nuevo_nombre = validar_texto(nombre, "nombre de sede")
        nueva_direccion = validar_texto(direccion, "direccion de sede")
        nuevo_telefono = validar_telefono(telefono, "telefono de sede")
        nuevo_horario = validar_horario(horario, "horario de sede")

        self.nombre = nuevo_nombre
        self.direccion = nueva_direccion
        self.telefono = nuevo_telefono
        self.horario = nuevo_horario

    def esta_activa(self):
        return self.activa
