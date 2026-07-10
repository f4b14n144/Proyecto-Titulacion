"""
Generador de documentos Word usando python-docx-template (Jinja2 en .docx).

Flujo:
  1. Carga la plantilla .docx base del tipo de informe (1-4)
  2. Renderiza con los datos del informe (contenido_json)
  3. Guarda el .docx en app/static/docx/
  4. Actualiza ruta_docx e incrementa version en la tabla informes
"""
from datetime import datetime, timezone
from pathlib import Path
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Inches
from loguru import logger
from sqlalchemy.orm import Session
from app.models.informe import Informe

PLANTILLAS_DIR = Path(__file__).parent.parent / "static" / "plantillas"
DOCX_OUTPUT_DIR = Path(__file__).parent.parent / "static" / "docx"
GRAFICOS_DIR = Path(__file__).parent.parent / "static" / "graficos"

PLANTILLAS_DIR.mkdir(parents=True, exist_ok=True)
DOCX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)


def _ruta_plantilla(tipo_informe: int) -> Path:
    return PLANTILLAS_DIR / f"informe_{tipo_informe}_plantilla.docx"


def generar_docx(db: Session, informe: Informe) -> str:
    """
    Genera el .docx para el informe usando su contenido_json.
    Retorna la ruta relativa guardada en la DB.

    Si no existe plantilla real, genera un .docx básico de texto.
    """
    plantilla_ruta = _ruta_plantilla(informe.tipo_informe)
    contenido = informe.contenido_json or {}

    nombre_archivo = (
        f"informe_{informe.tipo_informe}"
        f"_consejo{informe.consejo_id}"
        f"_area{informe.area_id}"
        f"_v{informe.version}.docx"
    )
    ruta_salida = DOCX_OUTPUT_DIR / nombre_archivo

    if plantilla_ruta.exists():
        _generar_desde_plantilla(plantilla_ruta, contenido, ruta_salida)
    else:
        logger.warning(
            f"Plantilla {plantilla_ruta} no encontrada — generando .docx básico"
        )
        _generar_docx_basico(informe, contenido, ruta_salida)

    # Actualizar informe en DB
    informe.ruta_docx = nombre_archivo
    informe.generado_en = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Informe {informe.id} generado: {nombre_archivo}")
    return nombre_archivo


def _aplanar_contexto(contenido: dict) -> dict:
    """
    Prepara el contexto para Jinja2.

    Las plantillas usan marcadores planos (`{{ agenda }}`), pero el contenido se
    guarda anidado bajo `secciones` / `secciones_direccion`. Sin este aplanado,
    los informes salían con los títulos pero SIN texto.

    Las secciones de dirección se exponen con el prefijo `dir_` para poder
    imprimirlas junto al aporte del jefe de área.
    """
    contexto = dict(contenido)
    for campo, valor in (contenido.get("secciones") or {}).items():
        contexto.setdefault(campo, valor)
    for campo, valor in (contenido.get("secciones_direccion") or {}).items():
        contexto[f"dir_{campo}"] = valor
    return contexto


def _incrustar_graficos(doc: DocxTemplate, contexto: dict) -> None:
    """
    Convierte las rutas de gráficos guardadas en `contenido_json` en imágenes
    incrustables. La plantilla las imprime con `{{ c.grafico }}`.

    Si el archivo no existe (p. ej. se regenera un informe antiguo) se deja el
    hueco vacío en vez de romper la generación.
    """
    originales = contexto.get("calificaciones_interciclo") or []
    if not originales:
        return

    # Copiar cada item: si mutáramos los originales, los objetos InlineImage
    # acabarían dentro de contenido_json y no son serializables a JSON.
    copias = []
    for item in originales:
        copia = dict(item)
        nombre = copia.get("grafico_ruta")
        if nombre:
            ruta = GRAFICOS_DIR / nombre
            if ruta.exists():
                copia["grafico"] = InlineImage(doc, str(ruta), width=Inches(5.4))
            else:
                logger.warning(f"Gráfico no encontrado: {ruta}")
                copia["grafico"] = ""
        copias.append(copia)
    contexto["calificaciones_interciclo"] = copias


def _generar_desde_plantilla(
    plantilla_ruta: Path, contexto: dict, ruta_salida: Path
) -> None:
    """Renderiza la plantilla Jinja2 .docx con el contexto dado."""
    doc = DocxTemplate(str(plantilla_ruta))
    aplanado = _aplanar_contexto(contexto)
    _incrustar_graficos(doc, aplanado)
    doc.render(aplanado)
    doc.save(str(ruta_salida))


def _generar_docx_basico(informe: Informe, contenido: dict, ruta_salida: Path) -> None:
    """Genera un .docx básico cuando no hay plantilla disponible."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    TIPO_NOMBRES = {
        1: "Informe Inicial — Centro Docente",
        2: "Informe de Revisión AVAC",
        3: "Informe de Visitas Áulicas e Interciclo",
        4: "Informe Final de Calificaciones",
    }

    doc = Document()

    # Encabezado institucional
    encabezado = doc.add_heading(
        f"UNIVERSIDAD POLITÉCNICA SALESIANA — SEDE CUENCA", level=1
    )
    encabezado.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitulo = doc.add_heading("Carrera de Computación", level=2)
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    nombre_tipo = TIPO_NOMBRES.get(informe.tipo_informe, f"Informe {informe.tipo_informe}")
    titulo = doc.add_heading(nombre_tipo.upper(), level=2)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Metadatos
    tabla_meta = doc.add_table(rows=3, cols=2)
    tabla_meta.style = "Table Grid"
    datos_meta = [
        ("Consejo de Carrera N°:", str(informe.consejo_id)),
        ("Área:", str(informe.area_id)),
        ("Versión:", str(informe.version)),
    ]
    for i, (etiqueta, valor) in enumerate(datos_meta):
        tabla_meta.rows[i].cells[0].text = etiqueta
        tabla_meta.rows[i].cells[1].text = valor

    doc.add_paragraph()

    # Contenido dinámico del informe
    secciones = contenido.get("secciones", {})
    if not secciones:
        doc.add_paragraph("Contenido del informe pendiente de generación.")
    else:
        for nombre_seccion, texto in secciones.items():
            doc.add_heading(nombre_seccion.replace("_", " ").title(), level=3)
            doc.add_paragraph(str(texto))

    # Análisis de calificaciones si existen
    analisis = contenido.get("analisis_calificaciones", [])
    if analisis:
        doc.add_heading("Análisis de Calificaciones", level=2)
        for item in analisis:
            doc.add_heading(
                f"Asignatura: {item.get('asignatura', '—')} — Grupo: {item.get('grupo', '—')}",
                level=3,
            )
            for campo, valor in item.items():
                if campo not in ("asignatura", "grupo"):
                    p = doc.add_paragraph()
                    p.add_run(f"{campo.replace('_', ' ').title()}: ").bold = True
                    p.add_run(str(valor))

    doc.add_paragraph()

    # Firmas
    doc.add_heading("Firmas", level=2)
    firmas = doc.add_table(rows=2, cols=2)
    firmas.rows[0].cells[0].text = "Jefe de Área"
    firmas.rows[0].cells[1].text = "Director/a de Carrera"
    firmas.rows[1].cells[0].text = "\n\n_______________________"
    firmas.rows[1].cells[1].text = "\n\n_______________________"

    doc.save(str(ruta_salida))


def regenerar_docx(db: Session, informe: Informe) -> str:
    """Incrementa la versión y regenera el .docx."""
    informe.version += 1
    db.flush()
    return generar_docx(db, informe)
