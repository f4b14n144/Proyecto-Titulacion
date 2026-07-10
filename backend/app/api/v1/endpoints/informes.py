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
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")


def _areas_del_jefe(db: Session, usuario_id: int) -> list[int]:
    from app.models.jefatura import JefaturaArea
    return [
        a_id for (a_id,) in
        db.query(JefaturaArea.area_id).filter(JefaturaArea.usuario_id == usuario_id).all()
    ]


def _validar_area_jefe(db: Session, usuario: Usuario, area_id: int, tipo_informe: int) -> None:
    """
    Un jefe solo puede generar informes de SU área — incluido el Informe 1, que
    ahora existe por área (hereda el contenido de dirección y el jefe añade lo suyo).
    """
    if getattr(usuario, "rol_efectivo", usuario.rol.nombre) != "JEFE_AREA":
        return
    if area_id not in _areas_del_jefe(db, usuario.id):
        raise HTTPException(status_code=403, detail="Solo puedes generar informes de tu área")


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
    # Derivados (para listar y filtrar en el panel de la directora)
    area_nombre: Optional[str] = None
    jefe_id: Optional[int] = None
    jefe_nombre: Optional[str] = None


class SeccionesUpdate(BaseModel):
    secciones: dict[str, str]


class ContenidoUpdate(BaseModel):
    """Contenido completo del informe, tal como quedó tras editarlo en la UI."""
    contenido_json: dict[str, Any]


def _informe_o_404(db: Session, informe_id: int) -> Informe:
    informe = db.query(Informe).filter(Informe.id == informe_id).first()
    if not informe:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    return informe


def _puede_editar(db: Session, usuario: Usuario, informe: Informe) -> None:
    """
    Solo la directora (cualquier informe) y el jefe de área (los de SU área).
    Un docente no edita informes.
    """
    rol = getattr(usuario, "rol_efectivo", usuario.rol.nombre)
    if rol == "DIRECTOR_CARRERA":
        return
    if rol == "JEFE_AREA" and informe.area_id in _areas_del_jefe(db, usuario.id):
        return
    raise HTTPException(status_code=403, detail="No puedes editar este informe")


def _mapa_area_jefe(db: Session) -> dict[int, Usuario]:
    """area_id → jefe de esa área (según su jefatura vigente)."""
    from app.models.jefatura import JefaturaArea
    filas = (
        db.query(JefaturaArea.area_id, Usuario)
        .join(Usuario, JefaturaArea.usuario_id == Usuario.id)
        .all()
    )
    return {area_id: jefe for area_id, jefe in filas}


@router.get("/", response_model=dict)
def listar_informes(
    consejo_id: Optional[int] = None,
    area_id: Optional[int] = None,
    jefe_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(Informe)
    if consejo_id:
        q = q.filter(Informe.consejo_id == consejo_id)
    if area_id:
        q = q.filter(Informe.area_id == area_id)
    if jefe_id:
        # Filtrar por jefe = filtrar por las áreas que ese jefe dirige
        q = q.filter(Informe.area_id.in_(_areas_del_jefe(db, jefe_id) or [-1]))

    # Un JEFE_AREA solo ve los informes de SU(S) área(s) — el Informe 1 ya es por área
    if getattr(current_user, "rol_efectivo", current_user.rol.nombre) == "JEFE_AREA":
        q = q.filter(Informe.area_id.in_(_areas_del_jefe(db, current_user.id) or [-1]))

    # Orden estable: primero por tipo (1,2,3,4) y luego por área
    informes = q.order_by(Informe.tipo_informe, Informe.area_id).all()

    from app.models.area import Area
    areas = {a.id: a.nombre for a in db.query(Area).all()}
    jefes = _mapa_area_jefe(db)

    data = []
    for i in informes:
        out = InformeOut.model_validate(i)
        out.area_nombre = areas.get(i.area_id)
        jefe = jefes.get(i.area_id)
        if jefe:
            out.jefe_id = jefe.id
            out.jefe_nombre = jefe.nombre_completo
        data.append(out)

    return {"data": data, "message": "OK", "success": True}


@router.get("/{informe_id}", response_model=dict)
def obtener_informe(
    informe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    informe = _informe_o_404(db, informe_id)

    # Lectura: la directora ve todos; el jefe, los de su área; el docente, ninguno.
    rol = getattr(current_user, "rol_efectivo", current_user.rol.nombre)
    if rol == "JEFE_AREA" and informe.area_id not in _areas_del_jefe(db, current_user.id):
        raise HTTPException(status_code=403, detail="No puedes ver este informe")
    if rol not in ("DIRECTOR_CARRERA", "JEFE_AREA"):
        raise HTTPException(status_code=403, detail="No puedes ver este informe")

    from app.models.area import Area
    area = db.query(Area).filter(Area.id == informe.area_id).first()
    out = InformeOut.model_validate(informe)
    out.area_nombre = area.nombre if area else None
    jefe = _mapa_area_jefe(db).get(informe.area_id)
    if jefe:
        out.jefe_id, out.jefe_nombre = jefe.id, jefe.nombre_completo
    return {"data": out, "message": "OK", "success": True}


@router.put("/{informe_id}/secciones", response_model=dict)
def actualizar_secciones(
    informe_id: int,
    payload: SeccionesUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Permite al jefe editar secciones del informe antes de exportar."""
    informe = _informe_o_404(db, informe_id)
    _puede_editar(db, current_user, informe)

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


@router.put("/{informe_id}/contenido", response_model=dict)
def actualizar_contenido(
    informe_id: int,
    payload: ContenidoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Reemplaza el contenido completo del informe.

    Es el endpoint del editor genérico: TODO el contenido es editable, incluidos
    los nombres de los docentes, el área, el período y el texto de la carátula.
    """
    informe = _informe_o_404(db, informe_id)
    _puede_editar(db, current_user, informe)

    informe.contenido_json = payload.contenido_json
    informe.estado = "REVISANDO"
    flag_modified(informe, "contenido_json")  # sin esto la columna JSON no persiste
    db.commit()
    db.refresh(informe)
    return {
        "data": InformeOut.model_validate(informe),
        "message": "Contenido actualizado",
        "success": True,
    }


@router.post("/{informe_id}/generar-docx", response_model=dict)
def generar_docx_endpoint(
    informe_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Genera o regenera el .docx del informe."""
    informe = _informe_o_404(db, informe_id)
    _puede_editar(db, current_user, informe)

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
    current_user: Usuario = Depends(_director_o_jefe),
):
    """
    Genera el borrador del informe solicitado usando IA.
    Director: cualquier informe. Jefe: informes de su área (2,3,4) + Informe 1.
    El endpoint responde inmediatamente y el trabajo ocurre en background.
    """
    from app.services.generador_informes import (
        generar_informe_1, generar_informe_2, generar_informe_3, generar_informe_4,
    )

    generadores = {1: generar_informe_1, 2: generar_informe_2, 3: generar_informe_3, 4: generar_informe_4}
    fn = generadores.get(payload.tipo_informe)
    if fn is None:
        raise HTTPException(status_code=400, detail="tipo_informe debe ser 1, 2, 3 o 4")

    _validar_area_jefe(db, current_user, payload.area_id, payload.tipo_informe)

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
