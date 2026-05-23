from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class RespuestaDocente(Base):
    __tablename__ = "respuestas_docentes"

    id = Column(Integer, primary_key=True)
    notificacion_id = Column(Integer, ForeignKey("notificaciones.id"), nullable=False)
    contenido = Column(Text, nullable=False)
    recibido_en = Column(DateTime(timezone=True), server_default=func.now())

    notificacion = relationship("Notificacion", back_populates="respuestas")
