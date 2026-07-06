"""
Endpoint de control del flujo automático (solo para desarrollo y testing).
Permite disparar el flujo de un consejo manualmente sin esperar la fecha.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.consejo import ConsejoCarrera
from app.models.usuario import Usuario
from app.models.notificacion import Notificacion
from app.models.respuesta_docente import RespuestaDocente
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.jefatura import JefaturaArea
from app.core.scheduler import programar_flujo_consejo
from app.services.flujo_consejo import ejecutar_flujo
from app.models.informe import Informe
from app.models.area import Area
from app.services.mail_service import enviar_email_estudiantes, enviar_reporte_mejoras_estudiantes
from datetime import datetime, timezone

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")


class RespuestaSimuladaIn(BaseModel):
    reply_to_token: str
    contenido: str


class NotificarEstudiantesIn(BaseModel):
    consejo_id: int
    area_id: Optional[int] = None  # el jefe usa su área; el director puede especificar


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


@router.post("/notificar-estudiantes", response_model=dict)
def notificar_estudiantes(
    payload: NotificarEstudiantesIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """
    Notifica a los estudiantes de las materias del área para que, si tienen quejas
    u observaciones, se acerquen al Jefe de Área. Una notificación por cada
    materia-grupo (lista de distribución del grupo). Modo simulado si no hay SMTP.
    """
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == payload.consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    # Determinar áreas a notificar
    if current_user.rol.nombre == "JEFE_AREA":
        areas = [a_id for (a_id,) in db.query(JefaturaArea.area_id).filter(
            JefaturaArea.usuario_id == current_user.id,
            JefaturaArea.periodo_id == consejo.periodo_id,
        ).all()]
        if not areas:
            raise HTTPException(status_code=400, detail="No tienes jefatura en el período de este consejo")
    else:  # DIRECTOR_CARRERA
        if payload.area_id:
            areas = [payload.area_id]
        else:
            areas = [a_id for (a_id,) in db.query(Asignatura.area_id).distinct().all()]

    # Materias-grupo únicos del área en el período
    rows = (
        db.query(AsignacionDocente, Asignatura)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(
            AsignacionDocente.periodo_id == consejo.periodo_id,
            Asignatura.area_id.in_(areas),
        )
        .all()
    )

    grupos_vistos: set[tuple[int, str]] = set()
    notificados = []
    for asig, asignatura in rows:
        clave = (asignatura.id, asig.grupo)
        if clave in grupos_vistos:
            continue
        grupos_vistos.add(clave)

        # Email de lista del grupo (en producción sería la lista real de distribución)
        destino = f"estudiantes.{asignatura.codigo.lower().replace('-', '')}.{asig.grupo.lower()}@est.ups.edu.ec"
        noti = Notificacion(
            informe_id=None,
            consejo_id=consejo.id,
            destinatario_email=destino,
            tipo="ESTUDIANTE_REPORTE",
            reply_to_token=str(uuid.uuid4()),
        )
        db.add(noti)
        notificados.append({"asignatura": asignatura.nombre, "grupo": asig.grupo, "destino": destino})

    db.commit()

    # Envío (simulado si no hay SMTP configurado)
    try:
        enviar_email_estudiantes([n["destino"] for n in notificados], consejo.id)
    except Exception:
        pass

    return {
        "data": {"total": len(notificados), "notificaciones": notificados},
        "message": f"Se notificó a estudiantes de {len(notificados)} materia(s)-grupo para reportar al Jefe de Área",
        "success": True,
    }


def _areas_del_usuario(db: Session, current_user: Usuario, consejo: ConsejoCarrera, area_id: Optional[int]) -> list[int]:
    if current_user.rol.nombre == "JEFE_AREA":
        areas = [a for (a,) in db.query(JefaturaArea.area_id).filter(
            JefaturaArea.usuario_id == current_user.id,
            JefaturaArea.periodo_id == consejo.periodo_id,
        ).all()]
        if not areas:
            raise HTTPException(status_code=400, detail="No tienes jefatura en el período de este consejo")
        return areas
    return [area_id] if area_id else [a for (a,) in db.query(Asignatura.area_id).distinct().all()]


def _destinos_por_grupo(db: Session, areas: list[int], periodo_id: int) -> list[str]:
    rows = (
        db.query(AsignacionDocente, Asignatura)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(AsignacionDocente.periodo_id == periodo_id, Asignatura.area_id.in_(areas))
        .all()
    )
    vistos, destinos = set(), []
    for asig, asignatura in rows:
        clave = (asignatura.id, asig.grupo)
        if clave in vistos:
            continue
        vistos.add(clave)
        destinos.append(f"estudiantes.{asignatura.codigo.lower().replace('-', '')}.{asig.grupo.lower()}@est.ups.edu.ec")
    return destinos


@router.post("/reporte-mejoras-estudiantes", response_model=dict)
def reporte_mejoras_estudiantes(
    payload: NotificarEstudiantesIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """
    Envía a los estudiantes del área un REPORTE FINAL con las acciones de mejora,
    tomado del Informe 3 (análisis de calificaciones interciclo) ya generado.
    """
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == payload.consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    areas = _areas_del_usuario(db, current_user, consejo, payload.area_id)
    area_id = areas[0]
    area = db.query(Area).filter(Area.id == area_id).first()

    # Tomar el Informe 3 del área (debe estar generado)
    informe = db.query(Informe).filter(
        Informe.consejo_id == consejo.id,
        Informe.area_id == area_id,
        Informe.tipo_informe == 3,
    ).first()
    if not informe or not informe.contenido_json:
        raise HTTPException(
            status_code=400,
            detail="Primero genera el Informe 3 del área (Visitas + Interciclo) para tener el reporte de mejoras",
        )

    cals = informe.contenido_json.get("calificaciones_interciclo", [])
    if not cals:
        raise HTTPException(status_code=400, detail="El Informe 3 no tiene análisis de calificaciones para reportar")

    # Componer los bloques del reporte (por asignatura: resultado + acciones de mejora)
    bloques = []
    for c in cals:
        bloques.append(
            f"<h3 style='color:#003DA5;margin-bottom:2px'>{c.get('asignatura','')} — Grupo {c.get('grupo','')}</h3>"
            f"<p style='margin:2px 0'><strong>Resultado:</strong> {c.get('conclusion','')}</p>"
            f"<p style='margin:2px 0'><strong>Acciones de mejora:</strong><br>{str(c.get('acciones_mejora','')).replace(chr(10), '<br>')}</p>"
        )
    bloques_html = "".join(bloques)

    destinos = _destinos_por_grupo(db, areas, consejo.periodo_id)

    # Registrar notificaciones y enviar (simulado si no hay SMTP)
    for destino in destinos:
        db.add(Notificacion(
            informe_id=informe.id,
            consejo_id=consejo.id,
            destinatario_email=destino,
            tipo="ESTUDIANTE_REPORTE",
            reply_to_token=str(uuid.uuid4()),
        ))
    db.commit()

    try:
        enviar_reporte_mejoras_estudiantes(destinos, consejo.id, area.nombre if area else "", bloques_html)
    except Exception:
        pass

    return {
        "data": {"total": len(destinos), "asignaturas_en_reporte": len(cals)},
        "message": f"Reporte de mejoras enviado a estudiantes de {len(destinos)} grupo(s) del área {area.nombre if area else ''}",
        "success": True,
    }
