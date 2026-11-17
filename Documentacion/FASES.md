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

- La API se publica bajo `/api` y devuelve JSON; los reportes también admiten descarga PDF.
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

- No se implementaron notificaciones, historial de lecturas ni recomendaciones;
  no son procesos obligatorios del enunciado. El acceso del personal se agregó
  posteriormente a pedido de la cátedra, como se registra más abajo.
- De los procesos opcionales se cubre en parte la revisión del estado de
  recepción: se registra el estado físico observado (daño), no el extravío ni
  la destrucción.
- La interfaz es web y no de consola. La API puede probarse por separado.
- Los reportes se calculan al momento de la consulta, no se guardan en tablas.
- La multa se calcula al registrar la devolución y queda guardada en el
  préstamo.
- El sistema no borra sedes, socios, libros ni ejemplares: usa bajas o estados
  para conservar la trazabilidad.

## Limpieza de la revisión final

- Se eliminaron dos métodos sin llamadas (`Prestamo.tiene_multa` y
  `Remito.numeros_solicitud`) y una colección de números de reserva que no se
  utilizaba en la revisión de datos heredados.
- `remito_a_diccionario` siempre incluye el historial, como ya hacían todas
  sus llamadas; se quitó la opción sin uso para omitirlo.
- Se quitó `frontend/__init__.py`: la interfaz se sirve como archivos
  estáticos y no se importa como paquete Python.
- Se retiró una aserción que comparaba un nombre de reporte consigo mismo;
  la prueba sigue verificando el tipo de producto creado por cada fábrica.
- Se centralizaron las instrucciones de ejecución en el README y se quitaron
  tablas históricas con cantidades de pruebas y rutas desactualizadas.

Comprobaciones ejecutadas después de la limpieza:

| Comprobación | Resultado |
|---|---|
| `python -B -m unittest discover -s tests` | 60 pruebas correctas, igual que antes de la limpieza |
| `node --check frontend/app.js` | sin errores de sintaxis |
| `node tests/test_frontend.js` | trayecto del remito, fechas y recepción correctos |
| Demo en una base temporal con el cliente HTTP de Flask | 10 rutas HTTP 200 (página, JS, CSS, salud, listados, historial y cuatro reportes); los nueve remitos conservan su historial |
| `git diff --check` | sin errores de espacios en los cambios |

### Comprobaciones anteriores conservadas como referencia

- Demo generada en una base temporal: revisión sin problemas y
  `/api/listados` HTTP 200; la demo versionada no se reemplazó en esa prueba.
- Migración de la base local: respaldo previo, columna agregada y sede
  inválida informada sin modificar sus datos.
- Última revisión de rutas: 48 reglas de URL, 46 bajo `/api`.
- Navegador con Playwright sobre una copia de la demo: las nueve secciones,
  el circuito de alta, préstamo y devolución, los reportes, la ayuda de
  solicitud, el buscador, el empaque y la recepción funcionaron. El HTTP 409
  al repetir una sede fue el error esperado. También se verificó el formato
  de horario `08001800` → `08:00-18:00`.

## Descarga de reportes PDF para la entrega

- Se agregó ReportLab 5.1.0 y `backend/reportes_pdf.py`, que presenta las
  filas calculadas por los reportes existentes. Usa funciones explícitas,
  un archivo en memoria y tablas que repiten los encabezados entre páginas.
- Las cuatro rutas admiten `formato=pdf`. Conservan las mismas fábricas,
  cálculos, filtros y validaciones; `responder_reporte` elige JSON o PDF.
  El archivo se envía como adjunto con `send_file`, sin guardarlo en SQLite
  ni escribirlo en el disco del servidor.
- Cada documento incluye título, fecha, filtros, utilidad para la gestión,
  alcance de las métricas y resultados. Disponibilidad y movimiento dividen
  las columnas en bloques legibles. Si no hay filas, se informa expresamente.
- La interfaz muestra **Descargar PDF** después de generar un reporte,
  incluidos los resultados vacíos. Conserva los parámetros de la consulta
  exitosa; la fecha de referencia predeterminada se fija al consultar.
  La descarga vuelve a consultar los registros al momento de generar el PDF.
- Se actualizó el informe de estudio para explicar el recorrido completo
  y reemplazar las advertencias sobre una funcionalidad antes pendiente.

Comprobaciones de esta ampliación:

- Suite Python: 68 pruebas correctas (60 existentes y 8 nuevas de PDF).
- `node --check frontend/app.js` y `node tests/test_frontend.js`: correctos,
  incluidas las direcciones de descarga, filtros, resultados vacíos y errores.
- Se generaron los cuatro PDF con una copia de la demo, un documento vacío
  y otro de once páginas con títulos largos y caracteres de marcado.
  Se extrajo texto con PyMuPDF disponible en Python 3.11 y se revisó el diseño.
  Se comprobó que el título de incidencias acompañe a su tabla.
- Servidor reiniciado con la misma base de práctica: las cuatro descargas
  respondieron HTTP 200 con `application/pdf` y disposición de adjunto.
  En un navegador real se descargaron movimiento y disponibilidad filtrada
  por S1/L1; el archivo descargado conserva los filtros y excluye otros libros.

## Ampliación del 17/11/2026: acceso del personal y gráficos

- `backend/usuarios.py` contiene la entidad de seguridad `Usuario` y las
  operaciones de cuentas con hashes de Werkzeug; no forma parte del dominio
  de circulación ni se incorporó a `modelos.py`.
- `app.py` configura una clave persistente en `instance/`, la cookie firmada,
  el control de cada petición y las siete rutas de sesión y usuarios.
  Solo sesión, login y primer registro son públicos. Las cuentas se desactivan;
  el servidor impide la baja propia y rechaza sesiones de cuentas inactivas.
- La preparación de una base anterior respalda antes de agregar `usuarios`.
  Las tres cuentas solicitadas se cargaron directamente en `biblioteca_demo.db`
  y se comprobó el ingreso de cada una. Sus contraseñas no están en el código.
  La base conserva el dominio existente y su revisión no informó problemas.
- La interfaz consulta sesión antes de cargar listados, tiene login y primer
  registro, cierre de sesión y Administración → Usuarios. Un 401 limpia los
  datos privados de la interfaz y vuelve al ingreso.
- `reportes_graficos.py` prepara series desde las filas de los reportes.
  JSON y PDF usan esa misma preparación. HTML/CSS muestra barras y ReportLab
  dibuja gráficos vectoriales. Se conservan tablas, filtros y todos los grupos.
  Los préstamos al día excluyen vencidos; reservas no se suman al inventario;
  las horas de tránsito se muestran separadas de las cantidades de envíos.
- No se agregaron dependencias ni patrones de diseño.

Comprobaciones finales:

- Suite Python completa: **84 pruebas correctas**. En Windows se ejecutó
  fuera del entorno restringido porque este impedía abrir las bases temporales.
- `node --check frontend/app.js`, `node tests/test_frontend.js` y
  `node tests/test_acceso_frontend.js`: correctos.
- Navegador sobre una copia de la demo: ingreso, sesión conservada al recargar,
  pantalla de usuarios, gráficos de los cuatro reportes, descarga autenticada
  de movimiento y vuelta al login al cerrar sesión. Se ajustó el ancho móvil
  para que la tabla tenga desplazamiento propio y no ensanche los gráficos.
- Cuatro PDF generados con la demo y todas sus páginas renderizadas con
  PyMuPDF para revisión visual. Se corrigió un título de gráfico que quedaba
  separado de sus barras al cambiar de página. Los casos vacíos y extensos
  también están cubiertos por las pruebas de PDF.
- Las tres cuentas solicitadas ingresaron correctamente; la revisión de la
  demo no informó problemas. La clave de sesión y los artefactos de revisión
  están excluidos de Git. El servidor temporal se detuvo al terminar.
- `git -c core.whitespace=cr-at-eol diff --check`: correcto; se respeta el
  formato CRLF del informe existente.

## Cómo continuar

Las instrucciones de arranque y comprobación están en el
[README](README.md#ejecución). Antes de entregar, ejecutar las
[pruebas](README.md#pruebas). Si se modifica el esquema, actualizar
`migracion.py` y agregar una prueba específica de migración.
