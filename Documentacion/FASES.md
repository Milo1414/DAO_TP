# FASES.md

Registro de decisiones, orden de trabajo y comprobaciones del TP.
El enunciado completo está en `ENUNCIADO.md` y las reglas de estilo en
`AGENTS.md`.

## Fase actual: revisión final y entrega

La aplicación está implementada y verificada. Queda mantener la documentación
alineada con el código y publicar el repositorio.

## Fases de trabajo

### Fase 1. Dominio y modelo relacional

- Se separaron las entidades en `sede.py`, `socio.py`, `catalogo.py`,
  `prestamos.py` y `remito.py`.
- Cada entidad valida sus datos en el constructor y en las modificaciones.
  Las modificaciones validan todos los campos nuevos antes de asignar, de modo
  que un error no deja el objeto a medio modificar.
- Se definieron las relaciones y claves foráneas del esquema:
  sedes, socios, libros, ejemplares, solicitudes, préstamos, reservas,
  remitos, remito_ejemplares y remito_historial.
- Los ejemplares guardan por separado la sede de pertenencia y la ubicación
  actual. La ubicación es `NULL` mientras la copia está en tránsito.
- Se usan punteros de asignación (`solicitud_asignada` y `reserva_asignada`)
  para impedir que una copia quede tomada por dos operaciones.

### Fase 2. Coordinador de negocio

- `RedBibliotecas` no guarda listas propias: consulta la sesión del ORM.
- Cada operación valida, modifica los objetos y confirma la transacción.
  Ante un error se hace `rollback`.
- Se fijaron las decisiones que el enunciado deja abiertas:
  - plazo de préstamo: 14 días corridos, configurable;
  - multa: 100 pesos por día de atraso, configurable;
  - reserva FIFO por libro y sede;
  - una solicitud aparta la copia desde su registro;
  - la entrega interbibliotecaria exige un remito recibido;
  - una devolución fuera de la sede de pertenencia deja la copia pendiente de
    retorno;
  - una copia dañada queda en reparación y no vuelve a prestarse hasta ser
    reparada;
  - una sede de baja conserva el historial y permite recibir un envío que ya
    había sido despachado, pero no inicia nuevas operaciones.
- Los identificadores de solicitudes, préstamos y reservas se calculan como
  `max + 1` recién después de validar la operación. Un rechazo no consume
  números.
- Se corrigió el orden de inserción entre una solicitud y la reserva asociada:
  la solicitud se inserta con `flush` antes de actualizar la clave foránea de
  la reserva.

### Fase 3. Patrones de diseño

- **Factory Method**: `Reporte` / `FabricaReportes` y cuatro pares
  reporte-fábrica.
- **Observer**: `Remito` notifica a `RegistradorHistorial` después de validar
  cada transición. La validación de secuencia y cronología queda en el remito.
- Los reportes implementados son:
  1. préstamos activos y vencidos por sede;
  2. disponibilidad del catálogo por sede y libro;
  3. libros más solicitados entre sedes;
  4. movimiento y tiempos de envío entre sedes.
- La disponibilidad no duplica copias: una copia en tránsito se atribuye al
  origen de su remito activo y una copia sin remito se muestra en su sede de
  pertenencia.

### Fase 4. Persistencia SQLite

- Flask-SQLAlchemy es la única vía de persistencia de las entidades.
- Las claves foráneas se activan en cada conexión con `PRAGMA foreign_keys = ON;`.
- `migracion.py` es el único módulo que usa `sqlite3` directamente, porque
  necesita inspeccionar el esquema heredado y ejecutar un `ALTER TABLE`.
- `preparar_base` crea las tablas faltantes, respalda la base antes de cambiar
  el esquema, siembra la configuración y revisa los datos heredados.
- La columna `estado_fisico_recepcion` se agregó a `remito_ejemplares` para
  conservar la evidencia del estado físico observado al recibir un envío.
  La base real se migró con respaldo previo.
- Los datos heredados inválidos no se corrigen en silencio: se informan en
  `/api/salud`.

### Fase 5. API y frontend

- La API se publica bajo `/api` y devuelve JSON.
- Flask sirve `index.html`, `styles.css` y `app.js`.
- El frontend tiene secciones para inicio, sedes, socios, catálogo,
  solicitudes, reservas, préstamos, remitos y reportes, agrupadas en el menú
  por administración, circulación, logística y análisis.
- El navegador no implementa reglas de negocio: llama a la API, muestra los
  errores y refresca los listados.
- Los errores del dominio se traducen a HTTP 400, 404 o 409. Un error de
  integridad de SQLite también se informa como 409.

### Fase 6. Pruebas y revisión

- Se reemplazaron las pruebas de la versión de consola por una suite sobre la
  aplicación web y el ORM.
- Archivos de prueba:
  - `tests/apoyo.py`: base temporal, cliente HTTP y datos de apoyo;
  - `tests/test_api.py`: CRUD, validaciones, préstamos, reservas y remitos;
  - `tests/test_orm.py`: persistencia, configuración, claves foráneas y
    modificaciones atómicas;
  - `tests/test_patrones.py`: Factory y Observer;
  - `tests/test_reportes.py`: cálculos, filtros y tiempos;
  - `tests/test_migracion.py`: respaldo, columna nueva y datos heredados;
  - `tests/test_regresiones.py`: casos de la revisión final (cancelaciones,
    fechas, reversión de fallos y datos recuperados inválidos);
  - `tests/test_frontend.js`: funciones de la interfaz ejecutadas con Node.
- Se eliminaron los módulos de consola Rich y la persistencia SQLite manual,
  que ya no forman parte de la arquitectura.
- Se simplificaron métodos sin uso y se movieron imports locales al inicio.
- Se corrigió una copia nueva para que atienda reservas pendientes de su sede.
- Se agregó la validación de socio ya inhabilitado para que la operación sea
  explícita y no silenciosa.

## Comprobaciones realizadas

| Comprobación | Resultado |
|---|---|
| `python -m unittest discover -s tests -v` | 40 pruebas, todas correctas |
| `python crear_base_demo.py` | base ficticia completa generada con el ORM |
| `python -c "from backend.app import crear_aplicacion; ..."` | 49 rutas registradas |
| `node --check frontend/app.js` | sin errores de sintaxis |
| Prueba de navegador con Playwright | alta de sede, socio, libro, ejemplar, solicitud, entrega, devolución y reporte sin errores de consola |
| Migración de `biblioteca.db` | respaldo creado y columna agregada |
| Revisión de datos heredados | sede inválida informada sin modificar |
| Apertura de `biblioteca_demo.db` | `/api/salud` sin problemas y nueve listados disponibles |
| Formateo de horario en el navegador | Playwright verificó `08001800` -> `08:00-18:00` sin errores de consola |

## Cierre de la entrega web

- Se eliminó `demo.py`; la demostración persistente se reemplazó por
  `crear_base_demo.py`, que usa el ORM y genera `biblioteca_demo.db`.
- Se versionó `biblioteca_demo.db` con casos locales e interbibliotecarios.
- Se agregó `Documentacion/GUIA_DEFENSA.md` con el mapa de archivos, la
  conexión frontend/backend y las piezas complejas.

## Correcciones de la revisión final

- Se agregó la cancelación de remitos antes del despacho, con evento histórico.
  En tránsito se exige recibir antes de cancelar la solicitud; tras recibir,
  la copia puede retornar aunque no haya nacido un préstamo. Los remitos
  cancelados no cuentan como envíos activos ni pendientes en los reportes.
- Solicitudes y entregas verifican la última devolución y recepción de la
  copia. Las solicitudes asociadas a reservas respetan su fecha de creación.
- La entrega valida la configuración antes de modificar entidades. Las
  operaciones de varias entidades revierten también los fallos anteriores al
  guardado, sin depender del manejador HTTP.
- Las entidades recuperadas se validan en las búsquedas y colecciones del
  coordinador. La revisión heredada detecta vencimientos/devoluciones incoherentes,
  préstamos superpuestos, relaciones cruzadas y secuencias o momentos inválidos
  en el historial. Los datos inválidos se conservan y las consultas afectadas
  pueden rechazarse; `/api/salud` conserva el diagnóstico inicial.
- La recepción exige `estado_fisico` en la API y en el formulario. La evidencia
  histórica usa esa observación, incluso si posteriormente se repara la copia.
  Si una copia de préstamo llega requiriendo reparación, su solicitud se cancela
  y la copia queda pendiente de retorno.
- Los momentos se interpretan como hora local sin zona horaria. Entradas con
  `Z` o desplazamiento se rechazan con HTTP 400 antes de modificar el remito.

Comprobaciones de esta revisión:

| Comprobación | Resultado |
|---|---|
| `python -B -m unittest discover -s tests -v` | 56 pruebas correctas, incluidas 16 regresiones nuevas |
| `node --check frontend/app.js` | sin errores de sintaxis |
| Generación de la demo en una base temporal | casos completos, revisión sin problemas y `/api/listados` HTTP 200 |
| `node tests/test_frontend.js` | formulario de recepción, estado observado y envío JSON correctos |

La demo versionada no se reemplaza durante estas comprobaciones.

## Revisión de documentación, interfaz y consignas

Se revisó el proyecto contra `ENUNCIADO.md` y se mejoró la interfaz sin tocar
el dominio ni la API.

- Cumplimiento: los ocho procesos obligatorios, las siete validaciones, los
  dos patrones y los cuatro reportes están implementados. La tabla que lo
  relaciona con el código y las pruebas está en `README.md`, sección
  "Cumplimiento del enunciado".
- Dos validaciones del enunciado no tenían una prueba propia: el ejemplar que
  no pertenece a la sede de origen y la sede dada de baja. Se agregaron cuatro
  pruebas en `tests/test_api.py` (`PruebaValidacionesDelEnunciado`); pasaron
  sin modificar el dominio.
- Interfaz:
  - textos con tildes y fechas en formato `dd/mm/aaaa`;
  - menú agrupado con contadores de pendientes;
  - inicio con tarjetas que llevan a cada sección y una lista "Para atender
    ahora" (vencidos, solicitudes, remitos, retornos y reparaciones);
  - remitos como tarjetas con el trayecto de estados y el momento de cada
    paso, incluido el remito cancelado;
  - préstamos vencidos resaltados con los días de atraso;
  - el estado del remito visible en cada solicitud interbibliotecaria;
  - buscador de texto en los listados;
  - el formulario de solicitud lista los ejemplares del libro elegido,
    completa la sede de origen y sugiere el tipo;
  - etiquetas asociadas a sus campos y botón de envío bloqueado mientras dura
    el pedido.
- Documentación: se completaron las listas de archivos de `AGENTS.md`,
  `FASES.md` y `GUIA_DEFENSA.md`, y se registró la cantidad actual de rutas.

Comprobaciones de esta revisión:

| Comprobación | Resultado |
|---|---|
| `python -B -m unittest discover -s tests` | 60 pruebas correctas, incluidas las 4 nuevas |
| `node --check frontend/app.js` | sin errores de sintaxis |
| `node tests/test_frontend.js` | trayecto del remito, fechas y recepción correctos |
| Rutas registradas | 48 reglas de URL, 46 bajo `/api` |
| Navegador (Playwright) sobre una copia de la demo | las nueve secciones cargan; ayuda de solicitud, buscador, empaque y recepción de remitos funcionan; el único error de consola es el HTTP 409 esperado al repetir una sede |

Observaciones que quedan abiertas (no son requisitos obligatorios):

- Un remito de retorno no puede cancelarse; solo se cancela el remito de una
  solicitud, al cancelar esa solicitud antes del despacho.
- Los ejemplares se dan de alta y se reparan, pero no se modifican ni se dan
  de baja. El extravío y la destrucción son parte de un proceso opcional.
- El plazo y la multa se guardan en `configuracion`, pero no hay una pantalla
  ni una ruta para cambiarlos.

Corrección posterior de textos: los mensajes del backend, los nombres de los
reportes y los datos de `crear_base_demo.py` ahora llevan tildes y "ñ"
("está dañado", "Cien años de soledad"). Los identificadores, las claves JSON
y las sentencias SQL no cambiaron. Se regeneró `biblioteca_demo.db` y se
ajustaron tres pruebas que comparaban los textos anteriores; la suite sigue en
60 pruebas correctas.

## Decisiones de alcance

- No se implementaron usuarios, autenticación, notificaciones, historial de
  lecturas ni recomendaciones; no son procesos obligatorios del enunciado.
- De los procesos opcionales se cubre en parte la revisión del estado de
  recepción: se registra el estado físico observado (daño), no el extravío ni
  la destrucción.
- La interfaz es web y no de consola. La API puede probarse por separado.
- Los reportes se calculan al momento de la consulta, no se guardan en tablas.
- La multa se calcula al registrar la devolución y queda guardada en el
  préstamo.
- El sistema no borra sedes, socios, libros ni ejemplares: usa bajas o estados
  para conservar la trazabilidad.

## Cómo continuar

1. Ejecutar `python main.py`.
2. Abrir `http://127.0.0.1:5000`.
3. Usar `python crear_base_demo.py` para regenerar `biblioteca_demo.db`; luego abrirla con `$env:BIBLIOTECA_DB = "biblioteca_demo.db"`.
4. Ejecutar `python -m unittest discover -s tests -v` antes de cualquier
   entrega.
5. Si se modifica el esquema, actualizar `migracion.py` y agregar una prueba
   específica de migración.
