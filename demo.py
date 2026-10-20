# Demostracion automatica del circuito principal.
#
# Usa una base SQLite temporal para no modificar biblioteca.db. No abre el
# servidor ni pide datos por teclado: crea los datos, ejecuta las operaciones
# y muestra el estado final de las copias.
#
# Ejecutar desde la raiz del proyecto:
#     python demo.py
import datetime
import os
import tempfile

from backend.app import crear_aplicacion
from backend.modelos import db
from backend.red import RedBibliotecas


def main():
    carpeta = tempfile.TemporaryDirectory()
    ruta = os.path.join(carpeta.name, "demo.db")
    aplicacion = crear_aplicacion(ruta)
    with aplicacion.app_context():
        red = RedBibliotecas()
        preparar_datos(red)
        prestamo_local(red)
        prestamo_interbibliotecario(red)
        mostrar_estado(red)
        db.session.remove()
        db.engine.dispose()
    carpeta.cleanup()
    print("Demostracion terminada. La base temporal fue eliminada.")


def preparar_datos(red):
    print("1. Se crean dos sedes, dos socios y un libro con dos copias.")
    red.agregar_sede("S1", "Sede Central", "Calle 1", "555-1234", "08:00-18:00")
    red.agregar_sede("S2", "Sede Norte", "Calle 2", "555-5678", "09:00-17:00")
    red.agregar_socio(1, "Ana Perez", "ana@mail.com", "555-1111")
    red.agregar_socio(2, "Luis Gomez", "luis@mail.com", "555-2222")
    red.agregar_libro("L1", "El libro de prueba", "Autor Ejemplo", 2020, "Novela")
    red.agregar_ejemplar("E1", "L1", "S1")
    red.agregar_ejemplar("E2", "L1", "S2")


def prestamo_local(red):
    print("2. Prestamo local en S1, entrega y devolucion.")
    solicitud = red.registrar_solicitud(
        1, "L1", "E1", "S1", "S1", datetime.date(2026, 1, 5), "local"
    )
    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 1, 5))
    red.registrar_devolucion(
        prestamo.numero, datetime.date(2026, 1, 10), "S1", "bueno"
    )


def prestamo_interbibliotecario(red):
    print("3. Prestamo interbibliotecario S2 -> S1 con remito y retorno.")
    solicitud = red.registrar_solicitud(
        2, "L1", "E2", "S2", "S1", datetime.date(2026, 1, 10), "interbibliotecario"
    )
    remito = red.crear_remito_para_solicitud(
        solicitud.numero, datetime.datetime(2026, 1, 10, 10, 0)
    )
    red.empaquetar_remito(remito.codigo, datetime.datetime(2026, 1, 10, 11, 0))
    red.despachar_remito(remito.codigo, datetime.datetime(2026, 1, 10, 12, 0))
    red.recibir_remito(remito.codigo, datetime.datetime(2026, 1, 10, 13, 0))

    prestamo = red.entregar_solicitud(solicitud.numero, datetime.date(2026, 1, 11))
    red.registrar_devolucion(
        prestamo.numero, datetime.date(2026, 1, 15), "S1", "requiere_reparacion"
    )

    retorno = red.crear_remito_retorno(
        "E2", datetime.datetime(2026, 1, 16, 9, 0)
    )
    red.empaquetar_remito(retorno.codigo, datetime.datetime(2026, 1, 16, 10, 0))
    red.despachar_remito(retorno.codigo, datetime.datetime(2026, 1, 16, 11, 0))
    red.recibir_remito(retorno.codigo, datetime.datetime(2026, 1, 16, 12, 0))
    red.reparar_ejemplar("E2")


def mostrar_estado(red):
    print("4. Estado final:")
    for ejemplar in red.ejemplares:
        print(
            "   "
            + ejemplar.codigo
            + ": "
            + ejemplar.estado_disponibilidad
            + " en "
            + str(ejemplar.ubicacion_actual)
        )
    resumen = red.resumen()
    print(
        "   solicitudes pendientes: "
        + str(resumen["solicitudes_pendientes"])
        + ", prestamos activos: "
        + str(resumen["prestamos_activos"])
    )


if __name__ == "__main__":
    main()
