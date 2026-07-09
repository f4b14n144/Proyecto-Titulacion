"""contenido_consejo: secciones del Informe 1 escritas por la dirección

El Informe 1 pasa a existir POR ÁREA. El contenido que escribe la directora es
común al consejo y se propaga en solo lectura al informe de cada jefe de área,
que añade encima sus propias secciones.

Revision ID: 006
Revises: 005
Create Date: 2026-07-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contenido_consejo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consejo_id", sa.Integer(), nullable=False),
        sa.Column("secciones", sa.JSON(), nullable=False),
        sa.Column("nombre_director", sa.String(), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["consejo_id"], ["consejos_carrera.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consejo_id", name="uq_contenido_consejo_consejo"),
    )


def downgrade() -> None:
    op.drop_table("contenido_consejo")
