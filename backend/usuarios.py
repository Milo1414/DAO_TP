"""Staff accounts belong to web security, independently of library members."""
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Forbidden
from werkzeug.security import check_password_hash, generate_password_hash

from backend.errores import ErrorConflicto, ErrorDatosInvalidos, ErrorNoEncontrado
from backend.modelos import db
from backend.validaciones import validar_codigo, validar_texto


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(40, collation="NOCASE"), nullable=False, unique=True)
    nombre = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    activa = db.Column(db.Boolean, nullable=False, default=True)

    def __init__(self, usuario, nombre, contrasena):
        usuario_validado = validar_codigo(usuario, "Usuario")
        nombre_validado = validar_texto(nombre, "Nombre", 120)
        if isinstance(contrasena, str) == False or len(contrasena) < 8:
            raise ErrorDatosInvalidos("La contraseña debe tener al menos 8 caracteres.")
        if len(contrasena) > 256:
            raise ErrorDatosInvalidos("La contraseña no puede superar los 256 caracteres.")
        self.usuario = usuario_validado
        self.nombre = nombre_validado
        self.password_hash = generate_password_hash(contrasena)
        self.activa = True

    def a_diccionario(self):
        return {"id": self.id, "usuario": self.usuario,
                "nombre": self.nombre, "activa": self.activa}


def hay_usuarios():
    return db.session.execute(db.select(Usuario.id).limit(1)).first() is not None


def listar_usuarios():
    return db.session.execute(db.select(Usuario).order_by(Usuario.usuario)).scalars().all()


def crear_usuario(usuario, nombre, contrasena, primero=False):
    if primero and hay_usuarios():
        raise Forbidden("La primera cuenta ya fue creada.")
    cuenta = Usuario(usuario, nombre, contrasena)
    existente = db.session.execute(
        db.select(Usuario).where(Usuario.usuario == cuenta.usuario)
    ).scalar_one_or_none()
    if existente is not None:
        raise ErrorConflicto("Ya existe una cuenta con ese usuario.")
    if primero:
        # A fixed primary key makes simultaneous initial registrations exclusive.
        cuenta.id = 1
    try:
        db.session.add(cuenta)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if primero:
            raise Forbidden("La primera cuenta ya fue creada.")
        raise ErrorConflicto("Ya existe una cuenta con ese usuario.")
    return cuenta


def autenticar(usuario, contrasena):
    if isinstance(usuario, str) == False or isinstance(contrasena, str) == False:
        return None
    if len(usuario) > 40 or len(contrasena) > 256:
        return None
    cuenta = db.session.execute(
        db.select(Usuario).where(Usuario.usuario == usuario.strip())
    ).scalar_one_or_none()
    if cuenta is None:
        return None
    if check_password_hash(cuenta.password_hash, contrasena) == False:
        return None
    if cuenta.activa == False:
        return None
    return cuenta


def cambiar_estado_usuario(identificador, activa, usuario_actual):
    if isinstance(activa, bool) == False:
        raise ErrorDatosInvalidos("El campo activa debe ser verdadero o falso.")
    if identificador == usuario_actual and activa == False:
        raise ErrorConflicto("No podés desactivar tu propia cuenta.")
    cuenta = db.session.get(Usuario, identificador)
    if cuenta is None:
        raise ErrorNoEncontrado("No existe la cuenta indicada.")
    try:
        cuenta.activa = activa
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise
    return cuenta
