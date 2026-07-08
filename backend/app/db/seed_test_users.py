"""
Cuentas de prueba para validar roles y el frontend.

Ejecutar:
  docker compose exec backend python -m app.db.seed_test_users

Crea/asegura:
  - Director de carrera (rol DIRECTOR_CARRERA)
  - Jefe de área (rol JEFE_AREA) asignado a un área del período activo
  - Docente de prueba (rol DOCENTE)
"""
import app.db.base  # noqa: F401 — registra modelos
from app.db.session import SessionLocal
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.area import Area
from app.models.periodo import PeriodoAcademico
from app.models.jefatura import JefaturaArea
from app.core.security import hash_password


# (email, nombre, rol_base, password)
# El rol BASE de todo profesor es DOCENTE. La jefatura (asignada abajo) es la
# que hace que el usuario opere como JEFE_AREA (rol efectivo). Solo el director
# tiene rol DIRECTOR_CARRERA.
CUENTAS = [
    ("director@ups.edu.ec",     "Director de Carrera (Prueba)", "DIRECTOR_CARRERA", "director123"),
    ("jefe@ups.edu.ec",         "Docente Jefe de Área (Prueba)", "DOCENTE",         "pass123"),
    ("docente@ups.edu.ec",      "Docente (Prueba)",             "DOCENTE",          "pass123"),
]

# Área a la que se asigna el jefe (debe tener informes para probar el panel)
AREA_JEFE = "Programación y Software"


def seed_test_users():
    db = SessionLocal()
    try:
        roles = {r.nombre: r for r in db.query(Rol).all()}
        if not roles:
            raise ValueError("No hay roles. Ejecuta primero: python -m app.db.seed")

        creados = {}
        for email, nombre, rol_nombre, password in CUENTAS:
            u = db.query(Usuario).filter(Usuario.email_institucional == email).first()
            if not u:
                u = Usuario(
                    nombre_completo=nombre,
                    email_institucional=email,
                    hashed_password=hash_password(password),
                    rol_id=roles[rol_nombre].id,
                    activo=True,
                )
                db.add(u)
                db.flush()
                print(f"  Creado: {email} ({rol_nombre}) / {password}")
            else:
                # Asegurar rol y password conocidos
                u.rol_id = roles[rol_nombre].id
                u.hashed_password = hash_password(password)
                u.activo = True
                print(f"  Actualizado: {email} ({rol_nombre}) / {password}")
            creados[rol_nombre] = u

        # Asignar jefatura al jefe de prueba en el período activo
        periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.activo == True).first()
        area = db.query(Area).filter(Area.nombre == AREA_JEFE).first()
        jefe = creados.get("JEFE_AREA")

        if periodo and area and jefe:
            existe = db.query(JefaturaArea).filter(
                JefaturaArea.area_id == area.id,
                JefaturaArea.periodo_id == periodo.id,
            ).first()
            if existe:
                existe.usuario_id = jefe.id
                print(f"  Jefatura actualizada: {jefe.email_institucional} → {area.nombre} ({periodo.nombre})")
            else:
                db.add(JefaturaArea(usuario_id=jefe.id, area_id=area.id, periodo_id=periodo.id))
                print(f"  Jefatura creada: {jefe.email_institucional} → {area.nombre} ({periodo.nombre})")

        # Asignar un par de asignaturas al docente de prueba (para que su panel muestre datos)
        from app.models.asignatura import Asignatura
        from app.models.asignacion import AsignacionDocente
        docente = creados.get("DOCENTE")
        if periodo and docente and area:
            asigs = (
                db.query(Asignatura)
                .filter(Asignatura.area_id == area.id)
                .order_by(Asignatura.nombre)
                .limit(2)
                .all()
            )
            for asig in asigs:
                ya = db.query(AsignacionDocente).filter(
                    AsignacionDocente.usuario_id == docente.id,
                    AsignacionDocente.asignatura_id == asig.id,
                    AsignacionDocente.periodo_id == periodo.id,
                    AsignacionDocente.grupo == "G1",
                ).first()
                if not ya:
                    db.add(AsignacionDocente(
                        usuario_id=docente.id, asignatura_id=asig.id,
                        periodo_id=periodo.id, grupo="G1",
                    ))
                    print(f"  Asignación docente prueba: {asig.nombre} G1")

        db.commit()
        print("\n=== CUENTAS DE PRUEBA LISTAS ===")
        print("  Director: director@ups.edu.ec / director123")
        print("  Jefe de área: jefe@ups.edu.ec / jefe123  (Área: Programación y Software)")
        print("  Docente: docente@ups.edu.ec / docente123")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_users()
