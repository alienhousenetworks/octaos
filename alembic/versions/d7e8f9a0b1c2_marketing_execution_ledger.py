"""durable marketing execution ledger

Revision ID: d7e8f9a0b1c2
Revises: f8a9b0c1d2e3
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa

revision = "d7e8f9a0b1c2"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketing_executions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("workflow_type", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("current_stage", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "workflow_type", "idempotency_key", name="uq_marketing_execution_idempotency"),
    )
    op.create_index("ix_marketing_executions_tenant_id", "marketing_executions", ["tenant_id"])
    op.create_index("ix_marketing_executions_workflow_type", "marketing_executions", ["workflow_type"])
    op.create_index("ix_marketing_executions_status", "marketing_executions", ["status"])

    op.create_table(
        "marketing_execution_steps",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("execution_id", sa.String(), sa.ForeignKey("marketing_executions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_payload", sa.JSON(), nullable=True),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_marketing_execution_steps_tenant_id", "marketing_execution_steps", ["tenant_id"])
    op.create_index("ix_marketing_execution_steps_execution_id", "marketing_execution_steps", ["execution_id"])


def downgrade() -> None:
    op.drop_table("marketing_execution_steps")
    op.drop_table("marketing_executions")
