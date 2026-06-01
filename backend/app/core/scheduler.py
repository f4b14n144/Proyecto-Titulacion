"""
Scheduler embebido en FastAPI usando APScheduler.
Dos tipos de jobs:
  1. flujo_consejo  — se activa 2 días antes de fecha_limite_informe de cada consejo
  2. polling_imap   — cada 15 min para capturar respuestas de docentes
"""
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

scheduler = BackgroundScheduler(timezone="America/Guayaquil")


def iniciar_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler iniciado")


def detener_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler detenido")


# ──────────────────────────────────────────────────────────
# Jobs de flujo por consejo
# ──────────────────────────────────────────────────────────

def programar_flujo_consejo(consejo_id: int, fecha_limite: datetime | None):
    """
    Programa (o reprograma) la activación del flujo 2 días antes de fecha_limite.
    Si fecha_limite ya pasó o es None, no programa nada.
    """
    job_id = f"flujo_consejo_{consejo_id}"

    # Cancelar job anterior si existe
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if fecha_limite is None:
        return

    fecha_activacion = fecha_limite - timedelta(days=2)
    ahora = datetime.now(timezone.utc)

    if fecha_activacion <= ahora:
        logger.warning(
            f"Consejo {consejo_id}: fecha de activación ({fecha_activacion.date()}) ya pasó, no se programa"
        )
        return

    scheduler.add_job(
        _ejecutar_flujo_consejo,
        trigger=DateTrigger(run_date=fecha_activacion),
        id=job_id,
        args=[consejo_id],
        replace_existing=True,
    )
    logger.info(f"Consejo {consejo_id}: flujo programado para {fecha_activacion.date()}")


def _ejecutar_flujo_consejo(consejo_id: int):
    """
    Punto de entrada del flujo automático para un consejo.
    Importación diferida para evitar ciclos con los modelos.
    """
    logger.info(f"Iniciando flujo automático para consejo {consejo_id}")
    try:
        from app.db.session import SessionLocal
        from app.models.consejo import ConsejoCarrera
        from app.services.flujo_consejo import ejecutar_flujo

        db = SessionLocal()
        try:
            consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
            if not consejo:
                logger.error(f"Consejo {consejo_id} no encontrado en DB")
                return
            if consejo.flujo_estado not in ("PENDIENTE",):
                logger.info(f"Consejo {consejo_id} ya está en estado {consejo.flujo_estado}, se omite")
                return
            ejecutar_flujo(db, consejo)
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error en flujo automático consejo {consejo_id}: {e}")


def sincronizar_todos_los_consejos():
    """
    Recorre todos los consejos PENDIENTE y programa sus jobs.
    Se llama al inicio del servidor para restaurar el estado tras un reinicio.
    """
    try:
        from app.db.session import SessionLocal
        from app.models.consejo import ConsejoCarrera

        db = SessionLocal()
        try:
            consejos = db.query(ConsejoCarrera).filter(ConsejoCarrera.flujo_estado == "PENDIENTE").all()
            for c in consejos:
                if c.fecha_limite_informe:
                    fecha_dt = datetime.combine(c.fecha_limite_informe, datetime.min.time()).replace(
                        tzinfo=timezone.utc
                    )
                    programar_flujo_consejo(c.id, fecha_dt)
            logger.info(f"Sincronizados {len(consejos)} consejos PENDIENTE")
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error sincronizando consejos al inicio: {e}")


# ──────────────────────────────────────────────────────────
# Job IMAP polling
# ──────────────────────────────────────────────────────────

def iniciar_polling_imap():
    """Registra el job de polling IMAP cada 15 minutos."""
    job_id = "polling_imap"
    if scheduler.get_job(job_id):
        return  # ya existe
    scheduler.add_job(
        _ejecutar_polling_imap,
        trigger=IntervalTrigger(minutes=15),
        id=job_id,
        replace_existing=True,
    )
    logger.info("Job polling IMAP registrado (cada 15 min)")


def _ejecutar_polling_imap():
    try:
        from app.services.mail_service import procesar_respuestas_imap
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            procesar_respuestas_imap(db)
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error en polling IMAP: {e}")
