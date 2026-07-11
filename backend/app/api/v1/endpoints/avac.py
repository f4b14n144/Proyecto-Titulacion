"""
Checklist AVAC del Informe 2 (revisión del aula virtual).

El jefe de área marca los 12 parámetros por asignatura-grupo. Estos datos son la
**fuente de verdad** del Informe 2: `generar_informe_2` los lee para armar el
documento y para que la IA proponga las acciones de mejora.

Antes la pantalla guardaba el checklist como un JSON suelto dentro de
`contenido_json.secciones`, que nadie leía: la IA no veía nada y al volver a entrar
el checklist aparecía vacío. Ahora se persiste en la tabla `ChecklistAVAC`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.checklist_avac import ChecklistAVAC
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


def _informe2(db: Session, consejo_id: int, area_id: int, crear: bool) -> Optional[Informe]:
    """El Informe 2 del área en ese consejo. Hay uno solo por (consejo, área)."""
    informe = db.query(Informe).filter(
        Informe.consejo_id == consejo_id,
        Informe.area_id == area_id,
        Informe.tipo_informe == 2,
    ).first()
    if informe or not crear:
        return informe

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    # Se crea vacío (sin llamar a la IA): guardar el checklist debe ser inmediato.
    informe = Informe(
        consejo_id=consejo_id, area_id=area_id, tipo_informe=2,
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

    informe = _informe2(db, consejo_id, area_id, crear=False)
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

    informe = _informe2(db, payload.consejo_id, payload.area_id, crear=True)

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
