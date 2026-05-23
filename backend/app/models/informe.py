from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Informe(Base):
    __tablename__ = "informes"

    id = Column(Integer, primary_key=True)
    consejo_id = Column(Integer, ForeignKey("consejos_carrera.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    tipo_informe = Column(Integer, nullable=False)  # 1 | 2 | 3 | 4
    estado = Column(String, default="BORRADOR")  # BORRADOR | REVISANDO | APROBADO
    contenido_json = Column(JSON, nullable=True)
    ruta_docx = Column(String, nullable=True)
    generado_en = Column(DateTime(timezone=True), nullable=True)
    enviado_en = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1)

    consejo = relationship("ConsejoCarrera", back_populates="informes")
    area = relationship("Area", back_populates="informes")
    checklists_avac = relationship("ChecklistAVAC", back_populates="informe")
    checklists_visita = relationship("ChecklistVisitaAulica", back_populates="informe")
    notificaciones = relationship("Notificacion", back_populates="informe")
