from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.core.deps import get_db, require_role
from app.models.consejo import ConsejoCarrera
from app.models.periodo import PeriodoAcademico
from app.models.usuario import Usuario
from app.schemas.consejo import ConsejoCreate, ConsejoUpdate, ConsejoOut

router = APIRouter()

# La fecha límite de los informes va estos días antes de la fecha del consejo.
DIAS_ANTES_LIMITE = 2

_solo_director = require_role("DIRECTOR_CARRERA")
# La lista de consejos la necesitan los tres roles: el docente elige un consejo para
# registrar sus aportes. (El nombre anterior, `_director_o_jefe`, engañaba: incluía
# también al docente.)
_lectura_todos = require_role("DIRECTOR_CARRERA", "JEFE_AREA", "DOCENTE")

# El contenido del consejo (agenda, resoluciones) y las fechas de entrega son de la
# gestión de la carrera: el docente no accede.
_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")


@router.get("/", response_model=dict)
def listar_consejos(
    periodo_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(_lectura_todos),   # el docente elige consejo en su panel
):
    q = db.query(ConsejoCarrera)
    if periodo_id is not None:
        q = q.filter(ConsejoCarrera.periodo_id == periodo_id)
    consejos = q.order_by(ConsejoCarrera.fecha_consejo.desc()).all()
    return {"data": [ConsejoOut.model_validate(c) for c in consejos], "message": "OK", "success": True}


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_consejo(
    payload: ConsejoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    if not db.query(PeriodoAcademico).filter(PeriodoAcademico.id == payload.periodo_id).first():
        raise HTTPException(status_code=404, detail="Período no encontrado")

    datos = payload.model_dump()
    # La fecha límite va 2 días antes del consejo si no se indicó otra
    if datos.get("fecha_limite_informe") is None:
        datos["fecha_limite_informe"] = payload.fecha_consejo - timedelta(days=DIAS_ANTES_LIMITE)

    consejo = ConsejoCarrera(**datos)
    db.add(consejo)
    db.commit()
    db.refresh(consejo)
    return {"data": ConsejoOut.model_validate(consejo), "message": "Consejo creado", "success": True}


@router.get("/{consejo_id}", response_model=dict)
def obtener_consejo(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")
    return {"data": ConsejoOut.model_validate(consejo), "message": "OK", "success": True}


@router.put("/{consejo_id}", response_model=dict)
def actualizar_consejo(
    consejo_id: int,
    payload: ConsejoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    if consejo.flujo_estado == "COMPLETADO":
        raise HTTPException(status_code=400, detail="No se puede modificar un consejo completado")

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(consejo, campo, valor)

    db.commit()
    db.refresh(consejo)
    return {"data": ConsejoOut.model_validate(consejo), "message": "Consejo actualizado", "success": True}


@router.delete("/{consejo_id}", response_model=dict)
def eliminar_consejo(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    if consejo.flujo_estado != "PENDIENTE":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden eliminar consejos en estado PENDIENTE",
        )

    db.delete(consejo)
    db.commit()
    return {"data": None, "message": "Consejo eliminado", "success": True}


# ──────────────────────────────────────────────────────────────────
# Fechas de entrega de cada informe (1-4)
#
# El planificador envía un recordatorio 2 días antes de cada una, a los jefes de
# área (que elaboran el informe) y a los docentes (que registran sus aportes).
# ──────────────────────────────────────────────────────────────────

class FechaEntregaIn(BaseModel):
    tipo_informe: int   # 1 | 2 | 3 | 4
    fecha_entrega: date


class FechasEntregaUpdate(BaseModel):
    fechas: list[FechaEntregaIn]


@router.get("/{consejo_id}/fechas-entrega", response_model=dict)
def obtener_fechas_entrega(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    """Fechas de entrega de los 4 informes, y cuándo saldría el recordatorio."""
    from app.core.scheduler import DIAS_ANTES
    from app.models.fecha_entrega import FechaEntregaInforme

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    filas = (
        db.query(FechaEntregaInforme)
        .filter(FechaEntregaInforme.consejo_id == consejo_id)
        .order_by(FechaEntregaInforme.tipo_informe)
        .all()
    )
    return {
        "data": [
            {
                "tipo_informe": f.tipo_informe,
                "fecha_entrega": str(f.fecha_entrega),
                "fecha_recordatorio": str(f.fecha_entrega - timedelta(days=DIAS_ANTES)),
            }
            for f in filas
        ],
        "message": f"{len(filas)} fecha(s) configurada(s)",
        "success": True,
    }


@router.put("/{consejo_id}/fechas-entrega", response_model=dict)
def guardar_fechas_entrega(
    consejo_id: int,
    payload: FechasEntregaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """
    Fija las fechas de entrega y **reprograma los recordatorios** en el acto.

    Solo la Dirección de Carrera. Es un upsert por tipo de informe: se puede volver
    a entrar y cambiar una fecha sin borrar las demás.
    """
    from app.core.scheduler import programar_recordatorios_consejo
    from app.models.fecha_entrega import FechaEntregaInforme

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    existentes = {
        f.tipo_informe: f
        for f in db.query(FechaEntregaInforme).filter(
            FechaEntregaInforme.consejo_id == consejo_id
        )
    }

    for item in payload.fechas:
        if item.tipo_informe not in (1, 2, 3, 4):
            raise HTTPException(status_code=400, detail="tipo_informe debe ser 1, 2, 3 o 4")
        fila = existentes.get(item.tipo_informe)
        if fila is None:
            db.add(FechaEntregaInforme(
                consejo_id=consejo_id,
                tipo_informe=item.tipo_informe,
                fecha_entrega=item.fecha_entrega,
            ))
        else:
            fila.fecha_entrega = item.fecha_entrega

    db.commit()

    # Sin esto las fechas quedarían guardadas pero nadie avisaría de ellas
    programados = programar_recordatorios_consejo(consejo_id)

    return {
        "data": {"guardadas": len(payload.fechas), "recordatorios_programados": programados},
        "message": (
            f"{len(payload.fechas)} fecha(s) guardada(s). "
            f"{programados} recordatorio(s) programado(s)."
        ),
        "success": True,
    }


# ──────────────────────────────────────────────────────────────────
# Contenido del Informe 1 escrito por la DIRECCIÓN
# Es común al consejo y se propaga en solo lectura al Informe 1 de cada área.
# ──────────────────────────────────────────────────────────────────

class ContenidoDireccionUpdate(BaseModel):
    secciones: dict[str, str]
    nombre_director: Optional[str] = None


def _contenido_out(contenido) -> dict:
    return {
        "consejo_id": contenido.consejo_id,
        "secciones": contenido.secciones or {},
        "nombre_director": contenido.nombre_director or "",
    }


@router.get("/{consejo_id}/contenido-direccion", response_model=dict)
def obtener_contenido_direccion(
    consejo_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_director_o_jefe),
):
    """Lo lee la directora (para editar) y los jefes (en solo lectura)."""
    from app.services.generador_informes import obtener_o_crear_contenido_direccion

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    contenido = obtener_o_crear_contenido_direccion(db, consejo_id)
    return {"data": _contenido_out(contenido), "message": "OK", "success": True}


@router.put("/{consejo_id}/contenido-direccion", response_model=dict)
def actualizar_contenido_direccion(
    consejo_id: int,
    payload: ContenidoDireccionUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_solo_director),
):
    """Solo la directora escribe aquí. Los jefes no pueden modificarlo."""
    from app.services.generador_informes import obtener_o_crear_contenido_direccion

    if not db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first():
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    contenido = obtener_o_crear_contenido_direccion(db, consejo_id)
    contenido.secciones = {**(contenido.secciones or {}), **payload.secciones}
    if payload.nombre_director is not None:
        contenido.nombre_director = payload.nombre_director
    flag_modified(contenido, "secciones")
    db.commit()

    # Propagar el cambio a los Informe 1 que ya existan. Cada uno guarda una COPIA
    # de este contenido (es de solo lectura para el jefe); sin regenerarlos, cada
    # área seguiría mostrando la versión anterior a esta edición. `generar_informe_1`
    # conserva el aporte propio de cada jefe, así que la propagación es segura.
    # (No se regenera el .docx: eso queda bajo demanda, como en el resto del sistema.)
    from app.models.informe import Informe
    from app.services.generador_informes import generar_informe_1

    informes_area = (
        db.query(Informe)
        .filter(Informe.consejo_id == consejo_id, Informe.tipo_informe == 1)
        .all()
    )
    for inf in informes_area:
        generar_informe_1(db, consejo_id, inf.area_id)

    return {
        "data": _contenido_out(contenido),
        "message": (
            f"Contenido de dirección actualizado y propagado a {len(informes_area)} informe(s) de área"
        ),
        "success": True,
    }
