"""
Establece la contraseña por defecto 'pass123' para TODOS los usuarios
con rol base DOCENTE. (El director conserva su propia contraseña.)

Ejecutar:
  docker compose exec backend python -m app.db.reset_passwords_docentes
"""
import app.db.base  # noqa: F401 — carga modelos
from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.core.security import hash_password

PASSWORD_DEFECTO = "pass123"


def reset():
    db = SessionLocal()
    try:
        rol_docente = db.query(Rol).filter(Rol.nombre == "DOCENTE").first()
        if not rol_docente:
            print("No existe el rol DOCENTE. Ejecuta primero: python -m app.db.seed")
            return

        docentes = db.query(Usuario).filter(Usuario.rol_id == rol_docente.id).all()
        for u in docentes:
            u.hashed_password = hash_password(PASSWORD_DEFECTO)
        db.commit()

        print(f"Contraseña '{PASSWORD_DEFECTO}' aplicada a {len(docentes)} docente(s).")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset()
