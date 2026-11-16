# Red de bibliotecas: coordina las operaciones sobre la base SQLite.
#
# Decisiones de negocio (reglas que la consigna deja abiertas):
# - Plazo de prestamo: 14 dias corridos, configurable en plazo_dias.
# - Multa: 100 pesos por dia de atraso, configurable en multa_por_dia.
# - Una solicitud valida aparta un ejemplar concreto desde su registro.
#   La copia apartada no aparece como disponible ni puede usarla otra
#   solicitud. La recepcion de un remito conserva esa asignacion.
# - Reserva por libro y sede, cola FIFO por fecha (y numero ante empate).
#   Al quedar una copia prestable se aparta para el primer socio habilitado:
#   la reserva pasa a asignada; cumplida significa que se entrego y nacio
#   el prestamo. Si la copia necesita reparacion o retorno, sigue esperando.
# - Solicitud local: origen igual a destino y copia fisicamente alli.
#   Interbibliotecaria: sedes distintas, copia en origen, remito recibido
#   obligatorio y entrega posterior a la recepcion.
# - Devolucion en sede distinta a la pertenencia: la copia queda pendiente
#   de retorno, no prestable, hasta que un remito de retorno la devuelve.
# - Sede dada de baja: no permite iniciar solicitudes, reservas, remitos
#   ni despachos con esa sede, pero conserva el historial y permite
#   registrar la recepcion de un envio que ya salio.
# - Una solicitud con remito se cancela antes del despacho o tras recibirlo.
#   Si ya llego, la copia queda pendiente de retorno. En transito se espera
#   la recepcion; una solicitud entregada no se cancela.
# - Si una operacion se rechaza, no cambia estados ni consume identificadores.
import datetime
import math

from backend.catalogo import Ejemplar, Libro
from backend.errores import ErrorConflicto, ErrorDatosInvalidos, ErrorNoEncontrado
from backend.modelos import Configuracion, db
from backend.prestamos import Prestamo, Reserva, SolicitudPrestamo
from backend.remito import Remito
from backend.sede import Sede
from backend.socio import Socio
from backend.validaciones import (
    validar_codigo,
    validar_email,
    validar_entero,
    validar_fecha,
    validar_horario,
    validar_momento,
    validar_telefono,
    validar_texto,
    validar_tipo_solicitud,
)


class RedBibliotecas:
    # Esta clase no guarda copias propias de las entidades. Cada consulta
    # se hace contra la sesion de SQLAlchemy, de modo que SQLite siga siendo
    # la fuente de verdad y no exista una lista global desactualizada.

    def __init__(self):
        pass

    # ---------- Colecciones consultadas desde el ORM ----------

    def _validar_coleccion(self, objetos):
        for objeto in objetos:
            objeto.validar_datos()
        return objetos

    def _validar_recuperado(self, objeto):
        if objeto is not None:
            objeto.validar_datos()
        return objeto

    @property
    def sedes(self):
        return self._validar_coleccion(Sede.query.order_by(Sede.codigo).all())

    @property
    def socios(self):
        return self._validar_coleccion(Socio.query.order_by(Socio.numero).all())

    @property
    def libros(self):
        return self._validar_coleccion(Libro.query.order_by(Libro.isbn).all())

    @property
    def ejemplares(self):
        return self._validar_coleccion(Ejemplar.query.order_by(Ejemplar.codigo).all())

    @property
    def solicitudes(self):
        return self._validar_coleccion(SolicitudPrestamo.query.order_by(SolicitudPrestamo.numero).all())

    @property
    def prestamos(self):
        return self._validar_coleccion(Prestamo.query.order_by(Prestamo.numero).all())

    @property
    def reservas(self):
        return self._validar_coleccion(Reserva.query.order_by(Reserva.numero).all())

    @property
    def remitos(self):
        return self._validar_coleccion(Remito.query.order_by(Remito.codigo).all())

    # ---------- Configuracion persistente ----------

    def _leer_configuracion(self, clave, valor_por_defecto):
        fila = db.session.get(Configuracion, clave)
        if fila is None:
            return valor_por_defecto
        return fila.valor

    def _guardar_configuracion(self, clave, valor):
        fila = db.session.get(Configuracion, clave)
        if fila is None:
            fila = Configuracion(clave, str(valor))
            db.session.add(fila)
        else:
            fila.valor = str(valor)

    @property
    def plazo_dias(self):
        valor = self._leer_configuracion("plazo_dias", "14")
        try:
            dias = int(valor)
        except ValueError:
            raise ErrorDatosInvalidos("La configuración plazo_dias no es un entero válido.")
        if dias < 1:
            raise ErrorDatosInvalidos("La configuración plazo_dias debe ser mayor a cero.")
        return dias

    @plazo_dias.setter
    def plazo_dias(self, valor):
        dias = validar_entero(valor, "plazo de préstamo", 1)
        self._guardar_configuracion("plazo_dias", dias)
        self._confirmar()

    @property
    def multa_por_dia(self):
        valor = self._leer_configuracion("multa_por_dia", "100")
        try:
            monto = float(valor)
        except ValueError:
            raise ErrorDatosInvalidos("La configuración multa_por_dia no es un número válido.")
        if math.isfinite(monto) == False:
            raise ErrorDatosInvalidos("La configuración multa_por_dia debe ser un número finito.")
        if monto < 0:
            raise ErrorDatosInvalidos("La configuración multa_por_dia no puede ser negativa.")
        return monto

    @multa_por_dia.setter
    def multa_por_dia(self, valor):
        try:
            monto = float(valor)
        except (TypeError, ValueError):
            raise ErrorDatosInvalidos("La multa por día debe ser un número.")
        if math.isfinite(monto) == False:
            raise ErrorDatosInvalidos("La multa por día debe ser un número finito.")
        if monto < 0:
            raise ErrorDatosInvalidos("La multa por día no puede ser negativa.")
        self._guardar_configuracion("multa_por_dia", monto)
        self._confirmar()

    # ---------- Ayudas generales ----------

    def _confirmar(self):
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def _siguiente_numero(self, modelo):
        maximo = db.session.query(db.func.max(modelo.numero)).scalar()
        if maximo is None:
            return 1
        return int(maximo) + 1

    def _siguiente_codigo_remito(self):
        maximo = 0
        for remito in self.remitos:
            if remito.codigo.startswith("R-") == False:
                continue
            parte = remito.codigo[2:]
            if parte.isdigit():
                numero = int(parte)
                if numero > maximo:
                    maximo = numero
        return "R-" + str(maximo + 1)

    def a_fecha(self, valor):
        if isinstance(valor, datetime.datetime):
            return valor.date()
        return valor

    # ---------- Busquedas ----------

    def buscar_sede(self, codigo):
        return self._validar_recuperado(db.session.get(Sede, codigo))

    def buscar_socio(self, numero):
        return self._validar_recuperado(db.session.get(Socio, numero))

    def buscar_libro(self, isbn):
        return self._validar_recuperado(db.session.get(Libro, isbn))

    def buscar_ejemplar(self, codigo):
        return self._validar_recuperado(db.session.get(Ejemplar, codigo))

    def buscar_solicitud(self, numero):
        return self._validar_recuperado(db.session.get(SolicitudPrestamo, numero))

    def buscar_prestamo(self, numero):
        return self._validar_recuperado(db.session.get(Prestamo, numero))

    def buscar_reserva(self, numero):
        return self._validar_recuperado(db.session.get(Reserva, numero))

    def buscar_remito(self, codigo):
        return self._validar_recuperado(db.session.get(Remito, codigo))

    def buscar_remito_por_solicitud(self, numero_solicitud):
        for remito in self.remitos:
            for asignacion in remito.asignaciones:
                if asignacion.numero_solicitud == numero_solicitud:
                    return remito
        return None

    def buscar_reserva_por_solicitud(self, numero_solicitud):
        for reserva in self.reservas:
            if reserva.solicitud_numero == numero_solicitud:
                return reserva
        return None

    # ---------- Sedes ----------

    def agregar_sede(self, codigo, nombre, direccion, telefono, horario):
        codigo_validado = validar_codigo(codigo, "código de sede")
        if self.buscar_sede(codigo_validado) is not None:
            raise ErrorConflicto("Ya existe una sede con ese código: " + str(codigo_validado))
        sede = Sede(
            codigo_validado,
            validar_texto(nombre, "nombre de sede"),
            validar_texto(direccion, "dirección de sede"),
            validar_telefono(telefono, "teléfono de sede"),
            validar_horario(horario, "horario de sede"),
        )
        db.session.add(sede)
        self._confirmar()
        return sede

    def modificar_sede(self, codigo, nombre, direccion, telefono, horario):
        sede = self.buscar_sede(codigo)
        if sede is None:
            raise ErrorNoEncontrado("No existe la sede: " + str(codigo))
        sede.modificar_datos(nombre, direccion, telefono, horario)
        self._confirmar()
        return sede

    def dar_baja_sede(self, codigo):
        sede = self.buscar_sede(codigo)
        if sede is None:
            raise ErrorNoEncontrado("No existe la sede: " + str(codigo))
        if sede.esta_activa() == False:
            raise ErrorConflicto("La sede ya está dada de baja: " + str(codigo))
        sede.dar_de_baja()
        self._confirmar()
        return sede

    def reactivar_sede(self, codigo):
        sede = self.buscar_sede(codigo)
        if sede is None:
            raise ErrorNoEncontrado("No existe la sede: " + str(codigo))
        if sede.esta_activa():
            raise ErrorConflicto("La sede ya está activa: " + str(codigo))
        sede.reactivar()
        self._confirmar()
        return sede

    def exigir_sede_activa(self, codigo):
        sede = self.buscar_sede(codigo)
        if sede is None:
            raise ErrorNoEncontrado("No existe la sede: " + str(codigo))
        if sede.esta_activa() == False:
            raise ErrorConflicto("La sede está dada de baja: " + str(codigo))
        return sede

    # ---------- Socios ----------

    def agregar_socio(self, numero, nombre, email, telefono):
        numero_validado = validar_entero(numero, "número de socio", 1)
        email_validado = validar_email(email, "email del socio")
        if self.buscar_socio(numero_validado) is not None:
            raise ErrorConflicto("Ya existe un socio con ese número: " + str(numero_validado))
        for socio in self.socios:
            if socio.email.lower() == email_validado.lower():
                raise ErrorConflicto("Ya existe un socio con ese email: " + email_validado)
        socio = Socio(numero_validado, nombre, email_validado, telefono)
        db.session.add(socio)
        self._confirmar()
        return socio

    def modificar_socio(self, numero, nombre, email, telefono):
        socio = self.buscar_socio(numero)
        if socio is None:
            raise ErrorNoEncontrado("No existe el socio: " + str(numero))
        email_validado = validar_email(email, "email del socio")
        for otro in self.socios:
            if otro.numero != socio.numero and otro.email.lower() == email_validado.lower():
                raise ErrorConflicto("Ya existe un socio con ese email: " + email_validado)
        socio.modificar_datos(nombre, email_validado, telefono)
        self._confirmar()
        return socio

    def inhabilitar_socio(self, numero):
        socio = self.buscar_socio(numero)
        if socio is None:
            raise ErrorNoEncontrado("No existe el socio: " + str(numero))
        if socio.esta_habilitado() == False:
            raise ErrorConflicto("El socio ya está inhabilitado: " + str(numero))
        try:
            socio.inhabilitar()
            pares_revisados = []
            for reserva in self.reservas:
                if reserva.socio_numero != numero:
                    continue
                if reserva.esta_activa() == False:
                    continue
                par = (reserva.libro_isbn, reserva.codigo_sede)
                if par in pares_revisados:
                    continue
                pares_revisados.append(par)
                self.revisar_reservas_asignadas(reserva.libro_isbn, reserva.codigo_sede)
                self.atender_cola_reservas(reserva.libro_isbn, reserva.codigo_sede)
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return socio

    def habilitar_socio(self, numero):
        socio = self.buscar_socio(numero)
        if socio is None:
            raise ErrorNoEncontrado("No existe el socio: " + str(numero))
        if socio.esta_habilitado():
            raise ErrorConflicto("El socio ya está habilitado: " + str(numero))
        socio.habilitar()
        self._confirmar()
        return socio

    def exigir_socio_habilitado(self, numero):
        socio = self.buscar_socio(numero)
        if socio is None:
            raise ErrorNoEncontrado("No existe el socio: " + str(numero))
        if socio.esta_habilitado() == False:
            raise ErrorConflicto("El socio está inhabilitado: " + str(numero))
        return socio

    # ---------- Catalogo y ejemplares ----------

    def agregar_libro(self, isbn, titulo, autor, anio, genero):
        isbn_validado = validar_codigo(isbn, "ISBN")
        if self.buscar_libro(isbn_validado) is not None:
            raise ErrorConflicto("Ya existe un libro con ese ISBN: " + str(isbn_validado))
        libro = Libro(isbn_validado, titulo, autor, anio, genero)
        db.session.add(libro)
        self._confirmar()
        return libro

    def modificar_libro(self, isbn, titulo, autor, anio, genero):
        libro = self.buscar_libro(isbn)
        if libro is None:
            raise ErrorNoEncontrado("No existe el libro: " + str(isbn))
        libro.modificar_datos(titulo, autor, anio, genero)
        self._confirmar()
        return libro

    def agregar_ejemplar(self, codigo, libro_isbn, sede_pertenencia):
        codigo_validado = validar_codigo(codigo, "código de ejemplar")
        if self.buscar_ejemplar(codigo_validado) is not None:
            raise ErrorConflicto("Ya existe un ejemplar con ese código: " + str(codigo_validado))
        if self.buscar_libro(libro_isbn) is None:
            raise ErrorNoEncontrado("No existe el libro: " + str(libro_isbn))
        self.exigir_sede_activa(sede_pertenencia)
        ejemplar = Ejemplar(codigo_validado, libro_isbn, sede_pertenencia, sede_pertenencia)
        db.session.add(ejemplar)
        try:
            # Una copia nueva puede atender reservas que ya estaban esperando.
            self.atender_cola_reservas(libro_isbn, sede_pertenencia)
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return ejemplar

    def reparar_ejemplar(self, codigo):
        ejemplar = self.buscar_ejemplar(codigo)
        if ejemplar is None:
            raise ErrorNoEncontrado("No existe el ejemplar: " + str(codigo))
        if ejemplar.estado_disponibilidad != Ejemplar.EN_REPARACION:
            raise ErrorConflicto("Solo se puede reparar un ejemplar en reparación.")
        if self.prestamo_activo_por_ejemplar(codigo) is not None:
            raise ErrorConflicto("No se puede reparar un ejemplar prestado.")
        if self.remito_activo_por_ejemplar(codigo) is not None:
            raise ErrorConflicto("No se puede reparar un ejemplar en envío.")
        if ejemplar.solicitud_asignada is not None or ejemplar.reserva_asignada is not None:
            raise ErrorConflicto("No se puede reparar un ejemplar asignado.")
        try:
            ejemplar.reparar()
            if ejemplar.ubicacion_actual != ejemplar.sede_pertenencia:
                ejemplar.marcar_pendiente_retorno()
            elif ejemplar.ubicacion_actual is not None:
                self.atender_cola_reservas(ejemplar.libro_isbn, ejemplar.ubicacion_actual)
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return ejemplar

    def prestamo_activo_por_ejemplar(self, codigo_ejemplar):
        return Prestamo.query.filter_by(
            ejemplar_codigo=codigo_ejemplar,
            estado=Prestamo.ESTADO_ACTIVO,
        ).first()

    def remito_activo_por_ejemplar(self, codigo_ejemplar):
        for remito in self.remitos:
            if remito.nombre_estado() in (Remito.ESTADO_RECIBIDO, Remito.ESTADO_CANCELADO):
                continue
            for asignacion in remito.asignaciones:
                if asignacion.ejemplar_codigo == codigo_ejemplar:
                    return remito
        return None

    def ultima_devolucion_de_ejemplar(self, codigo_ejemplar):
        ultima = None
        for prestamo in self.prestamos:
            if prestamo.ejemplar_codigo != codigo_ejemplar:
                continue
            if prestamo.fecha_devolucion is None:
                continue
            if ultima is None:
                ultima = prestamo
            elif prestamo.fecha_devolucion > ultima.fecha_devolucion:
                ultima = prestamo
        return ultima

    def copia_prestable_en_sede(self, libro_isbn, codigo_sede):
        for ejemplar in self.ejemplares:
            if ejemplar.libro_isbn != libro_isbn:
                continue
            if ejemplar.sede_pertenencia != codigo_sede:
                continue
            if ejemplar.ubicacion_actual != codigo_sede:
                continue
            if ejemplar.esta_disponible() == False:
                continue
            if ejemplar.esta_danado():
                continue
            return ejemplar
        return None

    # ---------- Disponibilidad ----------

    def disponibilidad_detallada(self, libro_isbn=None, codigo_sede=None):
        resultado = []
        for ejemplar in self.ejemplares:
            if libro_isbn is not None and ejemplar.libro_isbn != libro_isbn:
                continue
            if codigo_sede is not None and ejemplar.sede_pertenencia != codigo_sede:
                continue
            resultado.append(ejemplar)
        return resultado

    def motivo_no_disponible(self, ejemplar):
        if ejemplar.estado_disponibilidad == Ejemplar.DISPONIBLE and ejemplar.esta_danado() == False:
            return "disponible"
        if ejemplar.ubicacion_actual is None:
            return "en tránsito"
        if ejemplar.solicitud_asignada is not None:
            return "apartado para la solicitud " + str(ejemplar.solicitud_asignada)
        if ejemplar.reserva_asignada is not None:
            return "apartado para la reserva " + str(ejemplar.reserva_asignada)
        if ejemplar.estado_disponibilidad == Ejemplar.PENDIENTE_RETORNO:
            return "devuelto en otra sede, espera el retorno"
        if ejemplar.estado_disponibilidad == Ejemplar.PRESTADO:
            return "prestado"
        if ejemplar.estado_disponibilidad == Ejemplar.EN_REPARACION:
            return "en reparación"
        if ejemplar.esta_danado():
            return "devuelto dañado, espera reparación"
        return "no disponible"

    # ---------- Solicitudes y prestamos ----------

    def validar_fecha_de_ejemplar(self, ejemplar, fecha):
        ultima = self.ultima_devolucion_de_ejemplar(ejemplar.codigo)
        if ultima is not None and fecha < ultima.fecha_devolucion:
            raise ErrorDatosInvalidos("La operación no puede ser anterior a la última devolución del ejemplar.")
        for remito in self.remitos:
            recepcion = remito.fecha_de(Remito.ESTADO_RECIBIDO)
            if recepcion is None:
                continue
            if ejemplar.codigo in remito.codigos_ejemplares():
                if fecha < self.a_fecha(recepcion):
                    raise ErrorDatosInvalidos("La operación no puede ser anterior a la última recepción del ejemplar.")

    def registrar_solicitud(self, socio_numero, libro_isbn, ejemplar_codigo,
                            sede_origen, sede_destino, fecha_solicitud, tipo):
        tipo_validado = validar_tipo_solicitud(tipo)
        fecha_validada = validar_fecha(fecha_solicitud, "fecha de solicitud")
        self.exigir_sede_activa(sede_origen)
        self.exigir_sede_activa(sede_destino)
        self.exigir_socio_habilitado(socio_numero)
        if self.buscar_libro(libro_isbn) is None:
            raise ErrorNoEncontrado("No existe el libro: " + str(libro_isbn))
        ejemplar = self.buscar_ejemplar(ejemplar_codigo)
        if ejemplar is None:
            raise ErrorNoEncontrado("No existe el ejemplar: " + str(ejemplar_codigo))
        if ejemplar.libro_isbn != libro_isbn:
            raise ErrorConflicto("El ejemplar no corresponde a ese libro.")
        if tipo_validado == SolicitudPrestamo.TIPO_LOCAL and sede_origen != sede_destino:
            raise ErrorDatosInvalidos("El préstamo local usa la misma sede de origen y destino.")
        if tipo_validado == SolicitudPrestamo.TIPO_INTERBIBLIOTECARIO and sede_origen == sede_destino:
            raise ErrorDatosInvalidos("El préstamo interbibliotecario necesita dos sedes distintas.")
        if ejemplar.sede_pertenencia != sede_origen:
            raise ErrorConflicto("El ejemplar no pertenece a la sede de origen.")
        if ejemplar.ubicacion_actual != sede_origen:
            raise ErrorConflicto("El ejemplar no se encuentra en la sede de origen.")
        if ejemplar.esta_danado():
            raise ErrorConflicto("El ejemplar está dañado y necesita reparación.")
        if ejemplar.solicitud_asignada is not None:
            raise ErrorConflicto("El ejemplar ya está asignado a una solicitud.")
        self.validar_fecha_de_ejemplar(ejemplar, fecha_validada)

        reserva_asignada = None
        if ejemplar.esta_disponible():
            reserva_asignada = None
        elif ejemplar.esta_apartado() and ejemplar.reserva_asignada is not None:
            candidata = self.buscar_reserva(ejemplar.reserva_asignada)
            if candidata is None:
                raise ErrorConflicto("El ejemplar está apartado para una reserva inexistente.")
            if candidata.esta_asignada() == False:
                raise ErrorConflicto("La reserva del ejemplar ya no está activa.")
            if candidata.solicitud_numero is not None:
                raise ErrorConflicto("La reserva del ejemplar ya tiene una solicitud asociada.")
            if candidata.socio_numero != socio_numero:
                raise ErrorConflicto("El ejemplar está apartado para otra reserva.")
            if candidata.libro_isbn != libro_isbn or candidata.codigo_sede != sede_destino:
                raise ErrorConflicto("El ejemplar está apartado para otra reserva.")
            if fecha_validada < candidata.fecha_reserva:
                raise ErrorDatosInvalidos("La solicitud no puede ser anterior a su reserva.")
            reserva_asignada = candidata
        else:
            raise ErrorConflicto("El ejemplar no está disponible.")

        numero = self._siguiente_numero(SolicitudPrestamo)
        solicitud = SolicitudPrestamo(
            numero, socio_numero, libro_isbn, ejemplar_codigo,
            sede_origen, sede_destino, fecha_validada, tipo_validado,
        )
        db.session.add(solicitud)
        # La reserva apunta a la solicitud por clave foranea. Se inserta la
        # solicitud primero para que la actualizacion de la reserva encuentre
        # su numero ya existente en la base.
        try:
            db.session.flush()
        except Exception:
            db.session.rollback()
            raise
        ejemplar.apartar_para_solicitud(numero)
        if reserva_asignada is not None:
            reserva_asignada.solicitud_numero = numero
        self._confirmar()
        return solicitud

    def entregar_solicitud(self, numero_solicitud, fecha_prestamo):
        solicitud = self.buscar_solicitud(numero_solicitud)
        if solicitud is None:
            raise ErrorNoEncontrado("No existe la solicitud: " + str(numero_solicitud))
        if solicitud.estado != SolicitudPrestamo.ESTADO_PENDIENTE:
            raise ErrorConflicto("La solicitud ya fue atendida o cancelada.")
        fecha_validada = validar_fecha(fecha_prestamo, "fecha de préstamo")
        self.exigir_sede_activa(solicitud.sede_origen)
        self.exigir_sede_activa(solicitud.sede_destino)
        self.exigir_socio_habilitado(solicitud.socio_numero)
        ejemplar = self.buscar_ejemplar(solicitud.ejemplar_codigo)
        if ejemplar is None:
            raise ErrorNoEncontrado("No existe el ejemplar de la solicitud.")
        if ejemplar.libro_isbn != solicitud.libro_isbn or ejemplar.sede_pertenencia != solicitud.sede_origen:
            raise ErrorDatosInvalidos("El ejemplar no coincide con el libro y origen de la solicitud.")
        if ejemplar.solicitud_asignada != numero_solicitud:
            raise ErrorConflicto("El ejemplar no está asignado a esta solicitud.")
        if ejemplar.esta_apartado() == False:
            raise ErrorConflicto("El ejemplar no está apartado para esta entrega.")
        if ejemplar.esta_danado():
            raise ErrorConflicto("El ejemplar está dañado y necesita reparación.")
        if fecha_validada < solicitud.fecha_solicitud:
            raise ErrorDatosInvalidos("La entrega no puede ser anterior a la solicitud.")
        self.validar_fecha_de_ejemplar(ejemplar, fecha_validada)
        if solicitud.es_interbibliotecaria():
            remito = self.buscar_remito_por_solicitud(numero_solicitud)
            if remito is None:
                raise ErrorConflicto("La solicitud interbibliotecaria necesita un remito.")
            if remito.nombre_estado() != Remito.ESTADO_RECIBIDO:
                raise ErrorConflicto("El ejemplar todavía no llegó a destino.")
            if ejemplar.ubicacion_actual != solicitud.sede_destino:
                raise ErrorConflicto("El ejemplar no se encuentra en la sede de destino.")
            recepcion = remito.fecha_de(Remito.ESTADO_RECIBIDO)
            if recepcion is not None and fecha_validada < self.a_fecha(recepcion):
                raise ErrorDatosInvalidos("La entrega no puede ser anterior a la recepción.")
        else:
            if ejemplar.ubicacion_actual != solicitud.sede_origen:
                raise ErrorConflicto("El ejemplar no se encuentra en la sede del préstamo.")

        reserva = self.buscar_reserva_por_solicitud(numero_solicitud)
        dias = datetime.timedelta(days=self.plazo_dias)
        vencimiento = fecha_validada + dias
        numero = self._siguiente_numero(Prestamo)
        prestamo = Prestamo(
            numero, solicitud.numero, solicitud.socio_numero,
            solicitud.ejemplar_codigo, solicitud.sede_origen,
            solicitud.sede_destino, fecha_validada, vencimiento,
        )
        try:
            ejemplar.marcar_prestado()
            solicitud.marcar_entregada()
            if reserva is not None:
                reserva.marcar_cumplida()
            db.session.add(prestamo)
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return prestamo

    def cancelar_solicitud(self, numero_solicitud):
        solicitud = self.buscar_solicitud(numero_solicitud)
        if solicitud is None:
            raise ErrorNoEncontrado("No existe la solicitud: " + str(numero_solicitud))
        if solicitud.estado != SolicitudPrestamo.ESTADO_PENDIENTE:
            raise ErrorConflicto("Solo se puede cancelar una solicitud pendiente.")
        remito = self.buscar_remito_por_solicitud(numero_solicitud)
        if remito is not None and remito.nombre_estado() == Remito.ESTADO_DESPACHADO:
            raise ErrorConflicto("El envío está en tránsito: reciba el remito antes de cancelar la solicitud.")
        ejemplar = self.buscar_ejemplar(solicitud.ejemplar_codigo)
        if remito is not None and remito.nombre_estado() == Remito.ESTADO_RECIBIDO:
            try:
                solicitud.cancelar()
                ejemplar.marcar_pendiente_retorno()
                self._confirmar()
            except Exception:
                db.session.rollback()
                raise
            return solicitud
        try:
            if remito is not None and remito.nombre_estado() != Remito.ESTADO_CANCELADO:
                remito.cancelar()
            if ejemplar is not None and ejemplar.solicitud_asignada == numero_solicitud:
                if ejemplar.reserva_asignada is not None:
                    reserva = self.buscar_reserva(ejemplar.reserva_asignada)
                    if reserva is not None:
                        reserva.solicitud_numero = None
                    ejemplar.solicitud_asignada = None
                else:
                    ejemplar.liberar_asignacion()
                    self.atender_cola_reservas(ejemplar.libro_isbn, ejemplar.ubicacion_actual)
            solicitud.cancelar()
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return solicitud

    # ---------- Reservas ----------

    def registrar_reserva(self, socio_numero, libro_isbn, codigo_sede, fecha_reserva):
        fecha_validada = validar_fecha(fecha_reserva, "fecha de reserva")
        self.exigir_sede_activa(codigo_sede)
        self.exigir_socio_habilitado(socio_numero)
        if self.buscar_libro(libro_isbn) is None:
            raise ErrorNoEncontrado("No existe el libro: " + str(libro_isbn))
        for reserva in self.reservas:
            if reserva.esta_activa() == False:
                continue
            if (reserva.socio_numero == socio_numero and
                    reserva.libro_isbn == libro_isbn and
                    reserva.codigo_sede == codigo_sede):
                raise ErrorConflicto("Ya existe una reserva activa igual.")
        numero = self._siguiente_numero(Reserva)
        reserva = Reserva(numero, socio_numero, libro_isbn, codigo_sede, fecha_validada)
        try:
            db.session.add(reserva)
            self.atender_cola_reservas(libro_isbn, codigo_sede)
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return reserva

    def cancelar_reserva(self, numero_reserva):
        reserva = self.buscar_reserva(numero_reserva)
        if reserva is None:
            raise ErrorNoEncontrado("No existe la reserva: " + str(numero_reserva))
        if reserva.esta_activa() == False:
            raise ErrorConflicto("La reserva ya está cerrada.")
        if reserva.solicitud_numero is not None:
            raise ErrorConflicto("La reserva ya tiene una solicitud asociada: resuelva primero la solicitud.")
        if reserva.esta_asignada():
            ejemplar = self.buscar_ejemplar(reserva.ejemplar_codigo)
            try:
                if ejemplar is not None and ejemplar.reserva_asignada == numero_reserva:
                    if ejemplar.solicitud_asignada is None:
                        ejemplar.liberar_asignacion()
                reserva.ejemplar_codigo = None
                reserva.cancelar()
                self.atender_cola_reservas(reserva.libro_isbn, reserva.codigo_sede)
                self._confirmar()
            except Exception:
                db.session.rollback()
                raise
            return reserva
        reserva.cancelar()
        self._confirmar()
        return reserva

    def reservas_ordenadas_de_libro(self, libro_isbn, codigo_sede):
        pendientes = []
        for reserva in self.reservas:
            if reserva.libro_isbn != libro_isbn:
                continue
            if reserva.codigo_sede != codigo_sede:
                continue
            if reserva.esta_pendiente() == False:
                continue
            pendientes.append(reserva)
        ordenadas = []
        while len(pendientes) > 0:
            primera = pendientes[0]
            for candidata in pendientes:
                if candidata.fecha_reserva < primera.fecha_reserva:
                    primera = candidata
                elif candidata.fecha_reserva == primera.fecha_reserva and candidata.numero < primera.numero:
                    primera = candidata
            ordenadas.append(primera)
            pendientes.remove(primera)
        return ordenadas

    def revisar_reservas_asignadas(self, libro_isbn, codigo_sede):
        for reserva in self.reservas:
            if reserva.libro_isbn != libro_isbn:
                continue
            if reserva.codigo_sede != codigo_sede:
                continue
            if reserva.esta_asignada() == False:
                continue
            if reserva.solicitud_numero is not None:
                continue
            socio = self.buscar_socio(reserva.socio_numero)
            if socio is not None and socio.esta_habilitado():
                continue
            ejemplar = self.buscar_ejemplar(reserva.ejemplar_codigo)
            if ejemplar is not None and ejemplar.reserva_asignada == reserva.numero:
                if ejemplar.solicitud_asignada is None:
                    ejemplar.liberar_asignacion()
            reserva.ejemplar_codigo = None
            reserva.cancelar()

    def atender_cola_reservas(self, libro_isbn, codigo_sede):
        if codigo_sede is None:
            return None
        sede = self.buscar_sede(codigo_sede)
        if sede is None:
            return None
        self.revisar_reservas_asignadas(libro_isbn, codigo_sede)
        ordenadas = self.reservas_ordenadas_de_libro(libro_isbn, codigo_sede)
        ultima_asignada = None
        for reserva in ordenadas:
            socio = self.buscar_socio(reserva.socio_numero)
            if socio is None or socio.esta_habilitado() == False:
                reserva.cancelar()
                continue
            if sede.esta_activa() == False:
                return ultima_asignada
            copia = self.copia_prestable_en_sede(libro_isbn, codigo_sede)
            if copia is None:
                return ultima_asignada
            copia.apartar_para_reserva(reserva.numero)
            reserva.marcar_asignada(copia.codigo)
            ultima_asignada = reserva
        return ultima_asignada

    # ---------- Devoluciones ----------

    def registrar_devolucion(self, numero_prestamo, fecha_devolucion, sede_devolucion, estado_fisico):
        prestamo = self.buscar_prestamo(numero_prestamo)
        if prestamo is None:
            raise ErrorNoEncontrado("No existe el préstamo: " + str(numero_prestamo))
        if prestamo.esta_activo() == False:
            raise ErrorConflicto("El préstamo ya fue devuelto.")
        fecha_validada = validar_fecha(fecha_devolucion, "fecha de devolución")
        self.exigir_sede_activa(sede_devolucion)
        if estado_fisico not in Ejemplar.ESTADOS_FISICOS:
            raise ErrorDatosInvalidos("Estado físico desconocido: " + str(estado_fisico))
        if fecha_validada < prestamo.fecha_prestamo:
            raise ErrorDatosInvalidos("La devolución no puede ser anterior al préstamo.")
        ejemplar = self.buscar_ejemplar(prestamo.ejemplar_codigo)
        if ejemplar is None:
            raise ErrorNoEncontrado("No existe el ejemplar del préstamo.")
        multa = prestamo.multa_acumulada(fecha_validada, self.multa_por_dia)
        try:
            prestamo.registrar_devolucion(fecha_validada, sede_devolucion, estado_fisico, multa)
            ejemplar.mover_a(sede_devolucion)
            ejemplar.registrar_revision_fisica(estado_fisico)
            if ejemplar.ubicacion_actual != ejemplar.sede_pertenencia:
                ejemplar.marcar_pendiente_retorno()
            elif ejemplar.esta_danado():
                ejemplar.marcar_en_reparacion()
            else:
                ejemplar.marcar_disponible()
                self.atender_cola_reservas(ejemplar.libro_isbn, sede_devolucion)
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return prestamo

    # ---------- Logistica con remitos ----------

    def crear_remito_para_solicitud(self, numero_solicitud, fecha_creacion):
        solicitud = self.buscar_solicitud(numero_solicitud)
        if solicitud is None:
            raise ErrorNoEncontrado("No existe la solicitud: " + str(numero_solicitud))
        if solicitud.estado != SolicitudPrestamo.ESTADO_PENDIENTE:
            raise ErrorConflicto("Solo una solicitud pendiente puede tener remito.")
        if solicitud.es_interbibliotecaria() == False:
            raise ErrorDatosInvalidos("Solo las solicitudes interbibliotecarias usan remito.")
        self.exigir_sede_activa(solicitud.sede_origen)
        self.exigir_sede_activa(solicitud.sede_destino)
        if self.buscar_remito_por_solicitud(numero_solicitud) is not None:
            raise ErrorConflicto("La solicitud ya tiene un remito asignado.")
        ejemplar = self.buscar_ejemplar(solicitud.ejemplar_codigo)
        if ejemplar is None:
            raise ErrorNoEncontrado("No existe el ejemplar de la solicitud.")
        if ejemplar.solicitud_asignada != numero_solicitud:
            raise ErrorConflicto("El ejemplar ya no está asignado a esta solicitud.")
        momento = validar_momento(fecha_creacion, "fecha de creación del remito")
        if self.a_fecha(momento) < solicitud.fecha_solicitud:
            raise ErrorDatosInvalidos("El remito no puede crearse antes de la solicitud.")

        codigo = self._siguiente_codigo_remito()
        remito = Remito(codigo, solicitud.sede_origen, solicitud.sede_destino, momento)
        remito.agregar_ejemplar(ejemplar.codigo, solicitud.numero)
        ejemplar.mantener_apartado()
        db.session.add(remito)
        self._confirmar()
        return remito

    def crear_remito_retorno(self, codigo_ejemplar, fecha_creacion):
        ejemplar = self.buscar_ejemplar(codigo_ejemplar)
        if ejemplar is None:
            raise ErrorNoEncontrado("No existe el ejemplar: " + str(codigo_ejemplar))
        if ejemplar.ubicacion_actual is None:
            raise ErrorConflicto("El ejemplar ya está en un envío.")
        if ejemplar.ubicacion_actual == ejemplar.sede_pertenencia:
            raise ErrorConflicto("El ejemplar ya está en su sede de pertenencia.")
        if ejemplar.estado_disponibilidad != Ejemplar.PENDIENTE_RETORNO:
            raise ErrorConflicto("El ejemplar no está pendiente de retorno.")
        if self.prestamo_activo_por_ejemplar(codigo_ejemplar) is not None:
            raise ErrorConflicto("El ejemplar tiene un préstamo activo.")
        if ejemplar.solicitud_asignada is not None or ejemplar.reserva_asignada is not None:
            raise ErrorConflicto("El ejemplar está asignado y no puede retornar.")
        if self.remito_activo_por_ejemplar(codigo_ejemplar) is not None:
            raise ErrorConflicto("El ejemplar ya está en un envío.")
        devolucion = self.ultima_devolucion_de_ejemplar(codigo_ejemplar)
        solicitud_cancelada = False
        for envio in self.remitos:
            if envio.nombre_estado() != Remito.ESTADO_RECIBIDO or envio.es_retorno():
                continue
            for asignacion in envio.asignaciones:
                if asignacion.ejemplar_codigo != codigo_ejemplar:
                    continue
                solicitud = self.buscar_solicitud(asignacion.numero_solicitud)
                if solicitud is not None and solicitud.estado == SolicitudPrestamo.ESTADO_CANCELADA:
                    solicitud_cancelada = True
        if devolucion is None and solicitud_cancelada == False:
            raise ErrorConflicto("El ejemplar no tiene una devolución ni una solicitud cancelada recibida.")
        momento = validar_momento(fecha_creacion, "fecha de creación del retorno")
        self.validar_fecha_de_ejemplar(ejemplar, self.a_fecha(momento))
        for envio in self.remitos:
            recepcion = envio.fecha_de(Remito.ESTADO_RECIBIDO)
            if recepcion is not None and codigo_ejemplar in envio.codigos_ejemplares():
                if momento < recepcion:
                    raise ErrorDatosInvalidos("El retorno no puede crearse antes de la recepción.")
        origen = ejemplar.ubicacion_actual
        destino = ejemplar.sede_pertenencia
        self.exigir_sede_activa(origen)
        self.exigir_sede_activa(destino)

        codigo = self._siguiente_codigo_remito()
        remito = Remito(codigo, origen, destino, momento, Remito.MOTIVO_RETORNO)
        remito.agregar_ejemplar_de_retorno(ejemplar.codigo)
        ejemplar.mantener_apartado()
        db.session.add(remito)
        self._confirmar()
        return remito

    def empaquetar_remito(self, codigo, momento=None):
        remito = self.buscar_remito(codigo)
        if remito is None:
            raise ErrorNoEncontrado("No existe el remito: " + str(codigo))
        remito.empaquetar(momento)
        self._confirmar()
        return remito

    def despachar_remito(self, codigo, momento=None):
        remito = self.buscar_remito(codigo)
        if remito is None:
            raise ErrorNoEncontrado("No existe el remito: " + str(codigo))
        self.exigir_sede_activa(remito.sede_origen)
        self.exigir_sede_activa(remito.sede_destino)
        for asignacion in remito.asignaciones:
            ejemplar = self.buscar_ejemplar(asignacion.ejemplar_codigo)
            if ejemplar is None:
                raise ErrorNoEncontrado("No existe el ejemplar del remito: " + asignacion.ejemplar_codigo)
        try:
            remito.despachar(momento)
            for asignacion in remito.asignaciones:
                ejemplar = self.buscar_ejemplar(asignacion.ejemplar_codigo)
                ejemplar.marcar_en_transito()
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return remito

    def recibir_remito(self, codigo, momento=None, estado_fisico=None):
        remito = self.buscar_remito(codigo)
        if remito is None:
            raise ErrorNoEncontrado("No existe el remito: " + str(codigo))
        if estado_fisico not in Ejemplar.ESTADOS_FISICOS:
            raise ErrorDatosInvalidos("Estado físico desconocido: " + str(estado_fisico))
        # Se comprueban todas las copias antes de cambiar el remito.
        for asignacion in remito.asignaciones:
            if self.buscar_ejemplar(asignacion.ejemplar_codigo) is None:
                raise ErrorNoEncontrado("No existe el ejemplar del remito: " + asignacion.ejemplar_codigo)
        try:
            remito.recibir(momento)
            for asignacion in remito.asignaciones:
                ejemplar = self.buscar_ejemplar(asignacion.ejemplar_codigo)
                ejemplar.registrar_revision_fisica(estado_fisico)
                asignacion.estado_fisico_recepcion = ejemplar.estado_fisico
                ejemplar.mover_a(remito.sede_destino)
                if remito.es_retorno():
                    if ejemplar.esta_danado():
                        ejemplar.marcar_en_reparacion()
                    else:
                        ejemplar.marcar_disponible()
                        destino = self.buscar_sede(remito.sede_destino)
                        if destino is not None and destino.esta_activa():
                            self.atender_cola_reservas(ejemplar.libro_isbn, remito.sede_destino)
                else:
                    if ejemplar.esta_danado():
                        solicitud = self.buscar_solicitud(asignacion.numero_solicitud)
                        solicitud.cancelar()
                        ejemplar.marcar_pendiente_retorno()
                    else:
                        ejemplar.mantener_apartado()
            self._confirmar()
        except Exception:
            db.session.rollback()
            raise
        return remito

    # ---------- Resumen ----------

    def resumen(self):
        return {
            "sedes": Sede.query.count(),
            "socios": Socio.query.count(),
            "libros": Libro.query.count(),
            "ejemplares": Ejemplar.query.count(),
            "solicitudes_pendientes": SolicitudPrestamo.query.filter_by(estado=SolicitudPrestamo.ESTADO_PENDIENTE).count(),
            "prestamos_activos": Prestamo.query.filter_by(estado=Prestamo.ESTADO_ACTIVO).count(),
            "reservas_activas": Reserva.query.filter(Reserva.estado.in_((Reserva.ESTADO_PENDIENTE, Reserva.ESTADO_ASIGNADA))).count(),
            "remitos_activos": Remito.query.filter(Remito.estado_actual.notin_((Remito.ESTADO_RECIBIDO, Remito.ESTADO_CANCELADO))).count(),
        }
