from sqlalchemy import Column, Integer, ForeignKey, Date, String, DateTime
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class ConsejoCarrera(Base):
    __tablename__ = "consejos_carrera"

    id = Column(Integer, primary_key=True)
    periodo_id = Column(Integer, ForeignKey("periodos_academicos.id"), nullable=False)
    fecha_consejo = Column(Date, nullable=False)
    fecha_limite_informe = Column(Date, nullable=False)
    fecha_activacion = Column(Date, nullable=True)
    flujo_estado = Column(String, default="PENDIENTE")
    # PENDIENTE | PROCESANDO | COMPLETADO | ERROR

    periodo = relationship("PeriodoAcademico", back_populates="consejos")
    calificaciones = relationship("Calificacion", back_populates="consejo")
    informes = relationship("Informe", back_populates="consejo")
    notificaciones = relationship("Notificacion", back_populates="consejo")
