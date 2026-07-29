"""asignaturas: agregar columna activa (soft-delete)

Una materia inactiva desaparece del catálogo para asignar en períodos nuevos, pero
sigue existiendo en la base para no romper el histórico de asignaciones de períodos
anteriores. Las materias existentes quedan activas.

Revision ID: 013
Revises: 012
Create Date: 2026-07-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "asignaturas",
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("asignaturas", "activa")
