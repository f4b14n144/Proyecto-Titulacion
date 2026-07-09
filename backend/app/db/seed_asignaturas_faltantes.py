"""
Agrega asignaturas de la Carrera de Computación que aparecen en los Excel de
calificaciones pero no estaban en el catálogo del P67.

Sin ellas, `excel_processor` las descarta con "Sin asignación registrada" y no
llegan a ningún informe.

Uso:
    docker compose exec backend python -m app.db.seed_asignaturas_faltantes
"""
import app.db.base  # noqa: F401  (registra todos los modelos)
from loguru import logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.db.seed_p67 import _codigo, _nombre_a_email
from app.models.area import Area
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.periodo import PeriodoAcademico
from app.models.rol import Rol
from app.models.usuario import Usuario

# (asignatura, área, docente, grupo) — tomado del Excel de calificaciones del P67.
# Si la asignatura o el docente no existen, se crean; si ya existen, se reutilizan.
FALTANTES: list[tuple[str, str, str, str]] = [
    ("INGENIERÍA DE SOFTWARE",        "Programación y Software", "ORTIZ OCHOA MAURICIO SERGIO",     "G1"),
    ("ANÁLISIS Y DISEÑO DE SISTEMAS", "Sistemas de Información", "ARCE CUESTA DIANA CAROLINA",      "G1"),
    # Grupo compartido: 1 estudiante de Computación cursando Cálculo Integral en el G10
    ("CÁLCULO INTEGRAL",              "Ciencias Básicas",        "SAGBAY SACAQUIRIN JORGE GIOVANNI", "G10"),
]


def _codigo_unico(db, nombre: str) -> str:
    """Genera un código de asignatura único (mismo esquema que seed_p67)."""
    base = _codigo(nombre)
    codigo, sufijo = base, 0
    while db.query(Asignatura).filter(Asignatura.codigo == codigo).first():
        sufijo += 1
        codigo = f"{base}{sufijo}"
    return codigo


def _obtener_o_crear_docente(db, nombre: str, rol_docente_id: int) -> Usuario:
    email = _nombre_a_email(nombre)
    usuario = db.query(Usuario).filter(Usuario.email_institucional == email).first()
    if usuario:
        return usuario
    usuario = Usuario(
        nombre_completo=nombre.title(),
        titulo="Ing.",
        email_institucional=email,
        hashed_password=hash_password("pass123"),
        rol_id=rol_docente_id,
        activo=True,
    )
    db.add(usuario)
    db.flush()
    print(f"  Docente creado: {usuario.nombre_completo} ({email}) — pass123")
    return usuario


def seed_asignaturas_faltantes() -> None:
    db = SessionLocal()
    try:
        periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.activo.is_(True)).first()
        if periodo is None:
            raise RuntimeError("No hay período activo. Ejecuta seed_p67 primero.")

        rol_docente = db.query(Rol).filter(Rol.nombre == "DOCENTE").first()
        if rol_docente is None:
            raise RuntimeError("Rol DOCENTE no encontrado. Ejecuta seed.py primero.")

        for nombre_asig, nombre_area, nombre_doc, grupo in FALTANTES:
            area = db.query(Area).filter(Area.nombre == nombre_area).first()
            if area is None:
                logger.warning(f"Área '{nombre_area}' no existe — se omite {nombre_asig}")
                continue

            asig = db.query(Asignatura).filter(Asignatura.nombre == nombre_asig).first()
            if asig is None:
                asig = Asignatura(
                    area_id=area.id,
                    nombre=nombre_asig,
                    codigo=_codigo_unico(db, nombre_asig),
                )
                db.add(asig)
                db.flush()
                print(f"  Asignatura creada: [{asig.codigo}] {nombre_asig} → {nombre_area}")
            else:
                print(f"  Asignatura ya existía: {nombre_asig}")

            docente = _obtener_o_crear_docente(db, nombre_doc, rol_docente.id)

            existe = (
                db.query(AsignacionDocente)
                .filter(
                    AsignacionDocente.asignatura_id == asig.id,
                    AsignacionDocente.periodo_id == periodo.id,
                    AsignacionDocente.grupo == grupo,
                )
                .first()
            )
            if existe is None:
                db.add(AsignacionDocente(
                    usuario_id=docente.id,
                    asignatura_id=asig.id,
                    periodo_id=periodo.id,
                    grupo=grupo,
                ))
                print(f"  Asignación creada: {docente.nombre_completo} — {nombre_asig} ({grupo})")
            else:
                print(f"  Asignación ya existía: {nombre_asig} ({grupo})")

        db.commit()
        print("\nListo.\n")
    finally:
        db.close()


if __name__ == "__main__":
    seed_asignaturas_faltantes()
