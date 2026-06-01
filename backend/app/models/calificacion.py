from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.declarative import Base


class Calificacion(Base):
    __tablename__ = "calificaciones"

    id = Column(Integer, primary_key=True)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=False)
    consejo_id = Column(Integer, ForeignKey("consejos_carrera.id"), nullable=False)
    tipo = Column(String, nullable=False)  # INTERCICLO | FINAL
    datos_json = Column(JSON, nullable=False)
    # {"estudiantes": [{"parcial1": N, "parcial2": N,
    #   "recuperacion": N, "nota_final": N, "estado": "APROBADO"}]}
    procesado_en = Column(DateTime(timezone=True), server_default=func.now())

    asignatura = relationship("Asignatura", back_populates="calificaciones")
    consejo = relationship("ConsejoCarrera", back_populates="calificaciones")
