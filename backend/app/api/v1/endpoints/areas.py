from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.area import Area
from app.models.usuario import Usuario
from app.schemas.area import AreaCreate, AreaUpdate, AreaOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")


@router.get("/", response_model=dict)
def listar_areas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    areas = db.query(Area).order_by(Area.nombre).all()
    return {"data": [AreaOut.model_validate(a) for a in areas], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_area(
    payload: AreaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    if db.query(Area).filter(Area.nombre == payload.nombre).first():
        raise HTTPException(status_code=400, detail="Ya existe un área con ese nombre")

    area = Area(nombre=payload.nombre)
    db.add(area)
    db.commit()
    db.refresh(area)
    return {"data": AreaOut.model_validate(area), "message": "Área creada", "success": True}


@router.put("/{area_id}", response_model=dict)
def actualizar_area(
    area_id: int,
    payload: AreaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")

    duplicada = db.query(Area).filter(Area.nombre == payload.nombre, Area.id != area_id).first()
    if duplicada:
        raise HTTPException(status_code=400, detail="Ya existe un área con ese nombre")

    area.nombre = payload.nombre
    db.commit()
    db.refresh(area)
    return {"data": AreaOut.model_validate(area), "message": "Área actualizada", "success": True}


@router.delete("/{area_id}", response_model=dict)
def eliminar_area(
    area_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")

    if area.asignaturas:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un área con asignaturas asociadas",
        )

    db.delete(area)
    db.commit()
    return {"data": None, "message": "Área eliminada", "success": True}
