# Genera una base SQLite ficticia para mostrar los casos del sistema.
#
# Ejecutar desde la raiz del proyecto:
#     python crear_base_demo.py
#
# El archivo generado es biblioteca_demo.db y se puede abrir con:
#     $env:BIBLIOTECA_DB = "biblioteca_demo.db"
#     python main.py
import datetime
from pathlib import Path

from backend.app import crear_aplicacion
from backend.modelos import db
from backend.red import RedBibliotecas


RAIZ = Path(__file__).resolve().parent
RUTA = RAIZ / "biblioteca_demo.db"


def crear_datos_basicos(red):
    red.agregar_sede("S1", "Sede Central", "Av. Siempre Viva 742", "555-1001", "08:00-18:00")
    red.agregar_sede("S2", "Sede Norte", "Calle Norte 250", "555-2002", "09:00-17:00")
    red.agregar_sede("S3", "Sede Sur", "Pasaje Sur 815", "555-3003", "08:30-16:30")
    red.agregar_sede("S4", "Sede Historica", "Calle Antigua 120", "555-4004", "10:00-14:00")

    red.agregar_socio(1, "Ana Perez", "ana@ejemplo.com", "555-1101")
    red.agregar_socio(2, "Luis Gomez", "luis@ejemplo.com", "555-2202")
    red.agregar_socio(3, "Marta Diaz", "marta@ejemplo.com", "555-3303")
    red.agregar_socio(4, "Pedro Ruiz", "pedro@ejemplo.com", "555-4404")
    red.agregar_socio(5, "Lucia Fernandez", "lucia@ejemplo.com", "555-5505")
    red.agregar_socio(6, "Diego Sosa", "diego@ejemplo.com", "555-6606")

    red.agregar_libro("L1", "Cien anios de soledad", "Gabriel Garcia Marquez", 1967, "Novela")
    red.agregar_libro("L2", "El principito", "Antoine de Saint-Exupery", 1943, "Infantil")
    red.agregar_libro("L3", "Rayuela", "Julio Cortazar", 1963, "Novela")
    red.agregar_libro("L4", "La casa de los espiritus", "Isabel Allende", 1982, "Novela")
    red.agregar_libro("L5", "Martin Fierro", "Jose Hernandez", 1872, "Poesia")
    red.agregar_libro("L6", "Ficciones", "Jorge Luis Borges", 1944, "Cuento")

    red.agregar_ejemplar("E1", "L1", "S1")
    red.agregar_ejemplar("E2", "L1", "S2")
    red.agregar_ejemplar("E3", "L1", "S3")
    red.agregar_ejemplar("E4", "L2", "S1")
    red.agregar_ejemplar("E5", "L2", "S2")
    red.agregar_ejemplar("E6", "L2", "S3")
    red.agregar_ejemplar("E7", "L3", "S1")
    red.agregar_ejemplar("E8", "L3", "S2")
    red.agregar_ejemplar("E9", "L4", "S1")
    red.agregar_ejemplar("E10", "L4", "S2")
    red.agregar_ejemplar("E11", "L5", "S3")
    red.agregar_ejemplar("E12", "L6", "S2")
    red.agregar_ejemplar("E13", "L5", "S1")
    red.agregar_ejemplar("E14", "L6", "S3")
    red.agregar_ejemplar("E15", "L2", "S1")
    red.agregar_ejemplar("E16", "L6", "S4")


def crear_casos_locales(red):
    # Prestamo local entregado y devuelto en termino.
    solicitud = red.registrar_solicitud(
        1, "L1", "E1", "S1", "S1", datetime.date(2026, 9, 1), "local"
    )
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 9, 1))
    red.registrar_devolucion(prestamo.numero, datetime.date(2026, 9, 10), "S1", "bueno")

    # Prestamo local activo y vencido: al 20/10/2026 acumula 21 dias de atraso.
    solicitud = red.registrar_solicitud(
        2, "L2", "E4", "S1", "S1", datetime.date(2026, 9, 15), "local"
    )
    red.entregar_solicitud(solicitud.numero, datetime.date(2026, 9, 15))

    # Prestamo local activo todavia dentro del plazo.
    solicitud = red.registrar_solicitud(
        3, "L4", "E10", "S2", "S2", datetime.date(2026, 10, 15), "local"
    )
    red.entregar_solicitud(solicitud.numero, datetime.date(2026, 10, 15))

    # Devolucion con danio: la copia queda en reparacion.
    solicitud = red.registrar_solicitud(
        6, "L6", "E12", "S2", "S2", datetime.date(2026, 9, 5), "local"
    )
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 9, 5))
    red.registrar_devolucion(
        prestamo.numero, datetime.date(2026, 9, 10), "S2", "requiere_reparacion"
    )

    # Solicitud local cancelada: la copia vuelve a estar disponible.
    solicitud = red.registrar_solicitud(
        3, "L3", "E7", "S1", "S1", datetime.date(2026, 10, 1), "local"
    )
    red.cancelar_solicitud(solicitud.numero)

    # Solicitud local pendiente: la copia queda apartada.
    red.registrar_solicitud(
        6, "L2", "E5", "S2", "S2", datetime.date(2026, 10, 10), "local"
    )

    # Reserva cumplida: se crea, se usa para una solicitud y termina entregada.
    red.registrar_reserva(5, "L2", "S1", datetime.date(2026, 8, 15))
    solicitud = red.registrar_solicitud(
        5, "L2", "E15", "S1", "S1", datetime.date(2026, 8, 20), "local"
    )
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 8, 20))
    red.registrar_devolucion(prestamo.numero, datetime.date(2026, 8, 25), "S1", "bueno")

    # Reserva asignada a una copia disponible, sin solicitud todavia.
    red.registrar_reserva(1, "L6", "S3", datetime.date(2026, 9, 1))

    # Reserva pendiente: no hay copias de L4 en S3.
    red.registrar_reserva(3, "L4", "S3", datetime.date(2026, 9, 10))

    # Reserva cancelada y socio inhabilitado.
    reserva = red.registrar_reserva(4, "L3", "S3", datetime.date(2026, 9, 15))
    red.cancelar_reserva(reserva.numero)
    red.inhabilitar_socio(4)


def mover_remito_hasta_recibir(red, remito, momento):
    red.empaquetar_remito(remito.codigo, momento)
    red.despachar_remito(remito.codigo, momento + datetime.timedelta(hours=1))
    red.recibir_remito(remito.codigo, momento + datetime.timedelta(hours=2))


def crear_casos_interbibliotecarios(red):
    # Interbibliotecario completo: prestamo y retorno recibidos.
    solicitud = red.registrar_solicitud(
        1, "L1", "E2", "S2", "S1", datetime.date(2026, 8, 1), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 8, 1, 9, 0)
    )
    mover_remito_hasta_recibir(red, remito, datetime.datetime(2026, 8, 1, 10, 0))
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 8, 2))
    red.registrar_devolucion(prestamo.numero, datetime.date(2026, 8, 12), "S1", "bueno")
    retorno = red.crear_remito_retorno("E2", datetime.datetime(2026, 8, 13, 9, 0))
    mover_remito_hasta_recibir(red, retorno, datetime.datetime(2026, 8, 13, 10, 0))

    # Interbibliotecario con devolucion fuera de la sede y sin remito de retorno.
    solicitud = red.registrar_solicitud(
        3, "L3", "E8", "S2", "S1", datetime.date(2026, 8, 5), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 8, 5, 9, 0)
    )
    mover_remito_hasta_recibir(red, remito, datetime.datetime(2026, 8, 5, 10, 0))
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 8, 6))
    red.registrar_devolucion(prestamo.numero, datetime.date(2026, 8, 25), "S1", "bueno")

    # Remito despachado: la copia esta en transito.
    solicitud = red.registrar_solicitud(
        2, "L4", "E9", "S1", "S2", datetime.date(2026, 9, 20), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 9, 20, 9, 0)
    )
    red.empaquetar_remito(remito.codigo, datetime.datetime(2026, 9, 21, 9, 0))
    red.despachar_remito(remito.codigo, datetime.datetime(2026, 9, 22, 9, 0))

    # Remito pendiente de empaque.
    solicitud = red.registrar_solicitud(
        3, "L5", "E13", "S1", "S3", datetime.date(2026, 10, 1), "interbibliotecario"
    )
    red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 10, 1, 9, 0)
    )

    # Remito empaquetado, todavia sin despachar.
    solicitud = red.registrar_solicitud(
        6, "L2", "E6", "S3", "S1", datetime.date(2026, 10, 5), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 10, 5, 9, 0)
    )
    red.empaquetar_remito(remito.codigo, datetime.datetime(2026, 10, 6, 9, 0))

    # Remito recibido, pero la solicitud aun no fue entregada al socio.
    solicitud = red.registrar_solicitud(
        5, "L5", "E11", "S3", "S2", datetime.date(2026, 9, 25), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 9, 25, 9, 0)
    )
    mover_remito_hasta_recibir(red, remito, datetime.datetime(2026, 9, 25, 10, 0))

    # Devolucion pendiente con remito de retorno empaquetado.
    solicitud = red.registrar_solicitud(
        1, "L1", "E3", "S3", "S1", datetime.date(2026, 9, 1), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 9, 1, 9, 0)
    )
    mover_remito_hasta_recibir(red, remito, datetime.datetime(2026, 9, 1, 10, 0))
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 9, 2))
    red.registrar_devolucion(prestamo.numero, datetime.date(2026, 9, 15), "S1", "bueno")
    retorno = red.crear_remito_retorno("E3", datetime.datetime(2026, 10, 1, 9, 0))
    red.empaquetar_remito(retorno.codigo, datetime.datetime(2026, 10, 2, 9, 0))


def main():
    if RUTA.exists():
        RUTA.unlink()
    aplicacion = crear_aplicacion(str(RUTA))
    with aplicacion.app_context():
        red = RedBibliotecas()
        crear_datos_basicos(red)
        crear_casos_locales(red)
        crear_casos_interbibliotecarios(red)
        red.dar_baja_sede("S4")
        if aplicacion.config["PROBLEMAS_BASE"]:
            print("La base demo quedo con observaciones:")
            for problema in aplicacion.config["PROBLEMAS_BASE"]:
                print(" - " + problema)
        db.session.remove()
        db.engine.dispose()
    print("Base demo generada: " + str(RUTA))


if __name__ == "__main__":
    main()
