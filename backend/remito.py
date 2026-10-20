# Remito y patron Observer para registrar los cambios de estado.
#
# El Remito es el sujeto observado. Cada transicion valida notifica a los
# observadores suscritos. RegistradorHistorial es el observador concreto
# que agrega una fila al historial. La validacion de la secuencia y de la
# cronologia queda en el Remito: si algo falla, no cambia el estado ni se
# notifica ni se agrega historial.
import datetime
from abc import ABC, abstractmethod

from backend.errores import ErrorDatosInvalidos
from backend.modelos import db
from backend.validaciones import validar_codigo, validar_entero, validar_momento


class ObservadorRemito(ABC):
    @abstractmethod
    def actualizar(self, remito, nombre_estado, momento):
        pass


class RegistradorHistorial(ObservadorRemito):
    def actualizar(self, remito, nombre_estado, momento):
        orden = len(remito.historial)
        registro = RemitoHistorial(remito.codigo, orden, nombre_estado, momento)
        remito.historial.append(registro)


class Remito(db.Model):
    __tablename__ = "remitos"

    ESTADO_PENDIENTE_EMPAQUE = "pendiente_empaque"
    ESTADO_EMPAQUETADO = "empaquetado"
    ESTADO_DESPACHADO = "despachado"
    ESTADO_RECIBIDO = "recibido"

    MOTIVO_PRESTAMO = "prestamo"
    MOTIVO_RETORNO = "retorno"

    codigo = db.Column(db.String(40), primary_key=True)
    sede_origen = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    sede_destino = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.String(30), nullable=False, default=MOTIVO_PRESTAMO)
    estado_actual = db.Column(db.String(30), nullable=False, default=ESTADO_PENDIENTE_EMPAQUE)

    historial = db.relationship(
        "RemitoHistorial",
        cascade="all, delete-orphan",
        order_by="RemitoHistorial.orden",
        lazy="selectin",
    )
    asignaciones = db.relationship(
        "RemitoEjemplar",
        cascade="all, delete-orphan",
        order_by="RemitoEjemplar.ejemplar_codigo",
        lazy="selectin",
    )

    def __init__(self, codigo, sede_origen, sede_destino, fecha_creacion, motivo=MOTIVO_PRESTAMO):
        self.codigo = validar_codigo(codigo, "codigo de remito")
        self.sede_origen = validar_codigo(sede_origen, "sede de origen")
        self.sede_destino = validar_codigo(sede_destino, "sede de destino")
        if self.sede_origen == self.sede_destino:
            raise ErrorDatosInvalidos("Las sedes de origen y destino del remito no pueden ser iguales.")
        if motivo != Remito.MOTIVO_PRESTAMO and motivo != Remito.MOTIVO_RETORNO:
            raise ErrorDatosInvalidos("Motivo de remito no valido: " + str(motivo))
        self.fecha_creacion = validar_momento(fecha_creacion, "fecha de creacion del remito")
        self.motivo = motivo
        self.estado_actual = Remito.ESTADO_PENDIENTE_EMPAQUE
        self.observadores = []
        self.suscribir(RegistradorHistorial())
        # El estado inicial se registra una sola vez, al crear el remito.
        # Al recuperarlo desde la base no se vuelve a emitir este evento.
        self.notificar(self.estado_actual, self.fecha_creacion)

    def suscribir(self, observador):
        self._asegurar_lista_observadores()
        if observador not in self.observadores:
            self.observadores.append(observador)

    def desuscribir(self, observador):
        self._asegurar_lista_observadores()
        if observador in self.observadores:
            self.observadores.remove(observador)

    def _asegurar_lista_observadores(self):
        if hasattr(self, "observadores") == False:
            self.observadores = []

    def _asegurar_observador_historial(self):
        # Un remito recuperado por el ORM no ejecuta __init__. Por eso la
        # suscripcion se comprueba antes de cada transicion.
        self._asegurar_lista_observadores()
        tiene_registrador = False
        for observador in self.observadores:
            if isinstance(observador, RegistradorHistorial):
                tiene_registrador = True
                break
        if tiene_registrador == False:
            self.observadores.append(RegistradorHistorial())

    def notificar(self, nombre_estado, momento):
        self._asegurar_lista_observadores()
        for observador in self.observadores:
            observador.actualizar(self, nombre_estado, momento)

    def nombre_estado(self):
        return self.estado_actual

    def es_retorno(self):
        return self.motivo == Remito.MOTIVO_RETORNO

    def fecha_de(self, nombre_estado):
        for registro in self.historial:
            if registro.nombre_estado == nombre_estado:
                return registro.momento
        return None

    def codigos_ejemplares(self):
        codigos = []
        for asignacion in self.asignaciones:
            codigos.append(asignacion.ejemplar_codigo)
        return codigos

    def numeros_solicitud(self):
        numeros = []
        for asignacion in self.asignaciones:
            if asignacion.numero_solicitud is not None:
                numeros.append(asignacion.numero_solicitud)
        return numeros

    def _validar_cronologia(self, momento):
        if len(self.historial) > 0:
            ultimo_momento = self.historial[len(self.historial) - 1].momento
            if momento < ultimo_momento:
                raise ErrorDatosInvalidos("El momento no puede ser anterior al ultimo evento del remito.")

    def _preparar_transicion(self, momento, descripcion):
        self._asegurar_observador_historial()
        if momento is None:
            momento = datetime.datetime.now()
        momento = validar_momento(momento, descripcion)
        self._validar_cronologia(momento)
        return momento

    def empaquetar(self, momento=None):
        if self.estado_actual == Remito.ESTADO_EMPAQUETADO:
            raise ErrorDatosInvalidos("El remito ya esta empaquetado.")
        if self.estado_actual == Remito.ESTADO_DESPACHADO:
            raise ErrorDatosInvalidos("El remito ya fue despachado.")
        if self.estado_actual == Remito.ESTADO_RECIBIDO:
            raise ErrorDatosInvalidos("El remito ya fue recibido.")
        if self.estado_actual != Remito.ESTADO_PENDIENTE_EMPAQUE:
            raise ErrorDatosInvalidos("No se puede empaquetar el remito en su estado actual.")
        momento = self._preparar_transicion(momento, "momento de empaque")
        self.estado_actual = Remito.ESTADO_EMPAQUETADO
        self.notificar(self.estado_actual, momento)

    def despachar(self, momento=None):
        if self.estado_actual == Remito.ESTADO_PENDIENTE_EMPAQUE:
            raise ErrorDatosInvalidos("No se puede despachar un remito sin empaquetar.")
        if self.estado_actual == Remito.ESTADO_DESPACHADO:
            raise ErrorDatosInvalidos("El remito ya fue despachado.")
        if self.estado_actual == Remito.ESTADO_RECIBIDO:
            raise ErrorDatosInvalidos("El remito ya fue recibido.")
        if self.estado_actual != Remito.ESTADO_EMPAQUETADO:
            raise ErrorDatosInvalidos("No se puede despachar el remito en su estado actual.")
        momento = self._preparar_transicion(momento, "momento de despacho")
        self.estado_actual = Remito.ESTADO_DESPACHADO
        self.notificar(self.estado_actual, momento)

    def recibir(self, momento=None):
        if self.estado_actual == Remito.ESTADO_PENDIENTE_EMPAQUE:
            raise ErrorDatosInvalidos("No se puede recibir un remito sin despachar.")
        if self.estado_actual == Remito.ESTADO_EMPAQUETADO:
            raise ErrorDatosInvalidos("No se puede recibir un remito sin despachar.")
        if self.estado_actual == Remito.ESTADO_RECIBIDO:
            raise ErrorDatosInvalidos("El remito ya fue recibido.")
        if self.estado_actual != Remito.ESTADO_DESPACHADO:
            raise ErrorDatosInvalidos("No se puede recibir el remito en su estado actual.")
        momento = self._preparar_transicion(momento, "momento de recepcion")
        self.estado_actual = Remito.ESTADO_RECIBIDO
        self.notificar(self.estado_actual, momento)

    def agregar_ejemplar(self, codigo_ejemplar, numero_solicitud):
        # Un remito de prestamo transporta la copia de una sola solicitud.
        if len(self.asignaciones) > 0:
            raise ErrorDatosInvalidos("El remito ya transporta un ejemplar.")
        if self.nombre_estado() != Remito.ESTADO_PENDIENTE_EMPAQUE:
            raise ErrorDatosInvalidos("El remito ya empezo a moverse.")
        codigo = validar_codigo(codigo_ejemplar, "codigo de ejemplar")
        numero = validar_entero(numero_solicitud, "numero de solicitud", 1)
        asignacion = RemitoEjemplar(self.codigo, codigo, numero, None)
        self.asignaciones.append(asignacion)

    def agregar_ejemplar_de_retorno(self, codigo_ejemplar):
        # El retorno no nace de una solicitud de prestamo.
        if len(self.asignaciones) > 0:
            raise ErrorDatosInvalidos("El remito ya transporta un ejemplar.")
        if self.nombre_estado() != Remito.ESTADO_PENDIENTE_EMPAQUE:
            raise ErrorDatosInvalidos("El remito ya empezo a moverse.")
        codigo = validar_codigo(codigo_ejemplar, "codigo de ejemplar")
        asignacion = RemitoEjemplar(self.codigo, codigo, None, None)
        self.asignaciones.append(asignacion)


class RemitoEjemplar(db.Model):
    __tablename__ = "remito_ejemplares"

    remito_codigo = db.Column(db.String(40), db.ForeignKey("remitos.codigo"), primary_key=True)
    ejemplar_codigo = db.Column(db.String(40), db.ForeignKey("ejemplares.codigo"), primary_key=True)
    numero_solicitud = db.Column(db.Integer, db.ForeignKey("solicitudes.numero"), nullable=True)
    # Evidencia historica del estado fisico observado al recibir el remito.
    # El reporte de envios no atribuye danios mirando solamente el estado
    # actual del ejemplar.
    estado_fisico_recepcion = db.Column(db.String(30), nullable=True)

    def __init__(self, remito_codigo, ejemplar_codigo, numero_solicitud, estado_fisico_recepcion):
        self.remito_codigo = remito_codigo
        self.ejemplar_codigo = ejemplar_codigo
        self.numero_solicitud = numero_solicitud
        self.estado_fisico_recepcion = estado_fisico_recepcion


class RemitoHistorial(db.Model):
    __tablename__ = "remito_historial"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    remito_codigo = db.Column(db.String(40), db.ForeignKey("remitos.codigo"), nullable=False)
    orden = db.Column(db.Integer, nullable=False)
    nombre_estado = db.Column(db.String(30), nullable=False)
    momento = db.Column(db.DateTime, nullable=False)

    def __init__(self, remito_codigo, orden, nombre_estado, momento):
        self.remito_codigo = remito_codigo
        self.orden = orden
        self.nombre_estado = nombre_estado
        self.momento = momento
