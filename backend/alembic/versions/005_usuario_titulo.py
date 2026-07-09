"""usuarios: agregar columna titulo

Título académico del docente (Ing., Mg., PhD, Lic.). Lo requieren la carátula
de los informes ("Ing. Marcelo Flores V.") y los correos personalizados
("Estimado/a [titulo del docente]. [Nombre del Docente]").

Revision ID: 005
Revises: 004
Create Date: 2026-07-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("titulo", sa.String(), nullable=True))
    # Valor por defecto editable para los docentes existentes
    op.execute("UPDATE usuarios SET titulo = 'Ing.' WHERE titulo IS NULL")


def downgrade() -> None:
    op.drop_column("usuarios", "titulo")
