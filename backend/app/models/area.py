from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    # Soft-delete: un área inactiva sale del catálogo para asignar en períodos
    # nuevos, pero se conserva para no romper el histórico (informes, jefaturas).
    activa = Column(Boolean, default=True, nullable=False, server_default="true")

    asignaturas = relationship("Asignatura", back_populates="area")
    jefaturas = relationship("JefaturaArea", back_populates="area")
    informes = relationship("Informe", back_populates="area")
