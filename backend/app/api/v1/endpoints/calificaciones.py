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
# Director, jefe de área y docente pueden subir calificaciones (con distinto alcance)
_puede_subir = require_role("DIRECTOR_CARRERA", "JEFE_AREA", "DOCENTE")

TIPOS_VALIDOS = {"INTERCICLO", "FINAL"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _cargar_asignaciones(
    db: Session, periodo_id: int,
    usuario_id: int | None = None, areas: list[int] | None = None,
) -> list[dict]:
    """
    Devuelve las asignaciones del período con info de asignatura.
    - usuario_id (docente): solo SUS asignaciones.
    - areas (jefe): solo las asignaturas de su(s) área(s).
    - ninguno (director): todas.
    """
    q = (
        db.query(AsignacionDocente, Asignatura)
        .join(Asignatura, AsignacionDocente.asignatura_id == Asignatura.id)
        .filter(AsignacionDocente.periodo_id == periodo_id)
    )
    if usuario_id is not None:
        q = q.filter(AsignacionDocente.usuario_id == usuario_id)
    if areas is not None:
        q = q.filter(Asignatura.area_id.in_(areas))
    rows = q.all()
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


def _cargar_catalogo(db: Session, areas: list[int] | None) -> list[dict]:
    """
    Catálogo de materias del alcance (para reconocer materias cuyo grupo aún no
    está asignado). Director: todas; jefe: las de su(s) área(s). Para el docente
    se devuelve vacío: no crea asignaciones nuevas, solo sube las suyas.
    """
    q = db.query(Asignatura).filter(Asignatura.activa.is_(True))
    if areas is not None:
        q = q.filter(Asignatura.area_id.in_(areas))
    return [{"id": a.id, "nombre": a.nombre, "codigo": a.codigo} for a in q.all()]


def _resolver_o_crear_docente(db: Session, nombre_completo: str) -> Usuario | None:
    """
    Encuentra al docente por su nombre (como viene en el Excel) o lo crea si no
    existe. Devuelve None si el Excel no trae nombre de profesor.
    """
    from app.services.excel_processor import _normalizar

    nombre = (nombre_completo or "").strip()
    if not nombre:
        return None

    objetivo = _normalizar(nombre)
    for u in db.query(Usuario).all():
        if _normalizar(u.nombre_completo) == objetivo:
            return u

    # No existe: se crea como DOCENTE con un correo derivado del nombre
    from app.models.rol import Rol
    from app.core.security import hash_password

    rol_doc = db.query(Rol).filter(Rol.nombre == "DOCENTE").first()
    partes = objetivo.split()
    base = f"{partes[0]}.{partes[-1]}" if len(partes) >= 2 else (partes[0] if partes else "docente")
    email = f"{base}@ups.edu.ec"
    n = 1
    while db.query(Usuario).filter(Usuario.email_institucional == email).first():
        n += 1
        email = f"{base}{n}@ups.edu.ec"

    docente = Usuario(
        nombre_completo=nombre,
        titulo="Ing.",
        email_institucional=email,
        hashed_password=hash_password("pass123"),
        rol_id=rol_doc.id if rol_doc else None,
        activo=True,
    )
    db.add(docente)
    db.flush()
    return docente


def _alcance_por_rol(db: Session, current_user: Usuario, periodo_id: int) -> tuple[int | None, list[int] | None]:
    """Devuelve (usuario_id, areas) para filtrar según el rol:
    docente → sus materias; jefe → sus áreas; director → todo."""
    rol = getattr(current_user, "rol_efectivo", current_user.rol.nombre)
    if rol == "DOCENTE":
        return current_user.id, None
    if rol == "JEFE_AREA":
        from app.models.jefatura import JefaturaArea
        areas = [a for (a,) in db.query(JefaturaArea.area_id).filter(
            JefaturaArea.usuario_id == current_user.id,
            JefaturaArea.periodo_id == periodo_id,
        ).all()]
        return None, (areas or [-1])
    return None, None  # director


@router.post("/preview", response_model=dict)
async def preview_calificaciones(
    archivo: UploadFile = File(...),
    tipo: str = Form(...),
    consejo_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(_puede_subir),
):
    """Procesa el Excel y devuelve un preview sin guardar en DB.
    Docente: solo sus materias; jefe: su área; director: todas."""
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
        uid, areas = _alcance_por_rol(db, current_user, consejo.periodo_id)
        asignaciones = _cargar_asignaciones(db, consejo.periodo_id, uid, areas)
        if not asignaciones:
            detalle = ("No tienes asignaturas registradas en el período de este consejo"
                       if (uid or areas) else
                       "No hay asignaciones docente registradas para el período de este consejo")
            raise HTTPException(status_code=400, detail=detalle)

        # El docente (uid) solo sube sus materias ya asignadas: catálogo vacío para
        # que no cree asignaciones nuevas. Director y jefe sí autocompletan.
        catalogo = [] if uid is not None else _cargar_catalogo(db, areas)
        resultados, adv_archivo = procesar_excel(ruta_tmp, tipo.upper(), asignaciones, catalogo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(ruta_tmp)

    # Avisos del archivo completo (filtro de carrera, sin asignación) + los de cada asignatura
    advertencias_globales = list(adv_archivo) + [
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
    current_user: Usuario = Depends(_puede_subir),
):
    """Procesa el Excel y guarda las calificaciones en DB (sobreescribe si ya existen).
    Docente: solo sus materias; jefe: su área; director: todas."""
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
        uid, areas = _alcance_por_rol(db, current_user, consejo.periodo_id)
        asignaciones = _cargar_asignaciones(db, consejo.periodo_id, uid, areas)
        if not asignaciones:
            detalle = ("No tienes asignaturas registradas en este período"
                       if (uid or areas) else
                       "No hay asignaciones registradas para este período")
            raise HTTPException(status_code=400, detail=detalle)

        catalogo = [] if uid is not None else _cargar_catalogo(db, areas)
        resultados, _ = procesar_excel(ruta_tmp, tipo.upper(), asignaciones, catalogo)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(ruta_tmp)

    guardados: list[CalificacionOut] = []
    asignaciones_creadas = 0
    for r in resultados:
        # Si la materia+grupo venía sin asignación (el Excel manda), crear el
        # docente del Excel y su asignación, para que la materia entre al informe.
        if r.get("asignacion_faltante") and r.get("profesor_excel"):
            docente = _resolver_o_crear_docente(db, r["profesor_excel"])
            if docente:
                ya = db.query(AsignacionDocente).filter(
                    AsignacionDocente.usuario_id == docente.id,
                    AsignacionDocente.asignatura_id == r["asignatura_id"],
                    AsignacionDocente.periodo_id == consejo.periodo_id,
                    AsignacionDocente.grupo == r["grupo"],
                ).first()
                if not ya:
                    db.add(AsignacionDocente(
                        usuario_id=docente.id,
                        asignatura_id=r["asignatura_id"],
                        periodo_id=consejo.periodo_id,
                        grupo=r["grupo"],
                    ))
                    db.flush()
                    asignaciones_creadas += 1

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

    msg = f"{len(guardados)} registro(s) guardado(s) correctamente"
    if asignaciones_creadas:
        msg += f"; {asignaciones_creadas} asignación(es) creada(s) desde el Excel"
    return {
        "data": [c.model_dump() for c in guardados],
        "message": msg,
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
