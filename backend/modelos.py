# Configuracion central del ORM.
#
# Todas las entidades del sistema son clases de Flask-SQLAlchemy. La base
# SQLite es la fuente persistente: las consultas se hacen contra la sesion
# del ORM y cada operacion de negocio confirma con commit o revierte con
# rollback.
import sqlite3

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine


db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def activar_claves_foraneas(conexion, registro):
    # SQLite no activa las claves foraneas por defecto. Se activan en cada
    # conexion nueva para que el ORM y el motor respeten las relaciones.
    if isinstance(conexion, sqlite3.Connection):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()


class Configuracion(db.Model):
    __tablename__ = "configuracion"

    clave = db.Column(db.String(64), primary_key=True)
    valor = db.Column(db.String(255), nullable=False)

    def __init__(self, clave, valor):
        self.clave = clave
        self.valor = valor
