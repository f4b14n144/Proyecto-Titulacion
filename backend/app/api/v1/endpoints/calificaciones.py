"""
Endpoint para subir y procesar el Excel de calificaciones.

Flujo:
  1. POST /calificaciones/preview  — procesa el Excel y devuelve preview (sin guardar)
  2. POST /calificaciones/confirmar — guarda en DB los datos del preview
"""
import os
import tempfile
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, require_role
from app.models.usuario import Usuario
from app.models.consejo import ConsejoCarrera
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.calificacion import Calificacion
from app.schemas.calificacion import PreviewCalificaciones, CalificacionOut
from app.services.excel_processor import procesar_excel

router = APIRouter()

_solo_director = require_role("DIRECTOR_CARRERA")

TIPOS_VALIDOS = {"INTERCICLO", "FINAL"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _cargar_asignaciones(db: Session, periodo_id: int) -> list[dict]:
    """Devuelve las asignaciones del período con info de asignatura."""
    rows = (
        db.query(AsignacionDocente, Asignatura)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(AsignacionDocente.periodo_id == periodo_id)
        .all()
    )
    return [
        {
            "asignatura_id":     asig.asignatura_id,
            "asignatura_nombre": asignatura.nombre,
            "asignatura_codigo": asignatura.codigo,
            "usuario_id":        asig.usuario_id,
            "grupo":             asig.grupo,
        }
        for asig, asignatura in rows
    ]


@router.post("/preview", response_model=dict)
async def preview_calificaciones(
    archivo: UploadFile = File(...),
    tipo: str = Form(...),
    consejo_id: int = Form(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Procesa el Excel y devuelve un preview sin guardar en DB."""
    if tipo.upper() not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo debe ser INTERCICLO o FINAL, recibido: {tipo}")

    if not archivo.filename or not archivo.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx o .xls")

    # Verificar que el consejo existe
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo de Carrera no encontrado")

    # Leer el archivo en memoria con límite de tamaño
    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB")

    # Guardar temporalmente en disco para pandas
    suffix = ".xlsx" if archivo.filename.endswith(".xlsx") else ".xls"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contenido)
        ruta_tmp = tmp.name

    try:
        asignaciones = _cargar_asignaciones(db, consejo.periodo_id)
        if not asignaciones:
            raise HTTPException(
                status_code=400,
                detail="No hay asignaciones docente registradas para el período de este consejo",
            )

        resultados = procesar_excel(ruta_tmp, tipo.upper(), asignaciones)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(ruta_tmp)

    advertencias_globales = [
        adv
        for r in resultados
        for adv in r.get("advertencias", [])
    ]

    preview = PreviewCalificaciones(
        tipo=tipo.upper(),
        consejo_id=consejo_id,
        resultados=resultados,  # type: ignore[arg-type]
        total_asignaturas=len(resultados),
        advertencias_globales=list(set(advertencias_globales)),
    )

    return {
        "data": preview.model_dump(),
        "message": f"Preview listo: {len(resultados)} asignatura(s) detectada(s)",
        "success": True,
    }


@router.post("/confirmar", response_model=dict, status_code=status.HTTP_201_CREATED)
async def confirmar_calificaciones(
    archivo: UploadFile = File(...),
    tipo: str = Form(...),
    consejo_id: int = Form(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Procesa el Excel y guarda las calificaciones en DB (sobreescribe si ya existen)."""
    if tipo.upper() not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"tipo debe ser INTERCICLO o FINAL, recibido: {tipo}")

    if not archivo.filename or not archivo.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .xlsx o .xls")

    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo de Carrera no encontrado")

    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB")

    suffix = ".xlsx" if str(archivo.filename).endswith(".xlsx") else ".xls"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contenido)
        ruta_tmp = tmp.name

    try:
        asignaciones = _cargar_asignaciones(db, consejo.periodo_id)
        if not asignaciones:
            raise HTTPException(status_code=400, detail="No hay asignaciones registradas para este período")

        resultados = procesar_excel(ruta_tmp, tipo.upper(), asignaciones)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(ruta_tmp)

    guardados: list[CalificacionOut] = []
    for r in resultados:
        # Sobreescribir solo si ya existe para esta asignatura+consejo+tipo+GRUPO
        # (sin el grupo, asignaturas con varios grupos se pisaban entre sí)
        existente = db.query(Calificacion).filter(
            Calificacion.asignatura_id == r["asignatura_id"],
            Calificacion.consejo_id == consejo_id,
            Calificacion.tipo == tipo.upper(),
            Calificacion.grupo == r["grupo"],
        ).first()

        datos_json = {
            "grupo":               r["grupo"],
            "estudiantes":         r["estudiantes"],
            "total_estudiantes":   r["total_estudiantes"],
            "columnas_detectadas": r["columnas_detectadas"],
        }

        if existente:
            existente.datos_json = datos_json
            db.flush()
            guardados.append(CalificacionOut.model_validate(existente))
        else:
            nueva = Calificacion(
                asignatura_id=r["asignatura_id"],
                consejo_id=consejo_id,
                grupo=r["grupo"],
                tipo=tipo.upper(),
                datos_json=datos_json,
            )
            db.add(nueva)
            db.flush()
            guardados.append(CalificacionOut.model_validate(nueva))

    db.commit()

    return {
        "data": [c.model_dump() for c in guardados],
        "message": f"{len(guardados)} registro(s) guardado(s) correctamente",
        "success": True,
    }


@router.get("/", response_model=dict)
def listar_calificaciones(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    cals = db.query(Calificacion).filter(Calificacion.consejo_id == consejo_id).all()
    return {
        "data": [CalificacionOut.model_validate(c) for c in cals],
        "message": "OK",
        "success": True,
    }
