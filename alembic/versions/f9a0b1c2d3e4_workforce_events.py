"""Create the tenant-scoped workforce event stream.

Revision ID: f9a0b1c2d3e4
Revises: c4d5e6f7a8b9
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = "f9a0b1c2d3e4"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "workforce_events" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "workforce_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_key", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="system"),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "event_key", name="uq_workforce_event_tenant_key"),
    )
    op.create_index("ix_workforce_events_tenant_id", "workforce_events", ["tenant_id"])
    op.create_index("ix_workforce_events_event_type", "workforce_events", ["event_type"])
    op.create_index("ix_workforce_events_run_id", "workforce_events", ["run_id"])
    op.create_index("ix_workforce_events_agent_id", "workforce_events", ["agent_id"])
    op.create_index("ix_workforce_events_actor_user_id", "workforce_events", ["actor_user_id"])
    op.create_index("ix_workforce_events_created_at", "workforce_events", ["created_at"])
    op.create_index(
        "ix_workforce_event_tenant_created",
        "workforce_events",
        ["tenant_id", "created_at", "id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "workforce_events" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_workforce_event_tenant_created", table_name="workforce_events")
    op.drop_index("ix_workforce_events_created_at", table_name="workforce_events")
    op.drop_index("ix_workforce_events_actor_user_id", table_name="workforce_events")
    op.drop_index("ix_workforce_events_agent_id", table_name="workforce_events")
    op.drop_index("ix_workforce_events_run_id", table_name="workforce_events")
    op.drop_index("ix_workforce_events_event_type", table_name="workforce_events")
    op.drop_index("ix_workforce_events_tenant_id", table_name="workforce_events")
    op.drop_table("workforce_events")
