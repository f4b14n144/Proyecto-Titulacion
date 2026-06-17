from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.deps import get_db, require_role, get_current_user
from app.models.asignacion import AsignacionDocente
from app.models.usuario import Usuario
from app.models.asignatura import Asignatura
from app.models.periodo import PeriodoAcademico
from app.schemas.asignacion import AsignacionCreate, AsignacionOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")  # lectura compartida


@router.get("/mias", response_model=dict)
def mis_asignaciones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Asignaciones del docente autenticado (asignatura + grupo + período)."""
    rows = (
        db.query(AsignacionDocente, Asignatura, PeriodoAcademico)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .join(PeriodoAcademico, AsignacionDocente.periodo_id == PeriodoAcademico.id)
        .filter(AsignacionDocente.usuario_id == current_user.id)
        .all()
    )
    data = [
        {
            "id": asig.id,
            "asignatura": asignatura.nombre,
            "codigo": asignatura.codigo,
            "grupo": asig.grupo,
            "periodo": periodo.nombre,
            "periodo_activo": periodo.activo,
        }
        for asig, asignatura, periodo in rows
    ]
    return {"data": data, "message": f"{len(data)} asignación(es)", "success": True}


@router.get("/", response_model=dict)
def listar_asignaciones(
    periodo_id: Optional[int] = Query(None),
    area_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    from app.models.jefatura import JefaturaArea

    q = db.query(AsignacionDocente)
    if periodo_id:
        q = q.filter(AsignacionDocente.periodo_id == periodo_id)

    # Si es JEFE_AREA, solo puede ver asignaciones de SU(S) área(s) — se impone en backend
    if current_user.rol.nombre == "JEFE_AREA":
        jq = db.query(JefaturaArea.area_id).filter(JefaturaArea.usuario_id == current_user.id)
        if periodo_id:
            jq = jq.filter(JefaturaArea.periodo_id == periodo_id)
        areas_jefe = [a_id for (a_id,) in jq.all()]
        if not areas_jefe:
            return {"data": [], "message": "Sin jefatura en el período", "success": True}
        q = q.join(Asignatura).filter(Asignatura.area_id.in_(areas_jefe))
    elif area_id:
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
