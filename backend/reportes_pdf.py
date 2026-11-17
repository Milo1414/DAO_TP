import datetime

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.reportes_graficos import preparar_graficos


ETIQUETAS = {
    "sede": "Sede", "sede_nombre": "Nombre de sede", "isbn": "ISBN",
    "titulo": "Título", "activos": "Activos", "vencidos": "Vencidos",
    "proporcion_vencidos": "Proporción de vencidos",
    "promedio_dias_atraso": "Promedio de días de atraso", "multa_total": "Multa estimada ($)",
    "total": "Total", "disponibles": "Disponibles", "prestados": "Prestados",
    "en_transito": "En tránsito", "en_reparacion": "En reparación",
    "apartados": "Apartados", "pendientes_retorno": "Pendientes de retorno",
    "reservas_activas": "Reservas activas", "cantidad": "Solicitudes",
    "origen": "Origen", "destino": "Destino", "prestamos": "Préstamo",
    "retornos": "Retorno", "recibidos": "Recibidos", "pendientes": "Pendientes",
    "cancelados": "Cancelados", "copias_danadas_recepcion": "Copias dañadas al recibir",
    "tasa_exito": "Recibidos / total", "promedio_horas_transito": "Tránsito (horas)",
    "promedio_dias_transito": "Tránsito (días)", "promedio_horas_total": "Total (horas)",
    "promedio_dias_total": "Total (días)", "fecha_referencia": "Fecha de referencia",
    "fecha_desde": "Desde", "fecha_hasta": "Hasta",
    "sede_origen": "Sede origen", "sede_destino": "Sede destino",
}


def contenido_reporte(tipo):
    if tipo == "activos-vencidos":
        utilidad = "Ayuda a revisar las políticas de devolución y priorizar recursos de seguimiento por sede."
        alcance = (
            "Incluye préstamos que siguen activos al consultar, agrupados por sede de destino. "
            "La fecha de referencia permite calcular el atraso; no reconstruye el inventario histórico. "
            "La proporción es vencidos / activos y el atraso promedio considera solo vencidos. "
            "La multa es una estimación con la tarifa vigente, no dinero cobrado."
        )
        bloques = [("Situación por sede", [
            "sede", "sede_nombre", "activos", "vencidos", "proporcion_vencidos",
            "promedio_dias_atraso", "multa_total",
        ])]
    elif tipo == "disponibilidad":
        utilidad = "Ayuda a evaluar compras de ejemplares, necesidades de reparación y cobertura del catálogo por sede."
        alcance = (
            "Es una fotografía del inventario actual, no una tendencia histórica. Cada copia se cuenta una vez. "
            "Las copias en tránsito se atribuyen al origen de su remito activo; sin remito ni ubicación, "
            "a su sede de pertenencia. Las reservas activas incluyen pendientes y asignadas. "
            "Las tablas siguientes describen las mismas combinaciones de sede y libro."
        )
        bloques = [
            ("Inventario y circulación", [
                "sede", "isbn", "titulo", "total", "disponibles", "prestados", "apartados",
            ]),
            ("Logística, reparación y demanda pendiente", [
                "sede", "isbn", "titulo", "en_transito", "en_reparacion",
                "pendientes_retorno", "reservas_activas",
            ]),
        ]
    elif tipo == "libros-solicitados":
        utilidad = "Ayuda a priorizar compras y evaluar la distribución del catálogo según la demanda entre sedes."
        alcance = (
            "Cuenta solicitudes interbibliotecarias, incluidas las canceladas, no préstamos completados. "
            "Las fechas desde y hasta son inclusivas. Sin fechas se considera todo el historial disponible. "
            "El orden es descendente por cantidad y, ante empate, por ISBN."
        )
        bloques = [("Ranking de demanda entre sedes", ["isbn", "titulo", "cantidad"])]
    elif tipo == "movimiento":
        utilidad = "Ayuda a evaluar los recursos logísticos, comparar rutas y detectar trayectos que requieren revisión."
        alcance = (
            "Considera todo el historial de remitos, sin filtro temporal. Se agrupa por origen y destino. "
            "Recibidos / total incluye los cancelados en el denominador; recibido no significa sin daños. "
            "Las incidencias usan el estado físico observado al recibir. Los promedios se calculan sobre "
            "remitos recibidos con fechas completas: tránsito desde despacho, total desde creación. "
            "Un promedio cero también puede indicar que no hay duraciones disponibles."
        )
        bloques = [
            ("Volumen y estado de los envíos", [
                "origen", "destino", "total", "prestamos", "retornos",
                "recibidos", "pendientes", "cancelados",
            ]),
            ("Recepción e incidencias", [
                "origen", "destino", "copias_danadas_recepcion", "tasa_exito",
            ]),
            ("Tiempos promedio por ruta", [
                "origen", "destino", "promedio_horas_transito", "promedio_dias_transito",
                "promedio_horas_total", "promedio_dias_total",
            ]),
        ]
    else:
        raise ValueError("Tipo de reporte PDF desconocido: " + tipo)
    return utilidad, alcance, bloques


def formatear_valor(clave, valor):
    if valor is None:
        return "-"
    if isinstance(valor, datetime.date):
        return valor.strftime("%d/%m/%Y")
    if clave in ("proporcion_vencidos", "tasa_exito"):
        return f"{valor * 100:.0f}%"
    if clave == "multa_total":
        texto = f"{valor:,.2f}"
        texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
        return "$ " + texto
    if isinstance(valor, float):
        return f"{valor:.2f}".replace(".", ",")
    return str(valor)


def crear_tabla(filas, columnas, ancho, estilos):
    encabezados = []
    pesos = []
    for clave in columnas:
        encabezados.append(Paragraph(escape(ETIQUETAS[clave]), estilos["encabezado"]))
        peso = 1
        if clave in ("titulo", "sede_nombre"):
            peso = 3
        pesos.append(peso)

    datos = [encabezados]
    for fila in filas:
        celdas = []
        for clave in columnas:
            texto = formatear_valor(clave, fila[clave])
            celdas.append(Paragraph(escape(texto), estilos["celda"]))
        datos.append(celdas)

    total_pesos = 0
    for peso in pesos:
        total_pesos += peso
    anchos = []
    for peso in pesos:
        anchos.append(ancho * peso / total_pesos)

    tabla = Table(datos, colWidths=anchos, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163c50")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f5f7")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccd8df")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return tabla


def agregar_pie(pagina, documento):
    pagina.saveState()
    pagina.setFont("Helvetica", 8)
    pagina.setFillColor(colors.HexColor("#526773"))
    pagina.drawString(documento.leftMargin, 10 * mm, "Red de bibliotecas - Informe de gestión")
    pagina.drawRightString(documento.pagesize[0] - documento.rightMargin, 10 * mm,
                          "Página " + str(documento.page))
    pagina.restoreState()


def dibujar_barras(grafico, grupo, ancho):
    alto = len(grafico["series"]) * 19 + 28
    dibujo = Drawing(ancho, alto)
    izquierda = 130
    ancho_barras = ancho - izquierda - 85
    escala = max(grafico["maximo"], 1)
    dibujo.add(Line(izquierda, 22, izquierda, alto - 3, strokeColor=colors.HexColor("#ccd8df")))
    dibujo.add(Line(izquierda, 22, izquierda + ancho_barras, 22,
                    strokeColor=colors.HexColor("#ccd8df")))
    dibujo.add(String(izquierda, 8, "0", fontSize=8, fillColor=colors.HexColor("#526773")))
    extremo = formatear_valor("", escala) + " " + grafico["unidad"]
    dibujo.add(String(izquierda + ancho_barras, 8, extremo, textAnchor="end",
                      fontSize=8, fillColor=colors.HexColor("#526773")))
    for indice in range(len(grafico["series"])):
        serie = grafico["series"][indice]
        valor = grupo["valores"][indice]
        posicion = alto - 18 - indice * 19
        largo = ancho_barras * valor / escala
        dibujo.add(String(0, posicion + 1, serie["nombre"], fontSize=9))
        dibujo.add(Rect(izquierda, posicion, largo, 10,
                        fillColor=colors.HexColor(serie["color"]), strokeColor=None))
        dibujo.add(String(izquierda + largo + 5, posicion + 1, formatear_valor("", valor),
                          fontSize=9))
    return dibujo


def agregar_graficos(contenido, tipo, filas, ancho, estilos):
    for grafico in preparar_graficos(tipo, filas):
        encabezado = [Paragraph(escape(grafico["titulo"]), estilos["Heading2"])]
        encabezado.append(Paragraph("Unidad: " + grafico["unidad"] +
                                   ". Escala común para los grupos de este gráfico.", estilos["Normal"]))
        if grafico["maximo"] == 0:
            encabezado.append(Paragraph("Todos los valores son cero.", estilos["Normal"]))
        if grafico["unidad"] == "horas":
            encabezado.append(Paragraph("Cero también puede indicar que no hay duraciones disponibles.",
                                        estilos["Normal"]))
        for grupo in grafico["grupos"]:
            etiqueta = Paragraph(escape(grupo["etiqueta"]), estilos["Normal"])
            dibujo = dibujar_barras(grafico, grupo, ancho)
            contenido.append(KeepTogether(encabezado + [etiqueta, dibujo]))
            encabezado = []
        contenido.append(Spacer(1, 4 * mm))


def generar_pdf(tipo, titulo, filas, parametros):
    utilidad, alcance, bloques = contenido_reporte(tipo)
    archivo = BytesIO()
    documento = SimpleDocTemplate(
        archivo, pagesize=landscape(A4), title=titulo, author="Red de bibliotecas",
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=18 * mm,
    )
    estilos = getSampleStyleSheet()
    estilos["Normal"].fontSize = 10
    estilos["Normal"].leading = 14
    estilos["Heading2"].keepWithNext = True
    estilos["Title"].fontSize = 21
    estilos["Title"].leading = 25
    estilos["Title"].alignment = 0
    estilos["Title"].textColor = colors.HexColor("#163c50")
    encabezado = estilos["Normal"].clone("encabezado")
    encabezado.fontSize = 9
    encabezado.leading = 12
    encabezado.textColor = colors.white
    encabezado.fontName = "Helvetica-Bold"
    estilos.add(encabezado)
    celda = estilos["Normal"].clone("celda")
    celda.fontSize = 9
    celda.leading = 12
    estilos.add(celda)

    contenido = []
    contenido.append(Paragraph(escape(titulo), estilos["Title"]))
    momento = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    contenido.append(Paragraph("Generado: " + momento + " (hora local del servidor)", estilos["Normal"]))
    contenido.append(Paragraph("Datos consultados al descargar el documento.", estilos["Normal"]))
    contenido.append(Spacer(1, 3 * mm))
    contenido.append(Paragraph("Filtros aplicados", estilos["Heading2"]))
    for clave in parametros:
        valor = parametros[clave]
        if valor is None:
            texto = "Sin restricción"
        else:
            texto = formatear_valor(clave, valor)
        linea = ETIQUETAS[clave] + ": " + texto
        contenido.append(Paragraph(escape(linea), estilos["Normal"]))
    if len(parametros) == 0:
        contenido.append(Paragraph("Sin filtros: todo el historial disponible.", estilos["Normal"]))
    contenido.append(Paragraph("Utilidad para la gestión", estilos["Heading2"]))
    contenido.append(Paragraph(escape(utilidad), estilos["Normal"]))
    contenido.append(Paragraph("Alcance e interpretación", estilos["Heading2"]))
    contenido.append(Paragraph(escape(alcance), estilos["Normal"]))
    contenido.append(Spacer(1, 3 * mm))

    if len(filas) == 0:
        contenido.append(Paragraph("Sin datos para los filtros seleccionados.", estilos["Heading2"]))
    else:
        agregar_graficos(contenido, tipo, filas, documento.width, estilos)
        for nombre, columnas in bloques:
            contenido.append(Paragraph(nombre, estilos["Heading2"]))
            contenido.append(crear_tabla(filas, columnas, documento.width, estilos))
            contenido.append(Spacer(1, 4 * mm))

    documento.build(contenido, onFirstPage=agregar_pie, onLaterPages=agregar_pie)
    archivo.seek(0)
    return archivo
