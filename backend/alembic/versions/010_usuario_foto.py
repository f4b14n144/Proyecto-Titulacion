"""usuarios: agregar columna foto

Foto de perfil, guardada como data URI (JPEG en base64) en lugar de como archivo:
nginx no sirve /static (se cerró por seguridad), así la foto viaja dentro de
/auth/me sin necesidad de un endpoint de descarga ni de validar rutas de archivo.
Al subirla se recorta a un cuadrado y se recomprime con Pillow (~20 KB).

Revision ID: 010
Revises: 009
Create Date: 2026-07-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("foto", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "foto")
