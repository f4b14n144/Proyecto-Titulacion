"""
Observaciones del docente sobre sus materias (van al Informe 4).
El docente crea/edita desde su panel; se correlacionan por consejo+asignatura+grupo.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user, require_role
from app.models.usuario import Usuario
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.periodo import PeriodoAcademico
from app.models.consejo import ConsejoCarrera
from app.models.observacion_docente import ObservacionDocente

router = APIRouter()


class ObservacionIn(BaseModel):
    consejo_id: int
    asignatura_id: int
    grupo: str
    contenido: str


@router.get("/mis-materias", response_model=dict)
def mis_materias_para_observar(
    consejo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Materias del docente en el período del consejo + su observación (si existe)."""
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    rows = (
        db.query(AsignacionDocente, Asignatura)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(
            AsignacionDocente.periodo_id == consejo.periodo_id,
            AsignacionDocente.usuario_id == current_user.id,
        )
        .all()
    )

    data = []
    for asig, asignatura in rows:
        obs = db.query(ObservacionDocente).filter(
            ObservacionDocente.consejo_id == consejo_id,
            ObservacionDocente.usuario_id == current_user.id,
            ObservacionDocente.asignatura_id == asignatura.id,
            ObservacionDocente.grupo == asig.grupo,
        ).first()
        data.append({
            "asignatura_id": asignatura.id,
            "asignatura": asignatura.nombre,
            "codigo": asignatura.codigo,
            "grupo": asig.grupo,
            "contenido": obs.contenido if obs else "",
        })

    return {"data": data, "message": f"{len(data)} materia(s)", "success": True}


@router.post("/", response_model=dict)
def guardar_observacion(
    payload: ObservacionIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Crea o actualiza (upsert) la observación del docente para su materia-grupo."""
    # Validar que la materia-grupo es del docente en el período del consejo
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == payload.consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    es_mia = db.query(AsignacionDocente).filter(
        AsignacionDocente.usuario_id == current_user.id,
        AsignacionDocente.asignatura_id == payload.asignatura_id,
        AsignacionDocente.grupo == payload.grupo,
        AsignacionDocente.periodo_id == consejo.periodo_id,
    ).first()
    if not es_mia:
        raise HTTPException(status_code=403, detail="Solo puedes observar tus propias materias")

    obs = db.query(ObservacionDocente).filter(
        ObservacionDocente.consejo_id == payload.consejo_id,
        ObservacionDocente.usuario_id == current_user.id,
        ObservacionDocente.asignatura_id == payload.asignatura_id,
        ObservacionDocente.grupo == payload.grupo,
    ).first()

    if obs:
        obs.contenido = payload.contenido
    else:
        obs = ObservacionDocente(
            consejo_id=payload.consejo_id,
            usuario_id=current_user.id,
            asignatura_id=payload.asignatura_id,
            grupo=payload.grupo,
            contenido=payload.contenido,
        )
        db.add(obs)
    db.commit()

    return {"data": {"id": obs.id}, "message": "Observación guardada", "success": True}
