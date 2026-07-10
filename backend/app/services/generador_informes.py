"""
Generador de borradores de informes 1-4.

Cada función:
  1. Recopila datos de la DB (calificaciones, checklists, respuestas)
  2. Llama a ia_engine para análisis narrativos
  3. Construye contenido_json estructurado
  4. Crea o actualiza el registro en tabla `informes`
  5. Llama a doc_generator para producir el .docx
"""
import re
from datetime import datetime, timezone
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.contenido_consejo import ContenidoConsejo
from app.models.informe import Informe
from app.models.calificacion import Calificacion
from app.models.checklist_avac import ChecklistAVAC
from app.models.checklist_visita import ChecklistVisitaAulica
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.usuario import Usuario
from app.models.periodo import PeriodoAcademico
from app.models.area import Area
from app.models.consejo import ConsejoCarrera
from app.models.notificacion import Notificacion
from app.models.respuesta_docente import RespuestaDocente

from app.services import ia_engine
from app.services.doc_generator import generar_docx


# ──────────────────────────────────────────────────────────────────
# Helpers comunes
# ──────────────────────────────────────────────────────────────────

def _obtener_o_crear_informe(
    db: Session, consejo_id: int, area_id: int, tipo: int
) -> Informe:
    informe = db.query(Informe).filter(
        Informe.consejo_id == consejo_id,
        Informe.area_id == area_id,
        Informe.tipo_informe == tipo,
    ).first()
    if not informe:
        informe = Informe(
            consejo_id=consejo_id,
            area_id=area_id,
            tipo_informe=tipo,
            estado="BORRADOR",
            version=1,
        )
        db.add(informe)
        db.flush()
    return informe


def _nombre_usuario(db: Session, usuario_id: int) -> str:
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    return u.nombre_completo if u else f"Docente #{usuario_id}"


def _asignaturas_del_area(db: Session, area_id: int, periodo_id: int) -> list[AsignacionDocente]:
    return (
        db.query(AsignacionDocente)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(
            Asignatura.area_id == area_id,
            AsignacionDocente.periodo_id == periodo_id,
        )
        .all()
    )


def _aportes_materia(
    db: Session, consejo_id: int, asignatura_id: int, grupo: str
) -> dict[str, str]:
    """
    Aportes que el docente registró sobre la materia-grupo, ya concatenados.

    Son sumativos: se listan todos en orden cronológico, no solo el último.
    """
    from app.models.aporte_docente import AporteDocente

    aportes = (
        db.query(AporteDocente)
        .filter(
            AporteDocente.consejo_id == consejo_id,
            AporteDocente.asignatura_id == asignatura_id,
            AporteDocente.grupo == grupo,
        )
        .order_by(AporteDocente.creado_en)
        .all()
    )

    def _juntar(tipo: str) -> str:
        textos = [a.texto for a in aportes if a.tipo == tipo]
        if not textos:
            return ""
        if len(textos) == 1:
            return textos[0]
        return "\n".join(f"• {t}" for t in textos)

    return {
        "observaciones_materia": _juntar("OBSERVACION"),
        "acciones_mejora_docente": _juntar("ACCION_MEJORA"),
    }


def _respuesta_docente(db: Session, docente_id: int, consejo_id: int) -> str:
    """Recupera la última respuesta del docente para este consejo, si existe."""
    noti = (
        db.query(Notificacion)
        .filter(
            Notificacion.tipo == "DOCENTE_SUGERENCIA",
        )
        .first()
    )
    if not noti:
        return ""
    respuesta = (
        db.query(RespuestaDocente)
        .filter(RespuestaDocente.notificacion_id == noti.id)
        .order_by(RespuestaDocente.recibido_en.desc())
        .first()
    )
    return respuesta.contenido if respuesta else ""


# ──────────────────────────────────────────────────────────────────
# Informe 1 — Centro Docente (contenido de dirección + aporte del jefe)
# ──────────────────────────────────────────────────────────────────

# Secciones que escribe la DIRECTORA (comunes a todas las áreas del consejo)
SECCIONES_DIRECCION: list[str] = [
    "agenda",
    "designaciones",
    "observaciones_curriculares",
    "resultados_encuestas",
    "resoluciones",
    "observaciones_adicionales",
]


def _designaciones_jefes(db: Session, periodo_id: int) -> str:
    """Texto auto-llenado con las jefaturas de área del período."""
    from app.models.jefatura import JefaturaArea
    filas = (
        db.query(JefaturaArea, Area, Usuario)
        .join(Area, JefaturaArea.area_id == Area.id)
        .join(Usuario, JefaturaArea.usuario_id == Usuario.id)
        .filter(JefaturaArea.periodo_id == periodo_id)
        .order_by(Area.nombre)
        .all()
    )
    return "\n".join(
        f"• {area.nombre}: {usuario.nombre_completo}" for _, area, usuario in filas
    ) or "No hay jefes de área asignados para este período."


def _nombre_director(db: Session) -> str:
    from app.models.rol import Rol
    director = (
        db.query(Usuario).join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "DIRECTOR_CARRERA", Usuario.activo.is_(True))
        .first()
    )
    return director.nombre_completo if director else ""


def obtener_o_crear_contenido_direccion(db: Session, consejo_id: int) -> ContenidoConsejo:
    """
    Contenido del Informe 1 escrito por la dirección, único por consejo.
    Al crearlo se auto-llenan las designaciones de jefes y el nombre del director.
    """
    contenido = (
        db.query(ContenidoConsejo)
        .filter(ContenidoConsejo.consejo_id == consejo_id)
        .first()
    )
    if contenido:
        return contenido

    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if consejo is None:
        raise ValueError(f"Consejo {consejo_id} no existe")

    secciones = {campo: "" for campo in SECCIONES_DIRECCION}
    secciones["designaciones"] = _designaciones_jefes(db, consejo.periodo_id)

    contenido = ContenidoConsejo(
        consejo_id=consejo_id,
        secciones=secciones,
        nombre_director=_nombre_director(db),
    )
    db.add(contenido)
    db.commit()
    logger.info(f"Contenido de dirección creado para el consejo {consejo_id}")
    return contenido


def _jefe_del_area(db: Session, area_id: int, periodo_id: int) -> Usuario | None:
    from app.models.jefatura import JefaturaArea
    jefatura = (
        db.query(JefaturaArea)
        .filter(JefaturaArea.area_id == area_id, JefaturaArea.periodo_id == periodo_id)
        .first()
    )
    if jefatura is None:
        return None
    return db.query(Usuario).filter(Usuario.id == jefatura.usuario_id).first()


def _datos_jefe(db: Session, area_id: int, periodo_id: int) -> dict:
    """Nombre y título del jefe del área — van en la carátula y en las firmas."""
    jefe = _jefe_del_area(db, area_id, periodo_id)
    return {
        "jefe_nombre": jefe.nombre_completo if jefe else "",
        "jefe_titulo": (jefe.titulo or "") if jefe else "",
    }


# Texto de la carátula. Es editable desde el informe (contenido_json).
CARRERAS_TEXTO = "CARRERAS DE COMPUTACIÓN E INGENIERÍA DE SISTEMAS"


def _periodo_numero(periodo: PeriodoAcademico | None) -> str:
    """
    Número del período para la carátula ("CORRESPONDIENTE AL PERIODO 67").

    Los nombres tienen forma "2025-2026 (67)"; si no hay paréntesis, se devuelve
    el nombre completo.
    """
    if periodo is None:
        return ""
    m = re.search(r"\((\d+)\)", periodo.nombre or "")
    return m.group(1) if m else (periodo.nombre or "")


def _datos_caratula(periodo: PeriodoAcademico | None) -> dict:
    return {
        "periodo_numero": _periodo_numero(periodo),
        "carreras_texto": CARRERAS_TEXTO,
    }


def generar_informe_1(db: Session, consejo_id: int, area_id: int) -> Informe:
    """
    Informe 1 del ÁREA indicada.

    Hereda (en solo lectura) el contenido que escribió la dirección para el
    consejo y conserva las secciones propias que haya escrito el jefe de área.
    """
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == consejo.periodo_id).first()
    area = db.query(Area).filter(Area.id == area_id).first()

    direccion = obtener_o_crear_contenido_direccion(db, consejo_id)
    jefe = _jefe_del_area(db, area_id, consejo.periodo_id)

    informe = _obtener_o_crear_informe(db, consejo_id, area_id, 1)

    # No pisar lo que el jefe ya escribió
    previo = informe.contenido_json or {}
    secciones_jefe = dict(previo.get("secciones", {}))
    for campo in SECCIONES_DIRECCION:
        secciones_jefe.setdefault(campo, "")

    informe.contenido_json = {
        "periodo_nombre": periodo.nombre if periodo else "",
        **_datos_caratula(periodo),
        "fecha_consejo": str(consejo.fecha_consejo) if consejo else "",
        "fecha_informe": str(datetime.now(timezone.utc).date()),
        "area_nombre": area.nombre if area else "",
        "jefe_nombre": jefe.nombre_completo if jefe else "",
        "jefe_titulo": (jefe.titulo or "") if jefe else "",
        # Copia de solo lectura de lo que escribió la dirección
        "secciones_direccion": dict(direccion.secciones or {}),
        # Aporte propio del jefe de área
        "secciones": secciones_jefe,
        "nombre_director": direccion.nombre_director or "",
    }
    flag_modified(informe, "contenido_json")
    informe.estado = informe.estado or "BORRADOR"
    db.commit()
    logger.info(
        f"Informe 1 — consejo {consejo_id}, área {area_id} "
        f"({area.nombre if area else '?'}), jefe: {jefe.nombre_completo if jefe else 'sin jefe'}"
    )
    return informe


# ──────────────────────────────────────────────────────────────────
# Informe 2 — Revisión AVAC
# ──────────────────────────────────────────────────────────────────

def generar_informe_2(db: Session, consejo_id: int, area_id: int) -> Informe:
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == consejo.periodo_id).first()
    area = db.query(Area).filter(Area.id == area_id).first()

    informe = _obtener_o_crear_informe(db, consejo_id, area_id, 2)

    checklists_raw = (
        db.query(ChecklistAVAC).filter(ChecklistAVAC.informe_id == informe.id).all()
    )

    campos_bool = [
        "silabo_cargado", "registro_avance", "guia_practicas",
        "consejeria_academica", "recursos_derechos_autor", "libros_digitales",
        "seccion_practicas", "guias_componente", "actividades_con_rubrica",
        "seccion_investigativas", "actividad_investigacion", "proyecto_integrador",
    ]

    checklists_data = []
    total_params = 0
    cumplidos = 0

    for c in checklists_raw:
        asig = db.query(Asignatura).filter(Asignatura.id == c.asignatura_id).first()
        datos = {
            "docente": _nombre_usuario(db, c.usuario_id),
            "asignatura": asig.nombre if asig else f"#{c.asignatura_id}",
            "grupo": c.grupo,
            "observaciones": c.observaciones or "",
            "acciones_mejora": c.acciones_mejora or "",
        }
        for campo in campos_bool:
            valor = getattr(c, campo)
            datos[campo] = valor
            total_params += 1
            if valor:
                cumplidos += 1
        checklists_data.append(datos)

    pct_cumplimiento = round(cumplidos / total_params * 100, 1) if total_params > 0 else 0

    analisis_area = (
        f"El área {area.nombre if area else ''} presenta un cumplimiento del "
        f"{pct_cumplimiento}% de los parámetros AVAC evaluados "
        f"({cumplidos} de {total_params} parámetros)."
    ) if checklists_data else "Checklists AVAC pendientes de completar."

    informe.contenido_json = {
        "periodo_nombre": periodo.nombre if periodo else "",
        "area_nombre": area.nombre if area else "",
        **_datos_caratula(periodo),
        **_datos_jefe(db, area_id, consejo.periodo_id),
        "checklists": checklists_data,
        "pct_cumplimiento": pct_cumplimiento,
        "analisis_area": analisis_area,
        "secciones": {},
    }
    informe.estado = "BORRADOR"
    db.commit()

    ruta = generar_docx(db, informe)
    logger.info(f"Informe 2 generado — {ruta}")
    return informe


# ──────────────────────────────────────────────────────────────────
# Informe 3 — Visitas Áulicas + Interciclo
# ──────────────────────────────────────────────────────────────────

def generar_informe_3(db: Session, consejo_id: int, area_id: int) -> Informe:
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == consejo.periodo_id).first()
    area = db.query(Area).filter(Area.id == area_id).first()

    informe = _obtener_o_crear_informe(db, consejo_id, area_id, 3)

    # Parte A: visitas áulicas
    visitas_raw = db.query(ChecklistVisitaAulica).filter(
        ChecklistVisitaAulica.informe_id == informe.id
    ).all()

    visitas_data = []
    for v in visitas_raw:
        asig = db.query(Asignatura).filter(Asignatura.id == v.asignatura_id).first()
        visitas_data.append({
            "docente": _nombre_usuario(db, v.usuario_id),
            "asignatura": asig.nombre if asig else f"#{v.asignatura_id}",
            "grupo": v.grupo,
            "visita_realizada": v.visita_realizada,
            "puntualidad_docente": v.puntualidad_docente,
            "cumplimiento_silabo": v.cumplimiento_silabo,
            "cumplimiento_practicas": v.cumplimiento_practicas,
            "actividades_con_rubrica": v.actividades_con_rubrica,
            "actividad_investigacion": v.actividad_investigacion,
            "observaciones_estudiantes": v.observaciones_estudiantes or "",
            "observaciones_docente": v.observaciones_docente or "",
            "acciones_docente": v.acciones_docente or "",
        })

    # Parte B: calificaciones interciclo
    asignaciones = _asignaturas_del_area(db, area_id, consejo.periodo_id)
    calificaciones_data = []
    vistos: set[tuple[int, str]] = set()  # evita duplicar (asignatura, grupo) co-dictados

    for asig_doc in asignaciones:
        clave = (asig_doc.asignatura_id, asig_doc.grupo)
        if clave in vistos:
            continue
        vistos.add(clave)

        cal = db.query(Calificacion).filter(
            Calificacion.asignatura_id == asig_doc.asignatura_id,
            Calificacion.consejo_id == consejo_id,
            Calificacion.tipo == "INTERCICLO",
            Calificacion.grupo == asig_doc.grupo,
        ).first()
        if not cal:
            continue

        asig = db.query(Asignatura).filter(Asignatura.id == asig_doc.asignatura_id).first()
        estudiantes = cal.datos_json.get("estudiantes", [])
        stats = ia_engine.calcular_estadisticos_interciclo(estudiantes)

        analisis = ia_engine.analizar_calificaciones_interciclo(
            asignatura=asig.nombre if asig else f"#{asig_doc.asignatura_id}",
            grupo=cal.datos_json.get("grupo", asig_doc.grupo),
            docente=_nombre_usuario(db, asig_doc.usuario_id),
            estadisticos=stats,
            estudiantes=estudiantes,
        )

        calificaciones_data.append({
            "asignatura": asig.nombre if asig else f"#{asig_doc.asignatura_id}",
            "grupo": cal.datos_json.get("grupo", asig_doc.grupo),
            "docente": _nombre_usuario(db, asig_doc.usuario_id),
            # Aportes sumativos que el docente registró sobre esta materia
            **_aportes_materia(db, consejo_id, asig_doc.asignatura_id, asig_doc.grupo),
            **analisis,
        })

    informe.contenido_json = {
        "periodo_nombre": periodo.nombre if periodo else "",
        "area_nombre": area.nombre if area else "",
        **_datos_caratula(periodo),
        **_datos_jefe(db, area_id, consejo.periodo_id),
        "visitas": visitas_data,
        "calificaciones_interciclo": calificaciones_data,
        "secciones": {},
    }
    informe.estado = "BORRADOR"
    db.commit()

    ruta = generar_docx(db, informe)
    logger.info(f"Informe 3 generado — {ruta}")
    return informe


# ──────────────────────────────────────────────────────────────────
# Informe 4 — Análisis Final
# ──────────────────────────────────────────────────────────────────

def generar_informe_4(db: Session, consejo_id: int, area_id: int) -> Informe:
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == consejo.periodo_id).first()
    area = db.query(Area).filter(Area.id == area_id).first()

    informe = _obtener_o_crear_informe(db, consejo_id, area_id, 4)

    asignaciones = _asignaturas_del_area(db, area_id, consejo.periodo_id)
    calificaciones_data = []
    resumen_area = []
    vistos: set[tuple[int, str]] = set()  # evita duplicar (asignatura, grupo) co-dictados

    for asig_doc in asignaciones:
        clave = (asig_doc.asignatura_id, asig_doc.grupo)
        if clave in vistos:
            continue
        vistos.add(clave)

        cal = db.query(Calificacion).filter(
            Calificacion.asignatura_id == asig_doc.asignatura_id,
            Calificacion.consejo_id == consejo_id,
            Calificacion.tipo == "FINAL",
            Calificacion.grupo == asig_doc.grupo,
        ).first()
        if not cal:
            continue

        asig = db.query(Asignatura).filter(Asignatura.id == asig_doc.asignatura_id).first()
        estudiantes = cal.datos_json.get("estudiantes", [])
        stats = ia_engine.calcular_estadisticos_finales(estudiantes)
        respuesta_doc = _respuesta_docente(db, asig_doc.usuario_id, consejo_id)

        analisis = ia_engine.analizar_calificaciones_finales(
            asignatura=asig.nombre if asig else f"#{asig_doc.asignatura_id}",
            grupo=cal.datos_json.get("grupo", asig_doc.grupo),
            docente=_nombre_usuario(db, asig_doc.usuario_id),
            estadisticos=stats,
            estudiantes=estudiantes,
            respuesta_docente=respuesta_doc,
        )

        nombre_asig = asig.nombre if asig else f"#{asig_doc.asignatura_id}"
        grupo = cal.datos_json.get("grupo", asig_doc.grupo)

        # Aportes sumativos del docente sobre la materia (observaciones + acciones)
        aportes = _aportes_materia(db, consejo_id, asig_doc.asignatura_id, asig_doc.grupo)

        calificaciones_data.append({
            "asignatura": nombre_asig,
            "grupo": grupo,
            "docente": _nombre_usuario(db, asig_doc.usuario_id),
            **aportes,
            **analisis,
        })

        resumen_area.append({
            "asignatura": nombre_asig,
            "grupo": grupo,
            "pct_aprobacion": stats.get("pct_aprobacion", 0),
            "promedio_nf": stats.get("nota_final", {}).get("promedio", "—"),
        })

    # Análisis consolidado del área
    consolidado = ia_engine.analizar_consolidado_area(
        area=area.nombre if area else f"Área #{area_id}",
        resumen_por_asignatura=resumen_area,
    ) if resumen_area else {
        "analisis_consolidado_area": "Sin calificaciones finales registradas.",
        "acciones_generales_area": "",
    }

    informe.contenido_json = {
        "periodo_nombre": periodo.nombre if periodo else "",
        "area_nombre": area.nombre if area else "",
        **_datos_caratula(periodo),
        **_datos_jefe(db, area_id, consejo.periodo_id),
        "calificaciones_finales": calificaciones_data,
        **consolidado,
        "secciones": {},
    }
    informe.estado = "BORRADOR"
    db.commit()

    ruta = generar_docx(db, informe)
    logger.info(f"Informe 4 generado — {ruta}")
    return informe
