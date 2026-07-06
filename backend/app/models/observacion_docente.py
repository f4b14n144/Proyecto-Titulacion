from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.declarative import Base


class ObservacionDocente(Base):
    """
    Observaciones/sugerencias que el docente escribe sobre SU materia,
    directamente desde su panel. Se incorporan al Informe 4 (final).
    """
    __tablename__ = "observaciones_docente"

    id = Column(Integer, primary_key=True)
    consejo_id = Column(Integer, ForeignKey("consejos_carrera.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=False)
    grupo = Column(String, nullable=False)
    contenido = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("consejo_id", "usuario_id", "asignatura_id", "grupo",
                         name="uq_observacion_docente"),
    )
