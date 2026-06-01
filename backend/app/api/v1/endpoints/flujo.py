"""
Endpoint de control del flujo automático (solo para desarrollo y testing).
Permite disparar el flujo de un consejo manualmente sin esperar la fecha.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.consejo import ConsejoCarrera
from app.models.usuario import Usuario
from app.core.scheduler import programar_flujo_consejo
from app.services.flujo_consejo import ejecutar_flujo
from datetime import datetime, timezone

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")


@router.post("/{consejo_id}/disparar", response_model=dict)
def disparar_flujo_manual(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Dispara el flujo de un consejo inmediatamente (sin esperar la fecha). Solo desarrollo."""
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")
    if consejo.flujo_estado == "COMPLETADO":
        raise HTTPException(status_code=400, detail="El consejo ya está COMPLETADO")

    ejecutar_flujo(db, consejo)
    db.refresh(consejo)
    return {
        "data": {"consejo_id": consejo_id, "estado": consejo.flujo_estado},
        "message": "Flujo ejecutado manualmente",
        "success": True,
    }


@router.post("/{consejo_id}/reprogramar", response_model=dict)
def reprogramar_consejo(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Reprograma el job del scheduler para un consejo (útil tras editar la fecha)."""
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    if consejo.fecha_limite_informe:
        fecha_dt = datetime.combine(
            consejo.fecha_limite_informe, datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        programar_flujo_consejo(consejo_id, fecha_dt)

    return {
        "data": {"consejo_id": consejo_id},
        "message": "Job reprogramado en el scheduler",
        "success": True,
    }
