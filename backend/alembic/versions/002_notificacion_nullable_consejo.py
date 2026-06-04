"""notificacion: informe_id nullable + consejo_id

Las notificaciones a docentes se envían a nivel de Consejo de Carrera,
antes de que existan los informes. Por eso informe_id pasa a nullable
y se agrega consejo_id (FK a consejos_carrera).

Revision ID: 002
Revises: 001
Create Date: 2026-06-04

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # informe_id pasa a nullable
    op.alter_column("notificaciones", "informe_id", existing_type=sa.Integer(), nullable=True)
    # nueva columna consejo_id
    op.add_column("notificaciones", sa.Column("consejo_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_notificaciones_consejo",
        "notificaciones", "consejos_carrera",
        ["consejo_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_notificaciones_consejo", "notificaciones", type_="foreignkey")
    op.drop_column("notificaciones", "consejo_id")
    op.alter_column("notificaciones", "informe_id", existing_type=sa.Integer(), nullable=False)
