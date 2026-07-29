from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.deps import get_db, require_role, get_current_user
from app.models.asignacion import AsignacionDocente
from app.models.jefatura import JefaturaArea
from app.models.usuario import Usuario
from app.models.asignatura import Asignatura
from app.models.periodo import PeriodoAcademico
from app.schemas.asignacion import AsignacionCreate, AsignacionOut

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")  # lectura compartida


class CopiarPeriodoIn(BaseModel):
    periodo_origen: int
    periodo_destino: int


@router.post("/copiar-periodo", response_model=dict)
def copiar_periodo(
    payload: CopiarPeriodoIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """
    Copia las asignaciones docente-materia-grupo y las jefaturas de área de un
    período a otro. Reutiliza la configuración del período anterior sin rehacerla.

    - No duplica lo que el destino ya tenga (se salta).
    - Solo copia asignaciones de materias **activas** (una materia desactivada no
      vuelve al catálogo del período nuevo).
    """
    if payload.periodo_origen == payload.periodo_destino:
        raise HTTPException(status_code=400, detail="El período de origen y destino no pueden ser el mismo")
    for pid in (payload.periodo_origen, payload.periodo_destino):
        if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == pid).first():
            raise HTTPException(status_code=404, detail=f"Período {pid} no encontrado")

    # ── Asignaciones docente-materia-grupo (solo de materias activas) ──
    asig_origen = (
        db.query(AsignacionDocente)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(AsignacionDocente.periodo_id == payload.periodo_origen, Asignatura.activa.is_(True))
        .all()
    )
    existentes_asig = {
        (a.usuario_id, a.asignatura_id, a.grupo)
        for a in db.query(AsignacionDocente).filter(AsignacionDocente.periodo_id == payload.periodo_destino)
    }
    copiadas_asig = 0
    for a in asig_origen:
        if (a.usuario_id, a.asignatura_id, a.grupo) in existentes_asig:
            continue
        db.add(AsignacionDocente(
            usuario_id=a.usuario_id, asignatura_id=a.asignatura_id,
            periodo_id=payload.periodo_destino, grupo=a.grupo,
        ))
        copiadas_asig += 1

    # ── Jefaturas de área ──
    jef_origen = db.query(JefaturaArea).filter(JefaturaArea.periodo_id == payload.periodo_origen).all()
    existentes_jef = {
        (j.usuario_id, j.area_id)
        for j in db.query(JefaturaArea).filter(JefaturaArea.periodo_id == payload.periodo_destino)
    }
    # También respetar que un docente no dirija dos áreas en el destino
    usuarios_con_jefatura_destino = {
        j.usuario_id
        for j in db.query(JefaturaArea).filter(JefaturaArea.periodo_id == payload.periodo_destino)
    }
    copiadas_jef = 0
    for j in jef_origen:
        if (j.usuario_id, j.area_id) in existentes_jef:
            continue
        if j.usuario_id in usuarios_con_jefatura_destino:
            continue  # ya es jefe de otra área en el destino
        db.add(JefaturaArea(
            usuario_id=j.usuario_id, area_id=j.area_id, periodo_id=payload.periodo_destino,
        ))
        usuarios_con_jefatura_destino.add(j.usuario_id)
        copiadas_jef += 1

    db.commit()
    return {
        "data": {"asignaciones": copiadas_asig, "jefaturas": copiadas_jef},
        "message": f"Copiado del período anterior: {copiadas_asig} asignación(es) y {copiadas_jef} jefatura(s)",
        "success": True,
    }


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
    if getattr(current_user, "rol_efectivo", current_user.rol.nombre) == "JEFE_AREA":
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
