"""
Scheduler embebido en FastAPI usando APScheduler.
Dos tipos de jobs:
  1. flujo_consejo  — se activa 2 días antes de fecha_limite_informe de cada consejo
"""
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from loguru import logger

scheduler = BackgroundScheduler(timezone="America/Guayaquil")

# Antelación del recordatorio de entrega de cada informe
DIAS_ANTES = 2


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
# Recordatorios de entrega: 2 días antes de cada informe
# ──────────────────────────────────────────────────────────

def _job_recordatorio(consejo_id: int, tipo_informe: int) -> str:
    return f"recordatorio_c{consejo_id}_i{tipo_informe}"


def _ejecutar_recordatorio(consejo_id: int, tipo_informe: int):
    """Lo dispara APScheduler. Abre su propia sesión de BD."""
    from app.db.session import SessionLocal
    from app.services.recordatorios import enviar_recordatorios

    db = SessionLocal()
    try:
        resultado = enviar_recordatorios(db, consejo_id, tipo_informe)
        logger.info(
            f"Recordatorio informe {tipo_informe} del consejo {consejo_id}: {resultado}"
        )
    except Exception as e:
        logger.exception(f"Error enviando recordatorios: {e}")
    finally:
        db.close()


def programar_recordatorios_consejo(consejo_id: int):
    """
    (Re)programa el recordatorio de cada informe del consejo, 2 días antes de su
    fecha de entrega. Se llama al crear o editar las fechas.

    Una fecha que ya pasó no se programa: no tiene sentido avisar de algo vencido.
    """
    from app.db.session import SessionLocal
    from app.models.fecha_entrega import FechaEntregaInforme

    db = SessionLocal()
    try:
        fechas = (
            db.query(FechaEntregaInforme)
            .filter(FechaEntregaInforme.consejo_id == consejo_id)
            .all()
        )
        ahora = datetime.now(timezone.utc)
        programados = 0

        for f in fechas:
            job_id = _job_recordatorio(consejo_id, f.tipo_informe)
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            aviso = datetime.combine(f.fecha_entrega, datetime.min.time()).replace(
                tzinfo=timezone.utc
            ) - timedelta(days=DIAS_ANTES)

            if aviso <= ahora:
                logger.info(
                    f"Consejo {consejo_id}, informe {f.tipo_informe}: el aviso "
                    f"({aviso.date()}) ya pasó, no se programa"
                )
                continue

            scheduler.add_job(
                _ejecutar_recordatorio,
                trigger=DateTrigger(run_date=aviso),
                id=job_id,
                args=[consejo_id, f.tipo_informe],
                replace_existing=True,
            )
            programados += 1
            logger.info(
                f"Consejo {consejo_id}, informe {f.tipo_informe}: recordatorio "
                f"programado para {aviso.date()} (entrega {f.fecha_entrega})"
            )
        return programados
    finally:
        db.close()


def sincronizar_recordatorios():
    """Reprograma los recordatorios de todos los consejos al arrancar el servidor."""
    try:
        from app.db.session import SessionLocal
        from app.models.consejo import ConsejoCarrera

        db = SessionLocal()
        try:
            ids = [c.id for c in db.query(ConsejoCarrera).all()]
        finally:
            db.close()

        total = sum(programar_recordatorios_consejo(cid) for cid in ids)
        logger.info(f"Recordatorios programados al inicio: {total}")
    except Exception as e:
        logger.exception(f"Error sincronizando recordatorios: {e}")
