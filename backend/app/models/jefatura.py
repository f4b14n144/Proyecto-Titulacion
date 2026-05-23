from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class JefaturaArea(Base):
    __tablename__ = "jefaturas_area"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    periodo_id = Column(Integer, ForeignKey("periodos_academicos.id"), nullable=False)

    __table_args__ = (
        # Una área = un jefe por período
        UniqueConstraint("area_id", "periodo_id", name="uq_jefatura_area_periodo"),
        # Un docente = una sola área por período
        UniqueConstraint("usuario_id", "periodo_id", name="uq_jefatura_usuario_periodo"),
    )

    usuario = relationship("Usuario", back_populates="jefaturas")
    area = relationship("Area", back_populates="jefaturas")
    periodo = relationship("PeriodoAcademico", back_populates="jefaturas")
