import app.db.base  # noqa: F401 — registra todos los modelos SQLAlchemy al inicio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.core.config import settings
from app.api.v1.api_router import api_router
from app.core.scheduler import (
    iniciar_scheduler, detener_scheduler, sincronizar_todos_los_consejos,
    sincronizar_recordatorios,
)

# En producción no se publica la documentación interactiva de la API.
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url=None if settings.es_produccion else "/docs",
    redoc_url=None if settings.es_produccion else "/redoc",
    openapi_url=None if settings.es_produccion else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# NOTA: `app/static/` NO se monta como carpeta pública.
#
# Contiene los .docx generados (con notas de estudiantes) y los gráficos de los
# informes. Servirlos como estáticos permitía descargarlos sin autenticación con
# solo adivinar el nombre del archivo. Las descargas van por la API:
#   GET /api/v1/informes/{id}/descargar     — valida JWT y rol
#   GET /api/v1/informes/{id}/grafico/{n}   — valida JWT, rol y lista blanca


def _revisar_configuracion() -> None:
    """Avisa (o falla) si la configuración no es apta para producción."""
    problemas: list[str] = []

    if len(settings.SECRET_KEY) < 32 or "CAMBIAR" in settings.SECRET_KEY.upper():
        problemas.append(
            "SECRET_KEY débil o de ejemplo. Generar con: openssl rand -hex 32"
        )
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        problemas.append("SMTP sin configurar: no se enviarán correos.")
    if settings.MAIL_MODO_PRUEBA and settings.es_produccion:
        problemas.append(
            "MAIL_MODO_PRUEBA está activo en producción: los correos NO llegarán a "
            "docentes ni estudiantes."
        )
    if any(o.startswith("http://localhost") for o in settings.origenes_cors):
        problemas.append("CORS_ORIGINS apunta a localhost; poner el dominio real.")

    if not problemas:
        return

    if settings.es_produccion:
        # En producción una SECRET_KEY débil es un fallo de seguridad, no un aviso:
        # con ella se pueden falsificar tokens de cualquier usuario.
        criticos = [p for p in problemas if "SECRET_KEY" in p]
        for p in problemas:
            logger.error(f"Configuración de producción: {p}")
        if criticos:
            raise RuntimeError(
                "Arranque abortado: " + "; ".join(criticos)
            )
    else:
        for p in problemas:
            logger.warning(f"Configuración: {p}")


@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando {settings.APP_NAME} en modo {settings.ENVIRONMENT}")

    # Que nunca haya duda de si los correos salen de verdad o no
    if settings.MAIL_MODO_PRUEBA:
        destino = settings.MAIL_REDIRECT_TO or "(ninguno: no se enviará nada)"
        logger.warning(f"CORREO EN MODO PRUEBA — todo se redirige a: {destino}")
    else:
        logger.info("CORREO EN MODO REAL — los correos llegan a sus destinatarios")

    _revisar_configuracion()
    iniciar_scheduler()
    sincronizar_todos_los_consejos()
    sincronizar_recordatorios()   # recordatorios de entrega de cada informe


@app.on_event("shutdown")
async def shutdown_event():
    detener_scheduler()
    logger.info("Scheduler detenido")
