"""estudiantes y sus asignaturas por período

Se cargan desde el Excel institucional (nombre, correo, materias que cursa) para
poder enviar correos personalizados por materia.

Revision ID: 008
Revises: 007
Create Date: 2026-07-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estudiantes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos_academicos.id"), nullable=False),
        sa.Column("nombre_completo", sa.String(), nullable=False),
        sa.Column("correo", sa.String(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("periodo_id", "correo", name="uq_estudiante_periodo_correo"),
    )
    op.create_table(
        "estudiante_asignaturas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estudiante_id", sa.Integer(), sa.ForeignKey("estudiantes.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=True),
        sa.Column("asignatura_nombre", sa.String(), nullable=False),
    )
    op.create_index(
        "ix_estudiante_asignatura", "estudiante_asignaturas", ["estudiante_id", "asignatura_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_estudiante_asignatura", table_name="estudiante_asignaturas")
    op.drop_table("estudiante_asignaturas")
    op.drop_table("estudiantes")
