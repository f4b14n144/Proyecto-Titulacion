from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class Asignatura(Base):
    __tablename__ = "asignaturas"

    id = Column(Integer, primary_key=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    nombre = Column(String, nullable=False)
    codigo = Column(String, unique=True, nullable=False)
    # Soft-delete: una materia inactiva no aparece para asignar en períodos nuevos,
    # pero sigue existiendo para no romper el histórico de períodos anteriores.
    activa = Column(Boolean, default=True, nullable=False, server_default="true")

    area = relationship("Area", back_populates="asignaturas")
    asignaciones = relationship("AsignacionDocente", back_populates="asignatura")
    calificaciones = relationship("Calificacion", back_populates="asignatura")
    checklists_avac = relationship("ChecklistAVAC", back_populates="asignatura")
    checklists_visita = relationship("ChecklistVisitaAulica", back_populates="asignatura")
