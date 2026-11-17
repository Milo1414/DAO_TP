"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const elementos = {};
const contexto = vm.createContext({
    document: {
        addEventListener() {},
        getElementById(id) {
            if (!elementos[id]) {
                elementos[id] = { innerHTML: "", textContent: "", hidden: false };
            }
            return elementos[id];
        },
    },
    Intl,
    URLSearchParams,
});
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "frontend", "app.js"), "utf8"), contexto);

async function comprobarAcceso() {
    vm.runInContext("estado.requiereConfiguracion = true; mostrarAcceso()", contexto);
    assert.match(elementos.acceso.innerHTML, /data-form="primer-usuario"/);
    assert.match(elementos.acceso.innerHTML, /minlength="8"/);
    assert.equal(elementos.sistema.hidden, true);
    vm.runInContext("estado.requiereConfiguracion = false; mostrarAcceso()", contexto);
    assert.match(elementos.acceso.innerHTML, /data-form="login"/);
    assert.match(elementos.acceso.innerHTML, /type="password"/);

    vm.runInContext(`
        estado.usuario = { id: 1, nombre: "Personal" };
        estado.listados = { informacion: "privada" };
        estado.usuarios = [{ id: 1 }];
        estado.filasReporte = [{ total: 5 }];
        mostrarAcceso();
    `, contexto);
    assert.equal(elementos.acceso.hidden, true);
    assert.equal(elementos.sistema.hidden, false);
    assert.equal(elementos["nombre-personal"].textContent, "Personal");
    contexto.fetch = async function () {
        return { ok: false, status: 401, json: async () => ({ error: "Sesión cerrada" }) };
    };
    await assert.rejects(vm.runInContext('pedir("GET", "/listados")', contexto), /Sesión cerrada/);
    assert.equal(vm.runInContext("estado.usuario", contexto), null);
    assert.equal(vm.runInContext("estado.listados", contexto), null);
    assert.equal(vm.runInContext("estado.usuarios.length", contexto), 0);
    assert.equal(elementos.sistema.hidden, true);
    assert.equal(elementos.contenido.innerHTML, "");

    vm.runInContext(`
        estado.usuario = { id: 1, nombre: "Personal" };
        estado.usuarios = [
            { id: 1, usuario: "personal", nombre: "Personal", activa: true },
            { id: 2, usuario: "auxiliar", nombre: "Auxiliar", activa: true }
        ];
    `, contexto);
    const html = vm.runInContext("renderUsuarios()", contexto);
    assert.match(html, /Tu cuenta/);
    assert.doesNotMatch(html, /data-identificador="1"/);
    assert.match(html, /data-identificador="2"/);
    console.log("Access: initial setup, login, private data clearing and staff management passed.");
}

function comprobarGraficos() {
    contexto.graficos = [{
        titulo: "Préstamos", unidad: "préstamos", maximo: 10,
        series: [{ nombre: "Al día", color: "#247b76" }],
        grupos: [{ etiqueta: "<Sede & Central>", valores: [5] }],
    }];
    let html = vm.runInContext("renderGraficos(graficos)", contexto);
    assert.match(html, /width:50%/);
    assert.match(html, /&lt;Sede &amp; Central&gt;/);
    assert.match(html, /<strong>5<\/strong>/);
    contexto.graficos[0].maximo = 0;
    contexto.graficos[0].grupos[0].valores[0] = 0;
    html = vm.runInContext("renderGraficos(graficos)", contexto);
    assert.match(html, /Todos los valores son cero/);
    assert.doesNotMatch(html, /NaN|Infinity/);
    console.log("Charts: proportional bars, displayed values, escaped labels and zero values passed.");
}

comprobarAcceso().then(comprobarGraficos).catch(function (error) {
    console.error(error);
    process.exitCode = 1;
});
