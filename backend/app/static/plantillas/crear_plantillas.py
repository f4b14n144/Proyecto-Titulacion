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

    # Encabezado: logo centrado
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if LOGO.exists():
        hp.add_run().add_picture(str(LOGO), width=Inches(1.4))

    # Pie de página: nombre de la carrera + número de página "X / Y"
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.text = "Carrera de Computación"
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    pp = footer.add_paragraph()
    pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_campo(pp, "PAGE")
    pp.add_run(" / ")
    _add_campo(pp, "NUMPAGES")


def _encabezado_institucional(doc: Document, tipo: int, nombre: str):
    """Bloque de encabezado UPS común a todos los informes."""
    _configurar_seccion(doc)  # logo en header + footer con numeración en todas las hojas

    t = doc.add_heading("UNIVERSIDAD POLITÉCNICA SALESIANA — SEDE CUENCA", level=1)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.runs[0].font.color.rgb = UPS_BLUE

    s = doc.add_heading("Carrera de Computación", level=2)
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER

    n = doc.add_heading(f"INFORME {tipo} — {nombre.upper()}", level=2)
    n.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()


def _fila_meta(tabla, etiqueta: str, marcador: str):
    fila = tabla.add_row()
    fila.cells[0].text = etiqueta
    fila.cells[1].text = marcador


def crear_informe_1():
    """Plantilla Informe 1 — Centro Docente (formulario dirección)."""
    doc = Document()
    _encabezado_institucional(doc, 1, "Centro Docente")

    # Metadatos
    tabla = doc.add_table(rows=0, cols=2)
    tabla.style = "Table Grid"
    _fila_meta(tabla, "Período académico:", "{{ periodo_nombre }}")
    _fila_meta(tabla, "Fecha del Consejo:", "{{ fecha_consejo }}")
    _fila_meta(tabla, "Fecha del informe:", "{{ fecha_informe }}")
    doc.add_paragraph()

    # Secciones del formulario
    for titulo, marcador in [
        ("1. Agenda tratada en la reunión", "{{ agenda }}"),
        ("2. Designaciones de Jefes de Área", "{{ designaciones }}"),
        ("3. Observaciones curriculares de docentes", "{{ observaciones_curriculares }}"),
        ("4. Resultados de encuestas estudiantiles", "{{ resultados_encuestas }}"),
        ("5. Resoluciones y compromisos", "{{ resoluciones }}"),
        ("6. Observaciones adicionales", "{{ observaciones_adicionales }}"),
    ]:
        doc.add_heading(titulo, level=3)
        doc.add_paragraph(marcador)
        doc.add_paragraph()

    # Firmas
    doc.add_heading("Firmas de responsabilidad", level=2)
    tf = doc.add_table(rows=3, cols=2)
    tf.style = "Table Grid"
    tf.rows[0].cells[0].text = "Director/a de Carrera"
    tf.rows[0].cells[1].text = "Secretaria"
    tf.rows[1].cells[0].text = "\n\n{{ firma_director }}"
    tf.rows[1].cells[1].text = "\n\n_______________________"
    tf.rows[2].cells[0].text = "{{ nombre_director }}"
    tf.rows[2].cells[1].text = ""

    ruta = DIR / "informe_1_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


def crear_informe_2():
    """Plantilla Informe 2 — Revisión AVAC."""
    doc = Document()
    _encabezado_institucional(doc, 2, "Revisión AVAC")

    tabla_meta = doc.add_table(rows=0, cols=2)
    tabla_meta.style = "Table Grid"
    _fila_meta(tabla_meta, "Período:", "{{ periodo_nombre }}")
    _fila_meta(tabla_meta, "Área:", "{{ area_nombre }}")
    _fila_meta(tabla_meta, "Jefe de Área:", "{{ jefe_nombre }}")
    doc.add_paragraph()

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
    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Table Grid"
    tbl.rows[0].cells[0].text = "Parámetro"
    tbl.rows[0].cells[1].text = "Cumple"
    for nombre, campo in params:
        fila = tbl.add_row()
        fila.cells[0].text = nombre
        fila.cells[1].text = f"{{{{ 'Sí' if item.{campo} else 'No' }}}}"
    doc.add_paragraph()
    doc.add_paragraph("Observaciones: {{ item.observaciones }}")
    doc.add_paragraph("Acciones de mejora: {{ item.acciones_mejora }}")
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("Análisis de cumplimiento del área", level=2)
    doc.add_paragraph("{{ analisis_area }}")

    doc.add_heading("Firmas", level=2)
    tf = doc.add_table(rows=2, cols=2)
    tf.style = "Table Grid"
    tf.rows[0].cells[0].text = "Jefe de Área"
    tf.rows[0].cells[1].text = "Director/a de Carrera"
    tf.rows[1].cells[0].text = "\n\n_______________________"
    tf.rows[1].cells[1].text = "\n\n_______________________"

    ruta = DIR / "informe_2_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


def crear_informe_3():
    """Plantilla Informe 3 — Visitas Áulicas + Calificaciones Interciclo."""
    doc = Document()
    _encabezado_institucional(doc, 3, "Visitas Áulicas e Interciclo")

    tabla_meta = doc.add_table(rows=0, cols=2)
    tabla_meta.style = "Table Grid"
    _fila_meta(tabla_meta, "Período:", "{{ periodo_nombre }}")
    _fila_meta(tabla_meta, "Área:", "{{ area_nombre }}")
    _fila_meta(tabla_meta, "Jefe de Área:", "{{ jefe_nombre }}")
    doc.add_paragraph()

    doc.add_heading("PARTE A — Visitas Áulicas", level=2)
    doc.add_paragraph("{% for v in visitas %}")
    doc.add_heading("{{ v.docente }} — {{ v.asignatura }} (Grupo {{ v.grupo }})", level=3)
    tbl = doc.add_table(rows=1, cols=2)
    tbl.style = "Table Grid"
    tbl.rows[0].cells[0].text = "Parámetro"
    tbl.rows[0].cells[1].text = "Cumple"
    for nombre, campo in [
        ("Visita realizada", "visita_realizada"),
        ("Puntualidad del docente", "puntualidad_docente"),
        ("Cumplimiento del sílabo", "cumplimiento_silabo"),
        ("Cumplimiento de prácticas", "cumplimiento_practicas"),
        ("Actividades con rúbrica", "actividades_con_rubrica"),
        ("Actividad de investigación", "actividad_investigacion"),
    ]:
        fila = tbl.add_row()
        fila.cells[0].text = nombre
        fila.cells[1].text = f"{{{{ 'Sí' if v.{campo} else 'No' }}}}"
    doc.add_paragraph("Observaciones estudiantes: {{ v.observaciones_estudiantes }}")
    doc.add_paragraph("Observaciones docente: {{ v.observaciones_docente }}")
    doc.add_paragraph("Acciones docente: {{ v.acciones_docente }}")
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("PARTE B — Calificaciones Interciclo (Parcial 1)", level=2)
    doc.add_paragraph("{% for c in calificaciones_interciclo %}")
    doc.add_heading("{{ c.asignatura }} — Grupo {{ c.grupo }}", level=3)
    tbl2 = doc.add_table(rows=0, cols=2)
    tbl2.style = "Table Grid"
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
        fila.cells[0].text = etiqueta
        fila.cells[1].text = f"{{{{ c.{campo} }}}}"
    doc.add_paragraph("Análisis narrativo: {{ c.analisis_narrativo }}")
    doc.add_paragraph("Acciones de mejora: {{ c.acciones_mejora }}")
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("Firmas", level=2)
    tf = doc.add_table(rows=2, cols=2)
    tf.style = "Table Grid"
    tf.rows[0].cells[0].text = "Jefe de Área"
    tf.rows[0].cells[1].text = "Director/a de Carrera"
    tf.rows[1].cells[0].text = "\n\n_______________________"
    tf.rows[1].cells[1].text = "\n\n_______________________"

    ruta = DIR / "informe_3_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


def crear_informe_4():
    """Plantilla Informe 4 — Análisis Final de Calificaciones."""
    doc = Document()
    _encabezado_institucional(doc, 4, "Análisis Final de Calificaciones")

    tabla_meta = doc.add_table(rows=0, cols=2)
    tabla_meta.style = "Table Grid"
    _fila_meta(tabla_meta, "Período:", "{{ periodo_nombre }}")
    _fila_meta(tabla_meta, "Área:", "{{ area_nombre }}")
    _fila_meta(tabla_meta, "Jefe de Área:", "{{ jefe_nombre }}")
    doc.add_paragraph()

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
    doc.add_paragraph()
    doc.add_paragraph("{% endfor %}")

    doc.add_heading("Análisis Consolidado del Área", level=2)
    doc.add_paragraph("{{ analisis_consolidado_area }}")
    doc.add_heading("Acciones generales del área", level=3)
    doc.add_paragraph("{{ acciones_generales_area }}")

    doc.add_heading("Firmas", level=2)
    tf = doc.add_table(rows=2, cols=2)
    tf.style = "Table Grid"
    tf.rows[0].cells[0].text = "Jefe de Área"
    tf.rows[0].cells[1].text = "Director/a de Carrera"
    tf.rows[1].cells[0].text = "\n\n_______________________"
    tf.rows[1].cells[1].text = "\n\n_______________________"

    ruta = DIR / "informe_4_plantilla.docx"
    doc.save(str(ruta))
    print(f"Creada: {ruta}")


if __name__ == "__main__":
    crear_informe_1()
    crear_informe_2()
    crear_informe_3()
    crear_informe_4()
    print("Todas las plantillas creadas exitosamente.")
