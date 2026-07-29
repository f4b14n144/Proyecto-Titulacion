from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.area import Area
from app.models.asignatura import Asignatura
from app.models.usuario import Usuario
from app.schemas.area import AreaCreate, AreaUpdate, AreaOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
# La lista de áreas es de lectura compartida: el jefe la usa en sus pantallas
# de informes. Crear/editar/borrar siguen siendo solo de la dirección.
_lectura_compartida = require_role("DIRECTOR_CARRERA", "JEFE_AREA")


@router.get("/", response_model=dict)
def listar_areas(
    incluir_inactivas: bool = Query(False),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_lectura_compartida),
):
    """Áreas del catálogo. Por defecto solo las activas; `incluir_inactivas=true`
    trae también las desactivadas (para gestionarlas o ver el histórico)."""
    q = db.query(Area)
    if not incluir_inactivas:
        q = q.filter(Area.activa.is_(True))
    areas = q.order_by(Area.nombre).all()
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
    """
    "Elimina" un área. Si tiene histórico (asignaturas, informes o jefaturas) se
    **desactiva** para no romperlo — antes se intentaba borrar y la llave foránea
    de los informes daba error 500. Si nunca se usó, se borra de verdad.
    """
    from app.models.informe import Informe
    from app.models.jefatura import JefaturaArea

    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")

    tiene_asignaturas = db.query(Asignatura).filter(Asignatura.area_id == area_id).count() > 0
    tiene_informes = db.query(Informe).filter(Informe.area_id == area_id).count() > 0
    tiene_jefaturas = db.query(JefaturaArea).filter(JefaturaArea.area_id == area_id).count() > 0

    if tiene_asignaturas or tiene_informes or tiene_jefaturas:
        area.activa = False
        db.commit()
        return {
            "data": None,
            "message": "El área tiene datos asociados: se desactivó (sale del catálogo pero se conserva en el histórico)",
            "success": True,
        }

    db.delete(area)
    db.commit()
    return {"data": None, "message": "Área eliminada", "success": True}


@router.put("/{area_id}/activa", response_model=dict)
def cambiar_estado_area(
    area_id: int,
    activa: bool = Query(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Activa o desactiva un área (sacarla del catálogo o reincorporarla)."""
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Área no encontrada")
    area.activa = activa
    db.commit()
    db.refresh(area)
    return {"data": AreaOut.model_validate(area), "message": f"Área {'activada' if activa else 'desactivada'}", "success": True}
