"""
Aportes del docente sobre SUS materias: observaciones y acciones de mejora.

Son **sumativos**: cada envío se guarda como un registro nuevo, nunca sobreescribe
los anteriores. Alimentan los informes 3 y 4 del área de la asignatura.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.models.aporte_docente import AporteDocente, TIPOS_APORTE
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.consejo import ConsejoCarrera
from app.models.usuario import Usuario

router = APIRouter()


class AporteIn(BaseModel):
    consejo_id: int
    asignatura_id: int
    grupo: str
    tipo: str  # OBSERVACION | ACCION_MEJORA
    texto: str

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_APORTE:
            raise ValueError(f"tipo debe ser uno de {TIPOS_APORTE}")
        return v

    @field_validator("texto")
    @classmethod
    def _texto_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El texto no puede estar vacío")
        return v.strip()


class AporteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    consejo_id: int
    asignatura_id: int
    grupo: str
    tipo: str
    texto: str
    creado_en: Optional[datetime] = None


def _validar_materia_del_docente(
    db: Session, usuario_id: int, consejo_id: int, asignatura_id: int, grupo: str
) -> None:
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    es_mia = db.query(AsignacionDocente).filter(
        AsignacionDocente.usuario_id == usuario_id,
        AsignacionDocente.asignatura_id == asignatura_id,
        AsignacionDocente.grupo == grupo,
        AsignacionDocente.periodo_id == consejo.periodo_id,
    ).first()
    if not es_mia:
        raise HTTPException(
            status_code=403, detail="Solo puedes registrar aportes de tus propias materias"
        )


@router.get("/mis-materias", response_model=dict)
def mis_materias(
    consejo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Materias asignadas al docente en el período del consejo, con el historial
    completo de sus aportes (observaciones y acciones de mejora) por materia-grupo.
    """
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    filas = (
        db.query(AsignacionDocente, Asignatura)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(
            AsignacionDocente.periodo_id == consejo.periodo_id,
            AsignacionDocente.usuario_id == current_user.id,
        )
        .order_by(Asignatura.nombre, AsignacionDocente.grupo)
        .all()
    )

    aportes = (
        db.query(AporteDocente)
        .filter(
            AporteDocente.consejo_id == consejo_id,
            AporteDocente.usuario_id == current_user.id,
        )
        .order_by(AporteDocente.creado_en.desc())
        .all()
    )

    data = []
    for asignacion, asignatura in filas:
        propios = [
            a for a in aportes
            if a.asignatura_id == asignatura.id and a.grupo == asignacion.grupo
        ]
        data.append({
            "asignatura_id": asignatura.id,
            "asignatura": asignatura.nombre,
            "codigo": asignatura.codigo,
            "grupo": asignacion.grupo,
            "observaciones": [
                AporteOut.model_validate(a) for a in propios if a.tipo == "OBSERVACION"
            ],
            "acciones_mejora": [
                AporteOut.model_validate(a) for a in propios if a.tipo == "ACCION_MEJORA"
            ],
        })

    return {"data": data, "message": f"{len(data)} materia(s)", "success": True}


@router.post("/", response_model=dict, status_code=201)
def crear_aporte(
    payload: AporteIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Registra un aporte nuevo. Los anteriores se conservan (sumativo)."""
    _validar_materia_del_docente(
        db, current_user.id, payload.consejo_id, payload.asignatura_id, payload.grupo
    )

    aporte = AporteDocente(
        consejo_id=payload.consejo_id,
        usuario_id=current_user.id,
        asignatura_id=payload.asignatura_id,
        grupo=payload.grupo,
        tipo=payload.tipo,
        texto=payload.texto,
    )
    db.add(aporte)
    db.commit()
    db.refresh(aporte)
    return {"data": AporteOut.model_validate(aporte), "message": "Aporte registrado", "success": True}


@router.delete("/{aporte_id}", response_model=dict)
def eliminar_aporte(
    aporte_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """El docente puede borrar un aporte propio (por si se equivocó al escribirlo)."""
    aporte = db.query(AporteDocente).filter(AporteDocente.id == aporte_id).first()
    if not aporte:
        raise HTTPException(status_code=404, detail="Aporte no encontrado")
    if aporte.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo puedes eliminar tus propios aportes")
    db.delete(aporte)
    db.commit()
    return {"data": None, "message": "Aporte eliminado", "success": True}


@router.get("/por-materia", response_model=dict)
def aportes_por_materia(
    consejo_id: int,
    asignatura_id: int,
    grupo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Aportes de una materia-grupo — lo usan los jefes al armar sus informes.

    NO es para docentes: aquí se leerían las observaciones que escribió OTRO docente
    sobre su propia materia. Un docente ve las suyas en `/mis-materias`.
    Además, el jefe solo puede consultar las asignaturas de SU área.
    """
    rol = getattr(current_user, "rol_efectivo", current_user.rol.nombre)
    if rol not in ("DIRECTOR_CARRERA", "JEFE_AREA"):
        raise HTTPException(status_code=403, detail="No tienes acceso a los aportes de esta materia")

    if rol == "JEFE_AREA":
        from app.models.jefatura import JefaturaArea

        asignatura = db.query(Asignatura).filter(Asignatura.id == asignatura_id).first()
        if asignatura is None:
            raise HTTPException(status_code=404, detail="Asignatura no encontrada")
        suya = db.query(JefaturaArea).filter(
            JefaturaArea.usuario_id == current_user.id,
            JefaturaArea.area_id == asignatura.area_id,
        ).first()
        if not suya:
            raise HTTPException(status_code=403, detail="Esa asignatura no es de tu área")

    q = db.query(AporteDocente).filter(
        AporteDocente.consejo_id == consejo_id,
        AporteDocente.asignatura_id == asignatura_id,
    )
    if grupo:
        q = q.filter(AporteDocente.grupo == grupo)
    aportes = q.order_by(AporteDocente.creado_en).all()
    return {
        "data": [AporteOut.model_validate(a) for a in aportes],
        "message": "OK",
        "success": True,
    }
