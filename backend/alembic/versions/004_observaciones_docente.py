"""observaciones_docente

Observaciones del docente sobre su materia, que van al Informe 4.

Revision ID: 004
Revises: 003
Create Date: 2026-07-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "observaciones_docente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consejo_id", sa.Integer(), sa.ForeignKey("consejos_carrera.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("consejo_id", "usuario_id", "asignatura_id", "grupo",
                            name="uq_observacion_docente"),
    )


def downgrade() -> None:
    op.drop_table("observaciones_docente")
