from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.deps import get_db, require_role
from app.models.asignacion import AsignacionDocente
from app.models.usuario import Usuario
from app.models.asignatura import Asignatura
from app.models.periodo import PeriodoAcademico
from app.schemas.asignacion import AsignacionCreate, AsignacionOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")


@router.get("/", response_model=dict)
def listar_asignaciones(
    periodo_id: Optional[int] = Query(None),
    area_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    q = db.query(AsignacionDocente)
    if periodo_id:
        q = q.filter(AsignacionDocente.periodo_id == periodo_id)
    if area_id:
        q = q.join(Asignatura).filter(Asignatura.area_id == area_id)
    asignaciones = q.all()
    return {"data": [AsignacionOut.model_validate(a) for a in asignaciones], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_asignacion(
    payload: AsignacionCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    if not db.query(Usuario).filter(Usuario.id == payload.usuario_id, Usuario.activo == True).first():
        raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo")
    if not db.query(Asignatura).filter(Asignatura.id == payload.asignatura_id).first():
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == payload.periodo_id).first():
        raise HTTPException(status_code=404, detail="Período no encontrado")

    asignacion = AsignacionDocente(**payload.model_dump())
    db.add(asignacion)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="El docente ya tiene esa asignatura y grupo en ese período",
        )
    db.refresh(asignacion)
    return {"data": AsignacionOut.model_validate(asignacion), "message": "Asignación creada", "success": True}


@router.delete("/{asignacion_id}", response_model=dict)
def eliminar_asignacion(
    asignacion_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    asignacion = db.query(AsignacionDocente).filter(AsignacionDocente.id == asignacion_id).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    db.delete(asignacion)
    db.commit()
    return {"data": None, "message": "Asignación eliminada", "success": True}
