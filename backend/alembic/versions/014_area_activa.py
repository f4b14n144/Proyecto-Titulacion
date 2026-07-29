"""areas: agregar columna activa (soft-delete)

Un área inactiva desaparece del catálogo para asignar en períodos nuevos, pero
sigue existiendo para no romper el histórico (informes y jefaturas de períodos
anteriores la referencian). Borrar un área con histórico daba error 500 por la
llave foránea de informes; ahora se desactiva.

Revision ID: 014
Revises: 013
Create Date: 2026-07-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "areas",
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("areas", "activa")
