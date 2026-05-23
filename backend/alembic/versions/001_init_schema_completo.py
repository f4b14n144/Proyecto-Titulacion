"""init_schema_completo

Revision ID: 001
Revises:
Create Date: 2026-05-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre_completo", sa.String(), nullable=False),
        sa.Column("email_institucional", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("rol_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("activo", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "periodos_academicos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("activo", sa.Boolean(), default=True),
    )

    op.create_table(
        "consejos_carrera",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos_academicos.id"), nullable=False),
        sa.Column("fecha_consejo", sa.Date(), nullable=False),
        sa.Column("fecha_limite_informe", sa.Date(), nullable=False),
        sa.Column("fecha_activacion", sa.Date(), nullable=True),
        sa.Column("flujo_estado", sa.String(), default="PENDIENTE"),
    )

    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
    )

    op.create_table(
        "asignaturas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("area_id", sa.Integer(), sa.ForeignKey("areas.id"), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "jefaturas_area",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("area_id", sa.Integer(), sa.ForeignKey("areas.id"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos_academicos.id"), nullable=False),
        sa.UniqueConstraint("area_id", "periodo_id", name="uq_jefatura_area_periodo"),
        sa.UniqueConstraint("usuario_id", "periodo_id", name="uq_jefatura_usuario_periodo"),
    )

    op.create_table(
        "asignaciones_docente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("periodo_id", sa.Integer(), sa.ForeignKey("periodos_academicos.id"), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.UniqueConstraint("usuario_id", "asignatura_id", "periodo_id", "grupo", name="uq_asignacion_docente"),
    )

    op.create_table(
        "calificaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("consejo_id", sa.Integer(), sa.ForeignKey("consejos_carrera.id"), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("datos_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("procesado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "informes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("consejo_id", sa.Integer(), sa.ForeignKey("consejos_carrera.id"), nullable=False),
        sa.Column("area_id", sa.Integer(), sa.ForeignKey("areas.id"), nullable=False),
        sa.Column("tipo_informe", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(), default="BORRADOR"),
        sa.Column("contenido_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ruta_docx", sa.String(), nullable=True),
        sa.Column("generado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enviado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), default=1),
    )

    op.create_table(
        "checklist_avac",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("informe_id", sa.Integer(), sa.ForeignKey("informes.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.Column("silabo_cargado", sa.Boolean(), nullable=True),
        sa.Column("registro_avance", sa.Boolean(), nullable=True),
        sa.Column("guia_practicas", sa.Boolean(), nullable=True),
        sa.Column("consejeria_academica", sa.Boolean(), nullable=True),
        sa.Column("recursos_derechos_autor", sa.Boolean(), nullable=True),
        sa.Column("libros_digitales", sa.Boolean(), nullable=True),
        sa.Column("seccion_practicas", sa.Boolean(), nullable=True),
        sa.Column("guias_componente", sa.Boolean(), nullable=True),
        sa.Column("actividades_con_rubrica", sa.Boolean(), nullable=True),
        sa.Column("seccion_investigativas", sa.Boolean(), nullable=True),
        sa.Column("actividad_investigacion", sa.Boolean(), nullable=True),
        sa.Column("proyecto_integrador", sa.Boolean(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("acciones_mejora", sa.Text(), nullable=True),
    )

    op.create_table(
        "checklist_visita_aulica",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("informe_id", sa.Integer(), sa.ForeignKey("informes.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("asignatura_id", sa.Integer(), sa.ForeignKey("asignaturas.id"), nullable=False),
        sa.Column("grupo", sa.String(), nullable=False),
        sa.Column("visita_realizada", sa.Boolean(), nullable=True),
        sa.Column("puntualidad_docente", sa.Boolean(), nullable=True),
        sa.Column("cumplimiento_silabo", sa.Boolean(), nullable=True),
        sa.Column("cumplimiento_practicas", sa.Boolean(), nullable=True),
        sa.Column("actividades_con_rubrica", sa.Boolean(), nullable=True),
        sa.Column("actividad_investigacion", sa.Boolean(), nullable=True),
        sa.Column("observaciones_estudiantes", sa.Text(), nullable=True),
        sa.Column("observaciones_docente", sa.Text(), nullable=True),
        sa.Column("acciones_docente", sa.Text(), nullable=True),
    )

    op.create_table(
        "notificaciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("informe_id", sa.Integer(), sa.ForeignKey("informes.id"), nullable=False),
        sa.Column("destinatario_email", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("reply_to_token", sa.String(), nullable=False, unique=True),
        sa.Column("enviado_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("respondido", sa.Boolean(), default=False),
    )

    op.create_table(
        "respuestas_docentes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notificacion_id", sa.Integer(), sa.ForeignKey("notificaciones.id"), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("recibido_en", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("respuestas_docentes")
    op.drop_table("notificaciones")
    op.drop_table("checklist_visita_aulica")
    op.drop_table("checklist_avac")
    op.drop_table("informes")
    op.drop_table("calificaciones")
    op.drop_table("asignaciones_docente")
    op.drop_table("jefaturas_area")
    op.drop_table("asignaturas")
    op.drop_table("areas")
    op.drop_table("consejos_carrera")
    op.drop_table("periodos_academicos")
    op.drop_table("usuarios")
    op.drop_table("roles")
