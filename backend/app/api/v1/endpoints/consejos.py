from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
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
