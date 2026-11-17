import datetime
import unittest

from unittest.mock import patch

from backend.reportes_pdf import formatear_valor, generar_pdf
from tests.apoyo import PruebaBase


class PruebaReportesPDF(PruebaBase):
    def comprobar_pdf(self, respuesta, tipo):
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.mimetype, "application/pdf")
        self.assertIn("attachment;", respuesta.headers["Content-Disposition"])
        self.assertIn("reporte-" + tipo + "-", respuesta.headers["Content-Disposition"])
        self.assertTrue(respuesta.data.startswith(b"%PDF-"))
        self.assertTrue(respuesta.data.rstrip().endswith(b"%%EOF"))
        respuesta.close()

    def test_cuatro_descargas_usan_los_mismos_resultados_que_json(self):
        self.datos_basicos(dos_sedes=True)
        self.solicitud_local()
        self.entregar_local()
        self.solicitud_interbibliotecaria()
        remito = self.crear_remito(2)
        self.mover_remito(remito["codigo"])
        tipos = ["activos-vencidos", "disponibilidad", "libros-solicitados", "movimiento"]
        for tipo in tipos:
            with self.subTest(tipo=tipo):
                ruta = "/api/reportes/" + tipo
                datos = self.pedir("GET", ruta).get_json()["datos"]
                with patch("backend.rutas.generar_pdf", wraps=generar_pdf) as generador:
                    respuesta = self.pedir("GET", ruta + "?formato=pdf")
                    self.comprobar_pdf(respuesta, tipo)
                    argumentos = generador.call_args.args
                    self.assertEqual(argumentos[0], tipo)
                    self.assertEqual(argumentos[1], datos["reporte"])
                    self.assertEqual(argumentos[2], datos["filas"])
                    self.assertGreater(len(argumentos[2]), 0)

    def test_pdf_conserva_filtros_y_excluye_resultados_ajenos(self):
        self.datos_basicos(dos_sedes=True)
        self.crear_libro("L2", "Libro excluido")
        self.crear_ejemplar("E3", "L2", "S1")
        with patch("backend.rutas.generar_pdf", wraps=generar_pdf) as generador:
            respuesta = self.pedir("GET", "/api/reportes/disponibilidad?sede=S1&isbn=L1&formato=pdf")
            self.comprobar_pdf(respuesta, "disponibilidad")
            filas = generador.call_args.args[2]
            self.assertEqual(len(filas), 1)
            self.assertEqual(filas[0]["sede"], "S1")
            self.assertEqual(filas[0]["isbn"], "L1")
            self.assertEqual(filas[0]["total"], 1)
            self.assertEqual(generador.call_args.args[3], {"sede": "S1", "isbn": "L1"})

    def test_fechas_y_sedes_del_ranking_llegan_normalizadas_al_pdf(self):
        self.datos_basicos(dos_sedes=True)
        self.solicitud_interbibliotecaria("2026-01-10")
        ruta = "/api/reportes/libros-solicitados?desde=2026-01-10&hasta=2026-01-10"
        ruta += "&sede_origen=S2&sede_destino=S1&formato=pdf"
        with patch("backend.rutas.generar_pdf", wraps=generar_pdf) as generador:
            self.comprobar_pdf(self.pedir("GET", ruta), "libros-solicitados")
            self.assertEqual(generador.call_args.args[2][0]["cantidad"], 1)
            self.assertEqual(generador.call_args.args[3], {
                "fecha_desde": datetime.date(2026, 1, 10),
                "fecha_hasta": datetime.date(2026, 1, 10),
                "sede_origen": "S2", "sede_destino": "S1",
            })

    def test_fecha_referencia_del_pdf_es_la_usada_para_la_multa(self):
        self.datos_basicos()
        self.solicitud_local()
        self.entregar_local()
        with patch("backend.rutas.generar_pdf", wraps=generar_pdf) as generador:
            ruta = "/api/reportes/activos-vencidos?fecha_referencia=2026-01-30&formato=pdf"
            self.comprobar_pdf(self.pedir("GET", ruta), "activos-vencidos")
            self.assertEqual(generador.call_args.args[3]["fecha_referencia"], datetime.date(2026, 1, 30))
            self.assertEqual(generador.call_args.args[2][0]["multa_total"], 600)
        with patch("backend.rutas.generar_pdf", wraps=generar_pdf) as generador:
            self.comprobar_pdf(self.pedir("GET", "/api/reportes/activos-vencidos?formato=pdf"),
                               "activos-vencidos")
            self.assertEqual(generador.call_args.args[3]["fecha_referencia"], datetime.date.today())

    def test_los_cuatro_reportes_descargan_sin_datos(self):
        for tipo in ["activos-vencidos", "disponibilidad", "libros-solicitados", "movimiento"]:
            with self.subTest(tipo=tipo):
                with patch("backend.rutas.generar_pdf", wraps=generar_pdf) as generador:
                    respuesta = self.pedir("GET", "/api/reportes/" + tipo + "?formato=pdf")
                    self.comprobar_pdf(respuesta, tipo)
                    self.assertEqual(generador.call_args.args[2], [])

    def test_pdf_rechaza_fechas_invalidas_y_formatos_desconocidos(self):
        rutas = [
            "/api/reportes/activos-vencidos?fecha_referencia=mal&formato=pdf",
            "/api/reportes/libros-solicitados?desde=2026-02-01&hasta=2026-01-01&formato=pdf",
            "/api/reportes/movimiento?formato=otro",
        ]
        with patch("backend.rutas.generar_pdf") as generador:
            for ruta in rutas:
                with self.subTest(ruta=ruta):
                    respuesta = self.pedir("GET", ruta)
                    self.assertEqual(respuesta.status_code, 400)
                    self.assertIn("error", respuesta.get_json())
            generador.assert_not_called()

    def test_textos_largos_y_caracteres_de_marcado_en_varias_paginas(self):
        titulo = "Gestión & bibliotecas <centrales>: " + "Catálogo extenso " * 12
        filas = []
        for numero in range(120):
            filas.append({"isbn": "ISBN-" + str(numero), "titulo": titulo, "cantidad": numero})
        with generar_pdf("libros-solicitados", "Demanda entre sedes", filas, {}) as archivo:
            datos = archivo.getvalue()
        self.assertTrue(datos.startswith(b"%PDF-"))
        self.assertGreater(datos.count(b"/Type /Page\n"), 1)

    def test_formato_de_porcentajes_moneda_y_fechas(self):
        self.assertEqual(formatear_valor("tasa_exito", 0.75), "75%")
        self.assertEqual(formatear_valor("multa_total", 1234.5), "$ 1.234,50")
        self.assertEqual(formatear_valor("fecha_desde", datetime.date(2026, 1, 10)), "10/01/2026")


if __name__ == "__main__":
    unittest.main()
