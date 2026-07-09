"""
Asigna la jefatura de cada área curricular a un docente REAL del período.

Reglas del modelo (uq en jefaturas_area):
  - Un área = un jefe por período
  - Un docente = una sola área por período

Estrategia: para cada área se elige un docente que efectivamente dicte alguna
asignatura de esa área en el período; si no queda ninguno libre, se toma
cualquier docente sin jefatura. La asignación es determinista (orden alfabético)
para que el script sea reproducible.

Uso:
    docker compose exec backend python -m app.db.seed_jefaturas
"""
import app.db.base  # noqa: F401  (registra todos los modelos)
from loguru import logger
from app.db.session import SessionLocal
from app.models.area import Area
from app.models.asignacion import AsignacionDocente
from app.models.asignatura import Asignatura
from app.models.jefatura import JefaturaArea
from app.models.periodo import PeriodoAcademico
from app.models.usuario import Usuario


def _periodo_activo(db) -> PeriodoAcademico:
    periodo = db.query(PeriodoAcademico).filter(PeriodoAcademico.activo.is_(True)).first()
    if periodo is None:
        periodo = db.query(PeriodoAcademico).order_by(PeriodoAcademico.id).first()
    if periodo is None:
        raise RuntimeError("No hay períodos académicos. Ejecuta primero seed_p67.")
    return periodo


def _docentes_del_area(db, area_id: int, periodo_id: int) -> list[Usuario]:
    """Docentes que dictan alguna asignatura del área en el período, alfabéticamente."""
    asig_ids = [a.id for a in db.query(Asignatura).filter(Asignatura.area_id == area_id).all()]
    if not asig_ids:
        return []
    usuario_ids = {
        a.usuario_id
        for a in db.query(AsignacionDocente).filter(
            AsignacionDocente.asignatura_id.in_(asig_ids),
            AsignacionDocente.periodo_id == periodo_id,
        )
    }
    if not usuario_ids:
        return []
    return (
        db.query(Usuario)
        .filter(Usuario.id.in_(usuario_ids), Usuario.activo.is_(True))
        .order_by(Usuario.nombre_completo)
        .all()
    )


def seed_jefaturas() -> None:
    db = SessionLocal()
    try:
        periodo = _periodo_activo(db)
        areas = db.query(Area).order_by(Area.id).all()
        logger.info(f"Asignando jefaturas en el período {periodo.nombre} (id={periodo.id})")

        # Limpiar jefaturas previas del período (el script es idempotente)
        borradas = (
            db.query(JefaturaArea).filter(JefaturaArea.periodo_id == periodo.id).delete()
        )
        db.commit()
        if borradas:
            logger.info(f"Se eliminaron {borradas} jefatura(s) previa(s) del período")

        # Solo docentes (el director no puede ser jefe de área)
        usados: set[int] = set()
        asignadas: list[tuple[str, Usuario]] = []

        for area in areas:
            candidatos = [
                u for u in _docentes_del_area(db, area.id, periodo.id)
                if u.id not in usados and u.rol.nombre == "DOCENTE"
            ]
            if not candidatos:
                # Fallback: cualquier docente activo sin jefatura en el período
                candidatos = [
                    u for u in db.query(Usuario)
                    .join(Usuario.rol)
                    .filter(Usuario.activo.is_(True))
                    .order_by(Usuario.nombre_completo)
                    .all()
                    if u.id not in usados and u.rol.nombre == "DOCENTE"
                ]
            if not candidatos:
                logger.warning(f"Sin docentes disponibles para el área '{area.nombre}'")
                continue

            jefe = candidatos[0]
            db.add(JefaturaArea(usuario_id=jefe.id, area_id=area.id, periodo_id=periodo.id))
            usados.add(jefe.id)
            asignadas.append((area.nombre, jefe))

        db.commit()

        print(f"\nJefaturas asignadas — período {periodo.nombre}\n")
        for area_nombre, jefe in asignadas:
            titulo = f"{jefe.titulo} " if jefe.titulo else ""
            print(f"  {area_nombre:36} → {titulo}{jefe.nombre_completo}")
            print(f"  {'':36}   {jefe.email_institucional}  (pass123)")
        print(f"\nTotal: {len(asignadas)} jefatura(s).\n")
    finally:
        db.close()


if __name__ == "__main__":
    seed_jefaturas()
