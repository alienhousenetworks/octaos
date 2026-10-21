"""Enterprise HR lifecycle, calendar sync, workflow versioning and employee sequence.

Revision ID: c3b4a5d6e7f8
Revises: b2a3c4d5e6f7
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "c3b4a5d6e7f8"
down_revision = "b2a3c4d5e6f7"
branch_labels = None
depends_on = None

NEW_ENTERPRISE_TABLES = [
    "interview_deliveries",
    "hr_workflow_versions",
    "hr_workflow_import_records",
    "tenant_employee_sequences",
    "hr_outbox_events",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Create new enterprise tables if missing
    from app.models.base import Base
    import app.models.hr  # noqa: F401

    missing_tables = [
        Base.metadata.tables[name]
        for name in NEW_ENTERPRISE_TABLES
        if name in Base.metadata.tables and name not in tables
    ]
    if missing_tables:
        Base.metadata.create_all(bind=bind, tables=missing_tables, checkfirst=True)

    inspector = sa.inspect(bind)
    current_tables = set(inspector.get_table_names())

    # 2. Add columns to interviews table
    if "interviews" in current_tables:
        cols = {c["name"] for c in inspector.get_columns("interviews")}
        with op.batch_alter_table("interviews") as batch_op:
            if "duration_minutes" not in cols:
                batch_op.add_column(sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"))
            if "calendar_uid" not in cols:
                batch_op.add_column(sa.Column("calendar_uid", sa.String(), nullable=True))
                batch_op.create_index("ix_interviews_calendar_uid", ["calendar_uid"], unique=False)
            if "calendar_sequence" not in cols:
                batch_op.add_column(sa.Column("calendar_sequence", sa.Integer(), nullable=False, server_default="0"))
            if "custom_notes" not in cols:
                batch_op.add_column(sa.Column("custom_notes", sa.Text(), nullable=True))

    # 3. Add columns to interview_panelists table
    if "interview_panelists" in current_tables:
        cols = {c["name"] for c in inspector.get_columns("interview_panelists")}
        with op.batch_alter_table("interview_panelists") as batch_op:
            if "email" not in cols:
                batch_op.add_column(sa.Column("email", sa.String(), nullable=True))
            if "name" not in cols:
                batch_op.add_column(sa.Column("name", sa.String(), nullable=True))
            if "role" not in cols:
                batch_op.add_column(sa.Column("role", sa.String(), nullable=False, server_default="interviewer"))
            if "response_status" not in cols:
                batch_op.add_column(sa.Column("response_status", sa.String(), nullable=False, server_default="needs_action"))
            # Make user_id nullable for external/guest panelists
            if "user_id" in cols:
                batch_op.alter_column("user_id", existing_type=sa.String(), nullable=True)

    # 4. Add columns to hr_workflow_definitions table
    if "hr_workflow_definitions" in current_tables:
        cols = {c["name"] for c in inspector.get_columns("hr_workflow_definitions")}
        with op.batch_alter_table("hr_workflow_definitions") as batch_op:
            if "folder_path" not in cols:
                batch_op.add_column(sa.Column("folder_path", sa.String(), nullable=False, server_default="/"))
            if "department_id" not in cols:
                batch_op.add_column(sa.Column("department_id", sa.String(), nullable=True))
                batch_op.create_index("ix_hr_workflow_definitions_department_id", ["department_id"], unique=False)
            if "tags" not in cols:
                batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
            if "published_version_id" not in cols:
                batch_op.add_column(sa.Column("published_version_id", sa.String(), nullable=True))

    # 5. Add onboarding_instance_id to hr_employees table
    if "hr_employees" in current_tables:
        cols = {c["name"] for c in inspector.get_columns("hr_employees")}
        with op.batch_alter_table("hr_employees") as batch_op:
            if "onboarding_instance_id" not in cols:
                batch_op.add_column(sa.Column("onboarding_instance_id", sa.String(), nullable=True))
                batch_op.create_index("ix_hr_employees_onboarding_instance_id", ["onboarding_instance_id"], unique=True)


def downgrade() -> None:
    pass
