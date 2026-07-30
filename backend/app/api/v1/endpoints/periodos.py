from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.periodo import PeriodoAcademico
from app.models.usuario import Usuario
from app.schemas.periodo import PeriodoCreate, PeriodoUpdate, PeriodoOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA", "DOCENTE")  # lectura compartida


@router.get("/", response_model=dict)
def listar_periodos(
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    q = db.query(PeriodoAcademico)
    if activo is not None:
        q = q.filter(PeriodoAcademico.activo == activo)
    periodos = q.order_by(PeriodoAcademico.fecha_inicio.desc()).all()
    return {
        "data": [PeriodoOut.model_validate(p) for p in periodos],
        "message": "OK",
        "success": True,
    }


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_periodo(
    payload: PeriodoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    # Solo puede haber un período activo a la vez
    if payload.activo:
        db.query(PeriodoAcademico).filter(PeriodoAcademico.activo == True).update(
            {"activo": False}
        )

    periodo = PeriodoAcademico(**payload.model_dump())
    db.add(periodo)
    db.commit()
    db.refresh(periodo)
    return {"data": PeriodoOut.model_validate(periodo), "message": "Período creado", "success": True}


@router.get("/activo", response_model=dict)
def obtener_periodo_activo(
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),  # lectura compartida, igual que GET /periodos/
):
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.activo == True).first()
    if not periodo:
        return {"data": None, "message": "No hay período activo", "success": True}
    return {"data": PeriodoOut.model_validate(periodo), "message": "OK", "success": True}


@router.get("/{periodo_id}", response_model=dict)
def obtener_periodo(
    periodo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == periodo_id).first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    return {"data": PeriodoOut.model_validate(periodo), "message": "OK", "success": True}


@router.put("/{periodo_id}", response_model=dict)
def actualizar_periodo(
    periodo_id: int,
    payload: PeriodoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == periodo_id).first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período no encontrado")

    # Si se activa este, desactivar los demás
    if payload.activo is True:
        db.query(PeriodoAcademico).filter(
            PeriodoAcademico.id != periodo_id,
            PeriodoAcademico.activo == True,
        ).update({"activo": False})

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(periodo, campo, valor)

    db.commit()
    db.refresh(periodo)
    return {"data": PeriodoOut.model_validate(periodo), "message": "Período actualizado", "success": True}


@router.delete("/{periodo_id}", response_model=dict)
def eliminar_periodo(
    periodo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.id == periodo_id).first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período no encontrado")

    if periodo.consejos:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un período que tiene Consejos de Carrera asociados",
        )

    db.delete(periodo)
    db.commit()
    return {"data": None, "message": "Período eliminado", "success": True}
