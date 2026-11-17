import unittest

from backend.reportes_graficos import preparar_graficos
from tests.apoyo import PruebaBase


class PruebaDatosGraficos(unittest.TestCase):
    def test_vencidos_son_parte_de_activos(self):
        graficos = preparar_graficos("activos-vencidos", [
            {"sede": "S1", "sede_nombre": "Central", "activos": 10, "vencidos": 3},
        ])
        self.assertEqual(graficos[0]["grupos"][0]["valores"], [7, 3])

    def test_inventario_agrupa_libros_sin_sumar_reservas_como_ejemplares(self):
        filas = []
        for disponibles in [2, 5]:
            filas.append({"sede": "S1", "disponibles": disponibles, "prestados": 1,
                          "apartados": 0, "en_transito": 0, "en_reparacion": 0,
                          "pendientes_retorno": 0, "reservas_activas": 10})
        grafico = preparar_graficos("disponibilidad", filas)[0]
        self.assertEqual(grafico["grupos"], [{"etiqueta": "S1", "valores": [7, 2, 0, 0, 0, 0]}])

    def test_movimiento_separa_envios_de_horas(self):
        graficos = preparar_graficos("movimiento", [{
            "origen": "S1", "destino": "S2", "recibidos": 2,
            "pendientes": 1, "cancelados": 3, "promedio_horas_transito": 12.5,
        }])
        self.assertEqual(graficos[0]["unidad"], "envíos")
        self.assertEqual(graficos[0]["grupos"][0]["valores"], [2, 1, 3])
        self.assertEqual(graficos[1]["unidad"], "horas")
        self.assertEqual(graficos[1]["grupos"][0]["valores"], [12.5])

    def test_ranking_no_recorta_libros_ni_cambia_el_orden(self):
        filas = []
        for numero in range(20):
            filas.append({"isbn": str(numero), "titulo": "Libro", "cantidad": 20 - numero})
        grafico = preparar_graficos("libros-solicitados", filas)[0]
        self.assertEqual(len(grafico["grupos"]), 20)
        self.assertEqual(grafico["grupos"][0]["valores"], [20])
        self.assertEqual(grafico["grupos"][-1]["valores"], [1])

    def test_sin_datos_y_con_todos_los_valores_en_cero(self):
        for tipo in ["activos-vencidos", "disponibilidad", "libros-solicitados", "movimiento"]:
            self.assertEqual(preparar_graficos(tipo, []), [])
        graficos = preparar_graficos("activos-vencidos", [
            {"sede": "S1", "sede_nombre": "Central", "activos": 0, "vencidos": 0},
        ])
        self.assertEqual(graficos[0]["maximo"], 0)


class PruebaGraficosAPI(PruebaBase):
    def test_json_incluye_graficos_con_los_filtros_del_reporte(self):
        self.datos_basicos(dos_sedes=True)
        respuesta = self.pedir("GET", "/api/reportes/disponibilidad?sede=S1&isbn=L1")
        datos = respuesta.get_json()["datos"]
        self.assertEqual(datos["graficos"], preparar_graficos("disponibilidad", datos["filas"]))
        self.assertEqual(datos["graficos"][0]["grupos"], [{"etiqueta": "S1", "valores": [1, 0, 0, 0, 0, 0]}])


if __name__ == "__main__":
    unittest.main()
