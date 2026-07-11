"""
Envío de correos institucionales personalizados.

Tres flujos, todos con **modo prueba** (`modo_prueba=true`) que devuelve los
correos ya renderizados sin enviarlos:

  - a docentes: solicitud de observaciones y acciones de mejora por materia
  - a estudiantes: consulta sobre el desarrollo de cada materia que cursan
  - a docentes: coordinación de la visita áulica

Los envíos reales se hacen en segundo plano para no bloquear la respuesta.
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.models.area import Area
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.consejo import ConsejoCarrera
from app.models.estudiante import Estudiante, EstudianteAsignatura
from app.models.jefatura import JefaturaArea
from app.models.usuario import Usuario
from app.services import plantillas_correo as plantillas
from app.services.mail_service import enviar_email

router = APIRouter()

_director_o_jefe = require_role("DIRECTOR_CARRERA", "JEFE_AREA")


class EnvioBase(BaseModel):
    modo_prueba: bool = True
    # Red de seguridad para probar el formato: si se indica, TODOS los correos se
    # envían a esa dirección en vez de a los destinatarios reales. El destinatario
    # original queda anotado en el asunto.
    redirigir_a: Optional[str] = None
    # Tope de correos a preparar/enviar (útil al probar: evita mandar decenas).
    limite: Optional[int] = None


class EnvioDocentesIn(EnvioBase):
    consejo_id: int
    area_id: Optional[int] = None


class EnvioEstudiantesIn(EnvioBase):
    periodo_id: int
    asignatura_id: Optional[int] = None


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _remitente(db: Session, usuario: Usuario) -> tuple[str, str]:
    """Nombre y cargo que van en la firma, tomados del usuario que envía."""
    rol = getattr(usuario, "rol_efectivo", usuario.rol.nombre)
    nombre = f"{usuario.titulo} {usuario.nombre_completo}".strip() if usuario.titulo \
        else usuario.nombre_completo

    area_nombre = None
    if rol == "JEFE_AREA":
        jefatura = db.query(JefaturaArea).filter(JefaturaArea.usuario_id == usuario.id).first()
        if jefatura:
            area = db.query(Area).filter(Area.id == jefatura.area_id).first()
            area_nombre = area.nombre if area else None

    return nombre, plantillas.cargo_de_rol(rol, area_nombre)


def _areas_permitidas(db: Session, usuario: Usuario, area_id: Optional[int]) -> Optional[int]:
    """El jefe solo puede enviar correos de su área; la directora, de cualquiera."""
    rol = getattr(usuario, "rol_efectivo", usuario.rol.nombre)
    if rol != "JEFE_AREA":
        return area_id
    jefatura = db.query(JefaturaArea).filter(JefaturaArea.usuario_id == usuario.id).first()
    if not jefatura:
        raise HTTPException(status_code=403, detail="No tienes un área asignada")
    if area_id is not None and area_id != jefatura.area_id:
        raise HTTPException(status_code=403, detail="Solo puedes enviar correos de tu área")
    return jefatura.area_id


def _asignaciones(db: Session, periodo_id: int, area_id: Optional[int]) -> list[tuple[AsignacionDocente, Asignatura, Usuario]]:
    q = (
        db.query(AsignacionDocente, Asignatura, Usuario)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .join(Usuario, AsignacionDocente.usuario_id == Usuario.id)
        .filter(AsignacionDocente.periodo_id == periodo_id, Usuario.activo.is_(True))
    )
    if area_id:
        q = q.filter(Asignatura.area_id == area_id)
    return q.order_by(Usuario.nombre_completo, Asignatura.nombre).all()


def _despachar(correos: list[dict]) -> None:
    """Envía la tanda; un fallo individual no detiene al resto."""
    enviados, fallidos = 0, 0
    for c in correos:
        try:
            enviar_email(c["destinatario"], c["asunto"], c["cuerpo_html"])
            enviados += 1
        except Exception as e:  # noqa: BLE001
            fallidos += 1
            logger.error(f"No se pudo enviar a {c['destinatario']}: {e}")
    logger.info(f"Tanda de correos terminada: {enviados} enviados, {fallidos} fallidos")


def _aplicar_opciones(correos: list[dict], cfg: EnvioBase) -> list[dict]:
    """Aplica el tope y la redirección de prueba antes de enviar nada."""
    if cfg.limite is not None:
        correos = correos[: max(cfg.limite, 0)]

    if cfg.redirigir_a:
        redirigidos = []
        for c in correos:
            copia = dict(c)
            copia["destinatario_real"] = c["destinatario"]
            copia["destinatario"] = cfg.redirigir_a
            copia["asunto"] = f"[PRUEBA · para {c['destinatario']}] {c['asunto']}"
            redirigidos.append(copia)
        correos = redirigidos
    return correos


def _respuesta(correos: list[dict], cfg: EnvioBase, tareas: BackgroundTasks) -> dict:
    correos = _aplicar_opciones(correos, cfg)

    if cfg.modo_prueba:
        return {
            "data": {"modo_prueba": True, "total": len(correos), "correos": correos},
            "message": f"{len(correos)} correo(s) preparados. No se envió ninguno.",
            "success": True,
        }

    tareas.add_task(_despachar, correos)
    destino = f" (redirigidos a {cfg.redirigir_a})" if cfg.redirigir_a else ""
    return {
        "data": {
            "modo_prueba": False,
            "total": len(correos),
            "redirigido_a": cfg.redirigir_a,
        },
        "message": f"Enviando {len(correos)} correo(s) en segundo plano{destino}.",
        "success": True,
    }


# ──────────────────────────────────────────────────────────────────
# Correo a docentes — observaciones y acciones de mejora (Anexo B)
# ──────────────────────────────────────────────────────────────────

@router.post("/docentes", response_model=dict)
def correos_a_docentes(
    payload: EnvioDocentesIn,
    tareas: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """Un correo por cada materia que dicta cada docente."""
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == payload.consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    area_id = _areas_permitidas(db, current_user, payload.area_id)
    rem_nombre, rem_cargo = _remitente(db, current_user)

    correos = []
    for _, asignatura, docente in _asignaciones(db, consejo.periodo_id, area_id):
        asunto, cuerpo = plantillas.correo_docente_materia(
            titulo_docente=docente.titulo or "",
            nombre_docente=docente.nombre_completo,
            nombre_materia=asignatura.nombre,
            remitente_nombre=rem_nombre,
            remitente_cargo=rem_cargo,
        )
        correos.append({
            "destinatario": docente.email_institucional,
            "asunto": asunto,
            "materia": asignatura.nombre,
            "cuerpo_html": cuerpo,
        })

    return _respuesta(correos, payload, tareas)


# ──────────────────────────────────────────────────────────────────
# Correo a docentes — visitas áulicas (requerimiento 14)
# ──────────────────────────────────────────────────────────────────

@router.post("/visitas-aulicas", response_model=dict)
def correos_visitas_aulicas(
    payload: EnvioDocentesIn,
    tareas: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """Coordina la visita áulica con cada docente, por materia."""
    consejo = db.query(ConsejoCarrera).filter(ConsejoCarrera.id == payload.consejo_id).first()
    if not consejo:
        raise HTTPException(status_code=404, detail="Consejo no encontrado")

    area_id = _areas_permitidas(db, current_user, payload.area_id)
    rem_nombre, rem_cargo = _remitente(db, current_user)

    correos = []
    for _, asignatura, docente in _asignaciones(db, consejo.periodo_id, area_id):
        asunto, cuerpo = plantillas.correo_visita_aulica(
            titulo_docente=docente.titulo or "",
            nombre_docente=docente.nombre_completo,
            nombre_materia=asignatura.nombre,
            remitente_nombre=rem_nombre,
            remitente_cargo=rem_cargo,
        )
        correos.append({
            "destinatario": docente.email_institucional,
            "asunto": asunto,
            "materia": asignatura.nombre,
            "cuerpo_html": cuerpo,
        })

    return _respuesta(correos, payload, tareas)


# ──────────────────────────────────────────────────────────────────
# Correo a estudiantes — consulta por materia (Anexo C)
# ──────────────────────────────────────────────────────────────────

@router.post("/estudiantes", response_model=dict)
def correos_a_estudiantes(
    payload: EnvioEstudiantesIn,
    tareas: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_director_o_jefe),
):
    """
    Un correo por cada materia que cursa cada estudiante, con el nombre de la
    materia y el de su docente.
    """
    rem_nombre, rem_cargo = _remitente(db, current_user)

    # Docente de cada asignatura en el período (si hay varios grupos, el primero)
    docente_por_asignatura: dict[int, Usuario] = {}
    for _, asignatura, docente in _asignaciones(db, payload.periodo_id, None):
        docente_por_asignatura.setdefault(asignatura.id, docente)

    q = db.query(Estudiante).filter(Estudiante.periodo_id == payload.periodo_id)
    estudiantes = q.order_by(Estudiante.nombre_completo).all()

    correos: list[dict] = []
    sin_docente: list[str] = []

    for estudiante in estudiantes:
        for materia in estudiante.materias:
            if payload.asignatura_id and materia.asignatura_id != payload.asignatura_id:
                continue
            docente = docente_por_asignatura.get(materia.asignatura_id or -1)
            if docente is None:
                # Sin docente asignado no se puede personalizar el correo
                if materia.asignatura_nombre not in sin_docente:
                    sin_docente.append(materia.asignatura_nombre)
                continue

            asunto, cuerpo = plantillas.correo_estudiante_materia(
                nombre_estudiante=estudiante.nombre_completo,
                nombre_materia=materia.asignatura_nombre,
                titulo_docente=docente.titulo or "",
                nombre_docente=docente.nombre_completo,
                remitente_nombre=rem_nombre,
                remitente_cargo=rem_cargo,
            )
            correos.append({
                "destinatario": estudiante.correo,
                "asunto": asunto,
                "materia": materia.asignatura_nombre,
                "cuerpo_html": cuerpo,
            })

    respuesta = _respuesta(correos, payload, tareas)
    if sin_docente:
        respuesta["data"]["materias_sin_docente"] = sin_docente
        respuesta["message"] += (
            f" Se omitieron {len(sin_docente)} materia(s) sin docente asignado."
        )
    return respuesta
