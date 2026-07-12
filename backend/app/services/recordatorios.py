"""
Recordatorios de entrega de informes.

Dos días antes de la fecha de entrega de cada informe, el planificador avisa por
correo a:
  - los **jefes de área**, que son quienes elaboran el informe
  - los **docentes**, para que registren sus observaciones y acciones de mejora
    antes de que el informe se cierre

Las fechas las fija la Dirección de Carrera en cada Consejo (una por informe).
"""
import uuid
from datetime import date

from loguru import logger
from sqlalchemy.orm import Session

from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.area import Area
from app.models.consejo import ConsejoCarrera
from app.models.fecha_entrega import FechaEntregaInforme
from app.models.jefatura import JefaturaArea
from app.models.notificacion import Notificacion
from app.models.usuario import Usuario
from app.services import plantillas_correo as plantillas
from app.services.mail_service import enviar_email

# Días de antelación del recordatorio
DIAS_ANTES = 2


def _formatear(f: date) -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{f.day} de {meses[f.month - 1]} de {f.year}"


def _correos_a_jefes(db: Session, consejo: ConsejoCarrera, tipo: int, fecha: str) -> list[dict]:
    filas = (
        db.query(JefaturaArea, Area, Usuario)
        .join(Area, JefaturaArea.area_id == Area.id)
        .join(Usuario, JefaturaArea.usuario_id == Usuario.id)
        .filter(JefaturaArea.periodo_id == consejo.periodo_id, Usuario.activo.is_(True))
        .all()
    )
    correos = []
    for _, area, jefe in filas:
        asunto, cuerpo = plantillas.correo_recordatorio_jefe(
            titulo=jefe.titulo or "",
            nombre=jefe.nombre_completo,
            area_nombre=area.nombre,
            tipo_informe=tipo,
            fecha_entrega=fecha,
        )
        correos.append({
            "destinatario": jefe.email_institucional,
            "asunto": asunto,
            "cuerpo_html": cuerpo,
            "tipo": "RECORDATORIO_JEFE",
        })
    return correos


def _correos_a_docentes(db: Session, consejo: ConsejoCarrera, fecha: str) -> list[dict]:
    filas = (
        db.query(AsignacionDocente, Asignatura, Usuario)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .join(Usuario, AsignacionDocente.usuario_id == Usuario.id)
        .filter(AsignacionDocente.periodo_id == consejo.periodo_id, Usuario.activo.is_(True))
        .all()
    )
    # Un solo correo por docente, con todas sus materias
    por_docente: dict[int, dict] = {}
    for _, asignatura, docente in filas:
        entrada = por_docente.setdefault(
            docente.id, {"docente": docente, "materias": []}
        )
        if asignatura.nombre not in entrada["materias"]:
            entrada["materias"].append(asignatura.nombre)

    correos = []
    for entrada in por_docente.values():
        docente = entrada["docente"]
        asunto, cuerpo = plantillas.correo_recordatorio_docente(
            titulo=docente.titulo or "",
            nombre=docente.nombre_completo,
            materias=sorted(entrada["materias"]),
            fecha_entrega=fecha,
        )
        correos.append({
            "destinatario": docente.email_institucional,
            "asunto": asunto,
            "cuerpo_html": cuerpo,
            "tipo": "RECORDATORIO_DOCENTE",
        })
    return correos


def preparar_recordatorios(
    db: Session, consejo_id: int, tipo_informe: int
) -> list[dict]:
    """Arma los correos del recordatorio, sin enviarlos (útil para previsualizar)."""
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if consejo is None:
        return []

    fila = (
        db.query(FechaEntregaInforme)
        .filter(
            FechaEntregaInforme.consejo_id == consejo_id,
            FechaEntregaInforme.tipo_informe == tipo_informe,
        )
        .first()
    )
    if fila is None:
        logger.warning(f"Consejo {consejo_id}: sin fecha de entrega para el informe {tipo_informe}")
        return []

    fecha = _formatear(fila.fecha_entrega)
    return (
        _correos_a_jefes(db, consejo, tipo_informe, fecha)
        + _correos_a_docentes(db, consejo, fecha)
    )


def enviar_recordatorios(db: Session, consejo_id: int, tipo_informe: int) -> dict:
    """
    Envía los recordatorios y deja constancia en `notificaciones`.

    Un fallo individual no detiene la tanda: si un correo rebota, los demás salen.
    """
    correos = preparar_recordatorios(db, consejo_id, tipo_informe)
    if not correos:
        return {"enviados": 0, "fallidos": 0, "total": 0}

    enviados = fallidos = 0
    for c in correos:
        try:
            enviar_email(c["destinatario"], c["asunto"], c["cuerpo_html"])
            enviados += 1
        except Exception as e:  # noqa: BLE001
            fallidos += 1
            logger.error(f"Recordatorio no enviado a {c['destinatario']}: {e}")

        db.add(Notificacion(
            informe_id=None,
            consejo_id=consejo_id,
            destinatario_email=c["destinatario"],
            tipo=c["tipo"],
            reply_to_token=str(uuid.uuid4()),  # la columna es única y obligatoria
        ))

    db.commit()
    logger.info(
        f"Recordatorios del informe {tipo_informe} (consejo {consejo_id}): "
        f"{enviados} enviados, {fallidos} fallidos"
    )
    return {"enviados": enviados, "fallidos": fallidos, "total": len(correos)}
