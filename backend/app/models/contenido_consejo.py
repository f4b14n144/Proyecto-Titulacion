from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.declarative import Base


class ContenidoConsejo(Base):
    """
    Contenido del Informe 1 que escribe la DIRECTORA de carrera, común a todas
    las áreas de un consejo.

    Se propaga (en solo lectura) al Informe 1 de cada jefe de área; cada jefe
    añade encima sus propias secciones sin modificar esto.
    """

    __tablename__ = "contenido_consejo"

    id = Column(Integer, primary_key=True)
    consejo_id = Column(
        Integer, ForeignKey("consejos_carrera.id"), nullable=False, unique=True
    )
    # {agenda, designaciones, observaciones_curriculares, resultados_encuestas,
    #  resoluciones, observaciones_adicionales}
    secciones = Column(JSON, nullable=False, default=dict)
    nombre_director = Column(String, nullable=True)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    consejo = relationship("ConsejoCarrera", back_populates="contenido_direccion")
