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
- Gráficos de barras en la app y en los cuatro PDF, junto con las tablas.
- Login del personal y administración de cuentas persistentes.
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

La demo incluye las cuentas `CamiloMartin`, `CatalinaZapata` y `MelinaGigena`,
cargadas con las contraseñas indicadas por sus titulares. En una base sin
usuarios, la pantalla permite crear la primera cuenta. Las otras se crean en
**Administración → Usuarios**. Los socios no ingresan al sistema.

La base se crea o se prepara automáticamente en `biblioteca.db`. También se
puede indicar otra ruta con la variable de entorno `BIBLIOTECA_DB`.

Para abrir la aplicación con la base ficticia versionada, que ya contiene
todos los casos de uso:

```powershell
$env:BIBLIOTECA_DB = "biblioteca_demo.db"
python main.py
```

La base ficticia se puede regenerar con `python crear_base_demo.py`. Ese
script usa el ORM y las operaciones de `RedBibliotecas`, no SQL manual, y
reemplaza `biblioteca_demo.db` con datos de ejemplo completos.
La regeneración también elimina sus cuentas: la nueva base pedirá crear la
primera. El generador no contiene ni vuelve a cargar credenciales del personal.

La base local de trabajo es `biblioteca.db`: no se versiona porque puede
contener datos propios. La base ficticia `biblioteca_demo.db` sí se versiona
para que el proyecto se pueda abrir y probar sin cargar datos a mano.

## Estructura

```text
.
├── main.py                  arranque del servidor Flask
├── crear_base_demo.py       genera biblioteca_demo.db con el ORM
├── biblioteca_demo.db       base ficticia con todos los casos
├── requirements.txt
├── biblioteca.db            base SQLite local (no se versiona)
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
│   ├── reportes_pdf.py      presentación y descarga de los resultados en PDF
│   ├── reportes_graficos.py series compartidas por los gráficos web y PDF
│   ├── usuarios.py          cuentas del personal y hashes de contraseñas
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
    ├── ENUNCIADO.md
    ├── README.md
    ├── FASES.md
    └── GUIA_DEFENSA.md
```

## API

Todas las rutas de negocio se publican bajo `/api` y devuelven JSON.
Los cuatro reportes también permiten descargar PDF con `formato=pdf`.
Las rutas de negocio, usuarios y descargas requieren una sesión activa.

### Acceso del personal

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/sesion` | Usuario de la sesión y si falta crear la primera cuenta; pública |
| POST | `/api/login` | Recibe `usuario` y `contrasena`; pública |
| POST | `/api/primer-usuario` | Recibe `usuario`, `nombre` y `contrasena`; después del primer registro responde 403 |
| POST | `/api/logout` | Cierra la sesión |
| GET/POST | `/api/usuarios` | Listar o crear cuentas del personal |
| POST | `/api/usuarios/<id>/estado` | Activar o desactivar, con `{"activa": true}` o `false` |

El servidor devuelve 401 si falta la sesión o la cuenta está desactivada.
Una cuenta no puede desactivarse a sí misma y las cuentas no se borran.

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
| POST | `/api/solicitudes/<numero>/cancelar` | Cancelar una solicitud pendiente antes del despacho o tras la recepción |
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
| POST | `/api/remitos/<codigo>/recibir` | Recibir en destino; exige `estado_fisico` observado |

La recepción recibe, por ejemplo:

```json
{"estado_fisico": "bueno", "momento": "2026-11-16T10:00:00"}
```

`estado_fisico` admite `bueno`, `deteriorado` o `requiere_reparacion`.
`momento` es opcional; se usa la hora local si se omite. Los momentos con
zona horaria (`Z` o un desplazamiento como `+00:00`) se rechazan con HTTP 400.

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

Para descargar un documento, usá **Reportes → Generar reporte → Descargar PDF**.
También podés solicitar, por ejemplo,
`/api/reportes/disponibilidad?sede=S1&isbn=L1&formato=pdf`.
El PDF incluye filtros, alcance, utilidad para la gestión, gráficos y tablas de resultados;
se genera en memoria con ReportLab y consulta los datos al descargar.

`reportes_graficos.preparar_graficos()` transforma las filas ya calculadas en
etiquetas, series, colores y valores. El JSON incluye `graficos`; HTML/CSS
dibuja las barras en pantalla y ReportLab dibuja las mismas series en PDF.
Vencidos es parte de activos: el gráfico separa al día (`activos - vencidos`)
y vencidos. Disponibilidad suma por sede únicamente los estados de las copias,
sin contar las reservas como ejemplares. Movimiento separa cantidades de envíos
y horas de tránsito. Se conserva todo el ranking y una escala común por gráfico.

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
- Antes del despacho, cancelar la solicitud cancela también el remito y libera
  la copia. En tránsito se espera la recepción. Después de recibir, cancelar la
  solicitud deja la copia pendiente de retorno, aunque nunca se haya prestado.
- Las nuevas solicitudes y entregas no pueden ser anteriores a la última
  devolución o recepción del ejemplar. Una solicitud que usa una reserva no
  puede ser anterior a esa reserva.
- La reserva es por libro y sede; la cola es FIFO y solo asigna copias
  prestables de esa sede.
- Una devolución fuera de la sede de pertenencia deja la copia pendiente de
  retorno, no disponible para préstamos.
- Una copia dañada no vuelve a estar disponible hasta que se repara.
- Empaquetar, despachar y recibir son estados consecutivos; una transición
  inválida no cambia el estado ni agrega historial.
- El remito puede terminar `cancelado` antes del despacho y conserva todos sus
  eventos. Los reportes cuentan esos remitos por separado de los pendientes.
- La recepción guarda la revisión física informada. Si un envío de préstamo
  llega requiriendo reparación, se cancela la solicitud y se permite retornar
  la copia; al recibir el retorno dañado queda en reparación.
- El plazo de préstamo es de 14 días y la multa de 100 pesos por día de atraso;
  ambos valores se guardan en la tabla `configuracion`.

## Cumplimiento del enunciado

### Procesos obligatorios

| Proceso | Dónde se resuelve | Sección de la interfaz |
|---|---|---|
| 1. Administrar sedes (dirección, contacto, horarios, activa/baja) | `sede.py` y las operaciones de sedes de `red.py` | Sedes |
| 2. Administrar socios | `socio.py`, `red.py` | Socios |
| 3. Catálogo y ejemplares con su sede | `catalogo.py`, `red.py` | Catálogo y ejemplares |
| 4. Solicitudes locales e interbibliotecarias con origen y destino | `prestamos.py`, `red.registrar_solicitud` | Solicitudes |
| 5. Empaquetar, despachar y recibir con remito y trazabilidad | `remito.py` (estados y Observer), `red.py` | Remitos e historial |
| 6. Consultar disponibilidad | `red.motivo_no_disponible`, reporte de disponibilidad | Catálogo y ejemplares, Reportes |
| 7. Gestionar reservas | `prestamos.Reserva`, cola FIFO en `red.py` | Reservas |
| 8. Devoluciones y estado físico | `red.py` (devolución, multa y estado físico) | Préstamos y devoluciones |

### Validaciones de negocio

| Validación | Regla en el código | Prueba |
|---|---|---|
| No prestar ejemplares no disponibles | `registrar_solicitud` y `entregar_solicitud` | `test_no_se_presta_un_ejemplar_que_no_esta_disponible` |
| No prestar a socios inhabilitados | `exigir_socio_habilitado` | `test_no_se_presta_a_socio_inhabilitado` |
| Controlar vencimientos | `Prestamo.dias_atraso` y `multa_acumulada` | `test_multa_por_atraso`, `test_activos_y_vencidos` |
| Trazabilidad del remito | `Remito` + `RegistradorHistorial` | `test_transiciones_validas_notifican_y_guardan_historial`, `test_circuito_con_remito_y_retorno` |
| Evitar duplicados | altas de `red.py` (código de sede, número y email de socio, ISBN, código de ejemplar) | `test_crud_de_socio`, `test_catalogo_y_ejemplares`, `test_no_se_duplican_sedes_ni_libros` |
| Ejemplar de la sede de origen | `registrar_solicitud` | `test_no_se_presta_un_ejemplar_que_no_pertenece_a_la_sede_de_origen` |
| Sede dada de baja | `exigir_sede_activa` | `test_sede_dada_de_baja_no_inicia_solicitudes_reservas_ni_envios` |

### Reportes

El enunciado exige al menos cuatro reportes no triviales. Los cuatro
implementados cubren los seis sugeridos de esta forma:

| Reporte sugerido | Reporte que lo cubre |
|---|---|
| Préstamos activos y material en tránsito | Activos y vencidos; la columna "En tránsito" de Disponibilidad |
| Préstamos vencidos y multas acumuladas | Activos y vencidos |
| Libros más solicitados inter-sedes | Libros solicitados |
| Disponibilidad de catálogo por sede | Disponibilidad |
| Tasa de envíos exitosos e incidencias | Movimiento (tasa de éxito y copias dañadas al recibir) |
| Movimiento entre sedes y tiempo de tránsito | Movimiento |

### Patrones y procesos opcionales

- Se aplican dos patrones: Factory Method y Observer (ver la sección siguiente).
- De los procesos opcionales se cubre en parte la revisión del estado de
  recepción (se registra el daño observado; no el extravío ni la destrucción)
  y el inventario con códigos (cada ejemplar tiene un código único).
  Notificaciones, historial de lecturas y recomendaciones no se implementaron.

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
  1. respalda antes de agregar la tabla `usuarios` o la columna
     `estado_fisico_recepcion` en `remito_ejemplares`;
  2. agrega la columna y crea mediante el ORM las tablas que falten;
  3. siembra la configuración que falte;
  4. revisa los datos heredados y los informa en `/api/salud` sin corregirlos.
- La revisión comprueba también la secuencia y cronología del historial,
  vencimientos y devoluciones, préstamos superpuestos y coherencia de relaciones.
- Las entidades recuperadas por `RedBibliotecas` validan sus datos antes de
  utilizarse. Una consulta con datos de dominio inválidos devuelve HTTP 400.
  `/api/salud` sigue disponible con las observaciones de la revisión inicial;
  los datos originales se conservan para su corrección explícita.

### Decisión de alcance: login del personal

Se incorporó a pedido de la cátedra. `Usuario` está en `backend/usuarios.py`,
separado de `modelos.py` y de `RedBibliotecas`. La tabla `usuarios` guarda
`id`, `usuario` único (sin distinguir mayúsculas), `nombre`, `password_hash`
y `activa`. Las tres cuentas de la demo se cargaron una sola vez en la base;
el código de producción no contiene usuarios ni contraseñas iniciales.

Werkzeug genera un hash con salt y comprueba la contraseña al ingresar. Se
exigen entre 8 y 256 caracteres. La API devuelve solo id, usuario, nombre y
estado: nunca el hash. Usuario inexistente, contraseña incorrecta y cuenta
desactivada producen el mismo mensaje: «Usuario o contraseña incorrectos».

Flask guarda únicamente `usuario_id` en su cookie de sesión firmada. La firma
usa una clave creada con `secrets.token_hex(32)` y conservada en
`instance/clave_secreta`, excluida de Git. Una cookie firmada no está cifrada:
por eso no contiene contraseñas ni otros datos personales. Tiene `HttpOnly`
y `SameSite=Lax`. El `before_request` de `app.py` consulta en cada petición
que la cuenta exista y esté activa; por eso una baja bloquea también las
sesiones ya abiertas. Al ingresar o salir se limpia la sesión anterior.

El registro inicial usa el id 1 para que la clave primaria impida dos altas
iniciales simultáneas. Después de crear cualquier cuenta, devuelve 403.
Los demás registros requieren autenticación. Todos los usuarios tienen los
mismos permisos. El servidor continúa escuchando solo en `127.0.0.1`.

Alcance local: no hay roles, bloqueo por intentos, cambio o recuperación de
contraseña, token CSRF ni HTTPS. `SameSite=Lax` aporta una mitigación parcial
de CSRF; no equivale a una protección completa con token.

## Pruebas

```powershell
python -m unittest discover -s tests -v
node --check frontend/app.js
node tests/test_frontend.js
node tests/test_acceso_frontend.js
```

La suite usa bases SQLite temporales. Cubre la API, las reglas de préstamo y
retorno, reservas, reportes, patrones, persistencia, migración y validaciones
atómicas. `tests/test_frontend.js` ejecuta con Node las funciones de la
interfaz que arman el trayecto del remito, el formato de fechas y el envío de
la recepción.
También se comprueban los controles de acceso, bajas, persistencia de cuentas,
hashes, cookie, migración y las agrupaciones compartidas de los gráficos.

## Interfaz web

El frontend permite operar el sistema completo desde el navegador:
sedes, socios, catálogo, solicitudes, reservas, préstamos, devoluciones,
remitos, historial y reportes. No contiene reglas de negocio: muestra los
errores de la API y vuelve a consultar los listados después de cada operación.

- **Inicio**: cantidades generales, lista de tareas para atender (préstamos
  vencidos, solicitudes pendientes, remitos en curso, copias a retornar o en
  reparación) y aviso de datos heredados.
- **Menú**: agrupado por administración, circulación, logística y análisis,
  con un contador de pendientes por sección.
- **Remitos**: cada remito es una tarjeta con su trayecto de estados y el
  momento registrado de cada paso; el botón disponible es siempre el paso
  siguiente (empaquetar, despachar o recibir).
- **Préstamos**: los vencidos se resaltan con los días de atraso y la multa
  estimada.
- **Listados**: cada tabla tiene un buscador de texto.
- **Solicitudes**: al elegir el libro se listan sus ejemplares, al elegir el
  ejemplar se completa la sede de origen y el tipo se sugiere según las sedes.
  Es solo una ayuda de carga: el backend valida todos los datos.
