from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class AsignacionDocente(Base):
    __tablename__ = "asignaciones_docente"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=False)
    periodo_id = Column(Integer, ForeignKey("periodos_academicos.id"), nullable=False)
    grupo = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "usuario_id", "asignatura_id", "periodo_id", "grupo",
            name="uq_asignacion_docente"
        ),
    )

    usuario = relationship("Usuario", back_populates="asignaciones")
    asignatura = relationship("Asignatura", back_populates="asignaciones")
    periodo = relationship("PeriodoAcademico", back_populates="asignaciones")
