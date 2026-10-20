# Punto de arranque de la aplicacion web.
#
# Ejecutar desde la raiz del proyecto:
#     python main.py
# Luego abrir http://127.0.0.1:5000 en el navegador.
from backend.app import crear_aplicacion


def main():
    aplicacion = crear_aplicacion()
    print("Biblioteca iniciada en http://127.0.0.1:5000")
    print("Base SQLite: " + aplicacion.config["RUTA_BASE"])
    if aplicacion.config["PROBLEMAS_BASE"]:
        print("Datos heredados para revisar:")
        for problema in aplicacion.config["PROBLEMAS_BASE"]:
            print(" - " + problema)
    aplicacion.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
