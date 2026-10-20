# Solicitudes, prestamos y reservas.
from backend.errores import ErrorDatosInvalidos
from backend.modelos import db
from backend.validaciones import (
    validar_codigo,
    validar_entero,
    validar_estado_fisico,
    validar_fecha,
    validar_tipo_solicitud,
)


class SolicitudPrestamo(db.Model):
    __tablename__ = "solicitudes"

    TIPO_LOCAL = "local"
    TIPO_INTERBIBLIOTECARIO = "interbibliotecario"

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ENTREGADA = "entregada"
    ESTADO_CANCELADA = "cancelada"

    numero = db.Column(db.Integer, primary_key=True)
    socio_numero = db.Column(db.Integer, db.ForeignKey("socios.numero"), nullable=False)
    libro_isbn = db.Column(db.String(40), db.ForeignKey("libros.isbn"), nullable=False)
    ejemplar_codigo = db.Column(db.String(40), db.ForeignKey("ejemplares.codigo"), nullable=False)
    sede_origen = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    sede_destino = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    fecha_solicitud = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    estado = db.Column(db.String(30), nullable=False, default=ESTADO_PENDIENTE)

    def __init__(self, numero, socio_numero, libro_isbn, ejemplar_codigo,
                 sede_origen, sede_destino, fecha_solicitud, tipo):
        self.numero = validar_entero(numero, "numero de solicitud", 1)
        self.socio_numero = validar_entero(socio_numero, "numero de socio", 1)
        self.libro_isbn = validar_codigo(libro_isbn, "ISBN de libro")
        self.ejemplar_codigo = validar_codigo(ejemplar_codigo, "codigo de ejemplar")
        self.sede_origen = validar_codigo(sede_origen, "sede de origen")
        self.sede_destino = validar_codigo(sede_destino, "sede de destino")
        self.fecha_solicitud = validar_fecha(fecha_solicitud, "fecha de solicitud")
        self.tipo = validar_tipo_solicitud(tipo)
        self.estado = SolicitudPrestamo.ESTADO_PENDIENTE

    def es_interbibliotecaria(self):
        return self.tipo == SolicitudPrestamo.TIPO_INTERBIBLIOTECARIO

    def marcar_entregada(self):
        self.estado = SolicitudPrestamo.ESTADO_ENTREGADA

    def cancelar(self):
        self.estado = SolicitudPrestamo.ESTADO_CANCELADA


class Prestamo(db.Model):
    __tablename__ = "prestamos"

    ESTADO_ACTIVO = "activo"
    ESTADO_DEVUELTO = "devuelto"

    numero = db.Column(db.Integer, primary_key=True)
    solicitud_numero = db.Column(db.Integer, db.ForeignKey("solicitudes.numero"), nullable=False)
    socio_numero = db.Column(db.Integer, db.ForeignKey("socios.numero"), nullable=False)
    ejemplar_codigo = db.Column(db.String(40), db.ForeignKey("ejemplares.codigo"), nullable=False)
    sede_origen = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    sede_destino = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    fecha_prestamo = db.Column(db.Date, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)
    fecha_devolucion = db.Column(db.Date, nullable=True)
    sede_devolucion = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=True)
    estado_fisico_devolucion = db.Column(db.String(30), nullable=True)
    multa = db.Column(db.Float, nullable=False, default=0.0)
    estado = db.Column(db.String(30), nullable=False, default=ESTADO_ACTIVO)

    def __init__(self, numero, solicitud_numero, socio_numero, ejemplar_codigo,
                 sede_origen, sede_destino, fecha_prestamo, fecha_vencimiento):
        self.numero = validar_entero(numero, "numero de prestamo", 1)
        self.solicitud_numero = validar_entero(solicitud_numero, "numero de solicitud", 1)
        self.socio_numero = validar_entero(socio_numero, "numero de socio", 1)
        self.ejemplar_codigo = validar_codigo(ejemplar_codigo, "codigo de ejemplar")
        self.sede_origen = validar_codigo(sede_origen, "sede de origen")
        self.sede_destino = validar_codigo(sede_destino, "sede de destino")
        self.fecha_prestamo = validar_fecha(fecha_prestamo, "fecha de prestamo")
        self.fecha_vencimiento = validar_fecha(fecha_vencimiento, "fecha de vencimiento")
        if self.fecha_vencimiento < self.fecha_prestamo:
            raise ErrorDatosInvalidos("La fecha de vencimiento no puede ser anterior a la fecha de prestamo.")
        self.fecha_devolucion = None
        self.sede_devolucion = None
        self.estado_fisico_devolucion = None
        self.multa = 0.0
        self.estado = Prestamo.ESTADO_ACTIVO

    def esta_activo(self):
        return self.estado == Prestamo.ESTADO_ACTIVO

    def esta_vencido(self, fecha_referencia):
        if self.estado != Prestamo.ESTADO_ACTIVO:
            return False
        return fecha_referencia > self.fecha_vencimiento

    def dias_atraso(self, fecha_referencia):
        if self.esta_vencido(fecha_referencia) == False:
            return 0
        diferencia = fecha_referencia - self.fecha_vencimiento
        return diferencia.days

    def multa_acumulada(self, fecha_referencia, monto_por_dia):
        dias = self.dias_atraso(fecha_referencia)
        multa = dias * monto_por_dia
        return multa

    def registrar_devolucion(self, fecha_devolucion, sede_devolucion, estado_fisico, multa):
        fecha_validada = validar_fecha(fecha_devolucion, "fecha de devolucion")
        sede_validada = validar_codigo(sede_devolucion, "sede de devolucion")
        estado_validado = validar_estado_fisico(estado_fisico)
        if fecha_validada < self.fecha_prestamo:
            raise ErrorDatosInvalidos("La fecha de devolucion no puede ser anterior a la fecha de prestamo.")
        if multa < 0:
            raise ErrorDatosInvalidos("La multa no puede ser negativa.")
        self.fecha_devolucion = fecha_validada
        self.sede_devolucion = sede_validada
        self.estado_fisico_devolucion = estado_validado
        self.multa = float(multa)
        self.estado = Prestamo.ESTADO_DEVUELTO

    def tiene_multa(self):
        return self.multa > 0


class Reserva(db.Model):
    __tablename__ = "reservas"

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ASIGNADA = "asignada"
    ESTADO_CUMPLIDA = "cumplida"
    ESTADO_CANCELADA = "cancelada"

    numero = db.Column(db.Integer, primary_key=True)
    socio_numero = db.Column(db.Integer, db.ForeignKey("socios.numero"), nullable=False)
    libro_isbn = db.Column(db.String(40), db.ForeignKey("libros.isbn"), nullable=False)
    codigo_sede = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    fecha_reserva = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(30), nullable=False, default=ESTADO_PENDIENTE)
    ejemplar_codigo = db.Column(db.String(40), db.ForeignKey("ejemplares.codigo"), nullable=True)
    solicitud_numero = db.Column(db.Integer, db.ForeignKey("solicitudes.numero"), nullable=True)

    def __init__(self, numero, socio_numero, libro_isbn, codigo_sede, fecha_reserva):
        self.numero = validar_entero(numero, "numero de reserva", 1)
        self.socio_numero = validar_entero(socio_numero, "numero de socio", 1)
        self.libro_isbn = validar_codigo(libro_isbn, "ISBN de libro")
        self.codigo_sede = validar_codigo(codigo_sede, "codigo de sede")
        self.fecha_reserva = validar_fecha(fecha_reserva, "fecha de reserva")
        self.estado = Reserva.ESTADO_PENDIENTE
        self.ejemplar_codigo = None
        self.solicitud_numero = None

    def esta_pendiente(self):
        return self.estado == Reserva.ESTADO_PENDIENTE

    def esta_activa(self):
        return self.estado == Reserva.ESTADO_PENDIENTE or self.estado == Reserva.ESTADO_ASIGNADA

    def esta_asignada(self):
        return self.estado == Reserva.ESTADO_ASIGNADA

    def marcar_asignada(self, codigo_ejemplar):
        self.estado = Reserva.ESTADO_ASIGNADA
        self.ejemplar_codigo = codigo_ejemplar

    def marcar_cumplida(self):
        self.estado = Reserva.ESTADO_CUMPLIDA

    def cancelar(self):
        self.estado = Reserva.ESTADO_CANCELADA
