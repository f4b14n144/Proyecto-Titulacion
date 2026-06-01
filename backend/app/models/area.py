from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)

    asignaturas = relationship("Asignatura", back_populates="area")
    jefaturas = relationship("JefaturaArea", back_populates="area")
    informes = relationship("Informe", back_populates="area")
