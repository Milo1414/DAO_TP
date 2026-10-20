# Reglas de trabajo para los agentes

## Lectura inicial

Antes de diseñar, programar, modificar o revisar el proyecto, leer AGENTS.md, ENUNCIADO.md y FASES.md. Identificar la fase pendiente y trabajar sobre ella. Si se utilizan otros agentes, cada uno debe recibir y leer los tres documentos.

Este archivo define el estilo y la forma de trabajar. ENUNCIADO.md contiene los requisitos del TP. FASES.md contiene las decisiones de implementación, el orden de trabajo y el progreso.

## Objetivo del código

Es un trabajo universitario en Python. El estudiante debe poder seguir la ejecución, modificar el código y explicar por qué existe cada clase y cada método en la defensa oral.

Priorizar pasos explícitos y nombres claros. Se aceptan más líneas, algunos recorridos adicionales y algo de repetición cuando simplifiquen la comprensión. Mantener las validaciones, la corrección y los requisitos completos.

## Estructura de carpetas y responsabilidades

El proyecto se organiza en pocas carpetas claras:
- Raíz: `main.py` (arranque del sistema), `demo.py` (demostración automatizada), `requirements.txt` (dependencias), `AGENTS.md`.
- `backend/`: entidades del dominio (`sede.py`, `socio.py`, `catalogo.py`, `prestamos.py`, `remito.py`), coordinador (`red.py`), reportes y fábricas (`reportes.py`), conversión JSON (`serializadores.py`), rutas HTTP (`rutas.py`) y aplicación Flask (`app.py`).
- `backend/migracion.py`: preparación y migración de una base SQLite existente, respaldo y revisión de datos heredados. Es el único módulo que usa `sqlite3` directamente.
- `backend/modelos.py`: configuración de Flask-SQLAlchemy, `Configuracion` y activación de claves foráneas.
- `frontend/`: interfaz web con HTML, CSS y JavaScript (`index.html`, `styles.css`, `app.js`), servida por Flask y separada del dominio.
- `tests/`: pruebas con `unittest` (`apoyo.py`, `test_api.py`, `test_orm.py`, `test_patrones.py`, `test_reportes.py`, `test_migracion.py`).
- `Documentacion/`: `ENUNCIADO.md`, `README.md`, `FASES.md`.

Reglas de separación:
- `backend` y `RedBibliotecas` no deben importar módulos del frontend, hacer `input()`, ni contener sentencias SQL.
- `frontend` no implementa reglas de negocio ni interactúa directamente con SQL; usa la API JSON.
- Las entidades usan el ORM de Flask-SQLAlchemy. `backend/migracion.py` contiene el DDL, la conexión `sqlite3` y las consultas de verificación del esquema heredado.
- La API traduce excepciones del dominio a respuestas HTTP; no repite las reglas de negocio.

## Forma de escribir Python

- Usar nombres en español. Clases como `Reserva`, métodos como `registrar_reserva` y variables como `cantidad` o `prestamo`.
- Declarar clases con constructores `__init__` explícitos y asignaciones visibles a `self`.
- Escribir una operación por paso. Usar variables intermedias cuando ayuden a explicar el cálculo.
- Preferir `for`, `while` y condiciones `if / elif / else`.
- Resolver sumas, cantidades, promedios y búsquedas de máximos con contadores, acumuladores y recorridos.
- Preferir listas para colecciones de objetos. Utilizar diccionarios o conjuntos cuando hagan más clara una relación o una agrupación.
- Evitar por defecto comprensiones, generadores, `lambda`, `map`, `filter` y `reduce` cuando se puedan expresar con un recorrido sencillo.
- Evitar por defecto `dataclass`, anotaciones de tipos complejas, decoradores personalizados, reflexión, metaclases y código asíncrono.
- Utilizar sin complicaciones recursos útiles como `f-string`, `super()`, `ABC`, `abstractmethod`, propiedades y excepciones.

Ejemplo del estilo esperado:

```python
def calcular_total(self):
    total = 0
    for elemento in self.elementos:
        total += elemento.importe
    return total
```

## Patrones para la defensa: Factory y Observer

Los dos patrones de diseño del proyecto para explicar en la defensa son:
1. **Factory Method (Creacional)**: para la creación desacoplada de los cuatro reportes.
   - `Reporte` (producto abstracto) y `FabricaReportes` (creador abstracto).
   - Cuatro reportes concretos y cuatro fábricas concretas.
   - La API usa la fábrica concreta para instanciar el reporte y ejecuta polimórficamente `generar()`.
2. **Observer (Comportamiento)**: para la notificación y registro de cambios en el remito.
   - `Remito` (sujeto observable) mantiene la lista de observadores y notifica eventos tras validar transiciones.
   - `ObservadorRemito` (interfaz del observador) con `actualizar(remito, nombre_estado, momento)`.
   - `RegistradorHistorial` (observador concreto) asienta el historial y las fechas por estado.
   - Las validaciones de estado y de cronología permanecen en el modelo; si una transición falla, no se notifica ni se muta el historial.

No agregar Singleton a la interfaz ni introducir patrones artificiales.

## Persistencia en SQLite

- SQLite mediante Flask-SQLAlchemy (SQLAlchemy 2.x), sin ORM adicionales ni frameworks externos.
- Esquema relacional normalizado con claves foráneas activadas explícitamente (`PRAGMA foreign_keys = ON;`).
- Transacciones atómicas en cada operación de negocio (con `commit` y `rollback` ante error).
- `preparar_base` crea las tablas faltantes, respalda la base antes de un cambio de esquema y revisa los datos heredados sin corregirlos en silencio.
- Los objetos se consultan contra la sesión del ORM; no se mantiene una copia global de las entidades.

## Comprobaciones y cambios

- Validar entradas y reglas de negocio. Contemplar colecciones vacías, identificadores repetidos y divisiones por cero cuando correspondan.
- Obligación de validaciones en el dominio: revisar y hacer cumplir las validaciones al agregar, modificar y recuperar datos en todas las clases del modelo. Al modificar un objeto, validar todos los campos nuevos antes de realizar asignaciones; si alguno falla, conservar intactos sus valores anteriores. Al recuperar datos desde persistencia, verificar que los objetos reconstruidos cumplan las reglas del dominio.
- Cerrar conexiones y archivos correctamente. Capturar errores concretos y mostrar mensajes comprensibles.
- Verificar cada cambio con ejemplos o pruebas representativos del comportamiento esperado.
- Mantener los cambios centrados en la fase actual.
- Al terminar una fase, registrar qué se hizo y qué se comprobó en FASES.md.
- Afirmar que algo está implementado o probado solamente cuando exista el código y se haya ejecutado la comprobación.
