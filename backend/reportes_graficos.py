"""Prepare chart data once, for both the browser and the PDF document."""


def crear_grafico(titulo, unidad, series, grupos):
    maximo = 0
    for grupo in grupos:
        for valor in grupo["valores"]:
            if valor > maximo:
                maximo = valor
    return {"titulo": titulo, "unidad": unidad, "series": series,
            "grupos": grupos, "maximo": maximo}


def preparar_graficos(tipo, filas):
    if len(filas) == 0:
        return []
    grupos = []
    if tipo == "activos-vencidos":
        series = [
            {"nombre": "Al día", "color": "#247b76"},
            {"nombre": "Vencidos", "color": "#b44747"},
        ]
        for fila in filas:
            grupos.append({"etiqueta": fila["sede"] + " - " + fila["sede_nombre"],
                           "valores": [fila["activos"] - fila["vencidos"], fila["vencidos"]]})
        return [crear_grafico("Préstamos al día y vencidos por sede", "préstamos", series, grupos)]

    if tipo == "disponibilidad":
        series = [
            {"nombre": "Disponibles", "color": "#247b76"},
            {"nombre": "Prestados", "color": "#286b9c"},
            {"nombre": "Apartados", "color": "#8a62a6"},
            {"nombre": "En tránsito", "color": "#b57c1b"},
            {"nombre": "En reparación", "color": "#b44747"},
            {"nombre": "Pendientes de retorno", "color": "#617582"},
        ]
        claves = ["disponibles", "prestados", "apartados", "en_transito",
                  "en_reparacion", "pendientes_retorno"]
        por_sede = {}
        for fila in filas:
            sede = fila["sede"]
            if sede not in por_sede:
                por_sede[sede] = {"etiqueta": sede, "valores": [0, 0, 0, 0, 0, 0]}
            for indice in range(len(claves)):
                por_sede[sede]["valores"][indice] += fila[claves[indice]]
        for sede in por_sede:
            grupos.append(por_sede[sede])
        return [crear_grafico("Ejemplares por estado y sede", "ejemplares", series, grupos)]

    if tipo == "libros-solicitados":
        series = [{"nombre": "Solicitudes", "color": "#286b9c"}]
        for fila in filas:
            grupos.append({"etiqueta": fila["isbn"] + " - " + fila["titulo"],
                           "valores": [fila["cantidad"]]})
        return [crear_grafico("Demanda interbibliotecaria por libro", "solicitudes", series, grupos)]

    if tipo == "movimiento":
        series = [
            {"nombre": "Recibidos", "color": "#247b76"},
            {"nombre": "Pendientes", "color": "#b57c1b"},
            {"nombre": "Cancelados", "color": "#b44747"},
        ]
        tiempos = []
        for fila in filas:
            etiqueta = fila["origen"] + " a " + fila["destino"]
            grupos.append({"etiqueta": etiqueta,
                           "valores": [fila["recibidos"], fila["pendientes"], fila["cancelados"]]})
            tiempos.append({"etiqueta": etiqueta, "valores": [fila["promedio_horas_transito"]]})
        grafico_envios = crear_grafico("Estado de los envíos por trayecto", "envíos", series, grupos)
        grafico_tiempos = crear_grafico("Tiempo promedio de tránsito por trayecto", "horas",
                                      [{"nombre": "Tránsito", "color": "#286b9c"}], tiempos)
        return [grafico_envios, grafico_tiempos]
    raise ValueError("Tipo de reporte desconocido: " + tipo)
