# Funciones de validacion compartidas.
#
# Se usan al crear y al modificar datos, y tambien al revisar datos
# heredados de una base anterior. No dependen de Flask ni del ORM para
# poder probarse con objetos simples.
import datetime

from backend.errores import ErrorDatosInvalidos


def validar_texto(valor, descripcion, maximo=200):
    if valor is None:
        raise ErrorDatosInvalidos("Falta el dato: " + descripcion)
    if isinstance(valor, str) == False:
        raise ErrorDatosInvalidos(descripcion + " debe ser un texto.")
    texto = valor.strip()
    if texto == "":
        raise ErrorDatosInvalidos("Falta el dato: " + descripcion)
    if len(texto) > maximo:
        raise ErrorDatosInvalidos(descripcion + " no puede superar los " + str(maximo) + " caracteres.")
    return texto


def validar_codigo(valor, descripcion):
    # Los codigos internos no llevan espacios. Se aceptan letras (con o sin
    # tilde), numeros, guion, guion bajo y punto. No se interpreta como ISBN
    # real: el ISBN del TP es el codigo interno del catalogo.
    texto = validar_texto(valor, descripcion, 40)
    for caracter in texto:
        if caracter.isalnum():
            continue
        if caracter in "-_.":
            continue
        raise ErrorDatosInvalidos(descripcion + " contiene un caracter no permitido: " + caracter)
    return texto


def validar_entero(valor, descripcion, minimo=0, maximo=None):
    if valor is None:
        raise ErrorDatosInvalidos("Falta el dato: " + descripcion)
    if isinstance(valor, bool):
        raise ErrorDatosInvalidos(descripcion + " debe ser un numero entero.")
    if isinstance(valor, int):
        entero = valor
    elif isinstance(valor, float):
        if valor.is_integer() == False:
            raise ErrorDatosInvalidos(descripcion + " debe ser un numero entero: " + str(valor))
        entero = int(valor)
    elif isinstance(valor, str):
        texto = valor.strip()
        if texto == "":
            raise ErrorDatosInvalidos("Falta el dato: " + descripcion)
        if texto.isdigit():
            entero = int(texto)
        elif texto.startswith("-") and texto[1:].isdigit():
            entero = int(texto)
        else:
            raise ErrorDatosInvalidos(descripcion + " debe ser un numero entero: " + str(valor))
    else:
        raise ErrorDatosInvalidos(descripcion + " debe ser un numero entero.")
    if entero < minimo:
        raise ErrorDatosInvalidos(descripcion + " no puede ser menor a " + str(minimo) + ".")
    if maximo is not None and entero > maximo:
        raise ErrorDatosInvalidos(descripcion + " no puede ser mayor a " + str(maximo) + ".")
    return entero


def validar_anio(valor, descripcion="anio del libro"):
    # Regla del proyecto: se aceptan obras desde el anio 1000 y hasta el
    # anio en curso. Un libro no puede haberse publicado en el futuro.
    anio_actual = datetime.date.today().year
    anio = validar_entero(valor, descripcion, 1000, anio_actual)
    return anio


def validar_fecha(valor, descripcion):
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    raise ErrorDatosInvalidos(descripcion + " debe ser una fecha valida.")


def validar_momento(valor, descripcion):
    if isinstance(valor, datetime.datetime):
        return valor
    if isinstance(valor, datetime.date):
        return datetime.datetime.combine(valor, datetime.time(0, 0))
    raise ErrorDatosInvalidos(descripcion + " debe ser una fecha y hora valida.")


def validar_telefono(valor, descripcion="telefono"):
    texto = validar_texto(valor, descripcion, 40)
    caracteres_permitidos = "0123456789 -+()"
    cantidad_digitos = 0
    for caracter in texto:
        if caracter.isalpha():
            raise ErrorDatosInvalidos(descripcion + " no puede contener letras: " + texto)
        if caracter not in caracteres_permitidos:
            raise ErrorDatosInvalidos(descripcion + " contiene caracteres no permitidos: " + caracter)
        if caracter.isdigit():
            cantidad_digitos = cantidad_digitos + 1
    if cantidad_digitos < 3:
        raise ErrorDatosInvalidos(descripcion + " debe contener al menos 3 digitos: " + texto)
    return texto


def validar_email(valor, descripcion="email del socio"):
    texto = validar_texto(valor, descripcion, 254)
    if " " in texto:
        raise ErrorDatosInvalidos(descripcion + " no puede contener espacios: " + texto)
    if texto.count("@") != 1:
        raise ErrorDatosInvalidos(descripcion + " debe contener un unico '@': " + texto)
    partes = texto.split("@")
    usuario = partes[0]
    dominio = partes[1]
    if usuario == "" or dominio == "":
        raise ErrorDatosInvalidos(descripcion + " debe contener usuario y dominio: " + texto)
    if "." not in dominio:
        raise ErrorDatosInvalidos(descripcion + " debe contener un dominio con '.' (ej: socio@mail.com): " + texto)
    partes_dominio = dominio.split(".")
    for parte in partes_dominio:
        if parte == "":
            raise ErrorDatosInvalidos(descripcion + " tiene un dominio invalido: " + texto)
    return texto


def validar_horario(valor, descripcion="horario de sede"):
    # Formato elegido por el proyecto: HH:MM-HH:MM, ambas horas del mismo dia.
    # Por ejemplo 09:00-18:00. Se exigen dos digitos por componente.
    texto = validar_texto(valor, descripcion, 20)
    partes = texto.split("-")
    if len(partes) != 2:
        raise ErrorDatosInvalidos(descripcion + " debe tener formato HH:MM-HH:MM (ej: 08:00-18:00): " + texto)
    apertura = partes[0].strip()
    cierre = partes[1].strip()
    partes_apertura = apertura.split(":")
    partes_cierre = cierre.split(":")
    if len(partes_apertura) != 2 or len(partes_cierre) != 2:
        raise ErrorDatosInvalidos(descripcion + " debe tener formato HH:MM-HH:MM (ej: 08:00-18:00): " + texto)
    if (len(partes_apertura[0]) != 2 or len(partes_apertura[1]) != 2 or
            len(partes_cierre[0]) != 2 or len(partes_cierre[1]) != 2):
        raise ErrorDatosInvalidos(descripcion + " debe tener dos digitos para horas y minutos (ej: 08:00-18:00): " + texto)
    if (partes_apertura[0].isdigit() == False or partes_apertura[1].isdigit() == False or
            partes_cierre[0].isdigit() == False or partes_cierre[1].isdigit() == False):
        raise ErrorDatosInvalidos(descripcion + " contiene caracteres no numericos en horas o minutos: " + texto)
    hora_apertura = int(partes_apertura[0])
    minuto_apertura = int(partes_apertura[1])
    hora_cierre = int(partes_cierre[0])
    minuto_cierre = int(partes_cierre[1])
    if hora_apertura > 23 or hora_cierre > 23:
        raise ErrorDatosInvalidos(descripcion + " tiene horas fuera del rango 00-23: " + texto)
    if minuto_apertura > 59 or minuto_cierre > 59:
        raise ErrorDatosInvalidos(descripcion + " tiene minutos fuera del rango 00-59: " + texto)
    minutos_apertura = hora_apertura * 60 + minuto_apertura
    minutos_cierre = hora_cierre * 60 + minuto_cierre
    if minutos_cierre <= minutos_apertura:
        raise ErrorDatosInvalidos(descripcion + " debe tener cierre posterior a apertura dentro del mismo dia: " + texto)
    return f"{hora_apertura:02d}:{minuto_apertura:02d}-{hora_cierre:02d}:{minuto_cierre:02d}"


def validar_estado_fisico(valor):
    estados = ("bueno", "deteriorado", "requiere_reparacion")
    if valor not in estados:
        raise ErrorDatosInvalidos("Estado fisico no valido: " + str(valor))
    return valor


def validar_tipo_solicitud(valor):
    tipos = ("local", "interbibliotecario")
    if valor not in tipos:
        raise ErrorDatosInvalidos("Tipo de solicitud no valido: " + str(valor))
    return valor
