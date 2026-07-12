"""fechas de entrega por informe

El consejo tenía una única `fecha_limite_informe`, pero los cuatro informes se
entregan en momentos distintos del período. Con una fecha por informe, el
planificador puede enviar el recordatorio 2 días antes de cada entrega.

Migra la fecha límite existente del consejo como fecha del Informe 4 (el último),
para no perder el dato que ya estaba cargado.

Revision ID: 009
Revises: 008
Create Date: 2026-07-11

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fechas_entrega_informe",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consejo_id", sa.Integer(), sa.ForeignKey("consejos_carrera.id"), nullable=False),
        sa.Column("tipo_informe", sa.Integer(), nullable=False),
        sa.Column("fecha_entrega", sa.Date(), nullable=False),
        sa.UniqueConstraint("consejo_id", "tipo_informe", name="uq_fecha_entrega_consejo_tipo"),
    )

    # Conservar la fecha límite que ya existía, como la del Informe 4
    op.execute(
        """
        INSERT INTO fechas_entrega_informe (consejo_id, tipo_informe, fecha_entrega)
        SELECT id, 4, fecha_limite_informe
        FROM consejos_carrera
        WHERE fecha_limite_informe IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("fechas_entrega_informe")
