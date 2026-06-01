from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class ChecklistVisitaAulica(Base):
    __tablename__ = "checklist_visita_aulica"

    id = Column(Integer, primary_key=True)
    informe_id = Column(Integer, ForeignKey("informes.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=False)
    grupo = Column(String, nullable=False)

    visita_realizada = Column(Boolean, nullable=True)
    puntualidad_docente = Column(Boolean, nullable=True)
    cumplimiento_silabo = Column(Boolean, nullable=True)
    cumplimiento_practicas = Column(Boolean, nullable=True)
    actividades_con_rubrica = Column(Boolean, nullable=True)
    actividad_investigacion = Column(Boolean, nullable=True)

    observaciones_estudiantes = Column(Text, nullable=True)
    observaciones_docente = Column(Text, nullable=True)
    acciones_docente = Column(Text, nullable=True)

    informe = relationship("Informe", back_populates="checklists_visita")
    usuario = relationship("Usuario", back_populates="checklists_visita")
    asignatura = relationship("Asignatura", back_populates="checklists_visita")
