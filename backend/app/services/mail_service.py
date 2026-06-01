"""
Servicio de correo: envío SMTP (Brevo) y recepción IMAP.

Convención de Reply-To para correlacionar respuestas de docentes:
  respuestas+{uuid}@{REPLY_TO_DOMAIN}
"""
import email
import imaplib
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session
from app.core.config import settings


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def generar_reply_to_token() -> str:
    return str(uuid.uuid4())


def _reply_to_address(token: str) -> str:
    return f"respuestas+{token}@{settings.REPLY_TO_DOMAIN}"


def _conectar_smtp() -> smtplib.SMTP:
    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    server.starttls()
    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    return server


# ──────────────────────────────────────────────────────────────────
# Envío de emails
# ──────────────────────────────────────────────────────────────────

def enviar_email(
    destinatario: str,
    asunto: str,
    cuerpo_html: str,
    reply_to: str | None = None,
    adjunto_ruta: str | None = None,
    adjunto_nombre: str | None = None,
) -> None:
    """Envía un email vía SMTP. Lanza excepción si falla."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f"SMTP no configurado — email a {destinatario} omitido (modo dev)")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = destinatario
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    if adjunto_ruta and Path(adjunto_ruta).exists():
        with open(adjunto_ruta, "rb") as f:
            parte = MIMEBase("application", "octet-stream")
            parte.set_payload(f.read())
        encoders.encode_base64(parte)
        parte.add_header(
            "Content-Disposition",
            f'attachment; filename="{adjunto_nombre or Path(adjunto_ruta).name}"',
        )
        msg.attach(parte)

    try:
        server = _conectar_smtp()
        server.sendmail(settings.EMAIL_FROM, [destinatario], msg.as_string())
        server.quit()
        logger.info(f"Email enviado a {destinatario}: {asunto}")
    except Exception as e:
        logger.error(f"Error enviando email a {destinatario}: {e}")
        raise


def enviar_email_docente(
    destinatario: str,
    nombre_docente: str,
    reply_to_token: str,
    consejo_id: int,
) -> None:
    """Email a docente pidiendo observaciones sobre sus asignaturas."""
    reply_to = _reply_to_address(reply_to_token)
    asunto = f"[UPS Computación] Solicitud de observaciones — Consejo {consejo_id}"
    cuerpo = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
    <p>Estimado/a <strong>{nombre_docente}</strong>,</p>
    <p>Le solicitamos compartir sus observaciones y comentarios sobre el desarrollo
    de sus asignaturas en el período académico en curso, en el marco del proceso de
    seguimiento académico del <strong>Consejo de Carrera #{consejo_id}</strong>.</p>
    <p>Por favor responda directamente a este correo con sus observaciones.
    Su respuesta será registrada automáticamente en el sistema.</p>
    <p>Si tiene alguna inquietud, comuníquese con la Dirección de Carrera.</p>
    <br>
    <p>Atentamente,<br>
    <strong>Sistema de Informes Académicos</strong><br>
    Carrera de Computación — UPS Cuenca</p>
    </body></html>
    """
    enviar_email(destinatario, asunto, cuerpo, reply_to=reply_to)


def enviar_email_estudiantes(
    destinatarios: list[str],
    consejo_id: int,
) -> None:
    """Email a estudiantes invitando a reportar al jefe de área."""
    asunto = f"[UPS Computación] Espacio para compartir con tu Jefe de Área — Consejo {consejo_id}"
    cuerpo = """
    <html><body style="font-family: Arial, sans-serif; color: #333;">
    <p>Estimado/a estudiante,</p>
    <p>La Carrera de Computación te invita a compartir cualquier observación,
    sugerencia o inquietud sobre el desarrollo de tus asignaturas con tu
    <strong>Jefe de Área</strong>.</p>
    <p>Puedes contactarte directamente con tu jefe de área a través del sistema
    o acercarte a la Dirección de Carrera.</p>
    <br>
    <p>Carrera de Computación — UPS Cuenca</p>
    </body></html>
    """
    for dest in destinatarios:
        try:
            enviar_email(dest, asunto, cuerpo)
        except Exception as e:
            logger.warning(f"No se pudo enviar email a estudiante {dest}: {e}")


def enviar_docx_jefe(
    destinatario: str,
    nombre_jefe: str,
    tipo_informe: int,
    ruta_docx: str,
) -> None:
    """Envía el .docx generado al jefe de área por correo."""
    nombres = {1: "Centro Docente", 2: "Revisión AVAC", 3: "Visitas Áulicas", 4: "Análisis Final"}
    nombre_tipo = nombres.get(tipo_informe, f"Informe {tipo_informe}")
    asunto = f"[UPS Computación] Informe {tipo_informe} — {nombre_tipo} listo para revisión"
    cuerpo = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
    <p>Estimado/a <strong>{nombre_jefe}</strong>,</p>
    <p>El <strong>Informe {tipo_informe} — {nombre_tipo}</strong> ha sido generado
    y está adjunto en este correo.</p>
    <p>Por favor revíselo, realice las ediciones necesarias y proceda con su firma
    y envío a través de Quipux.</p>
    <br>
    <p>Sistema de Informes Académicos<br>Carrera de Computación — UPS Cuenca</p>
    </body></html>
    """
    nombre_archivo = f"Informe_{tipo_informe}_{nombre_tipo.replace(' ', '_')}.docx"
    enviar_email(destinatario, asunto, cuerpo, adjunto_ruta=ruta_docx, adjunto_nombre=nombre_archivo)


# ──────────────────────────────────────────────────────────────────
# Recepción IMAP
# ──────────────────────────────────────────────────────────────────

def _extraer_token_de_headers(msg_obj) -> str | None:
    """Extrae el reply_to_token de los headers del email recibido."""
    # Buscar en In-Reply-To, References o el To del mensaje
    for header in ("To", "In-Reply-To", "References", "X-Original-To"):
        valor = msg_obj.get(header, "")
        if "respuestas+" in valor:
            # Extraer UUID entre "respuestas+" y "@"
            inicio = valor.find("respuestas+") + len("respuestas+")
            fin = valor.find("@", inicio)
            if fin > inicio:
                return valor[inicio:fin]
    return None


def procesar_respuestas_imap(db: Session) -> int:
    """
    Conecta por IMAP, lee emails no vistos, correlaciona tokens y guarda respuestas.
    Retorna el número de respuestas procesadas.
    """
    if not settings.IMAP_HOST or not settings.IMAP_USER:
        logger.debug("IMAP no configurado — polling omitido")
        return 0

    from app.models.notificacion import Notificacion
    from app.models.respuesta_docente import RespuestaDocente

    procesados = 0
    try:
        imap = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
        imap.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        imap.select("INBOX")

        _, mensajes = imap.search(None, "UNSEEN")
        ids = mensajes[0].split()
        logger.info(f"IMAP: {len(ids)} mensajes no vistos")

        for uid in ids:
            _, data = imap.fetch(uid, "(RFC822)")
            raw = data[0][1]
            msg_obj = email.message_from_bytes(raw)

            token = _extraer_token_de_headers(msg_obj)
            if not token:
                continue

            notificacion = db.query(Notificacion).filter(
                Notificacion.reply_to_token == token
            ).first()
            if not notificacion or notificacion.respondido:
                continue

            # Extraer texto del cuerpo
            cuerpo = ""
            if msg_obj.is_multipart():
                for parte in msg_obj.walk():
                    if parte.get_content_type() == "text/plain":
                        cuerpo = parte.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                cuerpo = msg_obj.get_payload(decode=True).decode("utf-8", errors="ignore")

            respuesta = RespuestaDocente(
                notificacion_id=notificacion.id,
                contenido=cuerpo.strip(),
            )
            db.add(respuesta)
            notificacion.respondido = True

            # Marcar como leído
            imap.store(uid, "+FLAGS", "\\Seen")
            procesados += 1
            logger.info(f"Respuesta guardada para notificación {notificacion.id}")

        db.commit()
        imap.logout()

    except Exception as e:
        logger.error(f"Error en polling IMAP: {e}")

    return procesados
