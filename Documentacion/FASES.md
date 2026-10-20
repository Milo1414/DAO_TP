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
  solicitudes, reservas, préstamos, remitos y reportes.
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
  - `tests/test_migracion.py`: respaldo, columna nueva y datos heredados.
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
| `python demo.py` | circuito local e interbibliotecario completo |
| `python -c "from backend.app import crear_aplicacion; ..."` | 49 rutas registradas |
| `node --check frontend/app.js` | sin errores de sintaxis |
| Prueba de navegador con Playwright | alta de sede, socio, libro, ejemplar, solicitud, entrega, devolución y reporte sin errores de consola |
| Migración de `biblioteca.db` | respaldo creado y columna agregada |
| Revisión de datos heredados | sede inválida informada sin modificar |

## Decisiones de alcance

- No se implementaron usuarios, autenticación, notificaciones ni historial de
  lecturas; son procesos opcionales del enunciado.
- La interfaz es web y no de consola. La API puede probarse por separado.
- Los reportes se calculan al momento de la consulta, no se guardan en tablas.
- La multa se calcula al registrar la devolución y queda guardada en el
  préstamo.
- El sistema no borra sedes, socios, libros ni ejemplares: usa bajas o estados
  para conservar la trazabilidad.

## Cómo continuar

1. Ejecutar `python main.py`.
2. Abrir `http://127.0.0.1:5000`.
3. Usar `python demo.py` para ver el circuito completo sin tocar la base real.
4. Ejecutar `python -m unittest discover -s tests -v` antes de cualquier
   entrega.
5. Si se modifica el esquema, actualizar `migracion.py` y agregar una prueba
   específica de migración.
