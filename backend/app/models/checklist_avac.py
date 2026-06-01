from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class ChecklistAVAC(Base):
    __tablename__ = "checklist_avac"

    id = Column(Integer, primary_key=True)
    informe_id = Column(Integer, ForeignKey("informes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=False)
    grupo = Column(String, nullable=False)

    silabo_cargado = Column(Boolean, nullable=True)
    registro_avance = Column(Boolean, nullable=True)
    guia_practicas = Column(Boolean, nullable=True)
    consejeria_academica = Column(Boolean, nullable=True)
    recursos_derechos_autor = Column(Boolean, nullable=True)
    libros_digitales = Column(Boolean, nullable=True)
    seccion_practicas = Column(Boolean, nullable=True)
    guias_componente = Column(Boolean, nullable=True)
    actividades_con_rubrica = Column(Boolean, nullable=True)
    seccion_investigativas = Column(Boolean, nullable=True)
    actividad_investigacion = Column(Boolean, nullable=True)
    proyecto_integrador = Column(Boolean, nullable=True)

    observaciones = Column(Text, nullable=True)
    acciones_mejora = Column(Text, nullable=True)

    informe = relationship("Informe", back_populates="checklists_avac")
    usuario = relationship("Usuario", back_populates="checklists_avac")
    asignatura = relationship("Asignatura", back_populates="checklists_avac")
