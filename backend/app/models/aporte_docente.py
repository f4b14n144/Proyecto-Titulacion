from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.sql import func
from app.db.declarative import Base

# Tipos de aporte que el docente registra sobre SU materia
TIPO_OBSERVACION = "OBSERVACION"
TIPO_ACCION_MEJORA = "ACCION_MEJORA"
TIPOS_APORTE = (TIPO_OBSERVACION, TIPO_ACCION_MEJORA)


class AporteDocente(Base):
    """
    Observaciones y acciones de mejora que el docente escribe sobre SU materia.

    Es **sumativo**: cada envío se guarda como un registro nuevo y nunca
    sobreescribe los anteriores, de modo que queda el historial completo por
    materia-grupo. Alimentan los informes 3 y 4 del área correspondiente.
    """

    __tablename__ = "aportes_docente"

    id = Column(Integer, primary_key=True)
    consejo_id = Column(Integer, ForeignKey("consejos_carrera.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    asignatura_id = Column(Integer, ForeignKey("asignaturas.id"), nullable=False)
    grupo = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # OBSERVACION | ACCION_MEJORA
    texto = Column(Text, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    # Sin UNIQUE: los aportes se acumulan. Índice para leerlos por materia.
    __table_args__ = (
        Index("ix_aporte_consejo_asignatura_grupo", "consejo_id", "asignatura_id", "grupo"),
    )
