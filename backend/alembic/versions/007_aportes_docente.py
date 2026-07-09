"""aportes_docente: reemplaza observaciones_docente por una tabla sumativa y tipada

El docente ahora registra por materia-grupo tanto OBSERVACIONes como
ACCIONes de MEJORA, y cada envío se acumula (no se sobreescribe).

La fila existente de `observaciones_docente` se migra como tipo OBSERVACION.

Revision ID: 007
Revises: 006
Create Date: 2026-07-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aportes_docente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consejo_id", sa.Integer(), sa.ForeignKey("consejos_carrera.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_aporte_consejo_asignatura_grupo",
        "aportes_docente",
        ["consejo_id", "asignatura_id", "grupo"],
    )

    # Migrar los datos existentes como observaciones
    op.execute(
        """
        INSERT INTO aportes_docente
            (consejo_id, usuario_id, asignatura_id, grupo, tipo, texto, creado_en)
        SELECT consejo_id, usuario_id, asignatura_id, grupo, 'OBSERVACION', contenido, created_at
        FROM observaciones_docente
        """
    )
    op.drop_table("observaciones_docente")


def downgrade() -> None:
    op.create_table(
        "observaciones_docente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consejo_id", sa.Integer(), sa.ForeignKey("consejos_carrera.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("consejo_id", "usuario_id", "asignatura_id", "grupo",
                            name="uq_observacion_docente"),
    )
    op.execute(
        """
        INSERT INTO observaciones_docente
            (consejo_id, usuario_id, asignatura_id, grupo, contenido, created_at)
        SELECT DISTINCT ON (consejo_id, usuario_id, asignatura_id, grupo)
               consejo_id, usuario_id, asignatura_id, grupo, texto, creado_en
        FROM aportes_docente
        WHERE tipo = 'OBSERVACION'
        ORDER BY consejo_id, usuario_id, asignatura_id, grupo, creado_en DESC
        """
    )
    op.drop_index("ix_aporte_consejo_asignatura_grupo", table_name="aportes_docente")
    op.drop_table("aportes_docente")
