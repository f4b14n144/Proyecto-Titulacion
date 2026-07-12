from sqlalchemy import Column, Integer, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.declarative import Base


class FechaEntregaInforme(Base):
    """
    Fecha límite de entrega de cada informe (1-4) dentro de un consejo de carrera.

    El consejo ya tenía una única `fecha_limite_informe`, pero los cuatro informes
    se entregan en momentos distintos del período (el 2 tras la revisión del aula
    virtual, el 3 tras el interciclo, el 4 al cerrar notas). Con una fecha por
    informe el planificador puede avisar a tiempo de cada uno.

    El recordatorio sale **2 días antes** de esta fecha.
    """

    __tablename__ = "fechas_entrega_informe"

    id = Column(Integer, primary_key=True)
    consejo_id = Column(Integer, ForeignKey("consejos_carrera.id"), nullable=False)
    tipo_informe = Column(Integer, nullable=False)  # 1 | 2 | 3 | 4
    fecha_entrega = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("consejo_id", "tipo_informe", name="uq_fecha_entrega_consejo_tipo"),
    )

    consejo = relationship("ConsejoCarrera", back_populates="fechas_entrega")
