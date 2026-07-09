"""
Script para crear las plantillas .docx base con marcadores Jinja2.
Ejecutar UNA SOLA VEZ dentro del contenedor backend:

  docker compose exec backend python app/static/plantillas/crear_plantillas.py

Las plantillas se guardan en app/static/plantillas/ y son leídas
por doc_generator.py en tiempo de ejecución.
"""
from pathlib import Path
from docxtpl import DocxTemplate
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

DIR = Path(__file__).parent
LOGO = DIR.parent / "logo-ups.jpg"  # app/static/logo-ups.jpg

UPS_BLUE = RGBColor(0x00, 0x3D, 0xA5)
GRIS_TEXTO = RGBColor(0x33, 0x33, 0x33)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
AZUL_HEX = "003DA5"        # relleno encabezados de tabla
GRIS_META_HEX = "E8EDF6"   # relleno columna de etiquetas (metadatos)


def _aplicar_estilos(doc: Document):
    """Define estilos base uniformes para TODOS los informes.

    Así cada informe (1-4) se ve idéntico: misma tipografía, mismos tamaños
    y colores de encabezado, mismo interlineado y justificado.
    """
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = GRIS_TEXTO
    pf = normal.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Título del informe (Heading 1)
    h1 = doc.styles["Heading 1"]
    h1.font.name = "Calibri"
    h1.font.size = Pt(18)
    h1.font.bold = True
    h1.font.color.rgb = UPS_BLUE
    h1.paragraph_format.space_before = Pt(0)
    h1.paragraph_format.space_after = Pt(12)

    # Secciones principales (Heading 2)
    h2 = doc.styles["Heading 2"]
    h2.font.name = "Calibri"
    h2.font.size = Pt(14)
    h2.font.bold = True
    h2.font.color.rgb = UPS_BLUE
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(4)

    # Subsecciones (Heading 3)
    h3 = doc.styles["Heading 3"]
    h3.font.name = "Calibri"
    h3.font.size = Pt(12)
    h3.font.bold = True
    h3.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    h3.paragraph_format.space_before = Pt(8)
    h3.paragraph_format.space_after = Pt(2)


def _sombrear(cell, hexcolor: str):
    """Rellena el fondo de una celda con un color."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def _celda(cell, texto: str, *, negrita=False, blanco=False, relleno=None):
    """Escribe texto en una celda con formato uniforme."""
    cell.text = texto
    for run in cell.paragraphs[0].runs:
        run.font.name = "Calibri"
        run.font.size = Pt(11)
        run.font.bold = negrita
        run.font.color.rgb = BLANCO if blanco else GRIS_TEXTO
    if relleno:
        _sombrear(cell, relleno)


def _meta(doc: Document, filas):
    """Tabla de metadatos uniforme: etiqueta (sombreada) | valor."""
    tabla = doc.add_table(rows=0, cols=2)
    tabla.style = "Table Grid"
    for etiqueta, marcador in filas:
        fila = tabla.add_row()
        _celda(fila.cells[0], etiqueta, negrita=True, relleno=GRIS_META_HEX)
        _celda(fila.cells[1], marcador)
        fila.cells[0].width = Inches(2.3)
        fila.cells[1].width = Inches(4.2)
    doc.add_paragraph()
    return tabla


def _tabla_datos(doc: Document, encabezados):
    """Crea una tabla con fila de encabezado azul + texto blanco."""
    tbl = doc.add_table(rows=1, cols=len(encabezados))
    tbl.style = "Table Grid"
    for i, h in enumerate(encabezados):
        _celda(tbl.rows[0].cells[i], h, negrita=True, blanco=True, relleno=AZUL_HEX)
    return tbl


def _firmas(doc: Document, columnas):
    """Bloque de firmas uniforme. columnas: [(titulo, marcador_nombre), ...]."""
    doc.add_paragraph()
    doc.add_heading("Firmas de responsabilidad", level=2)
    tf = doc.add_table(rows=3, cols=len(columnas))
    tf.style = "Table Grid"
    for i, (titulo, marcador) in enumerate(columnas):
        _celda(tf.rows[0].cells[i], titulo, negrita=True, blanco=True, relleno=AZUL_HEX)
        tf.rows[1].cells[i].text = "\n\n_______________________"
        _celda(tf.rows[2].cells[i], marcador, negrita=True)


def _add_campo(parrafo, instr: str):
    """Inserta un campo de Word (PAGE / NUMPAGES) en un párrafo."""
    run = parrafo.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr_el)
    run._r.append(end)


def _configurar_seccion(doc: Document):
    """Header con logo UPS + footer con 'Carrera de Computación' y numeración X/Y."""
    section = doc.sections[0]

    # Encabezado: logo institucional arriba a la IZQUIERDA + línea divisoria
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if LOGO.exists():
        hp.add_run().add_picture(str(LOGO), width=Inches(2.4))
    # Línea horizontal bajo el logo (borde inferior del párrafo)
    _borde_inferior(hp)

    # Pie de página: línea divisoria + carrera (izq) y número de página "X / Y" (der)
    footer = section.footer
    fp = footer.paragraphs[0]
    _borde_superior(fp)
    # Tabulación: texto a la izquierda, numeración a la derecha
    from docx.enum.text import WD_TAB_ALIGNMENT
    from docx.shared import Cm
    fp.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT)
    fp.add_run("Carrera de Computación — Universidad Politécnica Salesiana, Sede Cuenca")
    fp.add_run("\tPág. ")
    _add_campo(fp, "PAGE")
    fp.add_run(" / ")
    _add_campo(fp, "NUMPAGES")


def _borde(parrafo, lado: str):
    """Agrega un borde (top/bottom) al párrafo (línea divisoria)."""
    p = parrafo._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    borde = OxmlElement(f"w:{lado}")
    borde.set(qn("w:val"), "single")
    borde.set(qn("w:sz"), "6")
    borde.set(qn("w:space"), "4")
    borde.set(qn("w:color"), "003DA5")
    pbdr.append(borde)
    p.append(pbdr)


def _borde_inferior(parrafo):
    _borde(parrafo, "bottom")


def _borde_superior(parrafo):
    _borde(parrafo, "top")


def _encabezado_institucional(doc: Document, tipo: int, nombre: str):
    """Bloque de encabezado UPS común a todos los informes."""
    _aplicar_estilos(doc)         # estilos uniformes (tipografía, headings, interlineado)
    _configurar_seccion(doc)      # logo en header + footer con numeración en todas las hojas

    n = doc.add_heading(f"INFORME {tipo} — {nombre.upper()}", level=1)
    n.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph("Carrera de Computación · Consejo de Carrera")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in sub.runs:
        run.font.size = Pt(10)
        run.font.color.rgb = GRIS_TEXTO
        run.italic = True
    doc.add_paragraph()


def crear_informe_1():
    """Plantilla Informe 1 — Centro Docente (formulario dirección)."""
    doc = Document()
    _encabezado_institucional(doc, 1, "Centro Docente")

    # Metadatos
    _meta(doc, [
        ("Período académico:", "{{ periodo_nombre }}"),
        ("Área:", "{{ area_nombre }}"),
        ("Jefe de Área:", "{{ jefe_titulo }} {{ jefe_nombre }}"),
        ("Fecha del Consejo:", "{{ fecha_consejo }}"),
        ("Fecha del informe:", "{{ fecha_informe }}"),
    ])

    # Cada sección lleva: lo que escribió la dirección (común a todas las áreas)
    # y debajo el aporte propio del jefe de área.
    for titulo, campo in [
        ("1. Agenda tratada en la reunión", "agenda"),
        ("2. Designaciones de Jefes de Área", "designaciones"),
        ("3. Observaciones curriculares de docentes", "observaciones_curriculares"),
        ("4. Resultados de encuestas estudiantiles", "resultados_encuestas"),
        ("5. Resoluciones y compromisos", "resoluciones"),
        ("6. Observaciones adicionales", "observaciones_adicionales"),
    ]:
        doc.add_heading(titulo, level=2)
        doc.add_paragraph(f"{{{{ dir_{campo} }}}}")
        doc.add_paragraph(
            f"{{%p if {campo} %}}"
        )
        doc.add_heading("Aporte del Área", level=3)
        doc.add_paragraph(f"{{{{ {campo} }}}}")
        doc.add_paragraph("{%p endif %}")

    _firmas(doc, [
        ("Jefe de Área", "{{ jefe_titulo }} {{ jefe_nombre }}"),
    ])

    ruta = DIR / "informe_1_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


def crear_informe_2():
    """Plantilla Informe 2 — Revisión AVAC."""
    doc = Document()
    _encabezado_institucional(doc, 2, "Revisión AVAC")

    _meta(doc, [
        ("Período:", "{{ periodo_nombre }}"),
        ("Área:", "{{ area_nombre }}"),
        ("Jefe de Área:", "{{ jefe_nombre }}"),
    ])

    doc.add_heading("Resultados del Checklist AVAC", level=2)
    doc.add_paragraph(
        "Los siguientes parámetros fueron evaluados para cada docente y asignatura:"
    )
    doc.add_paragraph("{% for item in checklists %}")
    doc.add_heading("{{ item.docente }} — {{ item.asignatura }} (Grupo {{ item.grupo }})", level=3)

    params = [
        ("Sílabo cargado", "silabo_cargado"),
        ("Registro de avance del sílabo", "registro_avance"),
        ("Guía de componente práctico", "guia_practicas"),
        ("Enlace consejería académica", "consejeria_academica"),
        ("Recursos con derechos de autor", "recursos_derechos_autor"),
        ("Libros digitales biblioteca", "libros_digitales"),
        ("Sección PRÁCTICAS", "seccion_practicas"),
        ("Guías de componente práctico", "guias_componente"),
        ("Actividades con rúbrica", "actividades_con_rubrica"),
        ("Sección INVESTIGATIVAS", "seccion_investigativas"),
        ("Actividad de investigación", "actividad_investigacion"),
        ("Proyecto integrador", "proyecto_integrador"),
    ]
    tbl = _tabla_datos(doc, ["Parámetro", "Cumple"])
    for nombre, campo in params:
        fila = tbl.add_row()
        _celda(fila.cells[0], nombre)
        _celda(fila.cells[1], f"{{{{ 'Sí' if item.{campo} else 'No' }}}}")
    doc.add_paragraph()
    doc.add_paragraph("Observaciones: {{ item.observaciones }}")
    doc.add_paragraph("Acciones de mejora: {{ item.acciones_mejora }}")
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("Análisis de cumplimiento del área", level=2)
    doc.add_paragraph("{{ analisis_area }}")

    _firmas(doc, [
        ("Jefe de Área", "{{ jefe_titulo }} {{ jefe_nombre }}"),
    ])

    ruta = DIR / "informe_2_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


def crear_informe_3():
    """Plantilla Informe 3 — Visitas Áulicas + Calificaciones Interciclo."""
    doc = Document()
    _encabezado_institucional(doc, 3, "Visitas Áulicas e Interciclo")

    _meta(doc, [
        ("Período:", "{{ periodo_nombre }}"),
        ("Área:", "{{ area_nombre }}"),
        ("Jefe de Área:", "{{ jefe_nombre }}"),
    ])

    doc.add_heading("PARTE A — Visitas Áulicas", level=2)
    doc.add_paragraph("{% for v in visitas %}")
    doc.add_heading("{{ v.docente }} — {{ v.asignatura }} (Grupo {{ v.grupo }})", level=3)
    tbl = _tabla_datos(doc, ["Parámetro", "Cumple"])
    for nombre, campo in [
        ("Visita realizada", "visita_realizada"),
        ("Puntualidad del docente", "puntualidad_docente"),
        ("Cumplimiento del sílabo", "cumplimiento_silabo"),
        ("Cumplimiento de prácticas", "cumplimiento_practicas"),
        ("Actividades con rúbrica", "actividades_con_rubrica"),
        ("Actividad de investigación", "actividad_investigacion"),
    ]:
        fila = tbl.add_row()
        _celda(fila.cells[0], nombre)
        _celda(fila.cells[1], f"{{{{ 'Sí' if v.{campo} else 'No' }}}}")
    doc.add_paragraph("Observaciones estudiantes: {{ v.observaciones_estudiantes }}")
    doc.add_paragraph("Observaciones docente: {{ v.observaciones_docente }}")
    doc.add_paragraph("Acciones docente: {{ v.acciones_docente }}")
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("PARTE B — Calificaciones Interciclo (Parcial 1)", level=2)
    doc.add_paragraph("{% for c in calificaciones_interciclo %}")
    doc.add_heading("{{ c.asignatura }} — Grupo {{ c.grupo }}", level=3)
    tbl2 = _tabla_datos(doc, ["Indicador", "Valor"])
    for etiqueta, campo in [
        ("Total estudiantes", "total_estudiantes"),
        ("Nota máxima /50", "maximo"),
        ("Nota mínima /50", "minimo"),
        ("Promedio /50", "promedio"),
        ("Mediana /50", "mediana"),
        ("Rango alto (≥40)", "rango_alto"),
        ("Rango medio (30-39)", "rango_medio"),
        ("Rango bajo (<30)", "rango_bajo"),
    ]:
        fila = tbl2.add_row()
        _celda(fila.cells[0], etiqueta, negrita=True, relleno=GRIS_META_HEX)
        _celda(fila.cells[1], f"{{{{ c.{campo} }}}}")
    doc.add_paragraph("Análisis narrativo: {{ c.analisis_narrativo }}")
    doc.add_paragraph("Acciones de mejora: {{ c.acciones_mejora }}")
    # Aportes registrados por el docente sobre la materia (sumativos)
    doc.add_paragraph("{%p if c.observaciones_materia %}")
    doc.add_heading("Observaciones del Docente a la Materia", level=3)
    doc.add_paragraph("{{ c.observaciones_materia }}")
    doc.add_paragraph("{%p endif %}")
    doc.add_paragraph("{%p if c.acciones_mejora_docente %}")
    doc.add_heading("Acciones de Mejora propuestas por el Docente", level=3)
    doc.add_paragraph("{{ c.acciones_mejora_docente }}")
    doc.add_paragraph("{%p endif %}")
    doc.add_paragraph("{% endfor %}")

    _firmas(doc, [
        ("Jefe de Área", "{{ jefe_titulo }} {{ jefe_nombre }}"),
    ])

    ruta = DIR / "informe_3_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


def crear_informe_4():
    """Plantilla Informe 4 — Análisis Final de Calificaciones."""
    doc = Document()
    _encabezado_institucional(doc, 4, "Análisis Final de Calificaciones")

    _meta(doc, [
        ("Período:", "{{ periodo_nombre }}"),
        ("Área:", "{{ area_nombre }}"),
        ("Jefe de Área:", "{{ jefe_nombre }}"),
    ])

    doc.add_paragraph("{% for c in calificaciones_finales %}")
    doc.add_heading("{{ c.docente }} — {{ c.asignatura }} (Grupo {{ c.grupo }})", level=2)

    sub_analisis = [
        ("1. Análisis general", "analisis_general"),
        ("2. Distribución aprobación/reprobación", "distribucion_aprobacion"),
        ("3. Comportamiento notas finales", "comportamiento_notas_finales"),
        ("4. Análisis Parcial 1", "analisis_parcial1"),
        ("5. Análisis Parcial 2", "analisis_parcial2"),
        ("6. Comparación entre parciales", "comparacion_parciales"),
        ("7. Uso de recuperación", "uso_recuperacion"),
        ("8. Relación parciales-nota final", "relacion_parciales_nota_final"),
        ("9. Identificación de outliers", "outliers"),
        ("10. Patrones generales", "patrones_generales"),
    ]
    for titulo, campo in sub_analisis:
        doc.add_heading(titulo, level=3)
        doc.add_paragraph(f"{{{{ c.{campo} }}}}")

    doc.add_heading("Acciones de mejora sugeridas", level=3)
    doc.add_paragraph("{{ c.acciones_mejora }}")

    # Aportes registrados por el docente sobre la materia (sumativos)
    doc.add_paragraph("{%p if c.observaciones_materia %}")
    doc.add_heading("Observaciones del Docente a la Materia", level=3)
    doc.add_paragraph("{{ c.observaciones_materia }}")
    doc.add_paragraph("{%p endif %}")
    doc.add_paragraph("{%p if c.acciones_mejora_docente %}")
    doc.add_heading("Acciones de Mejora propuestas por el Docente", level=3)
    doc.add_paragraph("{{ c.acciones_mejora_docente }}")
    doc.add_paragraph("{%p endif %}")
    doc.add_paragraph()
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("Análisis Consolidado del Área", level=2)
    doc.add_paragraph("{{ analisis_consolidado_area }}")
    doc.add_heading("Acciones generales del área", level=3)
    doc.add_paragraph("{{ acciones_generales_area }}")

    _firmas(doc, [
        ("Jefe de Área", "{{ jefe_titulo }} {{ jefe_nombre }}"),
    ])

    ruta = DIR / "informe_4_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


if __name__ == "__main__":
    crear_informe_1()
    crear_informe_2()
    crear_informe_3()
    crear_informe_4()
    print("Todas las plantillas creadas exitosamente.")
