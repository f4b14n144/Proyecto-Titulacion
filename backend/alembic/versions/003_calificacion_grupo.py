"""calificaciones: agregar columna grupo

Una asignatura puede tener varios grupos (G1, G2...). Sin esta columna,
los registros se sobreescribían entre grupos de la misma asignatura.

Revision ID: 003
Revises: 002
Create Date: 2026-06-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("calificaciones", sa.Column("grupo", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("calificaciones", "grupo")
