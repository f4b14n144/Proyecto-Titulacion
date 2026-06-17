from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel, ConfigDict
from typing import Any, Optional
from app.core.deps import get_db, get_current_user, require_role
from app.models.informe import Informe
from app.models.usuario import Usuario
from app.services.doc_generator import generar_docx, regenerar_docx

router = APIRouter()

DOCX_DIR = Path("app/static/docx")

_solo_director = require_role("DIRECTOR_CARRERA")


class InformeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    consejo_id: int
    area_id: int
    tipo_informe: int
    estado: str
    contenido_json: Optional[Any]
    ruta_docx: Optional[str]
    version: int


class SeccionesUpdate(BaseModel):
    secciones: dict[str, str]


@router.get("/", response_model=dict)
def listar_informes(
    consejo_id: Optional[int] = None,
    area_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(Informe)
    if consejo_id:
        q = q.filter(Informe.consejo_id == consejo_id)
    if area_id:
        q = q.filter(Informe.area_id == area_id)
    informes = q.all()
    return {"data": [InformeOut.model_validate(i) for i in informes], "message": "OK", "success": True}


@router.get("/{informe_id}", response_model=dict)
def obtener_informe(
    informe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    informe = db.query(Informe).filter(Informe.id == informe_id).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return {"data": InformeOut.model_validate(informe), "message": "OK", "success": True}


@router.put("/{informe_id}/secciones", response_model=dict)
def actualizar_secciones(
    informe_id: int,
    payload: SeccionesUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Permite al jefe editar secciones del informe antes de exportar."""
    informe = db.query(Informe).filter(Informe.id == informe_id).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    # Construir un dict NUEVO para que SQLAlchemy detecte el cambio en la columna JSON
    # (reasignar el mismo objeto no marca la fila como modificada)
    contenido_actual = informe.contenido_json or {}
    contenido = dict(contenido_actual)
    contenido["secciones"] = {**contenido_actual.get("secciones", {}), **payload.secciones}
    informe.contenido_json = contenido
    informe.estado = "REVISANDO"
    flag_modified(informe, "contenido_json")
    db.commit()
    return {"data": InformeOut.model_validate(informe), "message": "Secciones actualizadas", "success": True}


@router.post("/{informe_id}/generar-docx", response_model=dict)
def generar_docx_endpoint(
    informe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Genera o regenera el .docx del informe."""
    informe = db.query(Informe).filter(Informe.id == informe_id).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    if informe.ruta_docx:
        nombre = regenerar_docx(db, informe)
    else:
        nombre = generar_docx(db, informe)

    return {
        "data": {"ruta_docx": nombre, "version": informe.version},
        "message": "Documento generado",
        "success": True,
    }


@router.get("/{informe_id}/descargar")
def descargar_docx(
    informe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Sirve el .docx generado para descarga directa."""
    informe = db.query(Informe).filter(Informe.id == informe_id).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    if not informe.ruta_docx:
        raise HTTPException(status_code=404, detail="El informe no tiene documento generado aún")

    ruta = DOCX_DIR / informe.ruta_docx
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo .docx no encontrado en el servidor")

    return FileResponse(
        path=str(ruta),
        filename=informe.ruta_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.put("/{informe_id}/estado", response_model=dict)
def cambiar_estado(
    informe_id: int,
    estado: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estados_validos = {"BORRADOR", "REVISANDO", "APROBADO"}
    if estado not in estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {estados_validos}")

    informe = db.query(Informe).filter(Informe.id == informe_id).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    informe.estado = estado
    db.commit()
    return {"data": InformeOut.model_validate(informe), "message": "Estado actualizado", "success": True}


class GenerarBorradorRequest(BaseModel):
    consejo_id: int
    area_id: int
    tipo_informe: int  # 1 | 2 | 3 | 4


@router.post("/generar-borrador", response_model=dict)
def generar_borrador(
    payload: GenerarBorradorRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """
    Genera el borrador del informe solicitado usando IA.
    Los informes 3 y 4 pueden tardar 30-90 seg según la cantidad de asignaturas.
    El endpoint responde inmediatamente y el trabajo ocurre en background.
    """
    from app.services.generador_informes import (
        generar_informe_1, generar_informe_2, generar_informe_3, generar_informe_4,
    )

    generadores = {1: generar_informe_1, 2: generar_informe_2, 3: generar_informe_3, 4: generar_informe_4}
    fn = generadores.get(payload.tipo_informe)
    if fn is None:
        raise HTTPException(status_code=400, detail="tipo_informe debe ser 1, 2, 3 o 4")

    # IMPORTANTE: el BackgroundTask NO debe reutilizar la sesión del request
    # (se cierra al responder). Cada tarea abre y cierra su propia sesión.
    def _ejecutar(consejo_id: int, area_id: int):
        from app.db.session import SessionLocal
        from loguru import logger
        tarea_db = SessionLocal()
        try:
            fn(tarea_db, consejo_id, area_id)
        except Exception as e:
            logger.exception(f"Error generando informe tipo {payload.tipo_informe}: {e}")
        finally:
            tarea_db.close()

    background_tasks.add_task(_ejecutar, payload.consejo_id, payload.area_id)

    return {
        "data": {
            "consejo_id": payload.consejo_id,
            "area_id": payload.area_id,
            "tipo_informe": payload.tipo_informe,
        },
        "message": "Generación de borrador iniciada. Consulta GET /informes/ en unos momentos.",
        "success": True,
    }
