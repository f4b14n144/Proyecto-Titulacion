"""
Checklists que llena el jefe de área:
  - Informe 2: revisión del aula virtual (AVAC), 12 parámetros por asignatura-grupo
  - Informe 3: visita áulica, 6 parámetros + observaciones por asignatura-grupo

Estos datos son la **fuente de verdad** de sus informes: `generar_informe_2` y
`generar_informe_3` los leen de las tablas `ChecklistAVAC` y `ChecklistVisitaAulica`.

Antes las pantallas guardaban los checklists como un JSON suelto dentro de
`contenido_json.secciones` (`checklists_json`, `visitas_json`), que **nadie leía**:
la IA no veía nada y, al salir y volver a entrar, todo aparecía en blanco. Ahora se
persisten en sus tablas.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.checklist_avac import ChecklistAVAC
from app.models.checklist_visita import ChecklistVisitaAulica
from app.models.consejo import ConsejoCarrera
from app.models.informe import Informe
from app.models.usuario import Usuario

router = APIRouter()

_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")

CAMPOS_BOOL = [
    "silabo_cargado", "registro_avance", "guia_practicas",
    "consejeria_academica", "recursos_derechos_autor", "libros_digitales",
    "seccion_practicas", "guias_componente", "actividades_con_rubrica",
    "seccion_investigativas", "actividad_investigacion", "proyecto_integrador",
]


class ItemChecklist(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    asignatura_id: int
    grupo: str

    silabo_cargado: bool = False
    registro_avance: bool = False
    guia_practicas: bool = False
    consejeria_academica: bool = False
    recursos_derechos_autor: bool = False
    libros_digitales: bool = False
    seccion_practicas: bool = False
    guias_componente: bool = False
    actividades_con_rubrica: bool = False
    seccion_investigativas: bool = False
    actividad_investigacion: bool = False
    proyecto_integrador: bool = False

    observaciones: Optional[str] = ""
    # Lo que escribe el jefe. Las que sugiere la IA van aparte, en el informe.
    acciones_mejora: Optional[str] = ""


class GuardarChecklistIn(BaseModel):
    consejo_id: int
    area_id: int
    items: list[ItemChecklist]


def _validar_area(db: Session, usuario: Usuario, area_id: int) -> None:
    """El jefe solo puede tocar el checklist de SU área."""
    rol = getattr(usuario, "rol_efectivo", usuario.rol.nombre)
    if rol == "DIRECTOR_CARRERA":
        return
    from app.models.jefatura import JefaturaArea
    suya = db.query(JefaturaArea).filter(
        JefaturaArea.usuario_id == usuario.id,
        JefaturaArea.area_id == area_id,
    ).first()
    if not suya:
        raise HTTPException(status_code=403, detail="Solo puedes editar el checklist de tu área")


def _informe(
    db: Session, consejo_id: int, area_id: int, tipo: int, crear: bool
) -> Optional[Informe]:
    """El informe del área en ese consejo. Hay uno solo por (consejo, área, tipo)."""
    informe = db.query(Informe).filter(
        Informe.consejo_id == consejo_id,
        Informe.area_id == area_id,
        Informe.tipo_informe == tipo,
    ).first()
    if informe or not crear:
        return informe

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    # Se crea vacío (sin llamar a la IA): guardar el checklist debe ser inmediato.
    informe = Informe(
        consejo_id=consejo_id, area_id=area_id, tipo_informe=tipo,
        estado="BORRADOR", version=1,
    )
    db.add(informe)
    db.flush()
    return informe


@router.get("/checklist", response_model=dict)
def obtener_checklist(
    consejo_id: int = Query(...),
    area_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """
    Checklist guardado del Informe 2. Al volver a entrar, la pantalla se rellena
    con esto (antes siempre aparecía vacío).
    """
    _validar_area(db, current_user, area_id)

    informe = _informe(db, consejo_id, area_id, 2, crear=False)
    if informe is None:
        return {"data": {"informe_id": None, "items": []}, "message": "Sin checklist", "success": True}

    # Orden determinista: sin esto, el cliente no puede confiar en la posición.
    filas = (
        db.query(ChecklistAVAC)
        .filter(ChecklistAVAC.informe_id == informe.id)
        .order_by(ChecklistAVAC.asignatura_id, ChecklistAVAC.grupo)
        .all()
    )
    return {
        "data": {
            "informe_id": informe.id,
            "items": [ItemChecklist.model_validate(f) for f in filas],
        },
        "message": f"{len(filas)} asignatura(s) con checklist",
        "success": True,
    }


@router.put("/checklist", response_model=dict)
def guardar_checklist(
    payload: GuardarChecklistIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """
    Guarda el checklist. Es un *upsert* por (informe, asignatura, grupo): se puede
    volver a entrar y seguir modificando sobre lo ya marcado.
    """
    _validar_area(db, current_user, payload.area_id)

    informe = _informe(db, payload.consejo_id, payload.area_id, 2, crear=True)

    existentes = {
        (f.asignatura_id, f.grupo): f
        for f in db.query(ChecklistAVAC).filter(ChecklistAVAC.informe_id == informe.id)
    }

    guardados = 0
    for item in payload.items:
        fila = existentes.get((item.asignatura_id, item.grupo))
        if fila is None:
            fila = ChecklistAVAC(
                informe_id=informe.id,
                usuario_id=item.usuario_id,
                asignatura_id=item.asignatura_id,
                grupo=item.grupo,
            )
            db.add(fila)
        for campo in CAMPOS_BOOL:
            setattr(fila, campo, getattr(item, campo))
        fila.observaciones = item.observaciones or ""
        fila.acciones_mejora = item.acciones_mejora or ""
        guardados += 1

    db.commit()
    return {
        "data": {"informe_id": informe.id, "guardados": guardados},
        "message": f"Checklist guardado ({guardados} asignaturas).",
        "success": True,
    }


# ──────────────────────────────────────────────────────────────────
# Informe 3 — Checklist de visitas áulicas
# ──────────────────────────────────────────────────────────────────

CAMPOS_VISITA = [
    "visita_realizada", "puntualidad_docente", "cumplimiento_silabo",
    "cumplimiento_practicas", "actividades_con_rubrica", "actividad_investigacion",
]


class ItemVisita(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    asignatura_id: int
    grupo: str

    visita_realizada: bool = False
    puntualidad_docente: bool = False
    cumplimiento_silabo: bool = False
    cumplimiento_practicas: bool = False
    actividades_con_rubrica: bool = False
    actividad_investigacion: bool = False

    observaciones_estudiantes: Optional[str] = ""
    observaciones_docente: Optional[str] = ""
    # Lo que el jefe de área le indica al docente tras la visita
    acciones_docente: Optional[str] = ""


class GuardarVisitasIn(BaseModel):
    consejo_id: int
    area_id: int
    items: list[ItemVisita]


@router.get("/visitas", response_model=dict)
def obtener_visitas(
    consejo_id: int = Query(...),
    area_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """Checklist de visitas áulicas guardado, para rellenar la pantalla al volver."""
    _validar_area(db, current_user, area_id)

    informe = _informe(db, consejo_id, area_id, 3, crear=False)
    if informe is None:
        return {"data": {"informe_id": None, "items": []}, "message": "Sin visitas", "success": True}

    filas = (
        db.query(ChecklistVisitaAulica)
        .filter(ChecklistVisitaAulica.informe_id == informe.id)
        .order_by(ChecklistVisitaAulica.asignatura_id, ChecklistVisitaAulica.grupo)
        .all()
    )
    return {
        "data": {
            "informe_id": informe.id,
            "items": [ItemVisita.model_validate(f) for f in filas],
        },
        "message": f"{len(filas)} visita(s) registrada(s)",
        "success": True,
    }


@router.put("/visitas", response_model=dict)
def guardar_visitas(
    payload: GuardarVisitasIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """Upsert por (informe, asignatura, grupo): se puede seguir editando al volver."""
    _validar_area(db, current_user, payload.area_id)

    informe = _informe(db, payload.consejo_id, payload.area_id, 3, crear=True)

    existentes = {
        (f.asignatura_id, f.grupo): f
        for f in db.query(ChecklistVisitaAulica).filter(
            ChecklistVisitaAulica.informe_id == informe.id
        )
    }

    guardados = 0
    for item in payload.items:
        fila = existentes.get((item.asignatura_id, item.grupo))
        if fila is None:
            fila = ChecklistVisitaAulica(
                informe_id=informe.id,
                usuario_id=item.usuario_id,
                asignatura_id=item.asignatura_id,
                grupo=item.grupo,
            )
            db.add(fila)
        for campo in CAMPOS_VISITA:
            setattr(fila, campo, getattr(item, campo))
        fila.observaciones_estudiantes = item.observaciones_estudiantes or ""
        fila.observaciones_docente = item.observaciones_docente or ""
        fila.acciones_docente = item.acciones_docente or ""
        guardados += 1

    db.commit()
    return {
        "data": {"informe_id": informe.id, "guardados": guardados},
        "message": f"Visitas guardadas ({guardados} asignaturas).",
        "success": True,
    }
