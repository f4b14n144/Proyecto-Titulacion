from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class PeriodoAcademico(Base):
    __tablename__ = "periodos_academicos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activo = Column(Boolean, default=True)

    consejos = relationship("ConsejoCarrera", back_populates="periodo")
    jefaturas = relationship("JefaturaArea", back_populates="periodo")
    asignaciones = relationship("AsignacionDocente", back_populates="periodo")
