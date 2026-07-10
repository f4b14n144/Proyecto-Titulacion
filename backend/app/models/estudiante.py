from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.declarative import Base


class Estudiante(Base):
    """
    Estudiante de la carrera en un período, cargado desde el Excel institucional.

    El correo es el institucional que ya asigna la universidad; viene en el Excel.
    """

    __tablename__ = "estudiantes"

    id = Column(Integer, primary_key=True)
    periodo_id = Column(Integer, ForeignKey("periodos_academicos.id"), nullable=False)
    nombre_completo = Column(String, nullable=False)
    correo = Column(String, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Un mismo correo no se repite dentro del período
        UniqueConstraint("periodo_id", "correo", name="uq_estudiante_periodo_correo"),
    )

    materias = relationship(
        "EstudianteAsignatura", back_populates="estudiante", cascade="all, delete-orphan"
    )


class EstudianteAsignatura(Base):
    """
    Materia que un estudiante cursa en el período.

    `asignatura_nombre` guarda el texto tal como vino en el Excel. `asignatura_id`
    se resuelve contra el catálogo cuando hay coincidencia; puede quedar nulo si la
    materia no está registrada, y aun así el correo se puede personalizar con el
    nombre original.
    """

    __tablename__ = "estudiante_asignaturas"

    id = Column(Integer, primary_key=True)
    estudiante_id = Column(Integer, ForeignKey("estudiantes.id"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=True)
    asignatura_nombre = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_estudiante_asignatura", "estudiante_id", "asignatura_id"),
    )

    estudiante = relationship("Estudiante", back_populates="materias")
