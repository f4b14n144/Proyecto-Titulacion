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
from app.models.respuesta_docente import RespuestaDocente
from app.core.scheduler import programar_flujo_consejo
from app.services.flujo_consejo import ejecutar_flujo
from datetime import datetime, timezone

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")


class RespuestaSimuladaIn(BaseModel):
    reply_to_token: str
    contenido: str


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
                "reply_to_token": n.reply_to_token,
                "respondido": n.respondido,
            }
            for n in notis
        ],
        "message": f"{len(notis)} notificación(es)",
        "success": True,
    }


@router.post("/simular-respuesta", response_model=dict)
def simular_respuesta_docente(
    payload: RespuestaSimuladaIn,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """
    Simula la recepción de una respuesta de docente (lo que haría el polling IMAP).
    Correlaciona por reply_to_token, guarda la RespuestaDocente y marca respondido=True.
    Solo para desarrollo/testing.
    """
    noti = db.query(Notificacion).filter(
        Notificacion.reply_to_token == payload.reply_to_token
    ).first()
    if not noti:
        raise HTTPException(status_code=404, detail="Token de notificación no encontrado")
    if noti.respondido:
        raise HTTPException(status_code=400, detail="Esta notificación ya fue respondida")

    respuesta = RespuestaDocente(
        notificacion_id=noti.id,
        contenido=payload.contenido.strip(),
    )
    db.add(respuesta)
    noti.respondido = True
    db.commit()
    db.refresh(respuesta)

    return {
        "data": {
            "respuesta_id": respuesta.id,
            "notificacion_id": noti.id,
            "destinatario": noti.destinatario_email,
        },
        "message": "Respuesta de docente registrada (simulada)",
        "success": True,
    }
