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

# Un área puede tener hasta este número de jefes en un período (las áreas grandes
# necesitan dos). El límite se valida aquí, no con un UNIQUE en la base.
MAX_JEFES_POR_AREA = 2


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

    # El mismo docente no puede ser jefe dos veces de la misma área
    ya_es_jefe = db.query(JefaturaArea).filter(
        JefaturaArea.area_id == payload.area_id,
        JefaturaArea.periodo_id == payload.periodo_id,
        JefaturaArea.usuario_id == payload.usuario_id,
    ).first()
    if ya_es_jefe:
        raise HTTPException(status_code=400, detail="Ese docente ya es jefe de esta área")

    # Tope de jefes por área
    jefes_actuales = db.query(JefaturaArea).filter(
        JefaturaArea.area_id == payload.area_id,
        JefaturaArea.periodo_id == payload.periodo_id,
    ).count()
    if jefes_actuales >= MAX_JEFES_POR_AREA:
        raise HTTPException(
            status_code=400,
            detail=f"El área ya tiene {MAX_JEFES_POR_AREA} jefes en ese período (el máximo)",
        )

    jefatura = JefaturaArea(**payload.model_dump())
    db.add(jefatura)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Lo que queda es el UNIQUE (usuario_id, periodo_id): el docente ya dirige otra área
        raise HTTPException(
            status_code=400,
            detail="Ese docente ya es jefe de otra área en ese período",
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
