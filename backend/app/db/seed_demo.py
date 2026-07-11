"""
Deja el sistema listo para una demostración, en un solo comando.

    docker compose exec backend python -m app.db.seed_demo

Ejecuta, en orden y de forma idempotente:
  1. seed             — roles, directora y áreas curriculares
  2. seed_p67         — período 67, consejo, 44 asignaturas, 39 docentes, asignaciones
  3. seed_asignaturas_faltantes — materias de Computación que faltaban en el catálogo
  4. seed_jefaturas   — asigna las 6 áreas a docentes reales
  5. seed_test_users  — cuentas de prueba por rol
  6. reset_passwords_docentes — todos los docentes con pass123

Al terminar imprime las cuentas con las que entrar.

No carga calificaciones: los .xlsx tienen datos reales de estudiantes y no están en
el repositorio. Para cargarlos, entra como directora y usa "Subir Calificaciones".
"""
import app.db.base  # noqa: F401  (registra todos los modelos)
from loguru import logger

from app.db.session import SessionLocal
from app.models.area import Area
from app.models.asignatura import Asignatura
from app.models.jefatura import JefaturaArea
from app.models.usuario import Usuario


PASOS = [
    ("Roles, directora y áreas",        "app.db.seed",                        "seed"),
    ("Período 67, docentes y materias", "app.db.seed_p67",                    "seed_p67"),
    ("Asignaturas faltantes",           "app.db.seed_asignaturas_faltantes",  "seed_asignaturas_faltantes"),
    ("Jefaturas de área (reales)",      "app.db.seed_jefaturas",              "seed_jefaturas"),
    ("Cuentas de prueba por rol",       "app.db.seed_test_users",             "seed_test_users"),
    ("Contraseñas de docentes",         "app.db.reset_passwords_docentes",    "reset"),
]


def _ejecutar(modulo: str, funcion: str) -> None:
    import importlib

    mod = importlib.import_module(modulo)
    fn = getattr(mod, funcion)  # si no existe, es un error del script: que se vea
    fn()


def _resumen() -> None:
    db = SessionLocal()
    try:
        print("\n" + "═" * 74)
        print("  SISTEMA LISTO PARA LA DEMOSTRACIÓN")
        print("═" * 74)

        print("\n  Catálogo")
        print(f"    Áreas curriculares : {db.query(Area).count()}")
        print(f"    Asignaturas        : {db.query(Asignatura).count()}")
        print(f"    Usuarios           : {db.query(Usuario).count()}")

        print("\n  Entrar como DIRECTORA")
        print("    director@ups.edu.ec  /  director123")

        print("\n  Entrar como JEFE DE ÁREA  (contraseña: pass123)")
        filas = (
            db.query(JefaturaArea, Area, Usuario)
            .join(Area, JefaturaArea.area_id == Area.id)
            .join(Usuario, JefaturaArea.usuario_id == Usuario.id)
            .order_by(Area.nombre)
            .all()
        )
        for _, area, jefe in filas:
            print(f"    {jefe.email_institucional:34} {area.nombre}")

        print("\n  Entrar como DOCENTE  (contraseña: pass123)")
        print("    docente@ups.edu.ec")
        print("    …o cualquier docente del período 67")

        print("\n  Siguiente paso")
        print("    1. Entra como directora → Subir Calificaciones (Excel del período)")
        print("    2. Entra como jefe de área → genera sus informes 2, 3 y 4")
        print("    3. Ver Informes → previsualizar, editar y descargar el .docx")
        print("\n" + "═" * 74 + "\n")
    finally:
        db.close()


def main() -> None:
    for i, (titulo, modulo, funcion) in enumerate(PASOS, start=1):
        print(f"\n[{i}/{len(PASOS)}] {titulo}")
        try:
            _ejecutar(modulo, funcion)
        except Exception as e:  # noqa: BLE001 — un paso ya aplicado no debe abortar la demo
            logger.warning(f"Paso '{titulo}' terminó con aviso: {e}")
    _resumen()


if __name__ == "__main__":
    main()
