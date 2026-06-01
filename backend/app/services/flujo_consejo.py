"""
Orquestador del flujo automático de un Consejo de Carrera.

Pasos:
  1. Cambiar estado a PROCESANDO
  2. Enviar emails a docentes y estudiantes
  3. (Sprint 3) Generar borradores de informes con IA
  4. Cambiar estado a COMPLETADO
"""
from loguru import logger
from sqlalchemy.orm import Session
from app.models.consejo import ConsejoCarrera


def ejecutar_flujo(db: Session, consejo: ConsejoCarrera) -> None:
    """Ejecuta el flujo completo para un consejo. Llamado por el scheduler."""
    logger.info(f"Flujo consejo {consejo.id}: iniciando")
    try:
        consejo.flujo_estado = "PROCESANDO"
        db.commit()

        _enviar_notificaciones(db, consejo)

        # Sprint 3 completará este paso con generación IA
        logger.info(f"Flujo consejo {consejo.id}: notificaciones enviadas — generación IA pendiente (Sprint 3)")

        consejo.flujo_estado = "COMPLETADO"
        db.commit()
        logger.info(f"Flujo consejo {consejo.id}: COMPLETADO")

    except Exception as e:
        logger.exception(f"Flujo consejo {consejo.id} falló: {e}")
        consejo.flujo_estado = "ERROR"
        db.commit()
        raise


def _enviar_notificaciones(db: Session, consejo: ConsejoCarrera) -> None:
    """Envía emails a docentes de las asignaciones del período del consejo."""
    try:
        from app.services.mail_service import enviar_email_docente
        from app.models.asignacion import AsignacionDocente
        from app.models.usuario import Usuario
        from app.models.notificacion import Notificacion
        import uuid

        asignaciones = (
            db.query(AsignacionDocente)
            .filter(AsignacionDocente.periodo_id == consejo.periodo_id)
            .all()
        )

        # Agrupar por docente para no enviar duplicados al mismo docente
        docentes_vistos: set[int] = set()
        for asig in asignaciones:
            if asig.usuario_id in docentes_vistos:
                continue
            docentes_vistos.add(asig.usuario_id)

            docente = db.query(Usuario).filter(Usuario.id == asig.usuario_id).first()
            if not docente:
                continue

            token = str(uuid.uuid4())

            # Registrar notificación
            noti = Notificacion(
                informe_id=None,  # Se actualizará cuando se genere el informe en Sprint 3
                destinatario_email=docente.email_institucional,
                tipo="DOCENTE_SUGERENCIA",
                reply_to_token=token,
            )
            # No guardar informe_id = None por FK constraint — solo guardamos si tenemos informe
            # Por ahora solo enviamos email sin registrar en DB
            try:
                enviar_email_docente(
                    destinatario=docente.email_institucional,
                    nombre_docente=docente.nombre_completo,
                    reply_to_token=token,
                    consejo_id=consejo.id,
                )
                logger.info(f"Email enviado a docente {docente.email_institucional}")
            except Exception as e:
                logger.warning(f"No se pudo enviar email a {docente.email_institucional}: {e}")

    except Exception as e:
        logger.warning(f"Error enviando notificaciones consejo {consejo.id}: {e}")
        # No propagar — el flujo continúa aunque falle el correo
