import app.db.base  # noqa: F401 — registra todos los modelos SQLAlchemy al inicio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from app.core.config import settings
from app.api.v1.api_router import api_router
from app.core.scheduler import iniciar_scheduler, detener_scheduler, sincronizar_todos_los_consejos, iniciar_polling_imap

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:80", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Servir archivos .docx generados
app.mount("/static", StaticFiles(directory="app/static", html=False), name="static")


@app.on_event("startup")
async def startup_event():
    logger.info(f"Iniciando {settings.APP_NAME} en modo {settings.ENVIRONMENT}")
    iniciar_scheduler()
    sincronizar_todos_los_consejos()
    iniciar_polling_imap()


@app.on_event("shutdown")
async def shutdown_event():
    detener_scheduler()
    logger.info("Scheduler detenido")
