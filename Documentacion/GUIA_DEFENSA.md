# Guía de defensa y mapa del código

Esta guía explica qué hace cada archivo, cómo se conectan el frontend y el
backend, cuáles son las piezas más complejas y cómo contarle el sistema al
profesor.

## 1. Resumen en una frase

El navegador muestra una interfaz web; cada acción se envía como JSON a una
API Flask; la API llama a `RedBibliotecas`, que aplica las reglas de negocio
sobre objetos del dominio; Flask-SQLAlchemy guarda y recupera esos objetos en
SQLite.

## 2. Recorrido completo de una operación

```text
Navegador
   |
   | GET /
   v
backend/app.py  -----> frontend/index.html, styles.css, app.js
   |
   | fetch("/api/socios")
   v
backend/rutas.py
   |
   | llama a la operación del dominio
   v
backend/red.py  -----> Sede, Socio, Libro, Ejemplar, Solicitud, Prestamo,
   |                    Reserva, Remito, Reporte
   | ORM
   v
Flask-SQLAlchemy  -----> biblioteca.db (SQLite)
   |
   | entidad convertida a diccionario
   v
backend/serializadores.py  -----> JSON
   |
   v
frontend/app.js  -----> vuelve a pintar la sección
```

Puntos para remarcar:

1. El frontend no toca SQLite ni decide reglas de negocio.
2. La API no repite las validaciones; solo traduce HTTP, JSON y excepciones.
3. Las entidades validan sus datos y el coordinador arma las operaciones.
4. El ORM mantiene la sesión y las transacciones; no hay listas globales de
   objetos.
5. `migracion.py` es la única excepción que usa `sqlite3` directo, porque debe
   inspeccionar el esquema heredado.

## 3. Cómo levantarlo

Con la base local (se crea si no existe):

```powershell
python -m pip install -r requirements.txt
python main.py
```

Abrir `http://127.0.0.1:5000`.

Con la base ficticia incluida en el repositorio:

```powershell
$env:BIBLIOTECA_DB = "biblioteca_demo.db"
python main.py
```

Regenerar la base ficticia:

```powershell
python crear_base_demo.py
```

## 4. Backend archivo por archivo

### `main.py`

Es el punto de entrada. Crea la aplicación con `crear_aplicacion()`, imprime la
ruta de la base y los problemas de datos heredados, y arranca Flask en
`127.0.0.1:5000` con `debug=False`.

Qué explicar: “es el arranque, no contiene lógica de negocio”.

### `crear_base_demo.py`

Genera `biblioteca_demo.db` desde cero. Borra la base demo anterior y usa
`RedBibliotecas` para cargar sedes, socios, libros, ejemplares, préstamos,
reservas, solicitudes y remitos. No usa SQL manual: entra por el mismo dominio
y el mismo ORM que usa la aplicación.

Qué explicar: “es un cargador de datos de demostración; la base resultante es
un archivo SQLite normal que se puede abrir con la aplicación”.

### `backend/__init__.py`

Marca `backend` como paquete de Python. Está vacío.

### `backend/app.py`

Es la fábrica de la aplicación Flask:

- arma la URI de SQLite;
- inicializa Flask-SQLAlchemy con `db.init_app`;
- registra el blueprint de la API;
- sirve `index.html`, `styles.css` y `app.js`;
- ejecuta `preparar_base` al iniciar;
- convierte excepciones del dominio en respuestas HTTP 400, 404, 409 o 500;
- expone `/api/salud` con la ruta de la base y los problemas detectados.

Qué explicar: “es el pegamento entre Flask, el ORM, la API y el frontend”.

### `backend/modelos.py`

Define:

- `db = SQLAlchemy()`;
- el evento que ejecuta `PRAGMA foreign_keys = ON;` en cada conexión SQLite;
- el modelo `Configuracion`, que guarda `plazo_dias` y `multa_por_dia`.

Qué explicar: “SQLite no activa las claves foráneas por defecto; por eso se
activan en cada conexión”.

### `backend/rutas.py`

Contiene el blueprint `/api`. Sus tareas son:

1. leer el JSON o los parámetros de la URL;
2. validar tipos generales (texto, entero, fecha, momento);
3. llamar a la operación de `RedBibliotecas`;
4. serializar la respuesta;
5. dejar que `app.py` traduzca las excepciones a HTTP.

No implementa reglas como “no prestar a un socio inhabilitado”: eso está en
`red.py` y en las entidades.

### `backend/red.py`

Es el coordinador de casos de uso. No guarda listas propias: consulta las
entidades contra la sesión del ORM. Implementa, entre otras operaciones:

- alta y modificación de sedes, socios, libros y ejemplares;
- registro y cancelación de solicitudes;
- entrega de solicitudes y creación de préstamos;
- devoluciones, multa y estados físicos;
- reservas con cola FIFO;
- creación y movimiento de remitos;
- resumen general.

Es el archivo más largo y el que conviene explicar con un caso concreto:
“solicitud local → entrega → devolución”.

### `backend/sede.py`

Entidad `Sede`. Valida código, nombre, dirección, teléfono y horario. La baja
no borra la fila: cambia `activa` a `False` para conservar el historial.

### `backend/socio.py`

Entidad `Socio`. Valida número, nombre, email y teléfono. Habilitar e
inhabilitar cambian un booleano, no borran el socio.

### `backend/catalogo.py`

Contiene dos entidades:

- `Libro`: obra del catálogo, identificada por un código interno llamado ISBN
  en el TP;
- `Ejemplar`: copia física con `sede_pertenencia` (dueña), `ubicacion_actual`
  (dónde está), `estado_disponibilidad`, `estado_fisico` y dos punteros:
  `solicitud_asignada` y `reserva_asignada`.

La separación entre pertenencia y ubicación es la clave para entender los
préstamos interbibliotecarios: una copia puede pertenecer a S2 pero estar
físicamente en S1.

### `backend/prestamos.py`

Contiene:

- `SolicitudPrestamo`: pedido local o interbibliotecario;
- `Prestamo`: operación con fecha de vencimiento, devolución y multa;
- `Reserva`: espera por un libro en una sede.

También calcula días de atraso y multa acumulada.

### `backend/remito.py`

Contiene el sujeto observable `Remito`, el observador `ObservadorRemito`, el
observador concreto `RegistradorHistorial` y las tablas de asignaciones e
historial. El remito valida la secuencia:

```text
pendiente_empaque -> empaquetado -> despachado -> recibido
```

Si una transición es inválida o el momento es anterior al último evento, no
cambia el estado y no agrega historial.

### `backend/reportes.py`

Implementa Factory Method:

- `Reporte` y `FabricaReportes` son las clases abstractas;
- hay cuatro reportes concretos y cuatro fábricas concretas;
- `generar(red, parametros)` devuelve una lista de filas.

Los reportes son:

1. préstamos activos y vencidos por sede;
2. disponibilidad del catálogo por sede y libro;
3. libros más solicitados entre sedes;
4. movimiento y tiempos de envío entre sedes.

### `backend/serializadores.py`

Convierte entidades a diccionarios JSON. No guarda nada. Agrega datos
derivados para la interfaz, por ejemplo:

- nombre del socio y título del libro;
- si un ejemplar está realmente disponible;
- motivo por el que no está disponible;
- multa estimada de un préstamo activo;
- historial de un remito.

### `backend/validaciones.py`

Funciones compartidas para validar textos, códigos, enteros, años, fechas,
teléfonos, emails, horarios, estados físicos y tipos de solicitud.

Se usan al crear, al modificar y al revisar datos heredados.

### `backend/errores.py`

Define las excepciones del dominio:

- `ErrorDatosInvalidos` → HTTP 400;
- `ErrorNoEncontrado` → HTTP 404;
- `ErrorConflicto` → HTTP 409.

Así el dominio no depende de Flask.

### `backend/migracion.py`

Prepara una base existente:

1. si falta la columna `estado_fisico_recepcion`, crea un respaldo y ejecuta
   `ALTER TABLE`;
2. `db.create_all()` crea las tablas faltantes;
3. siembra la configuración;
4. revisa los datos heredados y devuelve una lista de problemas;
5. no corrige datos en silencio.

Es el único módulo que usa `sqlite3` directo, porque el ORM no sirve para
inspeccionar un esquema viejo antes de mapearlo.

### `tests/`

- `apoyo.py`: crea una aplicación y una base temporal por prueba, y ofrece
  helpers para pedir a la API;
- `test_api.py`: CRUD, validaciones, préstamos, devoluciones, remitos y
  reservas;
- `test_orm.py`: persistencia, claves foráneas, configuración y modificaciones
  atómicas;
- `test_patrones.py`: Factory Method y Observer;
- `test_reportes.py`: cálculos, filtros y tiempos;
- `test_migracion.py`: respaldo, columna nueva y datos heredados.

Cada prueba usa su propia base SQLite temporal. En Windows se llama a
`db.session.remove()` y `db.engine.dispose()` antes de borrar la carpeta.

### `biblioteca_demo.db` y `biblioteca.db`

- `biblioteca_demo.db`: base ficticia versionada, generada por
  `crear_base_demo.py`; sirve para mostrar todos los casos sin cargar datos.
- `biblioteca.db`: base local de trabajo. Está ignorada por Git porque puede
  contener datos propios.
- `biblioteca.db.respaldo-*`: respaldos automáticos de migraciones. También
  están ignorados.

## 5. Frontend archivo por archivo

### `frontend/index.html`

Es el esqueleto de la página:

- encabezado y estado de conexión;
- menú con las nueve secciones;
- contenedor `#contenido`, que el JavaScript rellena dinámicamente;
- carga de `styles.css` y `app.js`.

No contiene formularios escritos a mano: `app.js` genera el HTML de cada
sección.

### `frontend/styles.css`

Define variables de color, distribución, tarjetas, tablas, formularios,
mensajes, insignias y comportamiento responsive. No contiene lógica.

### `frontend/app.js`

Es toda la interfaz. Sus partes principales son:

- `estado`: datos en memoria de la pantalla (listados, sección actual, filtros,
  elemento en edición);
- `pedir`: función única para llamar a la API y manejar errores;
- `refrescar`: vuelve a pedir `/api/listados` y `/api/salud`;
- `render`: decide qué sección pintar;
- funciones `renderSedes`, `renderSocios`, `renderCatalogo`, etc.;
- `conectarEventos`: delegación de clics, envíos y escritura;
- `manejarFormulario`: arma el JSON según el formulario;
- `cargarReporte` y `pintarReporte`;
- `formatearHorario`: convierte ocho dígitos en `HH:MM-HH:MM`.

No hay reglas de negocio en el frontend. Si el backend rechaza una operación,
el error se muestra y se vuelve a consultar el estado real.

### `frontend/__init__.py`

Marca `frontend` como paquete. Está vacío.

## 6. Cómo se conectan frontend y backend

La conexión es HTTP + JSON:

```javascript
const API = "/api";

const respuesta = await fetch(API + ruta, {
    method: metodo,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
});
const cuerpo = await respuesta.json();
if (!respuesta.ok) {
    throw new Error(cuerpo.error);
}
return cuerpo;
```

Del otro lado, `rutas.py` devuelve:

```json
{
  "datos": {},
  "mensaje": "operación realizada"
}
```

Y ante un error:

```json
{
  "error": "mensaje comprensible"
}
```

El flujo de una entrega de solicitud es:

1. el usuario aprieta “Entregar”;
2. `app.js` hace `POST /api/solicitudes/1/entregar`;
3. `rutas.py` lee la fecha y llama a `red.entregar_solicitud`;
4. `red.py` valida sede, socio, ejemplar, remito y fechas;
5. crea el `Prestamo`, cambia la solicitud y el ejemplar;
6. `commit` guarda todo;
7. `prestamo_a_diccionario` arma el JSON;
8. `app.js` recibe la respuesta y actualiza la pantalla.

## 7. Piezas que conviene saber explicar

### 7.1 Factory Method en reportes

`Reporte` define el contrato. Cada fábrica crea un reporte concreto:

```python
class FabricaReporteActivosVencidos(FabricaReportes):
    def crear_reporte(self):
        return ReporteActivosVencidos()
```

La API usa la fábrica y ejecuta `generar` de forma polimórfica:

```python
fabrica = FabricaReporteActivosVencidos()
reporte = fabrica.crear_reporte()
filas = reporte.generar(red, {"fecha_referencia": fecha})
```

Para la defensa: “la API no conoce las clases concretas de los reportes; pide
un producto a una fábrica y lo usa a través de la interfaz”.

### 7.2 Observer en el remito

`Remito` es el sujeto observable. `RegistradorHistorial` es el observador:

```python
def actualizar(self, remito, nombre_estado, momento):
    orden = len(remito.historial)
    registro = RemitoHistorial(remito.codigo, orden, nombre_estado, momento)
    remito.historial.append(registro)
```

La transición se valida antes de notificar:

```python
def _preparar_transicion(self, momento, descripcion):
    self._asegurar_observador_historial()
    if momento is None:
        momento = datetime.datetime.now()
    momento = validar_momento(momento, descripcion)
    self._validar_cronologia(momento)
    return momento
```

Para la defensa: “si el remito no puede pasar de estado, no se notifica y no
se ensucia el historial”.

### 7.3 Validación atómica de modificaciones

Las entidades validan todos los campos nuevos antes de asignar. Ejemplo de
`Sede.modificar_datos`:

```python
nuevo_nombre = validar_texto(nombre, "nombre de sede")
nueva_direccion = validar_texto(direccion, "direccion de sede")
nuevo_telefono = validar_telefono(telefono, "telefono de sede")
nuevo_horario = validar_horario(horario, "horario de sede")

self.nombre = nuevo_nombre
self.direccion = nueva_direccion
self.telefono = nuevo_telefono
self.horario = nuevo_horario
```

Si falla una validación, el objeto conserva sus valores anteriores. La misma
idea se aplica en socios, libros y devoluciones.

### 7.4 Punteros de asignación y cola FIFO

El ejemplar tiene:

```python
solicitud_asignada = db.Column(db.Integer, nullable=True)
reserva_asignada = db.Column(db.Integer, nullable=True)
```

No son claves foráneas para no crear un ciclo entre ejemplares y solicitudes.
El dominio los mantiene coordinados:

- una solicitud aparta la copia y guarda su número;
- una reserva aparta la copia y guarda el número de reserva;
- cuando la reserva se convierte en solicitud, el ejemplar conserva ambos
  punteros porque la reserva apunta a esa solicitud;
- al entregar, `marcar_prestado` limpia los punteros.

La cola FIFO se arma en `reservas_ordenadas_de_libro`: ordena por
`fecha_reserva` y, si hay empate, por número. `atender_cola_reservas` asigna
copias prestables en ese orden.

### 7.5 Logística del remito

Un remito de préstamo transporta una copia de una solicitud interbibliotecaria.
Un remito de retorno transporta una copia que fue devuelta en otra sede.

Al despachar, la copia pasa a `en_transito` y `ubicacion_actual = None`.
Al recibir:

- se guarda el estado físico observado en `estado_fisico_recepcion`;
- la copia se mueve a la sede de destino;
- si es un préstamo, sigue apartada hasta que se entrega al socio;
- si es un retorno, vuelve a disponible o queda en reparación si llegó dañada.

### 7.6 Cálculos de reportes

- Activos y vencidos: recorre préstamos activos por sede, calcula proporción,
  atraso promedio y multa acumulada.
- Disponibilidad: cuenta cada copia una sola vez. Si está en tránsito, la
  atribuye a la sede de origen del remito activo; si no tiene ubicación ni
  remito, a su sede de pertenencia.
- Libros solicitados: cuenta solicitudes interbibliotecarias por ISBN y ordena
  de mayor a menor.
- Movimiento: agrupa remitos por origen/destino, calcula tiempos desde el
  historial y cuenta daños observados al recibir.

### 7.7 Migración y respaldo

`preparar_base` no borra la base. Si detecta que falta una columna, copia el
archivo con un nombre `.respaldo-AAAA...` y ejecuta:

```sql
ALTER TABLE remito_ejemplares
ADD COLUMN estado_fisico_recepcion TEXT
```

Después revisa los datos heredados sin corregirlos. La API los muestra en
`/api/salud`.

### 7.8 Estado y eventos del frontend

`app.js` mantiene un objeto `estado` con los listados y la sección actual. Cada
operación termina llamando a `refrescar()`, que vuelve a consultar la API y
pinta de nuevo. No se guardan copias permanentes de las entidades en el
navegador.

Los eventos se conectan una sola vez con delegación:

```javascript
document.addEventListener("click", async function (evento) {
    const botonAccion = evento.target.closest("[data-accion]");
    ...
});
```

Así los botones de las tablas generadas dinámicamente siguen funcionando.

### 7.9 Formato automático del horario

El campo acepta ocho dígitos y los convierte en `HH:MM-HH:MM`:

```javascript
function formatearHorario(valor) {
    let digitos = "";
    ...
    if (indice === 2 || indice === 6) {
        formateado += ":";
    }
    if (indice === 4) {
        formateado += "-";
    }
    ...
}
```

También conserva la posición del cursor y se aplica al enviar el formulario,
para que la API reciba siempre el formato que valida el backend.

### 7.10 Pruebas

Cada prueba crea una base nueva y usa el cliente de Flask. Se verifica el
comportamiento real de la API y del ORM, no solo funciones aisladas. Al
finalizar se cierran sesión y motor para poder borrar el archivo en Windows.

## 8. Guion corto para la defensa

1. “El proyecto es una red de bibliotecas con sedes, socios y ejemplares.”
2. “El navegador pide HTML a Flask y luego opera por JSON contra `/api`.”
3. “La API delega en `RedBibliotecas`; las entidades validan y el ORM guarda.”
4. “Un ejemplar separa pertenencia de ubicación; eso permite el préstamo
   interbibliotecario.”
5. “Una solicitud aparta la copia; una reserva espera en cola FIFO.”
6. “El remito usa Observer para guardar el historial de estados.”
7. “Los reportes usan Factory Method para que la API no dependa de las clases
   concretas.”
8. “La base demo se genera con `crear_base_demo.py` y el ORM.”
9. “La suite cubre API, ORM, patrones, reportes y migración; son 40 pruebas.”

## 9. Preguntas probables del profesor

### ¿Por qué usaron ORM?

Porque permite trabajar con objetos, relaciones y transacciones sin repetir
SQL en el dominio. SQLite sigue siendo el motor real. `migracion.py` usa
`sqlite3` solo para inspeccionar el esquema anterior.

### ¿Dónde están las reglas de negocio?

En `red.py` y en las entidades. Por ejemplo, `entregar_solicitud` verifica
socio, sede, ejemplar, remito y fechas. La API solo llama a esa operación.

### ¿Cómo evitan que una copia quede asignada dos veces?

Con `solicitud_asignada` y `reserva_asignada`. Antes de apartar se comprueba
que el ejemplar no esté tomado. La migración revisa la coherencia de esos
punteros.

### ¿Qué pasa si falla una operación a mitad de camino?

`RedBibliotecas._confirmar` hace `commit`; ante una excepción hace `rollback`.
Los manejadores de Flask también hacen `rollback` antes de devolver el error.
No queda una operación a medias.

### ¿Cómo se calcula la multa?

Al registrar la devolución se comparan `fecha_devolucion` y
`fecha_vencimiento`; los días de atraso se multiplican por el valor de
`multa_por_dia` guardado en configuración.

### ¿Qué diferencia hay entre estado físico y disponibilidad?

El estado físico describe la conservación (`bueno`, `deteriorado`,
`requiere_reparacion`). La disponibilidad describe la situación operativa
(`disponible`, `prestado`, `en_transito`, `apartado`, etc.).

### ¿Por qué hay dos bases?

`biblioteca.db` es local y no se publica. `biblioteca_demo.db` es ficticia y
está versionada para que el corrector vea todos los casos al abrir el
proyecto.

### ¿Qué pasa con los datos inválidos de una base vieja?

No se corrigen automáticamente. `preparar_base` los informa y `/api/salud` los
muestra para que una persona decida qué hacer.

### ¿Por qué el frontend no valida las reglas?

Valida formatos básicos para ayudar al usuario, pero la decisión final está en
el backend. Si alguien llama directo a la API, las reglas se siguen
cumpliendo.

### ¿Qué se puede borrar o qué no?

No se borran sedes, socios, libros ni ejemplares: se dan de baja o se cambia su
estado para conservar el historial. Las pruebas usan bases temporales que sí
se eliminan.

## 10. Casos que muestra `biblioteca_demo.db`

| Caso | Dónde verlo |
|---|---|
| Sede activa y sede dada de baja | S1, S2, S3 activas; S4 “Sede Historica” dada de baja |
| Socio habilitado e inhabilitado | Socios 1 a 3, 5 y 6 habilitados; socio 4 inhabilitado |
| Libro con varias copias | L1 y L2 en distintas sedes |
| Copia disponible | E1, E2, E7, E15, E16 |
| Préstamo activo en plazo | E10 |
| Préstamo activo vencido | E4 |
| Copia en reparación | E12 |
| Copia en tránsito | E9 |
| Copia pendiente de retorno | E8 |
| Copia apartada por solicitud | E5 |
| Copia apartada por remito | E6, E11, E13 |
| Copia apartada por reserva | E14 |
| Solicitud cancelada | Solicitud de E7 |
| Reserva cumplida, asignada, pendiente y cancelada | Reservas de L2/S1, L6/S3, L4/S3 y L3/S3 |
| Remito pendiente, empaquetado, despachado y recibido | R-5, R-6/R-9, R-4, R-1/R-2/R-3/R-7/R-8 |
| Devolución con multa | Préstamo de E8, devuelto con atraso |

## 11. Archivos de documentación

- `ENUNCIADO.md`: consigna del trabajo.
- `README.md`: instalación, ejecución, API y estructura.
- `FASES.md`: decisiones y orden de implementación.
- `GUIA_DEFENSA.md`: este documento.
