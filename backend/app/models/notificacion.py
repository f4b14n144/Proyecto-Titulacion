from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.declarative import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True)
    # Las notificaciones se envían a nivel de consejo (antes de que existan los informes),
    # por eso informe_id es nullable y se agrega consejo_id.
    informe_id = Column(Integer, ForeignKey("informes.id"), nullable=True)
    consejo_id = Column(Integer, ForeignKey("consejos_carrera.id"), nullable=True)
    destinatario_email = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # DOCENTE_SUGERENCIA | ESTUDIANTE_REPORTE
    reply_to_token = Column(String, unique=True, nullable=False)
    enviado_en = Column(DateTime(timezone=True), server_default=func.now())
    respondido = Column(Boolean, default=False)

    informe = relationship("Informe", back_populates="notificaciones")
    consejo = relationship("ConsejoCarrera", back_populates="notificaciones")
    respuestas = relationship("RespuestaDocente", back_populates="notificacion")
