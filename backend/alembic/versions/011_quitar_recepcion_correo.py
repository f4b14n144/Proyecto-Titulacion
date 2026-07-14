"""quitar la recepción de correo (IMAP)

Se elimina la lectura de respuestas de docentes por correo:
- la tabla `respuestas_docentes`, que guardaba lo que el docente contestaba;
- la columna `notificaciones.respondido`, que marcaba si ya había respondido.

El docente registra ahora sus observaciones y acciones de mejora desde su panel
(`/aportes`), que es la vía real y la que alimenta los informes. La columna
`notificaciones.reply_to_token` se conserva como identificador único del envío.

Revision ID: 011
Revises: 010
Create Date: 2026-07-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("respuestas_docentes")
    op.drop_column("notificaciones", "respondido")


def downgrade() -> None:
    op.add_column(
        "notificaciones",
        sa.Column("respondido", sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    op.create_table(
        "respuestas_docentes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notificacion_id", sa.Integer(), sa.ForeignKey("notificaciones.id"), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("recibido_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
