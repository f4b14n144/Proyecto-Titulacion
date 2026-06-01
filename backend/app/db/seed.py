"""
Datos iniciales: roles, usuario admin, áreas base de la Carrera de Computación UPS.
Ejecutar: docker compose exec backend python -m app.db.seed
"""
import app.db.base  # noqa: F401 — carga todos los modelos para SQLAlchemy
from app.db.session import SessionLocal
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.area import Area
from app.core.security import hash_password


ROLES = ["DIRECTOR_CARRERA", "JEFE_AREA", "DOCENTE"]

AREAS_BASE = [
    "Ciencias Básicas",
    "Programación y Software",
    "Redes y Comunicaciones",
    "Sistemas de Información",
    "Inteligencia Artificial y Datos",
]


def seed():
    db = SessionLocal()
    try:
        # Roles
        roles_creados = {}
        for nombre in ROLES:
            rol = db.query(Rol).filter(Rol.nombre == nombre).first()
            if not rol:
                rol = Rol(nombre=nombre)
                db.add(rol)
                db.flush()
                print(f"  Rol creado: {nombre}")
            roles_creados[nombre] = rol

        # Usuario director por defecto
        admin_email = "director@ups.edu.ec"
        admin = db.query(Usuario).filter(Usuario.email_institucional == admin_email).first()
        if not admin:
            admin = Usuario(
                nombre_completo="Director/a de Carrera",
                email_institucional=admin_email,
                hashed_password=hash_password("admin1234"),
                rol_id=roles_creados["DIRECTOR_CARRERA"].id,
            )
            db.add(admin)
            print(f"  Usuario admin creado: {admin_email} / admin1234")

        # Áreas base
        for nombre_area in AREAS_BASE:
            area = db.query(Area).filter(Area.nombre == nombre_area).first()
            if not area:
                db.add(Area(nombre=nombre_area))
                print(f"  Área creada: {nombre_area}")

        db.commit()
        print("Seed completado exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
