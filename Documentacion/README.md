# Biblioteca: Sistema de Préstamos Interbibliotecarios

Trabajo práctico integrador de la materia Desarrollo de Aplicaciones con Objetos.
El sistema administra una red de bibliotecas, sus socios, el catálogo, los
préstamos, las reservas y la logística de envío de ejemplares entre sedes.

La aplicación tiene dos partes:

- `backend/`: dominio en Python, persistencia SQLite con Flask-SQLAlchemy y API JSON.
- `frontend/`: interfaz web en HTML, CSS y JavaScript, servida por Flask.

No se usan frameworks de frontend ni una segunda base de datos. El navegador
consulta la API y la API trabaja contra el ORM; toda la lógica de negocio queda
en el dominio.

## Funcionalidades

- Alta, modificación, baja y reactivación de sedes.
- Alta, modificación, habilitación e inhabilitación de socios.
- Administración de libros y ejemplares físicos.
- Consulta de disponibilidad por libro y sede.
- Solicitudes de préstamo local e interbibliotecario.
- Reservas con cola FIFO por libro y sede.
- Entrega de solicitudes y registro de préstamos.
- Devoluciones con estado físico y cálculo de multa por atraso.
- Remitos de préstamo y de retorno con empaquetado, despacho y recepción.
- Historial de estados del remito.
- Cuatro reportes no triviales.
- Revisión de datos heredados al abrir una base existente.

## Requisitos

- Python 3.10 o superior.
- Las dependencias de `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

## Ejecución

Desde la raíz del proyecto:

```powershell
python main.py
```

Luego abrir `http://127.0.0.1:5000` en el navegador.

La base se crea o se prepara automáticamente en `biblioteca.db`. También se
puede indicar otra ruta con la variable de entorno `BIBLIOTECA_DB`:

```powershell
$env:BIBLIOTECA_DB = "C:\ruta\biblioteca.db"
python main.py
```

Para ejecutar una demostración automática que usa una base temporal y no
modifica `biblioteca.db`:

```powershell
python demo.py
```

## Estructura

```text
.
├── main.py                  arranque del servidor Flask
├── demo.py                  demostración del circuito principal
├── requirements.txt
├── biblioteca.db            base SQLite (no se versiona)
├── backend/
│   ├── app.py               fábrica Flask, frontend y manejo de errores
│   ├── rutas.py             endpoints de la API JSON
│   ├── red.py               coordinador de las operaciones de negocio
│   ├── modelos.py           SQLAlchemy, configuración y claves foráneas
│   ├── sede.py              entidad Sede
│   ├── socio.py             entidad Socio
│   ├── catalogo.py          entidades Libro y Ejemplar
│   ├── prestamos.py         Solicitud, Préstamo y Reserva
│   ├── remito.py            Remito, asignaciones, historial y Observer
│   ├── reportes.py          Factory Method y los cuatro reportes
│   ├── serializadores.py    conversión de entidades a JSON
│   ├── validaciones.py      validaciones compartidas
│   ├── errores.py           excepciones del dominio
│   └── migracion.py         respaldo, migración y revisión de datos heredados
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
└── Documentacion/
```

## API

Todas las rutas de negocio se publican bajo `/api` y devuelven JSON.

### Consultas generales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/salud` | Estado de la API, base usada y problemas de datos |
| GET | `/api/resumen` | Cantidades generales del sistema |
| GET | `/api/listados` | Sedes, socios, libros, ejemplares, solicitudes, préstamos, reservas y remitos |

### Sedes y socios

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/sedes` | Listar o crear sedes |
| GET/PUT | `/api/sedes/<codigo>` | Consultar o modificar una sede |
| POST | `/api/sedes/<codigo>/baja` | Dar de baja una sede |
| POST | `/api/sedes/<codigo>/reactivacion` | Reactivar una sede |
| GET/POST | `/api/socios` | Listar o crear socios |
| GET/PUT | `/api/socios/<numero>` | Consultar o modificar un socio |
| POST | `/api/socios/<numero>/habilitar` | Habilitar un socio |
| POST | `/api/socios/<numero>/inhabilitar` | Inhabilitar un socio |

### Catálogo y disponibilidad

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/libros` | Listar o crear libros |
| GET/PUT | `/api/libros/<isbn>` | Consultar o modificar un libro |
| GET/POST | `/api/ejemplares` | Listar o crear ejemplares; acepta `isbn` y `sede` como filtros |
| GET | `/api/ejemplares/<codigo>` | Consultar un ejemplar |
| POST | `/api/ejemplares/<codigo>/reparar` | Reparar una copia en reparación |

### Solicitudes, reservas y préstamos

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/solicitudes` | Listar o registrar solicitudes; acepta `estado` como filtro |
| GET | `/api/solicitudes/<numero>` | Consultar una solicitud |
| POST | `/api/solicitudes/<numero>/cancelar` | Cancelar una solicitud pendiente |
| POST | `/api/solicitudes/<numero>/entregar` | Entregar y crear el préstamo |
| GET/POST | `/api/reservas` | Listar o registrar reservas |
| POST | `/api/reservas/<numero>/cancelar` | Cancelar una reserva activa |
| GET | `/api/prestamos` | Listar préstamos; acepta `estado` como filtro |
| GET | `/api/prestamos/<numero>` | Consultar un préstamo |
| POST | `/api/prestamos/<numero>/devolucion` | Registrar una devolución |

### Remitos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/remitos` | Listar remitos; acepta `estado` y `motivo` |
| GET | `/api/remitos/<codigo>` | Consultar un remito |
| GET | `/api/remitos/<codigo>/historial` | Consultar solo el historial |
| POST | `/api/remitos/prestamo` | Crear remito para una solicitud interbibliotecaria |
| POST | `/api/remitos/retorno` | Crear remito de retorno para una copia pendiente |
| POST | `/api/remitos/<codigo>/empaquetar` | Pasar a empaquetado |
| POST | `/api/remitos/<codigo>/despachar` | Pasar a despachado y poner las copias en tránsito |
| POST | `/api/remitos/<codigo>/recibir` | Recibir en destino y registrar el estado físico |

### Reportes

| Ruta | Contenido |
|---|---|
| `/api/reportes/activos-vencidos` | Préstamos activos y vencidos por sede, con atraso y multa |
| `/api/reportes/disponibilidad` | Inventario por sede y libro, sin duplicar copias |
| `/api/reportes/libros-solicitados` | Ranking de libros pedidos entre sedes |
| `/api/reportes/movimiento` | Envíos por origen/destino, tiempos e incidencias |

Los reportes aceptan filtros opcionales por query string. Por ejemplo:
`/api/reportes/disponibilidad?sede=S1&isbn=L1` o
`/api/reportes/libros-solicitados?desde=2026-01-01&hasta=2026-01-31`.

Los errores se devuelven con un código HTTP y un cuerpo como
`{"error": "mensaje comprensible"}`.

## Reglas de negocio principales

- No se presta una copia que no esté disponible, que esté dañada, en tránsito
  o asignada a otra operación.
- No se atiende a un socio inhabilitado ni se inicia una operación desde o hacia
  una sede dada de baja.
- La sede de origen debe ser la sede de pertenencia de la copia.
- Una solicitud aparta la copia desde su registro y no permite que otra
  solicitud la use.
- El préstamo interbibliotecario necesita un remito recibido antes de la entrega.
- La reserva es por libro y sede; la cola es FIFO y solo asigna copias
  prestables de esa sede.
- Una devolución fuera de la sede de pertenencia deja la copia pendiente de
  retorno, no disponible para préstamos.
- Una copia dañada no vuelve a estar disponible hasta que se repara.
- Empaquetar, despachar y recibir son estados consecutivos; una transición
  inválida no cambia el estado ni agrega historial.
- El plazo de préstamo es de 14 días y la multa de 100 pesos por día de atraso;
  ambos valores se guardan en la tabla `configuracion`.

## Patrones de diseño

### Factory Method

`Reporte` es el producto abstracto y `FabricaReportes` el creador abstracto.
Cada fábrica concreta crea uno de los cuatro reportes. La API solicita el
reporte a la fábrica y ejecuta `generar()` de forma polimórfica.

### Observer

`Remito` es el sujeto observable. `ObservadorRemito` define la interfaz y
`RegistradorHistorial` es el observador concreto que guarda una fila por cada
estado. El remito valida la transición y la cronología antes de notificar; si
algo falla, no cambia el estado ni el historial.

## Persistencia y migración

- SQLite se usa mediante Flask-SQLAlchemy.
- Las claves foráneas se activan en cada conexión con `PRAGMA foreign_keys = ON;`.
- Cada operación de negocio confirma con `commit`; ante un error se hace
  `rollback`.
- Al abrir una base existente, `preparar_base`:
  1. crea las tablas que falten;
  2. si falta la columna `estado_fisico_recepcion` en `remito_ejemplares`, crea
     un respaldo `.respaldo-AAAA...` y agrega la columna;
  3. siembra la configuración que falte;
  4. revisa los datos heredados y los informa en `/api/salud` sin corregirlos.
- Una base heredada con datos inválidos sigue funcionando, pero el problema
  queda visible para que una persona lo resuelva.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

La suite usa bases SQLite temporales. Cubre la API, las reglas de préstamo y
retorno, reservas, reportes, patrones, persistencia, migración y validaciones
atómicas.

## Interfaz web

El frontend permite operar el sistema completo desde el navegador:
sedes, socios, catálogo, solicitudes, reservas, préstamos, devoluciones,
remitos, historial y reportes. No contiene reglas de negocio: muestra los
errores de la API y vuelve a consultar los listados después de cada operación.
