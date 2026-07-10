"""
Carga de estudiantes por período desde el Excel institucional.

El archivo trae nombre, correo institucional y las materias que cursa cada
estudiante. Las columnas se reconocen automáticamente (ver estudiantes_processor).
Estos datos alimentan los correos personalizados por materia.
"""
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.asignatura import Asignatura
from app.models.estudiante import Estudiante, EstudianteAsignatura
from app.models.periodo import PeriodoAcademico
from app.models.usuario import Usuario
from app.services.estudiantes_processor import procesar_excel_estudiantes

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")

MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _catalogo(db: Session) -> list[dict]:
    return [{"id": a.id, "nombre": a.nombre} for a in db.query(Asignatura).all()]


async def _procesar_subida(archivo: UploadFile, db: Session) -> dict:
    if not archivo.filename or not archivo.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx o .xls")

    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB")

    suffix = ".xlsx" if archivo.filename.endswith(".xlsx") else ".xls"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contenido)
        ruta = tmp.name
    try:
        return procesar_excel_estudiantes(ruta, _catalogo(db))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(ruta)


@router.post("/preview", response_model=dict)
async def preview_estudiantes(
    archivo: UploadFile = File(...),
    periodo_id: int = Form(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Procesa el Excel y devuelve lo detectado, sin guardar nada."""
    if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == periodo_id).first():
        raise HTTPException(status_code=404, detail="Período no encontrado")

    resultado = await _procesar_subida(archivo, db)
    return {
        "data": {"periodo_id": periodo_id, **resultado},
        "message": f"{resultado['total_estudiantes']} estudiante(s) detectado(s)",
        "success": True,
    }


@router.post("/confirmar", response_model=dict)
async def confirmar_estudiantes(
    archivo: UploadFile = File(...),
    periodo_id: int = Form(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """
    Guarda los estudiantes del período. Es idempotente: reemplaza por completo el
    padrón del período, de modo que volver a subir el archivo corregido no duplica.
    """
    if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == periodo_id).first():
        raise HTTPException(status_code=404, detail="Período no encontrado")

    resultado = await _procesar_subida(archivo, db)

    # Limpiar el padrón anterior del período (las materias caen en cascada)
    previos = db.query(Estudiante).filter(Estudiante.periodo_id == periodo_id).all()
    for e in previos:
        db.delete(e)
    db.flush()

    creados = 0
    for datos in resultado["estudiantes"]:
        estudiante = Estudiante(
            periodo_id=periodo_id,
            nombre_completo=datos["nombre_completo"],
            correo=datos["correo"],
        )
        db.add(estudiante)
        db.flush()
        for materia in datos["materias"]:
            db.add(EstudianteAsignatura(
                estudiante_id=estudiante.id,
                asignatura_id=materia["asignatura_id"],
                asignatura_nombre=materia["asignatura_nombre"],
            ))
        creados += 1

    db.commit()
    return {
        "data": {
            "periodo_id": periodo_id,
            "estudiantes_creados": creados,
            "reemplazados": len(previos),
            "total_materias": resultado["total_materias"],
            "advertencias": resultado["advertencias"],
        },
        "message": f"{creados} estudiante(s) guardado(s)",
        "success": True,
    }


@router.get("/", response_model=dict)
def listar_estudiantes(
    periodo_id: int = Query(...),
    asignatura_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    """Estudiantes del período; opcionalmente solo los que cursan una asignatura."""
    q = db.query(Estudiante).filter(Estudiante.periodo_id == periodo_id)
    if asignatura_id:
        q = q.join(EstudianteAsignatura).filter(
            EstudianteAsignatura.asignatura_id == asignatura_id
        )
    estudiantes = q.order_by(Estudiante.nombre_completo).all()

    data = [
        {
            "id": e.id,
            "nombre_completo": e.nombre_completo,
            "correo": e.correo,
            "materias": [
                {"asignatura_id": m.asignatura_id, "asignatura_nombre": m.asignatura_nombre}
                for m in e.materias
            ],
        }
        for e in estudiantes
    ]
    return {"data": data, "message": f"{len(data)} estudiante(s)", "success": True}
