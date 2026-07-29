from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.asignatura import Asignatura
from app.models.area import Area
from app.models.usuario import Usuario
from app.schemas.asignatura import AsignaturaCreate, AsignaturaUpdate, AsignaturaOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")  # lectura compartida


@router.get("/", response_model=dict)
def listar_asignaturas(
    area_id: Optional[int] = Query(None),
    incluir_inactivas: bool = Query(False),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    """
    Materias del catálogo. Por defecto solo las **activas** (las que sirven para
    asignar en el período nuevo). Con `incluir_inactivas=true` se ven todas —
    útil para gestionarlas o reactivarlas.
    """
    q = db.query(Asignatura)
    if area_id is not None:
        q = q.filter(Asignatura.area_id == area_id)
    if not incluir_inactivas:
        q = q.filter(Asignatura.activa.is_(True))
    asignaturas = q.order_by(Asignatura.nombre).all()
    return {"data": [AsignaturaOut.model_validate(a) for a in asignaturas], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_asignatura(
    payload: AsignaturaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    if not db.query(Area).filter(Area.id == payload.area_id).first():
        raise HTTPException(status_code=404, detail="Área no encontrada")

    if db.query(Asignatura).filter(Asignatura.codigo == payload.codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe una asignatura con ese código")

    asignatura = Asignatura(**payload.model_dump())
    db.add(asignatura)
    db.commit()
    db.refresh(asignatura)
    return {"data": AsignaturaOut.model_validate(asignatura), "message": "Asignatura creada", "success": True}


@router.put("/{asig_id}", response_model=dict)
def actualizar_asignatura(
    asig_id: int,
    payload: AsignaturaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    asignatura = db.query(Asignatura).filter(Asignatura.id == asig_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")

    if payload.area_id and not db.query(Area).filter(Area.id == payload.area_id).first():
        raise HTTPException(status_code=404, detail="Área no encontrada")

    if payload.codigo:
        dup = db.query(Asignatura).filter(
            Asignatura.codigo == payload.codigo, Asignatura.id != asig_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail="Código ya está en uso")

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(asignatura, campo, valor)

    db.commit()
    db.refresh(asignatura)
    return {"data": AsignaturaOut.model_validate(asignatura), "message": "Asignatura actualizada", "success": True}


@router.delete("/{asig_id}", response_model=dict)
def eliminar_asignatura(
    asig_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """
    "Elimina" la materia. Si nunca tuvo asignaciones (en ningún período) se borra
    de verdad; si ya tiene histórico, se **desactiva** (soft-delete) para no
    romperlo: desaparece del catálogo activo pero sigue visible en el histórico.
    """
    asignatura = db.query(Asignatura).filter(Asignatura.id == asig_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")

    if asignatura.asignaciones:
        asignatura.activa = False
        db.commit()
        return {
            "data": None,
            "message": "La materia tiene histórico: se desactivó (ya no aparece para asignar, pero se conserva en los períodos anteriores)",
            "success": True,
        }

    db.delete(asignatura)
    db.commit()
    return {"data": None, "message": "Asignatura eliminada", "success": True}


@router.put("/{asig_id}/activa", response_model=dict)
def cambiar_estado_asignatura(
    asig_id: int,
    activa: bool = Query(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Activa o desactiva una materia (para sacarla del catálogo o reincorporarla)."""
    asignatura = db.query(Asignatura).filter(Asignatura.id == asig_id).first()
    if not asignatura:
        raise HTTPException(status_code=404, detail="Asignatura no encontrada")
    asignatura.activa = activa
    db.commit()
    db.refresh(asignatura)
    estado = "activada" if activa else "desactivada"
    return {"data": AsignaturaOut.model_validate(asignatura), "message": f"Materia {estado}", "success": True}
