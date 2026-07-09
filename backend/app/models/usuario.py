from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.declarative import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre_completo = Column(String, nullable=False)
    # Título académico (Ing., Mg., PhD, Lic.). Se usa en la carátula de los
    # informes ("Ing. Marcelo Flores V.") y en los correos personalizados.
    titulo = Column(String, nullable=True)
    email_institucional = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    rol = relationship("Rol", back_populates="usuarios")
    jefaturas = relationship("JefaturaArea", back_populates="usuario")
    asignaciones = relationship("AsignacionDocente", back_populates="usuario")
    checklists_avac = relationship("ChecklistAVAC", back_populates="usuario")
    checklists_visita = relationship("ChecklistVisitaAulica", back_populates="usuario")
