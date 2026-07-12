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
from email.mime.image import MIMEImage
from email import encoders
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session
from app.core.config import settings

# Logo institucional que se incrusta en los correos (imagen inline por Content-ID)
_LOGO_PATH = Path(__file__).parent.parent / "static" / "logo-ups.jpg"

# Pie institucional con el logo, para los correos que no lo colocan ellos mismos.
# Las plantillas de `plantillas_correo` sí lo hacen: lo ponen junto a la firma, que
# es donde corresponde. Si el cuerpo ya referencia el logo, no se añade otro.
_REFERENCIA_LOGO = "cid:logo_ups"
_PIE_LOGO = (
    '<div style="margin-top:16px;padding-top:12px;border-top:1px solid #d9d9d9;text-align:right">'
    '<img src="cid:logo_ups" alt="Universidad Politécnica Salesiana" style="height:52px">'
    "</div>"
)


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

def _aplicar_modo_prueba(destinatario: str, asunto: str) -> tuple[str, str] | None:
    """
    Interruptor global de correo (`MAIL_MODO_PRUEBA` en el `.env`).

    Devuelve el (destinatario, asunto) que se debe usar, o `None` si el correo no
    debe enviarse en absoluto.

    Se aplica aquí, en la capa más baja, a propósito: **todos** los correos del
    sistema pasan por `enviar_email`, así que ningún camino puede saltárselo — ni
    los envíos manuales de la UI ni los automáticos del planificador. Un
    interruptor que viviera solo en la UI dejaría al scheduler mandando correos
    reales sin que nadie lo pidiera.
    """
    if not settings.MAIL_MODO_PRUEBA:
        return destinatario, asunto

    if not settings.MAIL_REDIRECT_TO:
        logger.warning(
            f"MAIL_MODO_PRUEBA activo y sin MAIL_REDIRECT_TO — correo a "
            f"{destinatario} NO enviado: {asunto}"
        )
        return None

    logger.info(f"MAIL_MODO_PRUEBA: correo para {destinatario} redirigido a {settings.MAIL_REDIRECT_TO}")
    return settings.MAIL_REDIRECT_TO, f"[PRUEBA · para {destinatario}] {asunto}"


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

    # Red de seguridad: nada sale de aquí si el modo prueba está activo
    redirigido = _aplicar_modo_prueba(destinatario, asunto)
    if redirigido is None:
        return
    destinatario, asunto = redirigido

    # multipart/related permite incrustar el logo inline junto al HTML
    msg = MIMEMultipart("related")
    msg["Subject"] = asunto
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = destinatario
    if reply_to:
        msg["Reply-To"] = reply_to

    # El logo va al PIE. Si la plantilla ya lo coloca (junto a la firma), se respeta;
    # si no, se añade un pie institucional para no dejar el correo sin identidad.
    if _LOGO_PATH.exists() and _REFERENCIA_LOGO not in cuerpo_html:
        cuerpo_html = cuerpo_html + _PIE_LOGO
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    # Adjuntar el logo como imagen inline (Content-ID: logo_ups)
    if _LOGO_PATH.exists():
        with open(_LOGO_PATH, "rb") as f:
            img = MIMEImage(f.read())
        img.add_header("Content-ID", "<logo_ups>")
        img.add_header("Content-Disposition", "inline", filename="logo-ups.jpg")
        msg.attach(img)

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
        # `send_message` y no `sendmail`: este último codifica las direcciones en
        # ASCII y reventaba con los correos que llevan tilde o eñe
        # (p. ej. ordoñez.vinicio@…). `send_message` negocia SMTPUTF8 con el
        # servidor cuando hace falta.
        server.send_message(msg)
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


# Aquí vivían `enviar_email_estudiantes` y `enviar_reporte_mejoras_estudiantes`.
#
# Se eliminaron porque sus destinatarios se fabricaban con una plantilla
# (`estudiantes.{codigo}.{grupo}@est.ups.edu.ec`): direcciones que no existen, así
# que los correos no llegaban a nadie. Además el envío iba dentro de un try/except
# silencioso, de modo que la interfaz respondía "enviado" igualmente.
#
# Los correos a estudiantes se envían desde `app/api/v1/endpoints/correos.py`, que
# usa los destinatarios REALES cargados del Excel del período (tabla `estudiantes`),
# aplica las plantillas de los anexos y ofrece un modo prueba.


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
