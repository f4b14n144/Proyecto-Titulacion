from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.core.deps import get_db, require_role
from app.models.consejo import ConsejoCarrera
from app.models.periodo import PeriodoAcademico
from app.models.usuario import Usuario
from app.schemas.consejo import ConsejoCreate, ConsejoUpdate, ConsejoOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA", "DOCENTE")  # lectura compartida


@router.get("/", response_model=dict)
def listar_consejos(
    periodo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    q = db.query(ConsejoCarrera)
    if periodo_id is not None:
        q = q.filter(ConsejoCarrera.periodo_id == periodo_id)
    consejos = q.order_by(ConsejoCarrera.fecha_consejo.desc()).all()
    return {"data": [ConsejoOut.model_validate(c) for c in consejos], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_consejo(
    payload: ConsejoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == payload.periodo_id).first():
        raise HTTPException(status_code=404, detail="Período no encontrado")

    consejo = ConsejoCarrera(**payload.model_dump())
    db.add(consejo)
    db.commit()
    db.refresh(consejo)
    return {"data": ConsejoOut.model_validate(consejo), "message": "Consejo creado", "success": True}


@router.get("/{consejo_id}", response_model=dict)
def obtener_consejo(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")
    return {"data": ConsejoOut.model_validate(consejo), "message": "OK", "success": True}


@router.put("/{consejo_id}", response_model=dict)
def actualizar_consejo(
    consejo_id: int,
    payload: ConsejoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    if consejo.flujo_estado == "COMPLETADO":
        raise HTTPException(status_code=400, detail="No se puede modificar un consejo completado")

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(consejo, campo, valor)

    db.commit()
    db.refresh(consejo)
    return {"data": ConsejoOut.model_validate(consejo), "message": "Consejo actualizado", "success": True}


@router.delete("/{consejo_id}", response_model=dict)
def eliminar_consejo(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    if consejo.flujo_estado != "PENDIENTE":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden eliminar consejos en estado PENDIENTE",
        )

    db.delete(consejo)
    db.commit()
    return {"data": None, "message": "Consejo eliminado", "success": True}


# ──────────────────────────────────────────────────────────────────
# Contenido del Informe 1 escrito por la DIRECCIÓN
# Es común al consejo y se propaga en solo lectura al Informe 1 de cada área.
# ──────────────────────────────────────────────────────────────────

class ContenidoDireccionUpdate(BaseModel):
    secciones: dict[str, str]
    nombre_director: Optional[str] = None


def _contenido_out(contenido) -> dict:
    return {
        "consejo_id": contenido.consejo_id,
        "secciones": contenido.secciones or {},
        "nombre_director": contenido.nombre_director or "",
    }


@router.get("/{consejo_id}/contenido-direccion", response_model=dict)
def obtener_contenido_direccion(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    """Lo lee la directora (para editar) y los jefes (en solo lectura)."""
    from app.services.generador_informes import obtener_o_crear_contenido_direccion

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    contenido = obtener_o_crear_contenido_direccion(db, consejo_id)
    return {"data": _contenido_out(contenido), "message": "OK", "success": True}


@router.put("/{consejo_id}/contenido-direccion", response_model=dict)
def actualizar_contenido_direccion(
    consejo_id: int,
    payload: ContenidoDireccionUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Solo la directora escribe aquí. Los jefes no pueden modificarlo."""
    from app.services.generador_informes import obtener_o_crear_contenido_direccion

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    contenido = obtener_o_crear_contenido_direccion(db, consejo_id)
    contenido.secciones = {**(contenido.secciones or {}), **payload.secciones}
    if payload.nombre_director is not None:
        contenido.nombre_director = payload.nombre_director
    flag_modified(contenido, "secciones")
    db.commit()
    return {
        "data": _contenido_out(contenido),
        "message": "Contenido de dirección actualizado",
        "success": True,
    }
