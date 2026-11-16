// Verifica el formulario de recepcion y el JSON enviado por la interfaz real.
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const contexto = vm.createContext({
    document: { addEventListener() {} },
    Intl,
    URLSearchParams,
    FormData: class {
        constructor(formulario) {
            this.datos = formulario.datos;
        }

        entries() {
            return Object.entries(this.datos);
        }
    },
});

const archivo = path.join(__dirname, "..", "frontend", "app.js");
vm.runInContext(fs.readFileSync(archivo, "utf8"), contexto);

async function comprobarRecepcion() {
    vm.runInContext(`
        estado.listados = {
            ejemplares: [],
            remitos: [{
                codigo: "R-1", motivo: "prestamo", sede_origen: "S1", sede_destino: "S2",
                fecha_creacion: "2026-01-10", estado_actual: "despachado", asignaciones: [], historial: [],
            }],
        };
    `, contexto);
    const html = vm.runInContext("renderRemitos()", contexto);
    assert.match(html, /data-form="recepcion"/);
    assert.match(html, /name="estado_fisico" required/);
    assert.match(html, /value="requiere_reparacion"/);

    const peticiones = [];
    contexto.pedir = async function (metodo, ruta, datos) {
        peticiones.push({ metodo, ruta, datos });
    };
    let refrescos = 0;
    contexto.refrescar = async function () {
        refrescos += 1;
    };
    contexto.formulario = {
        dataset: { form: "recepcion" },
        datos: { codigo: "R-1", estado_fisico: "requiere_reparacion" },
    };
    await vm.runInContext("manejarFormulario(formulario)", contexto);
    assert.equal(peticiones.length, 1);
    assert.equal(peticiones[0].metodo, "POST");
    assert.equal(peticiones[0].ruta, "/remitos/R-1/recibir");
    assert.equal(peticiones[0].datos.estado_fisico, "requiere_reparacion");
    assert.equal(refrescos, 1);
    console.log("Recepcion frontend: formulario, estado observado y envio JSON correctos.");
}

function comprobarTrayecto() {
    contexto.remito = {
        codigo: "R-2", estado_actual: "empaquetado",
        historial: [
            { orden: 0, estado: "pendiente_empaque", momento: "2026-01-10 09:00:00" },
            { orden: 1, estado: "empaquetado", momento: "2026-01-10 10:30:00" },
        ],
    };
    let pasos = vm.runInContext("pasosDeRemito(remito)", contexto);
    assert.equal(pasos.length, 4);
    assert.equal(pasos[0].clase, "hecho");
    assert.equal(pasos[1].clase, "actual");
    assert.equal(pasos[1].momento, "2026-01-10 10:30:00");
    assert.equal(pasos[2].clase, "pendiente");
    assert.equal(pasos[3].clase, "pendiente");
    const html = vm.runInContext("renderTrayecto(remito)", contexto);
    assert.match(html, /10\/01\/2026 10:30/);

    contexto.remito = {
        codigo: "R-3", estado_actual: "cancelado",
        historial: [
            { orden: 0, estado: "pendiente_empaque", momento: "2026-01-10 09:00:00" },
            { orden: 1, estado: "cancelado", momento: "2026-01-11 08:00:00" },
        ],
    };
    pasos = vm.runInContext("pasosDeRemito(remito)", contexto);
    assert.equal(pasos.length, 2);
    assert.equal(pasos[0].nombre, "pendiente_empaque");
    assert.equal(pasos[1].nombre, "cancelado");
    assert.equal(pasos[1].clase, "cancelado");
    assert.equal(pasos[1].momento, "2026-01-11 08:00:00");
    console.log("Trayecto frontend: pasos en curso y cancelados correctos.");
}

function comprobarFechas() {
    assert.equal(vm.runInContext('fechaTexto("2026-08-01")', contexto), "01/08/2026");
    assert.equal(vm.runInContext('momentoTexto("2026-08-01 09:05:00")', contexto), "01/08/2026 09:05");
    assert.equal(vm.runInContext("fechaTexto(null)", contexto), "-");
    console.log("Fechas frontend: formato dia/mes/anio correcto.");
}

comprobarTrayecto();
comprobarFechas();
comprobarRecepcion().catch(function (error) {
    console.error(error);
    process.exitCode = 1;
});
