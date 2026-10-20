"use strict";

const API = "/api";

const estado = {
    listados: null,
    salud: null,
    seccion: "inicio",
    sedeEditada: null,
    socioEditado: null,
    libroEditado: null,
    filtrosDisponibilidad: {},
    reporte: "movimiento",
    filtrosReporte: {},
    filasReporte: null,
    nombreReporte: "",
    cargandoReporte: false,
};

const NOMBRES_ESTADO = {
    disponible: "Disponible",
    apartado: "Apartado",
    prestado: "Prestado",
    en_transito: "En transito",
    en_reparacion: "En reparacion",
    pendiente_retorno: "Pendiente de retorno",
    pendiente: "Pendiente",
    entregada: "Entregada",
    cancelada: "Cancelada",
    activo: "Activo",
    devuelto: "Devuelto",
    asignada: "Asignada",
    cumplida: "Cumplida",
    pendiente_empaque: "Pendiente de empaque",
    empaquetado: "Empaquetado",
    despachado: "Despachado",
    recibido: "Recibido",
    bueno: "Bueno",
    deteriorado: "Deteriorado",
    requiere_reparacion: "Requiere reparacion",
    local: "Local",
    interbibliotecario: "Interbibliotecario",
    prestamo: "Prestamo",
    retorno: "Retorno",
};

const ETIQUETAS_REPORTE = {
    sede: "Sede",
    sede_nombre: "Nombre de sede",
    isbn: "ISBN",
    titulo: "Titulo",
    activos: "Activos",
    vencidos: "Vencidos",
    proporcion_vencidos: "Proporcion vencidos",
    promedio_dias_atraso: "Promedio dias de atraso",
    multa_total: "Multa acumulada",
    total: "Total",
    disponibles: "Disponibles",
    prestados: "Prestados",
    en_transito: "En transito",
    en_reparacion: "En reparacion",
    apartados: "Apartados",
    pendientes_retorno: "Pendientes de retorno",
    reservas_activas: "Reservas activas",
    cantidad: "Cantidad",
    origen: "Origen",
    destino: "Destino",
    prestamos: "Prestamos",
    retornos: "Retornos",
    recibidos: "Recibidos",
    pendientes: "Pendientes",
    copias_danadas_recepcion: "Copias danadas al recibir",
    tasa_exito: "Tasa de exito",
    promedio_horas_transito: "Horas de transito",
    promedio_dias_transito: "Dias de transito",
    promedio_horas_total: "Horas totales",
    promedio_dias_total: "Dias totales",
};

const RUTAS_REPORTES = {
    activos: "activos-vencidos",
    disponibilidad: "disponibilidad",
    libros: "libros-solicitados",
    movimiento: "movimiento",
};

document.addEventListener("DOMContentLoaded", function () {
    conectarEventos();
    refrescar().catch(function (error) {
        actualizarServidor(false);
        avisar(error.message, "error");
    });
});

function esc(valor) {
    if (valor === null || valor === undefined) {
        return "";
    }
    return String(valor).replace(/[&<>"']/g, function (caracter) {
        const mapa = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
        };
        return mapa[caracter];
    });
}

function hoyISO() {
    const fecha = new Date();
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const dia = String(fecha.getDate()).padStart(2, "0");
    return fecha.getFullYear() + "-" + mes + "-" + dia;
}

function moneda(valor) {
    if (valor === null || valor === undefined) {
        return "-";
    }
    return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        maximumFractionDigits: 2,
    }).format(Number(valor));
}

function numeroTexto(valor) {
    if (valor === null || valor === undefined) {
        return "-";
    }
    return new Intl.NumberFormat("es-AR").format(Number(valor));
}

function nombreEstado(valor) {
    if (valor === null || valor === undefined) {
        return "-";
    }
    if (NOMBRES_ESTADO[valor]) {
        return NOMBRES_ESTADO[valor];
    }
    return String(valor).replace(/_/g, " ");
}

function claseEstado(valor) {
    const buenos = ["disponible", "activo", "habilitado", "recibido", "cumplida", "bueno", "entregada"];
    const alertas = [
        "pendiente",
        "pendiente_retorno",
        "pendiente_empaque",
        "empaquetado",
        "asignada",
        "deteriorado",
        "requiere_reparacion",
        "apartado",
        "prestamo",
        "retorno",
    ];
    const peligros = ["cancelada", "en_reparacion", "inhabilitado"];
    if (buenos.indexOf(valor) >= 0) {
        return "ok";
    }
    if (peligros.indexOf(valor) >= 0) {
        return "peligro";
    }
    if (alertas.indexOf(valor) >= 0) {
        return "alerta";
    }
    return "info";
}

function insignia(valor) {
    return '<span class="insignia ' + claseEstado(valor) + '">' + esc(nombreEstado(valor)) + "</span>";
}

function insigniaBooleana(valor, textoVerdadero, textoFalso) {
    if (valor) {
        return '<span class="insignia ok">' + esc(textoVerdadero) + "</span>";
    }
    return '<span class="insignia peligro">' + esc(textoFalso) + "</span>";
}

function opciones(items, seleccionado, vacio) {
    let html = "";
    if (vacio !== null && vacio !== undefined) {
        html += '<option value="">' + esc(vacio) + "</option>";
    }
    for (let indice = 0; indice < items.length; indice += 1) {
        const item = items[indice];
        let valor = item;
        let etiqueta = item;
        if (typeof item === "object") {
            valor = item.valor;
            etiqueta = item.etiqueta;
        }
        let seleccion = "";
        if (seleccionado !== null && seleccionado !== undefined && String(valor) === String(seleccionado)) {
            seleccion = " selected";
        }
        html += '<option value="' + esc(valor) + '"' + seleccion + ">" + esc(etiqueta) + "</option>";
    }
    return html;
}

function opcionesSedes(seleccionado, vacio, soloActivas) {
    const lista = [];
    const sedes = estado.listados ? estado.listados.sedes : [];
    for (let indice = 0; indice < sedes.length; indice += 1) {
        const sede = sedes[indice];
        if (soloActivas && !sede.activa) {
            continue;
        }
        let etiqueta = sede.codigo + " - " + sede.nombre;
        if (!sede.activa) {
            etiqueta += " (baja)";
        }
        lista.push({ valor: sede.codigo, etiqueta: etiqueta });
    }
    return opciones(lista, seleccionado, vacio);
}

function opcionesSocios(seleccionado, vacio) {
    const lista = [];
    const socios = estado.listados ? estado.listados.socios : [];
    for (let indice = 0; indice < socios.length; indice += 1) {
        const socio = socios[indice];
        let etiqueta = socio.numero + " - " + socio.nombre;
        if (!socio.habilitado) {
            etiqueta += " (inhabilitado)";
        }
        lista.push({ valor: socio.numero, etiqueta: etiqueta });
    }
    return opciones(lista, seleccionado, vacio);
}

function opcionesLibros(seleccionado, vacio) {
    const lista = [];
    const libros = estado.listados ? estado.listados.libros : [];
    for (let indice = 0; indice < libros.length; indice += 1) {
        const libro = libros[indice];
        lista.push({ valor: libro.isbn, etiqueta: libro.isbn + " - " + libro.titulo });
    }
    return opciones(lista, seleccionado, vacio);
}

function opcionesEjemplares(seleccionado, vacio) {
    const lista = [];
    const ejemplares = estado.listados ? estado.listados.ejemplares : [];
    for (let indice = 0; indice < ejemplares.length; indice += 1) {
        const ejemplar = ejemplares[indice];
        const etiqueta = ejemplar.codigo + " - " + ejemplar.libro_titulo +
            " (" + ejemplar.sede_pertenencia + ", " + nombreEstado(ejemplar.estado_disponibilidad) + ")";
        lista.push({ valor: ejemplar.codigo, etiqueta: etiqueta });
    }
    return opciones(lista, seleccionado, vacio);
}

async function pedir(metodo, ruta, cuerpo) {
    const opcionesPeticion = { method: metodo, headers: {} };
    if (cuerpo !== undefined) {
        opcionesPeticion.headers["Content-Type"] = "application/json";
        opcionesPeticion.body = JSON.stringify(cuerpo);
    }
    const respuesta = await fetch(API + ruta, opcionesPeticion);
    let cuerpoRespuesta = null;
    try {
        cuerpoRespuesta = await respuesta.json();
    } catch (error) {
        cuerpoRespuesta = null;
    }
    if (!respuesta.ok) {
        let mensaje = "La operacion no se pudo completar.";
        if (cuerpoRespuesta && cuerpoRespuesta.error) {
            mensaje = cuerpoRespuesta.error;
        }
        throw new Error(mensaje);
    }
    return cuerpoRespuesta;
}

function avisar(mensaje, tipo) {
    const contenedor = document.getElementById("mensajes");
    const elemento = document.createElement("div");
    elemento.className = "mensaje " + (tipo === "error" ? "error" : "exito");
    elemento.textContent = mensaje;
    contenedor.appendChild(elemento);
    window.setTimeout(function () {
        elemento.remove();
    }, 5000);
}

function actualizarServidor(conectado) {
    const contenedor = document.getElementById("estado-servidor");
    const texto = document.getElementById("estado-servidor-texto");
    contenedor.classList.remove("conectado", "desconectado");
    if (conectado) {
        contenedor.classList.add("conectado");
        texto.textContent = "API conectada";
    } else {
        contenedor.classList.add("desconectado");
        texto.textContent = "Sin conexion";
    }
}

async function refrescar(mensaje) {
    const listados = await pedir("GET", "/listados");
    const salud = await pedir("GET", "/salud");
    estado.listados = listados.datos;
    estado.salud = salud.datos;
    actualizarServidor(true);
    render();
    if (mensaje) {
        avisar(mensaje, "exito");
    }
    if (estado.seccion === "reportes") {
        estado.filasReporte = null;
        await cargarReporte(estado.reporte);
    }
}

function render() {
    const botones = document.querySelectorAll(".menu [data-seccion]");
    for (let indice = 0; indice < botones.length; indice += 1) {
        const boton = botones[indice];
        if (boton.dataset.seccion === estado.seccion) {
            boton.classList.add("activo");
        } else {
            boton.classList.remove("activo");
        }
    }
    const contenido = document.getElementById("contenido");
    if (!estado.listados) {
        contenido.innerHTML = '<p class="cargando">Cargando datos...</p>';
        return;
    }
    if (estado.seccion === "inicio") {
        contenido.innerHTML = renderInicio();
    } else if (estado.seccion === "sedes") {
        contenido.innerHTML = renderSedes();
    } else if (estado.seccion === "socios") {
        contenido.innerHTML = renderSocios();
    } else if (estado.seccion === "catalogo") {
        contenido.innerHTML = renderCatalogo();
    } else if (estado.seccion === "solicitudes") {
        contenido.innerHTML = renderSolicitudes();
    } else if (estado.seccion === "reservas") {
        contenido.innerHTML = renderReservas();
    } else if (estado.seccion === "prestamos") {
        contenido.innerHTML = renderPrestamos();
    } else if (estado.seccion === "remitos") {
        contenido.innerHTML = renderRemitos();
    } else if (estado.seccion === "reportes") {
        contenido.innerHTML = renderReportes();
        pintarReporte();
    }
}

async function abrirSeccion(seccion) {
    estado.seccion = seccion;
    render();
    if (seccion === "reportes" && estado.filasReporte === null) {
        await cargarReporte(estado.reporte);
    }
}

function renderInicio() {
    const resumen = estado.listados.resumen;
    const tarjetas = [
        ["Sedes", resumen.sedes],
        ["Socios", resumen.socios],
        ["Libros", resumen.libros],
        ["Ejemplares", resumen.ejemplares],
        ["Solicitudes pendientes", resumen.solicitudes_pendientes],
        ["Prestamos activos", resumen.prestamos_activos],
        ["Reservas activas", resumen.reservas_activas],
        ["Remitos en curso", resumen.remitos_activos],
    ];
    let html = '<section class="panel">';
    html += '<div class="panel-encabezado"><div><h2>Estado general</h2>';
    html += "<p>Resumen de la red guardado en la base SQLite.</p></div></div>";
    html += '<div class="tarjetas">';
    for (let indice = 0; indice < tarjetas.length; indice += 1) {
        html += '<div class="tarjeta">';
        html += '<span class="numero">' + esc(tarjetas[indice][1]) + "</span>";
        html += '<span class="etiqueta">' + esc(tarjetas[indice][0]) + "</span>";
        html += "</div>";
    }
    html += "</div>";

    if (estado.salud && estado.salud.problemas_datos.length > 0) {
        html += '<div class="aviso"><strong>Datos heredados para revisar</strong>';
        html += "<p>La base existente se conserva sin cambios automaticos. Se encontraron estos problemas:</p><ul>";
        for (let indice = 0; indice < estado.salud.problemas_datos.length; indice += 1) {
            html += "<li>" + esc(estado.salud.problemas_datos[indice]) + "</li>";
        }
        html += "</ul></div>";
    } else {
        html += '<div class="aviso neutro"><strong>Datos sin observaciones</strong>';
        html += "<p>No se detectaron problemas al revisar los datos guardados.</p></div>";
    }

    html += '<h3>Flujo de trabajo</h3>';
    html += '<p class="nota">1. Cargar sedes, socios y catalogo. 2. Registrar una solicitud o reserva. ';
    html += "3. Crear y mover el remito interbibliotecario. 4. Entregar el prestamo y registrar la devolucion. ";
    html += "5. Consultar los reportes.</p>";
    html += "</section>";
    return html;
}

function renderSedes() {
    let sedeEditada = null;
    const sedes = estado.listados.sedes;
    if (estado.sedeEditada !== null) {
        for (let indice = 0; indice < sedes.length; indice += 1) {
            if (sedes[indice].codigo === estado.sedeEditada) {
                sedeEditada = sedes[indice];
            }
        }
    }
    const codigo = sedeEditada ? sedeEditada.codigo : "";
    const nombre = sedeEditada ? sedeEditada.nombre : "";
    const direccion = sedeEditada ? sedeEditada.direccion : "";
    const telefono = sedeEditada ? sedeEditada.telefono : "";
    const horario = sedeEditada ? sedeEditada.horario : "";

    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Sedes</h2>';
    html += "<p>Codigo interno, datos de contacto y estado de atencion.</p></div></div>";
    html += '<div class="grilla-dos"><div>';
    html += '<form class="formulario" data-form="sede">';
    html += "<h3>" + (sedeEditada ? "Editar sede" : "Nueva sede") + "</h3>";
    html += '<div class="campo"><label>Codigo</label>';
    html += '<input name="codigo" required maxlength="40" value="' + esc(codigo) + '"' +
        (sedeEditada ? " disabled" : "") + "></div>";
    html += '<div class="campo"><label>Nombre</label><input name="nombre" required maxlength="200" value="' + esc(nombre) + '"></div>';
    html += '<div class="campo"><label>Direccion</label><input name="direccion" required maxlength="200" value="' + esc(direccion) + '"></div>';
    html += '<div class="campo"><label>Telefono</label><input name="telefono" required maxlength="40" value="' + esc(telefono) + '"></div>';
    html += '<div class="campo"><label>Horario</label><input name="horario" required maxlength="20" placeholder="08:00-18:00" value="' + esc(horario) + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">' +
        (sedeEditada ? "Guardar cambios" : "Crear sede") + "</button>";
    if (sedeEditada) {
        html += '<button class="boton secundario" type="button" data-accion="cancelar-edicion-sede">Cancelar</button>';
    }
    html += "</div></form></div><div>";

    html += '<div class="tabla-contenedor"><table><thead><tr>';
    html += "<th>Codigo</th><th>Nombre</th><th>Direccion</th><th>Telefono</th><th>Horario</th><th>Estado</th><th>Acciones</th>";
    html += "</tr></thead><tbody>";
    if (sedes.length === 0) {
        html += '<tr><td colspan="7">No hay sedes cargadas.</td></tr>';
    }
    for (let indice = 0; indice < sedes.length; indice += 1) {
        const sede = sedes[indice];
        html += "<tr>";
        html += "<td>" + esc(sede.codigo) + "</td>";
        html += "<td>" + esc(sede.nombre) + "</td>";
        html += "<td>" + esc(sede.direccion) + "</td>";
        html += "<td>" + esc(sede.telefono) + "</td>";
        html += "<td>" + esc(sede.horario) + "</td>";
        html += "<td>" + insigniaBooleana(sede.activa, "Activa", "Baja") + "</td>";
        html += '<td><div class="acciones-tabla">';
        html += '<button class="boton secundario pequeno" type="button" data-accion="editar-sede" data-codigo="' + esc(sede.codigo) + '">Editar</button>';
        if (sede.activa) {
            html += '<button class="boton peligro pequeno" type="button" data-accion="baja-sede" data-codigo="' + esc(sede.codigo) + '">Dar de baja</button>';
        } else {
            html += '<button class="boton secundario pequeno" type="button" data-accion="reactivar-sede" data-codigo="' + esc(sede.codigo) + '">Reactivar</button>';
        }
        html += "</div></td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function renderSocios() {
    let socioEditado = null;
    const socios = estado.listados.socios;
    if (estado.socioEditado !== null) {
        for (let indice = 0; indice < socios.length; indice += 1) {
            if (socios[indice].numero === estado.socioEditado) {
                socioEditado = socios[indice];
            }
        }
    }
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Socios</h2>';
    html += "<p>Alta, edicion y habilitacion de socios.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="socio">';
    html += "<h3>" + (socioEditado ? "Editar socio" : "Nuevo socio") + "</h3>";
    html += '<div class="campo"><label>Numero</label><input name="numero" type="number" min="1" required value="' +
        esc(socioEditado ? socioEditado.numero : "") + '"' + (socioEditado ? " disabled" : "") + "></div>";
    html += '<div class="campo"><label>Nombre</label><input name="nombre" required maxlength="200" value="' +
        esc(socioEditado ? socioEditado.nombre : "") + '"></div>';
    html += '<div class="campo"><label>Email</label><input name="email" type="email" required maxlength="254" value="' +
        esc(socioEditado ? socioEditado.email : "") + '"></div>';
    html += '<div class="campo"><label>Telefono</label><input name="telefono" required maxlength="40" value="' +
        esc(socioEditado ? socioEditado.telefono : "") + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">' +
        (socioEditado ? "Guardar cambios" : "Crear socio") + "</button>";
    if (socioEditado) {
        html += '<button class="boton secundario" type="button" data-accion="cancelar-edicion-socio">Cancelar</button>';
    }
    html += "</div></form></div><div>";
    html += '<div class="tabla-contenedor"><table><thead><tr><th>Numero</th><th>Nombre</th><th>Email</th><th>Telefono</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>';
    if (socios.length === 0) {
        html += '<tr><td colspan="6">No hay socios cargados.</td></tr>';
    }
    for (let indice = 0; indice < socios.length; indice += 1) {
        const socio = socios[indice];
        html += "<tr><td>" + esc(socio.numero) + "</td><td>" + esc(socio.nombre) + "</td><td>" + esc(socio.email) +
            "</td><td>" + esc(socio.telefono) + "</td><td>" + insigniaBooleana(socio.habilitado, "Habilitado", "Inhabilitado") + "</td>";
        html += '<td><div class="acciones-tabla">';
        html += '<button class="boton secundario pequeno" type="button" data-accion="editar-socio" data-numero="' + esc(socio.numero) + '">Editar</button>';
        if (socio.habilitado) {
            html += '<button class="boton peligro pequeno" type="button" data-accion="inhabilitar-socio" data-numero="' + esc(socio.numero) + '">Inhabilitar</button>';
        } else {
            html += '<button class="boton secundario pequeno" type="button" data-accion="habilitar-socio" data-numero="' + esc(socio.numero) + '">Habilitar</button>';
        }
        html += "</div></td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function renderCatalogo() {
    let libroEditado = null;
    const libros = estado.listados.libros;
    if (estado.libroEditado !== null) {
        for (let indice = 0; indice < libros.length; indice += 1) {
            if (libros[indice].isbn === estado.libroEditado) {
                libroEditado = libros[indice];
            }
        }
    }
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Catalogo y ejemplares</h2>';
    html += "<p>El libro es la obra; cada ejemplar es una copia fisica de una sede.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="libro">';
    html += "<h3>" + (libroEditado ? "Editar libro" : "Nuevo libro") + "</h3>";
    html += '<div class="campo"><label>ISBN interno</label><input name="isbn" required maxlength="40" value="' +
        esc(libroEditado ? libroEditado.isbn : "") + '"' + (libroEditado ? " disabled" : "") + "></div>";
    html += '<div class="campo"><label>Titulo</label><input name="titulo" required maxlength="200" value="' +
        esc(libroEditado ? libroEditado.titulo : "") + '"></div>';
    html += '<div class="campo"><label>Autor</label><input name="autor" required maxlength="200" value="' +
        esc(libroEditado ? libroEditado.autor : "") + '"></div>';
    html += '<div class="campo"><label>Anio</label><input name="anio" type="number" min="1000" required value="' +
        esc(libroEditado ? libroEditado.anio : "") + '"></div>';
    html += '<div class="campo"><label>Genero</label><input name="genero" required maxlength="100" value="' +
        esc(libroEditado ? libroEditado.genero : "") + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">' +
        (libroEditado ? "Guardar cambios" : "Crear libro") + "</button>";
    if (libroEditado) {
        html += '<button class="boton secundario" type="button" data-accion="cancelar-edicion-libro">Cancelar</button>';
    }
    html += "</div></form></div><div>";
    html += '<div class="tabla-contenedor"><table><thead><tr><th>ISBN</th><th>Titulo</th><th>Autor</th><th>Anio</th><th>Genero</th><th>Acciones</th></tr></thead><tbody>';
    if (libros.length === 0) {
        html += '<tr><td colspan="6">No hay libros cargados.</td></tr>';
    }
    for (let indice = 0; indice < libros.length; indice += 1) {
        const libro = libros[indice];
        html += "<tr><td>" + esc(libro.isbn) + "</td><td>" + esc(libro.titulo) + "</td><td>" + esc(libro.autor) +
            "</td><td>" + esc(libro.anio) + "</td><td>" + esc(libro.genero) + "</td>";
        html += '<td><button class="boton secundario pequeno" type="button" data-accion="editar-libro" data-isbn="' +
            esc(libro.isbn) + '">Editar</button></td></tr>';
    }
    html += "</tbody></table></div></div></div></section>";

    html += '<section class="panel"><div class="panel-encabezado"><div><h2>Ejemplares y disponibilidad</h2>';
    html += "<p>La sede de pertenencia no cambia; la ubicacion actual indica donde esta la copia.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="ejemplar">';
    html += "<h3>Nuevo ejemplar</h3>";
    html += '<div class="campo"><label>Codigo</label><input name="codigo" required maxlength="40"></div>';
    html += '<div class="campo"><label>Libro</label><select name="libro_isbn" required>' + opcionesLibros(null, "Seleccione un libro") + "</select></div>";
    html += '<div class="campo"><label>Sede de pertenencia</label><select name="sede_pertenencia" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Crear ejemplar</button></div>';
    html += "</form></div><div>";
    html += '<form class="filtros" data-form="filtro-disponibilidad">';
    html += '<div class="campo"><label>Libro</label><select name="isbn">' + opcionesLibros(estado.filtrosDisponibilidad.isbn || null, "Todos los libros") + "</select></div>";
    html += '<div class="campo"><label>Sede de pertenencia</label><select name="sede">' + opcionesSedes(estado.filtrosDisponibilidad.sede || null, "Todas las sedes", false) + "</select></div>";
    html += '<div class="acciones-formulario"><button class="boton secundario" type="submit">Filtrar</button></div>';
    html += "</form>";
    const filtrados = [];
    for (let indice = 0; indice < estado.listados.ejemplares.length; indice += 1) {
        const ejemplar = estado.listados.ejemplares[indice];
        if (estado.filtrosDisponibilidad.isbn && ejemplar.libro_isbn !== estado.filtrosDisponibilidad.isbn) {
            continue;
        }
        if (estado.filtrosDisponibilidad.sede && ejemplar.sede_pertenencia !== estado.filtrosDisponibilidad.sede) {
            continue;
        }
        filtrados.push(ejemplar);
    }
    html += '<div class="tabla-contenedor"><table><thead><tr><th>Codigo</th><th>Libro</th><th>Pertenencia</th><th>Ubicacion</th><th>Disponibilidad</th><th>Estado fisico</th><th>Motivo / acciones</th></tr></thead><tbody>';
    if (filtrados.length === 0) {
        html += '<tr><td colspan="7">No hay ejemplares para el filtro elegido.</td></tr>';
    }
    for (let indice = 0; indice < filtrados.length; indice += 1) {
        const ejemplar = filtrados[indice];
        html += "<tr><td>" + esc(ejemplar.codigo) + "</td><td>" + esc(ejemplar.libro_titulo) + "</td><td>" +
            esc(ejemplar.sede_pertenencia) + "</td><td>" + esc(ejemplar.ubicacion_actual || "En transito") + "</td><td>" +
            insignia(ejemplar.estado_disponibilidad) + "</td><td>" + insignia(ejemplar.estado_fisico) + "</td>";
        html += '<td><div class="acciones-tabla"><span class="nota">' + esc(ejemplar.motivo) + "</span>";
        if (ejemplar.estado_disponibilidad === "en_reparacion") {
            html += '<button class="boton secundario pequeno" type="button" data-accion="reparar-ejemplar" data-codigo="' +
                esc(ejemplar.codigo) + '">Marcar reparado</button>';
        }
        html += "</div></td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function renderSolicitudes() {
    const solicitudes = estado.listados.solicitudes;
    const pendientes = [];
    for (let indice = 0; indice < solicitudes.length; indice += 1) {
        if (solicitudes[indice].estado === "pendiente") {
            pendientes.push({
                valor: solicitudes[indice].numero,
                etiqueta: "#" + solicitudes[indice].numero + " - " + solicitudes[indice].socio_nombre +
                    " - " + solicitudes[indice].libro_titulo + " (" + nombreEstado(solicitudes[indice].tipo) + ")",
            });
        }
    }
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Solicitudes</h2>';
    html += "<p>Una solicitud aparta un ejemplar. La interbibliotecaria necesita un remito recibido antes de entregarse.</p></div></div>";
    html += '<div class="grilla-dos"><div>';
    html += '<form class="formulario" data-form="solicitud">';
    html += "<h3>Nueva solicitud</h3>";
    html += '<div class="campo"><label>Socio</label><select name="socio_numero" required>' + opcionesSocios(null, "Seleccione un socio") + "</select></div>";
    html += '<div class="campo"><label>Libro</label><select name="libro_isbn" required>' + opcionesLibros(null, "Seleccione un libro") + "</select></div>";
    html += '<div class="campo"><label>Ejemplar</label><select name="ejemplar_codigo" required>' + opcionesEjemplares(null, "Seleccione un ejemplar") + "</select></div>";
    html += '<div class="campo"><label>Sede de origen</label><select name="sede_origen" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Sede de destino</label><select name="sede_destino" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Fecha</label><input name="fecha_solicitud" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="campo"><label>Tipo</label><select name="tipo" required><option value="local">Local</option><option value="interbibliotecario">Interbibliotecario</option></select></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Registrar solicitud</button></div>';
    html += "</form>";
    html += '<form class="formulario" data-form="entrega" style="margin-top:1rem">';
    html += "<h3>Entregar una solicitud</h3>";
    html += '<div class="campo"><label>Solicitud pendiente</label><select name="solicitud_numero" required>' + opciones(pendientes, null, "Seleccione una solicitud") + "</select></div>";
    html += '<div class="campo"><label>Fecha de prestamo</label><input name="fecha_prestamo" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Entregar</button></div>';
    html += "</form></div><div>";
    html += '<div class="tabla-contenedor"><table><thead><tr><th>#</th><th>Socio</th><th>Libro</th><th>Ejemplar</th><th>Recorrido</th><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Remito</th><th>Acciones</th></tr></thead><tbody>';
    if (solicitudes.length === 0) {
        html += '<tr><td colspan="10">No hay solicitudes registradas.</td></tr>';
    }
    for (let indice = 0; indice < solicitudes.length; indice += 1) {
        const solicitud = solicitudes[indice];
        html += "<tr><td>" + esc(solicitud.numero) + "</td><td>" + esc(solicitud.socio_nombre) + "</td><td>" +
            esc(solicitud.libro_titulo) + "</td><td>" + esc(solicitud.ejemplar_codigo) + "</td><td>" +
            esc(solicitud.sede_origen) + " a " + esc(solicitud.sede_destino) + "</td><td>" +
            esc(solicitud.fecha_solicitud) + "</td><td>" + esc(nombreEstado(solicitud.tipo)) + "</td><td>" +
            insignia(solicitud.estado) + "</td><td>" + esc(solicitud.remito_codigo || "-") + "</td>";
        html += '<td><div class="acciones-tabla">';
        if (solicitud.estado === "pendiente") {
            if (solicitud.tipo === "interbibliotecario" && !solicitud.remito_codigo) {
                html += '<button class="boton secundario pequeno" type="button" data-accion="crear-remito-solicitud" data-numero="' +
                    esc(solicitud.numero) + '">Crear remito</button>';
            }
            html += '<button class="boton peligro pequeno" type="button" data-accion="cancelar-solicitud" data-numero="' +
                esc(solicitud.numero) + '">Cancelar</button>';
        }
        html += "</div></td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function renderReservas() {
    const reservas = estado.listados.reservas;
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Reservas</h2>';
    html += "<p>Cola por libro y sede. La copia disponible se aparta para la primera reserva habilitada.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="reserva">';
    html += "<h3>Nueva reserva</h3>";
    html += '<div class="campo"><label>Socio</label><select name="socio_numero" required>' + opcionesSocios(null, "Seleccione un socio") + "</select></div>";
    html += '<div class="campo"><label>Libro</label><select name="libro_isbn" required>' + opcionesLibros(null, "Seleccione un libro") + "</select></div>";
    html += '<div class="campo"><label>Sede</label><select name="codigo_sede" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Fecha</label><input name="fecha_reserva" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Registrar reserva</button></div>';
    html += "</form></div><div>";
    html += '<div class="tabla-contenedor"><table><thead><tr><th>#</th><th>Socio</th><th>Libro</th><th>Sede</th><th>Fecha</th><th>Estado</th><th>Ejemplar</th><th>Solicitud</th><th>Acciones</th></tr></thead><tbody>';
    if (reservas.length === 0) {
        html += '<tr><td colspan="9">No hay reservas registradas.</td></tr>';
    }
    for (let indice = 0; indice < reservas.length; indice += 1) {
        const reserva = reservas[indice];
        html += "<tr><td>" + esc(reserva.numero) + "</td><td>" + esc(reserva.socio_nombre) + "</td><td>" +
            esc(reserva.libro_titulo) + "</td><td>" + esc(reserva.codigo_sede) + "</td><td>" +
            esc(reserva.fecha_reserva) + "</td><td>" + insignia(reserva.estado) + "</td><td>" +
            esc(reserva.ejemplar_codigo || "-") + "</td><td>" + esc(reserva.solicitud_numero || "-") + "</td>";
        html += '<td><div class="acciones-tabla">';
        if (reserva.estado === "pendiente" || reserva.estado === "asignada") {
            html += '<button class="boton peligro pequeno" type="button" data-accion="cancelar-reserva" data-numero="' +
                esc(reserva.numero) + '">Cancelar</button>';
        }
        html += "</div></td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function renderPrestamos() {
    const prestamos = estado.listados.prestamos;
    const activos = [];
    for (let indice = 0; indice < prestamos.length; indice += 1) {
        if (prestamos[indice].estado === "activo") {
            activos.push({
                valor: prestamos[indice].numero,
                etiqueta: "#" + prestamos[indice].numero + " - " + prestamos[indice].socio_nombre +
                    " - " + (prestamos[indice].libro_titulo || prestamos[indice].ejemplar_codigo),
            });
        }
    }
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Prestamos y devoluciones</h2>';
    html += "<p>La multa se calcula con los dias de atraso configurados. Una devolucion fuera de la sede de pertenencia deja la copia pendiente de retorno.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="devolucion">';
    html += "<h3>Registrar devolucion</h3>";
    html += '<div class="campo"><label>Prestamo activo</label><select name="numero" required>' + opciones(activos, null, "Seleccione un prestamo") + "</select></div>";
    html += '<div class="campo"><label>Fecha de devolucion</label><input name="fecha_devolucion" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="campo"><label>Sede de devolucion</label><select name="sede_devolucion" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Estado fisico</label><select name="estado_fisico" required><option value="bueno">Bueno</option><option value="deteriorado">Deteriorado</option><option value="requiere_reparacion">Requiere reparacion</option></select></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Registrar devolucion</button></div>';
    html += "</form></div><div>";
    html += '<div class="tabla-contenedor"><table><thead><tr><th>#</th><th>Socio</th><th>Libro</th><th>Recorrido</th><th>Prestamo</th><th>Vence</th><th>Devolucion</th><th>Estado</th><th>Multa</th></tr></thead><tbody>';
    if (prestamos.length === 0) {
        html += '<tr><td colspan="9">No hay prestamos registrados.</td></tr>';
    }
    for (let indice = 0; indice < prestamos.length; indice += 1) {
        const prestamo = prestamos[indice];
        let multa = moneda(prestamo.multa);
        if (prestamo.estado === "activo") {
            multa = moneda(prestamo.multa_estimada) + " estimada";
        }
        html += "<tr><td>" + esc(prestamo.numero) + "</td><td>" + esc(prestamo.socio_nombre) + "</td><td>" +
            esc(prestamo.libro_titulo || prestamo.ejemplar_codigo) + "</td><td>" + esc(prestamo.sede_origen) +
            " a " + esc(prestamo.sede_destino) + "</td><td>" + esc(prestamo.fecha_prestamo) + "</td><td>" +
            esc(prestamo.fecha_vencimiento) + "</td><td>" + esc(prestamo.fecha_devolucion || "-") + "</td><td>" +
            insignia(prestamo.estado) + "</td><td>" + esc(multa) + "</td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function renderRemitos() {
    const ejemplares = estado.listados.ejemplares;
    const pendientesRetorno = [];
    for (let indice = 0; indice < ejemplares.length; indice += 1) {
        if (ejemplares[indice].estado_disponibilidad === "pendiente_retorno") {
            pendientesRetorno.push({
                valor: ejemplares[indice].codigo,
                etiqueta: ejemplares[indice].codigo + " - " + ejemplares[indice].libro_titulo +
                    " (" + ejemplares[indice].ubicacion_actual + " a " + ejemplares[indice].sede_pertenencia + ")",
            });
        }
    }
    const remitos = estado.listados.remitos.slice();
    remitos.sort(function (a, b) {
        return numeroRemito(b.codigo) - numeroRemito(a.codigo);
    });

    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Remitos e historial</h2>';
    html += "<p>El remito registra el empaque, el despacho y la recepcion. El historial se guarda en SQLite.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="retorno">';
    html += "<h3>Crear remito de retorno</h3>";
    html += '<div class="campo"><label>Ejemplar pendiente de retorno</label><select name="ejemplar_codigo" required>' +
        opciones(pendientesRetorno, null, "Seleccione un ejemplar") + "</select></div>";
    html += '<div class="campo"><label>Fecha de creacion</label><input name="fecha_creacion" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Crear remito</button></div>';
    html += "</form>";
    html += '<p class="nota">Los remitos de prestamo se crean desde la seccion Solicitudes.</p></div><div>';
    html += '<div class="tabla-contenedor"><table><thead><tr><th>Codigo</th><th>Motivo</th><th>Recorrido</th><th>Creacion</th><th>Estado</th><th>Ejemplares</th><th>Acciones</th></tr></thead><tbody>';
    if (remitos.length === 0) {
        html += '<tr><td colspan="7">No hay remitos registrados.</td></tr>';
    }
    for (let indice = 0; indice < remitos.length; indice += 1) {
        const remito = remitos[indice];
        let codigos = [];
        for (let posicion = 0; posicion < remito.asignaciones.length; posicion += 1) {
            codigos.push(remito.asignaciones[posicion].ejemplar_codigo);
        }
        html += "<tr><td>" + esc(remito.codigo) + "</td><td>" + esc(nombreEstado(remito.motivo)) + "</td><td>" +
            esc(remito.sede_origen) + " a " + esc(remito.sede_destino) + "</td><td>" +
            esc(remito.fecha_creacion) + "</td><td>" + insignia(remito.estado_actual) + "</td><td>" +
            esc(codigos.join(", ")) + "</td>";
        html += '<td><div class="acciones-tabla">';
        if (remito.estado_actual === "pendiente_empaque") {
            html += '<button class="boton secundario pequeno" type="button" data-accion="empaquetar-remito" data-codigo="' +
                esc(remito.codigo) + '">Empaquetar</button>';
        } else if (remito.estado_actual === "empaquetado") {
            html += '<button class="boton secundario pequeno" type="button" data-accion="despachar-remito" data-codigo="' +
                esc(remito.codigo) + '">Despachar</button>';
        } else if (remito.estado_actual === "despachado") {
            html += '<button class="boton secundario pequeno" type="button" data-accion="recibir-remito" data-codigo="' +
                esc(remito.codigo) + '">Recibir</button>';
        }
        html += "</div>";
        html += '<details class="detalle-remito"><summary>Historial</summary><ul>';
        if (remito.historial.length === 0) {
            html += "<li>Sin eventos.</li>";
        }
        for (let posicion = 0; posicion < remito.historial.length; posicion += 1) {
            const evento = remito.historial[posicion];
            html += "<li>" + esc(evento.orden) + ". " + esc(nombreEstado(evento.estado)) + " - " + esc(evento.momento) + "</li>";
        }
        html += "</ul></details>";
        if (remito.asignaciones.length > 0) {
            html += '<details class="detalle-remito"><summary>Recepcion</summary><ul>';
            for (let posicion = 0; posicion < remito.asignaciones.length; posicion += 1) {
                const asignacion = remito.asignaciones[posicion];
                html += "<li>" + esc(asignacion.ejemplar_codigo) + ": " +
                    esc(asignacion.estado_fisico_recepcion ? nombreEstado(asignacion.estado_fisico_recepcion) : "sin registrar") + "</li>";
            }
            html += "</ul></details>";
        }
        html += "</td></tr>";
    }
    html += "</tbody></table></div></div></div></section>";
    return html;
}

function numeroRemito(codigo) {
    if (!codigo || codigo.indexOf("R-") !== 0) {
        return 0;
    }
    const parte = codigo.substring(2);
    if (!/^\d+$/.test(parte)) {
        return 0;
    }
    return Number(parte);
}

function renderReportes() {
    const botones = [
        ["activos", "Activos y vencidos"],
        ["disponibilidad", "Disponibilidad"],
        ["libros", "Libros solicitados"],
        ["movimiento", "Movimiento de envios"],
    ];
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Reportes</h2>';
    html += "<p>Los reportes se generan con el patron Factory Method y consultan la base mediante el ORM.</p></div></div>";
    html += '<div class="botones-reportes">';
    for (let indice = 0; indice < botones.length; indice += 1) {
        const activo = estado.reporte === botones[indice][0] ? " activo" : "";
        html += '<button type="button" class="' + activo.trim() + '" data-reporte="' + botones[indice][0] + '">' +
            esc(botones[indice][1]) + "</button>";
    }
    html += "</div>";
    html += '<form class="filtros" data-form="reporte">';
    const filtros = estado.filtrosReporte;

    if (estado.reporte === "activos") {
        html += '<div class="campo"><label>Fecha de referencia</label><input type="date" name="fecha_referencia" value="' +
            esc(filtros.fecha_referencia || hoyISO()) + '"></div>';
    } else if (estado.reporte === "disponibilidad") {
        html += '<div class="campo"><label>Sede</label><select name="sede">' + opcionesSedes(filtros.sede || null, "Todas las sedes", false) + "</select></div>";
        html += '<div class="campo"><label>Libro</label><select name="isbn">' + opcionesLibros(filtros.isbn || null, "Todos los libros") + "</select></div>";
    } else if (estado.reporte === "libros") {
        html += '<div class="campo"><label>Desde</label><input type="date" name="desde" value="' + esc(filtros.desde || "") + '"></div>';
        html += '<div class="campo"><label>Hasta</label><input type="date" name="hasta" value="' + esc(filtros.hasta || "") + '"></div>';
        html += '<div class="campo"><label>Sede origen</label><select name="sede_origen">' + opcionesSedes(filtros.sede_origen || null, "Todas", false) + "</select></div>";
        html += '<div class="campo"><label>Sede destino</label><select name="sede_destino">' + opcionesSedes(filtros.sede_destino || null, "Todas", false) + "</select></div>";
    } else {
        html += '<p class="nota">Agrupado por sede de origen y destino, con tiempos de transito y recepcion.</p>';
    }
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Generar reporte</button></div>';
    html += "</form>";
    html += '<div id="reporte-contenido"></div>';
    html += "</section>";
    return html;
}

function pintarReporte() {
    const contenedor = document.getElementById("reporte-contenido");
    if (!contenedor) {
        return;
    }
    if (estado.cargandoReporte) {
        contenedor.innerHTML = '<p class="cargando">Generando reporte...</p>';
        return;
    }
    if (!estado.filasReporte) {
        contenedor.innerHTML = '<p class="nota">Elija un reporte y presione Generar reporte.</p>';
        return;
    }
    if (estado.filasReporte.length === 0) {
        contenedor.innerHTML = '<div class="aviso neutro"><strong>Sin datos</strong><p>No hay informacion para los filtros elegidos.</p></div>';
        return;
    }
    const columnas = Object.keys(estado.filasReporte[0]);
    let html = '<p class="titulo-reporte">' + esc(estado.nombreReporte) + "</p>";
    html += '<div class="tabla-contenedor"><table><thead><tr>';
    for (let indice = 0; indice < columnas.length; indice += 1) {
        const clave = columnas[indice];
        html += "<th>" + esc(ETIQUETAS_REPORTE[clave] || clave) + "</th>";
    }
    html += "</tr></thead><tbody>";
    for (let fila = 0; fila < estado.filasReporte.length; fila += 1) {
        html += "<tr>";
        for (let columna = 0; columna < columnas.length; columna += 1) {
            const clave = columnas[columna];
            html += "<td>" + esc(formatearValorReporte(clave, estado.filasReporte[fila][clave])) + "</td>";
        }
        html += "</tr>";
    }
    html += "</tbody></table></div>";
    contenedor.innerHTML = html;
}

function formatearValorReporte(clave, valor) {
    if (valor === null || valor === undefined) {
        return "-";
    }
    if (clave === "proporcion_vencidos" || clave === "tasa_exito") {
        return (Number(valor) * 100).toFixed(0) + "%";
    }
    if (clave === "multa_total") {
        return moneda(valor);
    }
    if (typeof valor === "number") {
        return numeroTexto(valor);
    }
    return String(valor);
}

async function cargarReporte(nombre) {
    estado.cargandoReporte = true;
    pintarReporte();
    const parametros = new URLSearchParams();
    const filtros = estado.filtrosReporte;
    if (nombre === "activos" && filtros.fecha_referencia) {
        parametros.set("fecha_referencia", filtros.fecha_referencia);
    }
    if (nombre === "disponibilidad") {
        if (filtros.sede) {
            parametros.set("sede", filtros.sede);
        }
        if (filtros.isbn) {
            parametros.set("isbn", filtros.isbn);
        }
    }
    if (nombre === "libros") {
        if (filtros.desde) {
            parametros.set("desde", filtros.desde);
        }
        if (filtros.hasta) {
            parametros.set("hasta", filtros.hasta);
        }
        if (filtros.sede_origen) {
            parametros.set("sede_origen", filtros.sede_origen);
        }
        if (filtros.sede_destino) {
            parametros.set("sede_destino", filtros.sede_destino);
        }
    }
    const ruta = "/reportes/" + RUTAS_REPORTES[nombre];
    const consulta = parametros.toString();
    try {
        const respuesta = await pedir("GET", ruta + (consulta ? "?" + consulta : ""));
        estado.filasReporte = respuesta.datos.filas;
        estado.nombreReporte = respuesta.datos.reporte;
    } catch (error) {
        estado.filasReporte = null;
        estado.nombreReporte = "";
        avisar(error.message, "error");
    } finally {
        estado.cargandoReporte = false;
        pintarReporte();
    }
}

function conectarEventos() {
    document.addEventListener("click", async function (evento) {
        const botonSeccion = evento.target.closest(".menu [data-seccion]");
        if (botonSeccion) {
            await abrirSeccion(botonSeccion.dataset.seccion);
            return;
        }
        const botonReporte = evento.target.closest("[data-reporte]");
        if (botonReporte) {
            estado.reporte = botonReporte.dataset.reporte;
            estado.filtrosReporte = {};
            estado.filasReporte = null;
            estado.nombreReporte = "";
            render();
            await cargarReporte(estado.reporte);
            return;
        }
        const botonAccion = evento.target.closest("[data-accion]");
        if (!botonAccion) {
            return;
        }
        evento.preventDefault();
        try {
            await manejarAccion(botonAccion.dataset.accion, botonAccion.dataset);
        } catch (error) {
            avisar(error.message, "error");
        }
    });

    document.addEventListener("submit", async function (evento) {
        const formulario = evento.target.closest("form[data-form]");
        if (!formulario) {
            return;
        }
        evento.preventDefault();
        try {
            await manejarFormulario(formulario);
        } catch (error) {
            avisar(error.message, "error");
        }
    });
}

async function manejarFormulario(formulario) {
    const tipo = formulario.dataset.form;
    const datos = Object.fromEntries(new FormData(formulario).entries());

    if (tipo === "sede") {
        if (estado.sedeEditada !== null) {
            await pedir("PUT", "/sedes/" + encodeURIComponent(estado.sedeEditada), {
                nombre: datos.nombre,
                direccion: datos.direccion,
                telefono: datos.telefono,
                horario: datos.horario,
            });
            estado.sedeEditada = null;
            await refrescar("Sede modificada.");
        } else {
            await pedir("POST", "/sedes", datos);
            await refrescar("Sede creada.");
        }
        return;
    }

    if (tipo === "socio") {
        if (estado.socioEditado !== null) {
            await pedir("PUT", "/socios/" + encodeURIComponent(estado.socioEditado), {
                nombre: datos.nombre,
                email: datos.email,
                telefono: datos.telefono,
            });
            estado.socioEditado = null;
            await refrescar("Socio modificado.");
        } else {
            datos.numero = Number(datos.numero);
            await pedir("POST", "/socios", datos);
            await refrescar("Socio creado.");
        }
        return;
    }

    if (tipo === "libro") {
        if (estado.libroEditado !== null) {
            await pedir("PUT", "/libros/" + encodeURIComponent(estado.libroEditado), {
                titulo: datos.titulo,
                autor: datos.autor,
                anio: Number(datos.anio),
                genero: datos.genero,
            });
            estado.libroEditado = null;
            await refrescar("Libro modificado.");
        } else {
            datos.anio = Number(datos.anio);
            await pedir("POST", "/libros", datos);
            await refrescar("Libro creado.");
        }
        return;
    }

    if (tipo === "ejemplar") {
        await pedir("POST", "/ejemplares", datos);
        await refrescar("Ejemplar creado.");
        return;
    }

    if (tipo === "filtro-disponibilidad") {
        estado.filtrosDisponibilidad = datos;
        render();
        return;
    }

    if (tipo === "solicitud") {
        datos.socio_numero = Number(datos.socio_numero);
        await pedir("POST", "/solicitudes", datos);
        await refrescar("Solicitud registrada.");
        return;
    }

    if (tipo === "entrega") {
        datos.solicitud_numero = Number(datos.solicitud_numero);
        const numero = datos.solicitud_numero;
        delete datos.solicitud_numero;
        await pedir("POST", "/solicitudes/" + numero + "/entregar", datos);
        await refrescar("Prestamo entregado.");
        return;
    }

    if (tipo === "reserva") {
        datos.socio_numero = Number(datos.socio_numero);
        await pedir("POST", "/reservas", datos);
        await refrescar("Reserva registrada.");
        return;
    }

    if (tipo === "devolucion") {
        const numero = Number(datos.numero);
        delete datos.numero;
        await pedir("POST", "/prestamos/" + numero + "/devolucion", datos);
        await refrescar("Devolucion registrada.");
        return;
    }

    if (tipo === "retorno") {
        await pedir("POST", "/remitos/retorno", datos);
        await refrescar("Remito de retorno creado.");
        return;
    }

    if (tipo === "reporte") {
        estado.filtrosReporte = datos;
        await cargarReporte(estado.reporte);
        return;
    }
}

async function manejarAccion(accion, datos) {
    if (accion === "editar-sede") {
        estado.sedeEditada = datos.codigo;
        render();
        return;
    }
    if (accion === "cancelar-edicion-sede") {
        estado.sedeEditada = null;
        render();
        return;
    }
    if (accion === "baja-sede") {
        if (!window.confirm("Dar de baja la sede " + datos.codigo + "?")) {
            return;
        }
        await pedir("POST", "/sedes/" + encodeURIComponent(datos.codigo) + "/baja", {});
        await refrescar("Sede dada de baja.");
        return;
    }
    if (accion === "reactivar-sede") {
        await pedir("POST", "/sedes/" + encodeURIComponent(datos.codigo) + "/reactivacion", {});
        await refrescar("Sede reactivada.");
        return;
    }
    if (accion === "editar-socio") {
        estado.socioEditado = Number(datos.numero);
        render();
        return;
    }
    if (accion === "cancelar-edicion-socio") {
        estado.socioEditado = null;
        render();
        return;
    }
    if (accion === "habilitar-socio") {
        await pedir("POST", "/socios/" + encodeURIComponent(datos.numero) + "/habilitar", {});
        await refrescar("Socio habilitado.");
        return;
    }
    if (accion === "inhabilitar-socio") {
        if (!window.confirm("Inhabilitar el socio " + datos.numero + "?")) {
            return;
        }
        await pedir("POST", "/socios/" + encodeURIComponent(datos.numero) + "/inhabilitar", {});
        await refrescar("Socio inhabilitado.");
        return;
    }
    if (accion === "editar-libro") {
        estado.libroEditado = datos.isbn;
        render();
        return;
    }
    if (accion === "cancelar-edicion-libro") {
        estado.libroEditado = null;
        render();
        return;
    }
    if (accion === "reparar-ejemplar") {
        await pedir("POST", "/ejemplares/" + encodeURIComponent(datos.codigo) + "/reparar", {});
        await refrescar("Ejemplar reparado.");
        return;
    }
    if (accion === "crear-remito-solicitud") {
        await pedir("POST", "/remitos/prestamo", { solicitud_numero: Number(datos.numero) });
        await refrescar("Remito de prestamo creado.");
        return;
    }
    if (accion === "cancelar-solicitud") {
        if (!window.confirm("Cancelar la solicitud " + datos.numero + "?")) {
            return;
        }
        await pedir("POST", "/solicitudes/" + encodeURIComponent(datos.numero) + "/cancelar", {});
        await refrescar("Solicitud cancelada.");
        return;
    }
    if (accion === "cancelar-reserva") {
        if (!window.confirm("Cancelar la reserva " + datos.numero + "?")) {
            return;
        }
        await pedir("POST", "/reservas/" + encodeURIComponent(datos.numero) + "/cancelar", {});
        await refrescar("Reserva cancelada.");
        return;
    }
    if (accion === "empaquetar-remito") {
        await pedir("POST", "/remitos/" + encodeURIComponent(datos.codigo) + "/empaquetar", {});
        await refrescar("Remito empaquetado.");
        return;
    }
    if (accion === "despachar-remito") {
        await pedir("POST", "/remitos/" + encodeURIComponent(datos.codigo) + "/despachar", {});
        await refrescar("Remito despachado.");
        return;
    }
    if (accion === "recibir-remito") {
        await pedir("POST", "/remitos/" + encodeURIComponent(datos.codigo) + "/recibir", {});
        await refrescar("Remito recibido.");
    }
}
