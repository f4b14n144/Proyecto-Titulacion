"""
Endpoint de control del flujo automático (solo para desarrollo y testing).
Permite disparar el flujo de un consejo manualmente sin esperar la fecha.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.consejo import ConsejoCarrera
from app.models.usuario import Usuario
from app.models.notificacion import Notificacion
from app.core.scheduler import programar_flujo_consejo
from app.services.flujo_consejo import ejecutar_flujo
from datetime import datetime, timezone

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")


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


@router.get("/{consejo_id}/notificaciones", response_model=dict)
def listar_notificaciones(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Lista las notificaciones generadas por el flujo de un consejo."""
    notis = db.query(Notificacion).filter(Notificacion.consejo_id == consejo_id).all()
    return {
        "data": [
            {
                "id": n.id,
                "destinatario_email": n.destinatario_email,
                "tipo": n.tipo,
                "enviado_en": str(n.enviado_en) if n.enviado_en else None,
            }
            for n in notis
        ],
        "message": f"{len(notis)} notificación(es)",
        "success": True,
    }


# El endpoint /simular-respuesta se eliminó junto con la recepción de correo por
# IMAP: el docente registra sus observaciones y acciones de mejora desde su panel
# (/aportes), que es la vía real y la que alimenta los informes.
#
# Los endpoints /notificar-estudiantes y /reporte-mejoras-estudiantes se
# eliminaron: fabricaban direcciones de correo inexistentes con la plantilla
#   estudiantes.{codigo}.{grupo}@est.ups.edu.ec
# y el envio iba dentro de un try/except que se tragaba el error, asi que la
# UI respondia "enviado" aunque no llegara a nadie.
#
# Los correos a estudiantes se envian desde /correos/estudiantes, que usa los
# destinatarios REALES cargados del Excel del periodo, aplica las plantillas de
# los anexos y tiene modo prueba.
