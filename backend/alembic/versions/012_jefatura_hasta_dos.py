"""jefaturas_area: permitir hasta 2 jefes por área

Se elimina el UNIQUE (area_id, periodo_id) que obligaba a un solo jefe por área.
Las áreas grandes pueden tener 2 jefes. El tope de 2 se valida en el endpoint.
Se conserva el UNIQUE (usuario_id, periodo_id): un docente dirige una sola área.

Revision ID: 012
Revises: 011
Create Date: 2026-07-29

"""
from typing import Sequence, Union
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_jefatura_area_periodo", "jefaturas_area", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_jefatura_area_periodo", "jefaturas_area", ["area_id", "periodo_id"]
    )
