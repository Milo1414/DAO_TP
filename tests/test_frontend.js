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

comprobarRecepcion().catch(function (error) {
    console.error(error);
    process.exitCode = 1;
});
