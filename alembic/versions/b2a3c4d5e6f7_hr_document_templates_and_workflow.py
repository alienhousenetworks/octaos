"""Add governed HR document and dynamic workflow tables and sync template columns.

Revision ID: b2a3c4d5e6f7
Revises: b1a2c3d4e5f6
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "b2a3c4d5e6f7"
down_revision = "b1a2c3d4e5f6"
branch_labels = None
depends_on = None

HR_GOVERNED_TABLES = [
    "tenant_document_templates",
    "template_versions",
    "template_variable_schemas",
    "hr_document_packets",
    "hr_document_artifacts",
    "document_verification_runs",
    "hr_artifact_approvals",
    "candidate_acceptance_records",
    "hr_workflow_definitions",
    "hr_workflow_instances",
    "hr_workflow_tasks",
    "candidate_evidence_items",
    "candidate_field_values",
    "hr_document_drafts",
    "hr_document_review_comments",
    "hr_scheduled_deliveries",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Create governed HR tables if not already present
    from app.models.base import Base
    import app.models.hr  # noqa: F401

    missing_tables = [
        Base.metadata.tables[name]
        for name in HR_GOVERNED_TABLES
        if name in Base.metadata.tables and name not in tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables, checkfirst=True)

    # 2. Add missing columns to tenant_document_templates
    inspector = sa.inspect(bind)
    current_tables = set(inspector.get_table_names())
    if "tenant_document_templates" in current_tables:
        tpl_cols = {c["name"] for c in inspector.get_columns("tenant_document_templates")}
        with op.batch_alter_table("tenant_document_templates") as batch_op:
            if "category" not in tpl_cols:
                batch_op.add_column(sa.Column("category", sa.String(), nullable=False, server_default="onboarding"))
                batch_op.create_index("ix_tenant_document_templates_category", ["category"], unique=False)
            if "folder_path" not in tpl_cols:
                batch_op.add_column(sa.Column("folder_path", sa.String(), nullable=False, server_default="/"))
            if "tags" not in tpl_cols:
                batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
            if "description" not in tpl_cols:
                batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
            if "is_active" not in tpl_cols:
                batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
            if "created_at" not in tpl_cols:
                batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))

    # 3. Add missing columns to template_versions
    if "template_versions" in current_tables:
        ver_cols = {c["name"] for c in inspector.get_columns("template_versions")}
        with op.batch_alter_table("template_versions") as batch_op:
            if "docx_structure" not in ver_cols:
                batch_op.add_column(sa.Column("docx_structure", sa.JSON(), nullable=True, server_default="{}"))
            if "detected_clauses" not in ver_cols:
                batch_op.add_column(sa.Column("detected_clauses", sa.JSON(), nullable=True, server_default="[]"))
            if "proposed_mappings" not in ver_cols:
                batch_op.add_column(sa.Column("proposed_mappings", sa.JSON(), nullable=True, server_default="[]"))
            if "raw_content" not in ver_cols:
                batch_op.add_column(sa.Column("raw_content", sa.Text(), nullable=True))
            if "published_at" not in ver_cols:
                batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
            if "published_by_user_id" not in ver_cols:
                batch_op.add_column(sa.Column("published_by_user_id", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tenant_document_templates" in tables:
        tpl_cols = {c["name"] for c in inspector.get_columns("tenant_document_templates")}
        with op.batch_alter_table("tenant_document_templates") as batch_op:
            if "category" in tpl_cols:
                try:
                    batch_op.drop_index("ix_tenant_document_templates_category")
                except Exception:
                    pass
                try:
                    batch_op.drop_column("category")
                except Exception:
                    pass
            for col in ("folder_path", "tags", "description", "is_active", "created_at"):
                if col in tpl_cols:
                    try:
                        batch_op.drop_column(col)
                    except Exception:
                        pass

    if "template_versions" in tables:
        ver_cols = {c["name"] for c in inspector.get_columns("template_versions")}
        with op.batch_alter_table("template_versions") as batch_op:
            for col in ("docx_structure", "detected_clauses", "proposed_mappings", "raw_content", "published_at", "published_by_user_id"):
                if col in ver_cols:
                    try:
                        batch_op.drop_column(col)
                    except Exception:
                        pass
