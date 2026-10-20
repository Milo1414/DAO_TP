# Libro del catalogo y ejemplares fisicos.
#
# El Libro es la obra del catalogo. Su identificador es un codigo interno
# del sistema (el TP no valida el digito verificador de un ISBN real).
# El Ejemplar es cada copia fisica y guarda dos datos distintos:
# - sede_pertenencia: sede duenia de la copia, no cambia con los envios.
# - ubicacion_actual: donde esta fisicamente en cada momento; es None
#   mientras la copia esta en transito.
from backend.errores import ErrorDatosInvalidos
from backend.modelos import db
from backend.validaciones import validar_anio, validar_codigo, validar_texto


class Libro(db.Model):
    __tablename__ = "libros"

    isbn = db.Column(db.String(40), primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(200), nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    genero = db.Column(db.String(100), nullable=False)

    def __init__(self, isbn, titulo, autor, anio, genero):
        self.isbn = validar_codigo(isbn, "ISBN")
        self.titulo = validar_texto(titulo, "titulo del libro")
        self.autor = validar_texto(autor, "autor del libro")
        self.anio = validar_anio(anio, "anio del libro")
        self.genero = validar_texto(genero, "genero del libro")

    def modificar_datos(self, titulo, autor, anio, genero):
        nuevo_titulo = validar_texto(titulo, "titulo del libro")
        nuevo_autor = validar_texto(autor, "autor del libro")
        nuevo_anio = validar_anio(anio, "anio del libro")
        nuevo_genero = validar_texto(genero, "genero del libro")

        self.titulo = nuevo_titulo
        self.autor = nuevo_autor
        self.anio = nuevo_anio
        self.genero = nuevo_genero


class Ejemplar(db.Model):
    __tablename__ = "ejemplares"

    DISPONIBLE = "disponible"
    APARTADO = "apartado"
    PRESTADO = "prestado"
    EN_TRANSITO = "en_transito"
    EN_REPARACION = "en_reparacion"
    PENDIENTE_RETORNO = "pendiente_retorno"

    FISICO_BUENO = "bueno"
    FISICO_DETERIORADO = "deteriorado"
    FISICO_REPARACION = "requiere_reparacion"

    ESTADOS_DISPONIBILIDAD = (
        DISPONIBLE,
        APARTADO,
        PRESTADO,
        EN_TRANSITO,
        EN_REPARACION,
        PENDIENTE_RETORNO,
    )

    ESTADOS_FISICOS = (
        FISICO_BUENO,
        FISICO_DETERIORADO,
        FISICO_REPARACION,
    )

    codigo = db.Column(db.String(40), primary_key=True)
    libro_isbn = db.Column(db.String(40), db.ForeignKey("libros.isbn"), nullable=False)
    sede_pertenencia = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=False)
    ubicacion_actual = db.Column(db.String(40), db.ForeignKey("sedes.codigo"), nullable=True)
    estado_disponibilidad = db.Column(db.String(30), nullable=False, default=DISPONIBLE)
    estado_fisico = db.Column(db.String(30), nullable=False, default=FISICO_BUENO)
    # Punteros de asignacion. Se mantienen en el dominio para que una copia
    # no pueda quedar tomada por dos solicitudes o reservas. No son claves
    # foraneas para evitar un ciclo entre ejemplares y solicitudes; su
    # coherencia se valida en cada operacion y al revisar datos heredados.
    solicitud_asignada = db.Column(db.Integer, nullable=True)
    reserva_asignada = db.Column(db.Integer, nullable=True)

    def __init__(self, codigo, libro_isbn, sede_pertenencia, ubicacion_actual):
        self.codigo = validar_codigo(codigo, "codigo de ejemplar")
        self.libro_isbn = validar_codigo(libro_isbn, "ISBN de libro")
        self.sede_pertenencia = validar_codigo(sede_pertenencia, "sede de pertenencia")
        if ubicacion_actual is None:
            self.ubicacion_actual = None
        else:
            self.ubicacion_actual = validar_codigo(ubicacion_actual, "ubicacion actual")
        self.estado_disponibilidad = Ejemplar.DISPONIBLE
        self.estado_fisico = Ejemplar.FISICO_BUENO
        self.solicitud_asignada = None
        self.reserva_asignada = None

    def esta_disponible(self):
        return self.estado_disponibilidad == Ejemplar.DISPONIBLE

    def esta_apartado(self):
        return self.estado_disponibilidad == Ejemplar.APARTADO

    def esta_danado(self):
        return self.estado_fisico == Ejemplar.FISICO_REPARACION

    def apartar_para_solicitud(self, numero_solicitud):
        self.estado_disponibilidad = Ejemplar.APARTADO
        self.solicitud_asignada = numero_solicitud

    def apartar_para_reserva(self, numero_reserva):
        self.estado_disponibilidad = Ejemplar.APARTADO
        self.reserva_asignada = numero_reserva

    def mantener_apartado(self):
        self.estado_disponibilidad = Ejemplar.APARTADO

    def liberar_asignacion(self):
        self.estado_disponibilidad = Ejemplar.DISPONIBLE
        self.solicitud_asignada = None
        self.reserva_asignada = None

    def marcar_prestado(self):
        self.estado_disponibilidad = Ejemplar.PRESTADO
        self.solicitud_asignada = None
        self.reserva_asignada = None

    def marcar_disponible(self):
        self.estado_disponibilidad = Ejemplar.DISPONIBLE
        self.solicitud_asignada = None
        self.reserva_asignada = None

    def marcar_en_transito(self):
        # El transito cambia la ubicacion fisica: ya no esta en una sede.
        self.estado_disponibilidad = Ejemplar.EN_TRANSITO
        self.ubicacion_actual = None

    def marcar_pendiente_retorno(self):
        self.estado_disponibilidad = Ejemplar.PENDIENTE_RETORNO
        self.solicitud_asignada = None
        self.reserva_asignada = None

    def marcar_en_reparacion(self):
        self.estado_disponibilidad = Ejemplar.EN_REPARACION
        self.estado_fisico = Ejemplar.FISICO_REPARACION

    def reparar(self):
        self.estado_fisico = Ejemplar.FISICO_BUENO
        self.estado_disponibilidad = Ejemplar.DISPONIBLE
        self.solicitud_asignada = None
        self.reserva_asignada = None

    def registrar_revision_fisica(self, estado_fisico):
        if estado_fisico not in Ejemplar.ESTADOS_FISICOS:
            raise ErrorDatosInvalidos("Estado fisico no valido: " + str(estado_fisico))
        self.estado_fisico = estado_fisico

    def mover_a(self, codigo_sede):
        if codigo_sede is None:
            self.ubicacion_actual = None
        else:
            self.ubicacion_actual = validar_codigo(codigo_sede, "codigo de sede")
