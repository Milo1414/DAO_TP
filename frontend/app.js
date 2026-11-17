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
    rutaReporteGenerado: "",
    cargandoReporte: false,
    numeroCampo: 0,
};

const NOMBRES_ESTADO = {
    disponible: "Disponible",
    apartado: "Apartado",
    prestado: "Prestado",
    en_transito: "En tránsito",
    en_reparacion: "En reparación",
    pendiente_retorno: "Pendiente de retorno",
    pendiente: "Pendiente",
    entregada: "Entregada",
    cancelada: "Cancelada",
    cancelado: "Cancelado",
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
    requiere_reparacion: "Requiere reparación",
    local: "Local",
    interbibliotecario: "Interbibliotecario",
    prestamo: "Préstamo",
    retorno: "Retorno",
};

const ETIQUETAS_REPORTE = {
    sede: "Sede",
    sede_nombre: "Nombre de sede",
    isbn: "ISBN",
    titulo: "Título",
    activos: "Activos",
    vencidos: "Vencidos",
    proporcion_vencidos: "Proporción de vencidos",
    promedio_dias_atraso: "Promedio de días de atraso",
    multa_total: "Multa acumulada",
    total: "Total",
    disponibles: "Disponibles",
    prestados: "Prestados",
    en_transito: "En tránsito",
    en_reparacion: "En reparación",
    apartados: "Apartados",
    pendientes_retorno: "Pendientes de retorno",
    reservas_activas: "Reservas activas",
    cantidad: "Cantidad",
    origen: "Origen",
    destino: "Destino",
    prestamos: "Préstamos",
    retornos: "Retornos",
    recibidos: "Recibidos",
    pendientes: "Pendientes",
    cancelados: "Cancelados",
    copias_danadas_recepcion: "Copias dañadas al recibir",
    tasa_exito: "Tasa de éxito",
    promedio_horas_transito: "Horas de tránsito",
    promedio_dias_transito: "Días de tránsito",
    promedio_horas_total: "Horas totales",
    promedio_dias_total: "Días totales",
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

function esDigitoHorario(caracter) {
    return caracter >= "0" && caracter <= "9";
}

function formatearHorario(valor) {
    let digitos = "";
    for (let indice = 0; indice < valor.length; indice += 1) {
        if (esDigitoHorario(valor[indice])) {
            digitos += valor[indice];
        }
    }
    if (digitos.length > 8) {
        digitos = digitos.substring(0, 8);
    }
    let formateado = "";
    for (let indice = 0; indice < digitos.length; indice += 1) {
        if (indice === 2 || indice === 6) {
            formateado += ":";
        }
        if (indice === 4) {
            formateado += "-";
        }
        formateado += digitos[indice];
    }
    return formateado;
}

function contarDigitosAntes(valor, posicion) {
    let cantidad = 0;
    const limite = Math.min(posicion, valor.length);
    for (let indice = 0; indice < limite; indice += 1) {
        if (esDigitoHorario(valor[indice])) {
            cantidad += 1;
        }
    }
    return cantidad;
}

function posicionDespuesDeDigitos(valor, cantidad) {
    if (cantidad <= 0) {
        return 0;
    }
    let vistos = 0;
    for (let indice = 0; indice < valor.length; indice += 1) {
        if (esDigitoHorario(valor[indice])) {
            vistos += 1;
            if (vistos === cantidad) {
                return indice + 1;
            }
        }
    }
    return valor.length;
}

function formatearCampoHorario(campo) {
    const valorAnterior = campo.value;
    const posicionAnterior = campo.selectionStart;
    const formateado = formatearHorario(valorAnterior);
    if (formateado === valorAnterior) {
        return;
    }
    campo.value = formateado;
    if (posicionAnterior !== null) {
        const digitosAntes = contarDigitosAntes(valorAnterior, posicionAnterior);
        const nuevaPosicion = posicionDespuesDeDigitos(formateado, digitosAntes);
        campo.setSelectionRange(nuevaPosicion, nuevaPosicion);
    }
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
    const peligros = ["cancelada", "cancelado", "en_reparacion", "inhabilitado"];
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

function opcionesEjemplares(seleccionado, vacio, isbn) {
    const lista = [];
    const ejemplares = estado.listados ? estado.listados.ejemplares : [];
    for (let indice = 0; indice < ejemplares.length; indice += 1) {
        const ejemplar = ejemplares[indice];
        if (isbn && ejemplar.libro_isbn !== isbn) {
            continue;
        }
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
        let mensaje = "La operación no se pudo completar.";
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
    let duracion = 4000;
    if (tipo === "error") {
        elemento.className = "mensaje error";
        elemento.setAttribute("role", "alert");
        duracion = 9000;
    } else {
        elemento.className = "mensaje exito";
    }
    elemento.textContent = mensaje;
    elemento.title = "Clic para cerrar";
    elemento.addEventListener("click", function () {
        elemento.remove();
    });
    contenedor.appendChild(elemento);
    window.setTimeout(function () {
        elemento.remove();
    }, duracion);
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
        texto.textContent = "Sin conexión";
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
            boton.setAttribute("aria-current", "page");
        } else {
            boton.classList.remove("activo");
            boton.removeAttribute("aria-current");
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
    asociarEtiquetas(contenido);
    actualizarContadores();
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
    const pendientes = calcularPendientes();
    const tarjetas = [
        ["Sedes", resumen.sedes, "sedes"],
        ["Socios", resumen.socios, "socios"],
        ["Libros", resumen.libros, "catalogo"],
        ["Ejemplares", resumen.ejemplares, "catalogo"],
        ["Solicitudes pendientes", resumen.solicitudes_pendientes, "solicitudes"],
        ["Préstamos activos", resumen.prestamos_activos, "prestamos"],
        ["Reservas activas", resumen.reservas_activas, "reservas"],
        ["Remitos en curso", resumen.remitos_activos, "remitos"],
    ];
    const tareas = [
        [pendientes.vencidos, "Préstamos vencidos sin devolver", "prestamos", true],
        [pendientes.solicitudes, "Solicitudes pendientes de entrega", "solicitudes", false],
        [pendientes.remitos, "Remitos en curso: empaque, despacho o recepción", "remitos", false],
        [pendientes.retornos, "Copias a la espera de un remito de retorno", "remitos", false],
        [pendientes.reparacion, "Copias en reparación", "catalogo", false],
    ];

    let html = '<section class="panel">';
    html += '<div class="panel-encabezado"><h2>Estado general</h2>';
    html += "<p>Resumen de la red. Cada tarjeta lleva a su sección.</p></div>";
    html += '<div class="tarjetas">';
    for (let indice = 0; indice < tarjetas.length; indice += 1) {
        html += '<button type="button" class="tarjeta" data-seccion="' + tarjetas[indice][2] + '">';
        html += '<span class="numero">' + esc(tarjetas[indice][1]) + "</span>";
        html += '<span class="etiqueta">' + esc(tarjetas[indice][0]) + "</span>";
        html += "</button>";
    }
    html += "</div>";

    html += "<h3>Para atender ahora</h3>";
    let hayTareas = false;
    let lista = '<ul class="atencion">';
    for (let indice = 0; indice < tareas.length; indice += 1) {
        const tarea = tareas[indice];
        if (tarea[0] === 0) {
            continue;
        }
        hayTareas = true;
        lista += '<li><button type="button" data-seccion="' + tarea[2] + '"' + (tarea[3] ? ' class="urgente"' : "") + ">";
        lista += '<span class="cantidad">' + esc(tarea[0]) + "</span><span>" + esc(tarea[1]) + "</span>";
        lista += "</button></li>";
    }
    lista += "</ul>";
    if (hayTareas) {
        html += lista;
    } else {
        html += '<p class="nota">No hay tareas pendientes.</p>';
    }

    if (estado.salud && estado.salud.problemas_datos.length > 0) {
        html += '<div class="aviso"><strong>Datos heredados para revisar</strong>';
        html += "<p>La base existente se conserva sin cambios automáticos. Se encontraron estos problemas:</p><ul>";
        for (let indice = 0; indice < estado.salud.problemas_datos.length; indice += 1) {
            html += "<li>" + esc(estado.salud.problemas_datos[indice]) + "</li>";
        }
        html += "</ul></div>";
    } else {
        html += '<div class="aviso neutro"><strong>Datos sin observaciones</strong>';
        html += "<p>No se detectaron problemas al revisar los datos guardados.</p></div>";
    }

    html += "<h3>Flujo de trabajo</h3>";
    html += '<ol class="pasos">';
    html += "<li><strong>Cargar datos</strong>Sedes, socios, libros y ejemplares.</li>";
    html += "<li><strong>Solicitar o reservar</strong>La solicitud aparta una copia; la reserva espera en cola.</li>";
    html += "<li><strong>Enviar entre sedes</strong>El remito se empaqueta, se despacha y se recibe.</li>";
    html += "<li><strong>Entregar y devolver</strong>La entrega crea el préstamo; la devolución calcula la multa.</li>";
    html += "<li><strong>Consultar reportes</strong>Vencidos, disponibilidad, pedidos y envíos.</li>";
    html += "</ol>";
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
    html += "<p>Código interno, dirección, datos de contacto, horario y estado de cada sede.</p></div></div>";
    html += '<div class="grilla-dos"><div>';
    html += '<form class="formulario" data-form="sede">';
    html += "<h3>" + (sedeEditada ? "Editar sede" : "Nueva sede") + "</h3>";
    html += '<div class="campo"><label>Código</label>';
    html += '<input name="codigo" required maxlength="40" value="' + esc(codigo) + '"' +
        (sedeEditada ? " disabled" : "") + "></div>";
    html += '<div class="campo"><label>Nombre</label><input name="nombre" required maxlength="200" value="' + esc(nombre) + '"></div>';
    html += '<div class="campo"><label>Dirección</label><input name="direccion" required maxlength="200" value="' + esc(direccion) + '"></div>';
    html += '<div class="campo"><label>Teléfono</label><input name="telefono" required maxlength="40" value="' + esc(telefono) + '"></div>';
    html += '<div class="campo"><label>Horario</label><input name="horario" required maxlength="11" inputmode="numeric" placeholder="08001800" value="' + esc(horario) + '">';
    html += '<span class="campo-ayuda">Escriba solo los 8 números; los : y el - se agregan solos.</span></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">' +
        (sedeEditada ? "Guardar cambios" : "Crear sede") + "</button>";
    if (sedeEditada) {
        html += '<button class="boton secundario" type="button" data-accion="cancelar-edicion-sede">Cancelar</button>';
    }
    html += "</div></form></div><div>";

    html += buscador("Buscar sede");
    html += '<div class="tabla-contenedor"><table><thead><tr>';
    html += "<th>Código</th><th>Nombre</th><th>Dirección</th><th>Teléfono</th><th>Horario</th><th>Estado</th><th>Acciones</th>";
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
    html += "<p>Alta, edición y habilitación de socios.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="socio">';
    html += "<h3>" + (socioEditado ? "Editar socio" : "Nuevo socio") + "</h3>";
    html += '<div class="campo"><label>Número</label><input name="numero" type="number" min="1" required value="' +
        esc(socioEditado ? socioEditado.numero : "") + '"' + (socioEditado ? " disabled" : "") + "></div>";
    html += '<div class="campo"><label>Nombre</label><input name="nombre" required maxlength="200" value="' +
        esc(socioEditado ? socioEditado.nombre : "") + '"></div>';
    html += '<div class="campo"><label>Email</label><input name="email" type="email" required maxlength="254" value="' +
        esc(socioEditado ? socioEditado.email : "") + '"></div>';
    html += '<div class="campo"><label>Teléfono</label><input name="telefono" required maxlength="40" value="' +
        esc(socioEditado ? socioEditado.telefono : "") + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">' +
        (socioEditado ? "Guardar cambios" : "Crear socio") + "</button>";
    if (socioEditado) {
        html += '<button class="boton secundario" type="button" data-accion="cancelar-edicion-socio">Cancelar</button>';
    }
    html += "</div></form></div><div>";
    html += buscador("Buscar socio");
    html += '<div class="tabla-contenedor"><table><thead><tr><th>Número</th><th>Nombre</th><th>Email</th><th>Teléfono</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>';
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
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Catálogo y ejemplares</h2>';
    html += "<p>El libro es la obra; cada ejemplar es una copia física de una sede.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="libro">';
    html += "<h3>" + (libroEditado ? "Editar libro" : "Nuevo libro") + "</h3>";
    html += '<div class="campo"><label>ISBN interno</label><input name="isbn" required maxlength="40" value="' +
        esc(libroEditado ? libroEditado.isbn : "") + '"' + (libroEditado ? " disabled" : "") + "></div>";
    html += '<div class="campo"><label>Título</label><input name="titulo" required maxlength="200" value="' +
        esc(libroEditado ? libroEditado.titulo : "") + '"></div>';
    html += '<div class="campo"><label>Autor</label><input name="autor" required maxlength="200" value="' +
        esc(libroEditado ? libroEditado.autor : "") + '"></div>';
    html += '<div class="campo"><label>Año</label><input name="anio" type="number" min="1000" required value="' +
        esc(libroEditado ? libroEditado.anio : "") + '"></div>';
    html += '<div class="campo"><label>Género</label><input name="genero" required maxlength="100" value="' +
        esc(libroEditado ? libroEditado.genero : "") + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">' +
        (libroEditado ? "Guardar cambios" : "Crear libro") + "</button>";
    if (libroEditado) {
        html += '<button class="boton secundario" type="button" data-accion="cancelar-edicion-libro">Cancelar</button>';
    }
    html += "</div></form></div><div>";
    html += buscador("Buscar libro");
    html += '<div class="tabla-contenedor"><table><thead><tr><th>ISBN</th><th>Título</th><th>Autor</th><th>Año</th><th>Género</th><th>Acciones</th></tr></thead><tbody>';
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
    html += "<p>La sede de pertenencia no cambia; la ubicación actual indica dónde está la copia.</p></div></div>";
    html += '<div class="grilla-dos"><div><form class="formulario" data-form="ejemplar">';
    html += "<h3>Nuevo ejemplar</h3>";
    html += '<div class="campo"><label>Código</label><input name="codigo" required maxlength="40"></div>';
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
    html += '<div class="tabla-contenedor"><table><thead><tr><th>Código</th><th>Libro</th><th>Pertenencia</th><th>Ubicación</th><th>Disponibilidad</th><th>Estado físico</th><th>Motivo / acciones</th></tr></thead><tbody>';
    if (filtrados.length === 0) {
        html += '<tr><td colspan="7">No hay ejemplares para el filtro elegido.</td></tr>';
    }
    for (let indice = 0; indice < filtrados.length; indice += 1) {
        const ejemplar = filtrados[indice];
        html += "<tr><td>" + esc(ejemplar.codigo) + "</td><td>" + esc(ejemplar.libro_titulo) + "</td><td>" +
            esc(ejemplar.sede_pertenencia) + "</td><td>" + esc(ejemplar.ubicacion_actual || "En tránsito") + "</td><td>" +
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
    let html = '<section class="panel"><div class="panel-encabezado"><h2>Solicitudes</h2>';
    html += "<p>Una solicitud aparta un ejemplar. La interbibliotecaria necesita un remito recibido antes de entregarse.</p></div>";
    html += '<div class="formularios-fila">';
    html += '<form class="formulario" data-form="solicitud">';
    html += "<h3>Nueva solicitud</h3>";
    html += '<div class="campos">';
    html += '<div class="campo"><label>Socio</label><select name="socio_numero" required>' + opcionesSocios(null, "Seleccione un socio") + "</select></div>";
    html += '<div class="campo"><label>Libro</label><select name="libro_isbn" required>' + opcionesLibros(null, "Seleccione un libro") + "</select></div>";
    html += '<div class="campo"><label>Ejemplar</label><select name="ejemplar_codigo" required>' + opcionesEjemplares(null, "Seleccione un ejemplar") + "</select></div>";
    html += '<div class="campo"><label>Sede de origen</label><select name="sede_origen" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Sede de destino</label><select name="sede_destino" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Tipo</label><select name="tipo" required><option value="local">Local</option><option value="interbibliotecario">Interbibliotecario</option></select></div>';
    html += '<div class="campo"><label>Fecha</label><input name="fecha_solicitud" type="date" required value="' + hoyISO() + '"></div>';
    html += "</div>";
    html += '<span class="campo-ayuda">Al elegir el libro se listan solo sus ejemplares. Al elegir el ejemplar se completa la sede de origen, y el tipo se sugiere según las sedes.</span>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Registrar solicitud</button></div>';
    html += "</form>";
    html += '<form class="formulario" data-form="entrega">';
    html += "<h3>Entregar una solicitud</h3>";
    html += '<div class="campo"><label>Solicitud pendiente</label><select name="solicitud_numero" required>' + opciones(pendientes, null, "Seleccione una solicitud") + "</select></div>";
    html += '<div class="campo"><label>Fecha de préstamo</label><input name="fecha_prestamo" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Entregar</button></div>';
    html += "</form></div>";

    html += buscador("Buscar por socio, libro, ejemplar o estado");
    html += '<div class="tabla-contenedor"><table><thead><tr><th>#</th><th>Socio</th><th>Libro</th><th>Recorrido</th><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Remito</th><th>Acciones</th></tr></thead><tbody>';
    if (solicitudes.length === 0) {
        html += '<tr><td colspan="9">No hay solicitudes registradas.</td></tr>';
    }
    for (let indice = 0; indice < solicitudes.length; indice += 1) {
        const solicitud = solicitudes[indice];
        let celdaRemito = "-";
        if (solicitud.remito_codigo) {
            celdaRemito = esc(solicitud.remito_codigo);
            const remito = buscarRemito(solicitud.remito_codigo);
            if (remito) {
                celdaRemito += " " + insignia(remito.estado_actual);
            }
        }
        html += "<tr><td>" + esc(solicitud.numero) + "</td><td>" + esc(solicitud.socio_nombre) + "</td><td>" +
            esc(solicitud.libro_titulo) + '<span class="dato-secundario">Ejemplar ' + esc(solicitud.ejemplar_codigo) + "</span></td><td>" +
            '<span class="recorrido">' + esc(solicitud.sede_origen) + " → " + esc(solicitud.sede_destino) + "</span></td><td>" +
            esc(fechaTexto(solicitud.fecha_solicitud)) + "</td><td>" + esc(nombreEstado(solicitud.tipo)) + "</td><td>" +
            insignia(solicitud.estado) + "</td><td>" + celdaRemito + "</td>";
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
    html += "</tbody></table></div></section>";
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
    html += buscador("Buscar reserva");
    html += '<div class="tabla-contenedor"><table><thead><tr><th>#</th><th>Socio</th><th>Libro</th><th>Sede</th><th>Fecha</th><th>Estado</th><th>Ejemplar</th><th>Solicitud</th><th>Acciones</th></tr></thead><tbody>';
    if (reservas.length === 0) {
        html += '<tr><td colspan="9">No hay reservas registradas.</td></tr>';
    }
    for (let indice = 0; indice < reservas.length; indice += 1) {
        const reserva = reservas[indice];
        html += "<tr><td>" + esc(reserva.numero) + "</td><td>" + esc(reserva.socio_nombre) + "</td><td>" +
            esc(reserva.libro_titulo) + "</td><td>" + esc(reserva.codigo_sede) + "</td><td>" +
            esc(fechaTexto(reserva.fecha_reserva)) + "</td><td>" + insignia(reserva.estado) + "</td><td>" +
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
    let html = '<section class="panel"><div class="panel-encabezado"><h2>Préstamos y devoluciones</h2>';
    html += "<p>La multa se calcula con los días de atraso. Una devolución fuera de la sede de pertenencia deja la copia pendiente de retorno.</p></div>";
    html += '<form class="formulario" data-form="devolucion" style="margin-bottom:1.1rem">';
    html += "<h3>Registrar devolución</h3>";
    html += '<div class="campos">';
    html += '<div class="campo"><label>Préstamo activo</label><select name="numero" required>' + opciones(activos, null, "Seleccione un préstamo") + "</select></div>";
    html += '<div class="campo"><label>Fecha de devolución</label><input name="fecha_devolucion" type="date" required value="' + hoyISO() + '"></div>';
    html += '<div class="campo"><label>Sede de devolución</label><select name="sede_devolucion" required>' + opcionesSedes(null, "Seleccione una sede", true) + "</select></div>";
    html += '<div class="campo"><label>Estado físico del material</label><select name="estado_fisico" required><option value="bueno">Bueno</option><option value="deteriorado">Deteriorado</option><option value="requiere_reparacion">Requiere reparación</option></select></div>';
    html += "</div>";
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Registrar devolución</button></div>';
    html += "</form>";

    html += buscador("Buscar por socio, libro o estado");
    html += '<div class="tabla-contenedor"><table><thead><tr><th>#</th><th>Socio</th><th>Libro</th><th>Recorrido</th><th>Préstamo</th><th>Vence</th><th>Devolución</th><th>Estado</th><th>Multa</th></tr></thead><tbody>';
    if (prestamos.length === 0) {
        html += '<tr><td colspan="9">No hay préstamos registrados.</td></tr>';
    }
    for (let indice = 0; indice < prestamos.length; indice += 1) {
        const prestamo = prestamos[indice];
        const vencido = prestamo.estado === "activo" && prestamo.dias_atraso > 0;
        let multa = moneda(prestamo.multa);
        let celdaEstado = insignia(prestamo.estado);
        let celdaDevolucion = "-";
        if (prestamo.estado === "activo") {
            multa = moneda(prestamo.multa_estimada) + " estimada";
        }
        if (vencido) {
            celdaEstado = '<span class="insignia peligro">Vencido · ' + esc(prestamo.dias_atraso) + " días</span>";
        }
        if (prestamo.fecha_devolucion) {
            celdaDevolucion = esc(fechaTexto(prestamo.fecha_devolucion)) + '<span class="dato-secundario">En ' +
                esc(prestamo.sede_devolucion) + " · " + esc(nombreEstado(prestamo.estado_fisico_devolucion)) + "</span>";
        }
        html += "<tr" + (vencido ? ' class="fila-vencida"' : "") + "><td>" + esc(prestamo.numero) + "</td><td>" + esc(prestamo.socio_nombre) + "</td><td>" +
            esc(prestamo.libro_titulo || prestamo.ejemplar_codigo) + '<span class="dato-secundario">Ejemplar ' + esc(prestamo.ejemplar_codigo) + "</span></td><td>" +
            '<span class="recorrido">' + esc(prestamo.sede_origen) + " → " + esc(prestamo.sede_destino) + "</span></td><td>" +
            esc(fechaTexto(prestamo.fecha_prestamo)) + "</td><td>" + esc(fechaTexto(prestamo.fecha_vencimiento)) + "</td><td>" +
            celdaDevolucion + "</td><td>" + celdaEstado + "</td><td>" + esc(multa) + "</td></tr>";
    }
    html += "</tbody></table></div></section>";
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

    let html = '<section class="panel"><div class="panel-encabezado"><h2>Remitos e historial</h2>';
    html += "<p>Cada remito recorre los estados pendiente de empaque, empaquetado, despachado y recibido. El trayecto muestra el momento registrado de cada paso.</p></div>";
    html += '<form class="formulario" data-form="retorno" style="margin-bottom:1.1rem">';
    html += "<h3>Crear remito de retorno</h3>";
    html += '<div class="campos">';
    html += '<div class="campo"><label>Ejemplar pendiente de retorno</label><select name="ejemplar_codigo" required>' +
        opciones(pendientesRetorno, null, "Seleccione un ejemplar") + "</select></div>";
    html += '<div class="campo"><label>Fecha de creación</label><input name="fecha_creacion" type="date" required value="' + hoyISO() + '"></div>';
    html += "</div>";
    html += '<span class="campo-ayuda">Los remitos de préstamo se crean desde la sección Solicitudes.</span>';
    html += '<div class="acciones-formulario"><button class="boton" type="submit">Crear remito</button></div>';
    html += "</form>";

    html += buscador("Buscar por código, sede, ejemplar o estado");
    if (remitos.length === 0) {
        html += '<p class="nota">No hay remitos registrados.</p>';
    }
    html += '<div class="remitos">';
    for (let indice = 0; indice < remitos.length; indice += 1) {
        const remito = remitos[indice];
        html += '<article class="remito">';
        html += '<div class="remito-encabezado"><div class="remito-titulo">';
        html += '<span class="remito-codigo">' + esc(remito.codigo) + "</span>";
        html += insignia(remito.motivo);
        html += '<span class="recorrido">' + esc(remito.sede_origen) + " → " + esc(remito.sede_destino) + "</span>";
        html += "</div>" + insignia(remito.estado_actual) + "</div>";

        for (let posicion = 0; posicion < remito.asignaciones.length; posicion += 1) {
            const asignacion = remito.asignaciones[posicion];
            let detalle = "Ejemplar " + asignacion.ejemplar_codigo;
            if (asignacion.numero_solicitud !== null && asignacion.numero_solicitud !== undefined) {
                detalle += " · Solicitud #" + asignacion.numero_solicitud;
            }
            if (asignacion.estado_fisico_recepcion) {
                detalle += " · Recibido en estado: " + nombreEstado(asignacion.estado_fisico_recepcion);
            }
            html += '<p class="nota">' + esc(detalle) + "</p>";
        }

        html += renderTrayecto(remito);

        if (remito.estado_actual === "pendiente_empaque") {
            html += '<div class="remito-acciones"><button class="boton pequeno" type="button" data-accion="empaquetar-remito" data-codigo="' +
                esc(remito.codigo) + '">Empaquetar</button></div>';
        } else if (remito.estado_actual === "empaquetado") {
            html += '<div class="remito-acciones"><button class="boton pequeno" type="button" data-accion="despachar-remito" data-codigo="' +
                esc(remito.codigo) + '">Despachar</button></div>';
        } else if (remito.estado_actual === "despachado") {
            html += '<div class="remito-acciones"><form data-form="recepcion">';
            html += '<input type="hidden" name="codigo" value="' + esc(remito.codigo) + '">';
            html += '<select name="estado_fisico" required aria-label="Estado físico al recibir">';
            html += '<option value="">Estado observado...</option><option value="bueno">Bueno</option>';
            html += '<option value="deteriorado">Deteriorado</option><option value="requiere_reparacion">Requiere reparación</option></select>';
            html += '<button class="boton pequeno" type="submit">Recibir</button></form></div>';
        }
        html += "</article>";
    }
    html += "</div></section>";
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
        ["movimiento", "Movimiento de envíos"],
    ];
    let html = '<section class="panel"><div class="panel-encabezado"><div><h2>Reportes</h2>';
    html += "<p>Consultá los resultados y descargá un PDF con su alcance y utilidad para la gestión.</p></div></div>";
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
        html += '<p class="nota">Agrupado por sede de origen y destino, con tiempos de tránsito y recepción.</p>';
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
    let html = '<p class="titulo-reporte">' + esc(estado.nombreReporte) + "</p>";
    const rutaPDF = API + estado.rutaReporteGenerado +
        (estado.rutaReporteGenerado.includes("?") ? "&" : "?") + "formato=pdf";
    html += '<p><a class="boton" href="' + esc(rutaPDF) +
        '" target="_blank" rel="noopener">Descargar PDF</a></p>';
    html += '<p class="nota">El PDF consulta los datos al descargar y conserva los filtros del último reporte generado.</p>';
    if (estado.filasReporte.length === 0) {
        html += '<div class="aviso neutro"><strong>Sin datos</strong><p>No hay información para los filtros elegidos.</p></div>';
        contenedor.innerHTML = html;
        return;
    }
    const columnas = Object.keys(estado.filasReporte[0]);
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

function crearRutaReporte(nombre, filtros) {
    const parametros = new URLSearchParams();
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
    return ruta + (consulta ? "?" + consulta : "");
}

async function cargarReporte(nombre) {
    estado.cargandoReporte = true;
    estado.rutaReporteGenerado = "";
    pintarReporte();
    if (nombre === "activos" && !estado.filtrosReporte.fecha_referencia) {
        estado.filtrosReporte.fecha_referencia = hoyISO();
    }
    const ruta = crearRutaReporte(nombre, estado.filtrosReporte);
    try {
        const respuesta = await pedir("GET", ruta);
        estado.filasReporte = respuesta.datos.filas;
        estado.nombreReporte = respuesta.datos.reporte;
        estado.rutaReporteGenerado = ruta;
    } catch (error) {
        estado.filasReporte = null;
        estado.nombreReporte = "";
        avisar(error.message, "error");
    } finally {
        estado.cargandoReporte = false;
        pintarReporte();
    }
}

function fechaTexto(valor) {
    if (valor === null || valor === undefined || valor === "") {
        return "-";
    }
    const texto = String(valor);
    if (texto.length < 10) {
        return texto;
    }
    const anio = texto.substring(0, 4);
    const mes = texto.substring(5, 7);
    const dia = texto.substring(8, 10);
    return dia + "/" + mes + "/" + anio;
}

function momentoTexto(valor) {
    if (valor === null || valor === undefined || valor === "") {
        return "-";
    }
    const texto = String(valor);
    const fecha = fechaTexto(texto);
    if (texto.length < 16) {
        return fecha;
    }
    return fecha + " " + texto.substring(11, 16);
}

function buscador(texto) {
    return '<div class="buscador"><input type="search" data-buscador placeholder="' + esc(texto) +
        '" aria-label="' + esc(texto) + '"></div>';
}

function filtrarElementos(campo) {
    const panel = campo.closest(".panel");
    if (!panel) {
        return;
    }
    const texto = campo.value.trim().toLowerCase();
    const elementos = panel.querySelectorAll("tbody tr, .remito");
    for (let indice = 0; indice < elementos.length; indice += 1) {
        const elemento = elementos[indice];
        const contenido = elemento.textContent.toLowerCase();
        if (texto !== "" && contenido.indexOf(texto) < 0) {
            elemento.hidden = true;
        } else {
            elemento.hidden = false;
        }
    }
}

function buscarEjemplar(codigo) {
    const ejemplares = estado.listados ? estado.listados.ejemplares : [];
    for (let indice = 0; indice < ejemplares.length; indice += 1) {
        if (ejemplares[indice].codigo === codigo) {
            return ejemplares[indice];
        }
    }
    return null;
}

function buscarRemito(codigo) {
    const remitos = estado.listados ? estado.listados.remitos : [];
    for (let indice = 0; indice < remitos.length; indice += 1) {
        if (remitos[indice].codigo === codigo) {
            return remitos[indice];
        }
    }
    return null;
}

// Cuenta lo que espera una accion del personal. Solo suma datos que la API
// ya calculo (estados y dias de atraso); no decide reglas de negocio.
function calcularPendientes() {
    const pendientes = {
        solicitudes: 0,
        reservas: 0,
        prestamos: 0,
        vencidos: 0,
        remitos: 0,
        retornos: 0,
        reparacion: 0,
    };
    const listados = estado.listados;
    for (let indice = 0; indice < listados.solicitudes.length; indice += 1) {
        if (listados.solicitudes[indice].estado === "pendiente") {
            pendientes.solicitudes += 1;
        }
    }
    for (let indice = 0; indice < listados.reservas.length; indice += 1) {
        const estadoReserva = listados.reservas[indice].estado;
        if (estadoReserva === "pendiente" || estadoReserva === "asignada") {
            pendientes.reservas += 1;
        }
    }
    for (let indice = 0; indice < listados.prestamos.length; indice += 1) {
        const prestamo = listados.prestamos[indice];
        if (prestamo.estado === "activo") {
            pendientes.prestamos += 1;
            if (prestamo.dias_atraso > 0) {
                pendientes.vencidos += 1;
            }
        }
    }
    for (let indice = 0; indice < listados.remitos.length; indice += 1) {
        const estadoRemito = listados.remitos[indice].estado_actual;
        if (estadoRemito === "pendiente_empaque" || estadoRemito === "empaquetado" || estadoRemito === "despachado") {
            pendientes.remitos += 1;
        }
    }
    for (let indice = 0; indice < listados.ejemplares.length; indice += 1) {
        const disponibilidad = listados.ejemplares[indice].estado_disponibilidad;
        if (disponibilidad === "pendiente_retorno") {
            pendientes.retornos += 1;
        }
        if (disponibilidad === "en_reparacion") {
            pendientes.reparacion += 1;
        }
    }
    return pendientes;
}

function actualizarContadores() {
    const pendientes = calcularPendientes();
    const contadores = document.querySelectorAll(".menu [data-contador]");
    for (let indice = 0; indice < contadores.length; indice += 1) {
        const contador = contadores[indice];
        const cantidad = pendientes[contador.dataset.contador];
        contador.textContent = cantidad;
        contador.hidden = cantidad === 0;
        contador.classList.remove("urgente");
        if (contador.dataset.contador === "prestamos" && pendientes.vencidos > 0) {
            contador.classList.add("urgente");
            contador.title = pendientes.vencidos + " vencidos";
        }
    }
}

// Une cada etiqueta con su campo para que un clic en el texto enfoque el
// control y los lectores de pantalla anuncien el nombre correcto.
function asociarEtiquetas(contenedor) {
    const campos = contenedor.querySelectorAll(".campo");
    for (let indice = 0; indice < campos.length; indice += 1) {
        const etiqueta = campos[indice].querySelector("label");
        const control = campos[indice].querySelector("input, select");
        if (!etiqueta || !control) {
            continue;
        }
        estado.numeroCampo += 1;
        control.id = "campo-" + estado.numeroCampo;
        etiqueta.htmlFor = control.id;
    }
}

// Ayuda de carga del formulario de solicitud. Solo completa campos a partir
// de lo que el usuario eligio; el backend valida igual todos los datos.
function ayudarSolicitud(formulario, nombreCampo) {
    const campos = formulario.elements;
    if (nombreCampo === "libro_isbn") {
        campos.ejemplar_codigo.innerHTML = opcionesEjemplares(null, "Seleccione un ejemplar", campos.libro_isbn.value);
    }
    if (nombreCampo === "ejemplar_codigo") {
        const ejemplar = buscarEjemplar(campos.ejemplar_codigo.value);
        if (ejemplar) {
            campos.libro_isbn.value = ejemplar.libro_isbn;
            campos.sede_origen.value = ejemplar.sede_pertenencia;
        }
    }
    if (nombreCampo === "tipo") {
        return;
    }
    const origen = campos.sede_origen.value;
    const destino = campos.sede_destino.value;
    if (origen !== "" && destino !== "") {
        if (origen === destino) {
            campos.tipo.value = "local";
        } else {
            campos.tipo.value = "interbibliotecario";
        }
    }
}

// Arma los pasos del trayecto de un remito: los estados ya registrados en el
// historial con su momento, y los que todavia faltan.
function pasosDeRemito(remito) {
    const secuencia = ["pendiente_empaque", "empaquetado", "despachado", "recibido"];
    const posicionActual = secuencia.indexOf(remito.estado_actual);
    const cancelado = remito.estado_actual === "cancelado";
    const pasos = [];
    for (let indice = 0; indice < secuencia.length; indice += 1) {
        const nombre = secuencia[indice];
        let momento = null;
        for (let posicion = 0; posicion < remito.historial.length; posicion += 1) {
            if (remito.historial[posicion].estado === nombre) {
                momento = remito.historial[posicion].momento;
            }
        }
        let clase = "pendiente";
        if (momento !== null || indice <= posicionActual) {
            clase = "hecho";
        }
        if (indice === posicionActual) {
            clase = "actual";
        }
        if (cancelado && clase === "pendiente") {
            continue;
        }
        pasos.push({ nombre: nombre, momento: momento, clase: clase });
    }
    if (cancelado) {
        let momentoCancelacion = null;
        for (let posicion = 0; posicion < remito.historial.length; posicion += 1) {
            if (remito.historial[posicion].estado === "cancelado") {
                momentoCancelacion = remito.historial[posicion].momento;
            }
        }
        pasos.push({ nombre: "cancelado", momento: momentoCancelacion, clase: "cancelado" });
    }
    return pasos;
}

function renderTrayecto(remito) {
    const pasos = pasosDeRemito(remito);
    let html = '<ol class="trayecto" aria-label="Trayecto del remito ' + esc(remito.codigo) + '">';
    for (let indice = 0; indice < pasos.length; indice += 1) {
        const paso = pasos[indice];
        html += '<li class="' + paso.clase + '"><span class="paso-nombre">' + esc(nombreEstado(paso.nombre)) + "</span>";
        if (paso.momento !== null) {
            html += "<span>" + esc(momentoTexto(paso.momento)) + "</span>";
        } else if (paso.clase === "pendiente") {
            html += "<span>Falta</span>";
        }
        html += "</li>";
    }
    html += "</ol>";
    return html;
}

function conectarEventos() {
    document.addEventListener("input", function (evento) {
        const campoHorario = evento.target.closest('input[name="horario"]');
        if (campoHorario) {
            formatearCampoHorario(campoHorario);
        }
        const campoBuscador = evento.target.closest("[data-buscador]");
        if (campoBuscador) {
            filtrarElementos(campoBuscador);
        }
    });

    document.addEventListener("change", function (evento) {
        const formulario = evento.target.closest('form[data-form="solicitud"]');
        if (formulario) {
            ayudarSolicitud(formulario, evento.target.name);
        }
    });

    document.addEventListener("click", async function (evento) {
        const botonSeccion = evento.target.closest("[data-seccion]");
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
        // El boton se bloquea mientras dura el pedido para no enviar dos veces.
        const boton = formulario.querySelector('button[type="submit"]');
        if (boton) {
            boton.disabled = true;
        }
        try {
            await manejarFormulario(formulario);
        } catch (error) {
            avisar(error.message, "error");
        } finally {
            if (boton) {
                boton.disabled = false;
            }
        }
    });
}

async function manejarFormulario(formulario) {
    const tipo = formulario.dataset.form;
    const datos = Object.fromEntries(new FormData(formulario).entries());

    if (tipo === "sede") {
        datos.horario = formatearHorario(datos.horario);
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
        await refrescar("Préstamo entregado.");
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
        await refrescar("Devolución registrada.");
        return;
    }

    if (tipo === "retorno") {
        await pedir("POST", "/remitos/retorno", datos);
        await refrescar("Remito de retorno creado.");
        return;
    }

    if (tipo === "recepcion") {
        await pedir("POST", "/remitos/" + encodeURIComponent(datos.codigo) + "/recibir", {
            estado_fisico: datos.estado_fisico,
        });
        await refrescar("Remito recibido.");
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
        if (!window.confirm("¿Dar de baja la sede " + datos.codigo + "?")) {
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
        if (!window.confirm("¿Inhabilitar el socio " + datos.numero + "?")) {
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
        await refrescar("Remito de préstamo creado.");
        return;
    }
    if (accion === "cancelar-solicitud") {
        if (!window.confirm("¿Cancelar la solicitud " + datos.numero + "?")) {
            return;
        }
        await pedir("POST", "/solicitudes/" + encodeURIComponent(datos.numero) + "/cancelar", {});
        await refrescar("Solicitud cancelada.");
        return;
    }
    if (accion === "cancelar-reserva") {
        if (!window.confirm("¿Cancelar la reserva " + datos.numero + "?")) {
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
}
