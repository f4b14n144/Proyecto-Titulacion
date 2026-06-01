from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, auth, usuarios, periodos, consejos,
    areas, asignaturas, jefaturas, asignaciones, calificaciones,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
api_router.include_router(periodos.router, prefix="/periodos", tags=["periodos"])
api_router.include_router(consejos.router, prefix="/consejos", tags=["consejos"])
api_router.include_router(areas.router, prefix="/areas", tags=["areas"])
api_router.include_router(asignaturas.router, prefix="/asignaturas", tags=["asignaturas"])
api_router.include_router(jefaturas.router, prefix="/jefaturas", tags=["jefaturas"])
api_router.include_router(asignaciones.router, prefix="/asignaciones", tags=["asignaciones"])
api_router.include_router(calificaciones.router, prefix="/calificaciones", tags=["calificaciones"])
