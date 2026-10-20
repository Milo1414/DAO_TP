# Errores del dominio.
#
# Los tres errores heredan de ValueError para conservar la compatibilidad
# con las comprobaciones de negocio que ya esperaban ese tipo. Cada uno
# permite que la API responda con un codigo HTTP distinto:
# - ErrorDatosInvalidos -> 400
# - ErrorNoEncontrado   -> 404
# - ErrorConflicto      -> 409


class ErrorAplicacion(ValueError):
    pass


class ErrorDatosInvalidos(ErrorAplicacion):
    pass


class ErrorNoEncontrado(ErrorAplicacion):
    pass


class ErrorConflicto(ErrorAplicacion):
    pass
