from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.deps import get_db, require_role
from app.models.jefatura import JefaturaArea
from app.models.usuario import Usuario
from app.models.area import Area
from app.models.periodo import PeriodoAcademico
from app.schemas.jefatura import JefaturaCreate, JefaturaOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")


@router.get("/", response_model=dict)
def listar_jefaturas(
    periodo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    q = db.query(JefaturaArea)
    if periodo_id:
        q = q.filter(JefaturaArea.periodo_id == periodo_id)
    jefaturas = q.all()
    return {"data": [JefaturaOut.model_validate(j) for j in jefaturas], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def asignar_jefatura(
    payload: JefaturaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    # Verificar que existen los recursos
    usuario = db.query(Usuario).filter(Usuario.id == payload.usuario_id, Usuario.activo == True).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo")
    if not db.query(Area).filter(Area.id == payload.area_id).first():
        raise HTTPException(status_code=404, detail="Área no encontrada")
    if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == payload.periodo_id).first():
        raise HTTPException(status_code=404, detail="Período no encontrado")

    jefatura = JefaturaArea(**payload.model_dump())
    db.add(jefatura)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="El área ya tiene jefe asignado en ese período, o el docente ya es jefe de otra área en ese período",
        )
    db.refresh(jefatura)
    return {"data": JefaturaOut.model_validate(jefatura), "message": "Jefatura asignada", "success": True}


@router.delete("/{jefatura_id}", response_model=dict)
def eliminar_jefatura(
    jefatura_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    jefatura = db.query(JefaturaArea).filter(JefaturaArea.id == jefatura_id).first()
    if not jefatura:
        raise HTTPException(status_code=404, detail="Jefatura no encontrada")
    db.delete(jefatura)
    db.commit()
    return {"data": None, "message": "Jefatura eliminada", "success": True}
