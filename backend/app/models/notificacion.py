from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
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
    # Identificador único de la notificación. Nació como token del Reply-To para
    # correlacionar respuestas por correo; esa recepción (IMAP) se eliminó, pero la
    # columna se conserva como id único del envío.
    reply_to_token = Column(String, unique=True, nullable=False)
    enviado_en = Column(DateTime(timezone=True), server_default=func.now())

    informe = relationship("Informe", back_populates="notificaciones")
    consejo = relationship("ConsejoCarrera", back_populates="notificaciones")
