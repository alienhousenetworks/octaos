"""Create external agent connection, webhook, command, and activity tables.

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
"""
from alembic import op
import sqlalchemy as sa


revision = "c5d6e7f8a9b0"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "external_agent_connections" not in tables:
        op.create_table(
            "external_agent_connections",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("endpoint_url", sa.String(length=500), nullable=False),
            sa.Column("auth_type", sa.String(length=30), nullable=False, server_default="bearer"),
            sa.Column("auth_secret_encrypted", sa.Text(), nullable=True),
            sa.Column("custom_header_name", sa.String(length=120), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_test_status", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_id", "name", name="uq_ext_agent_conn_tenant_name"),
        )
        op.create_index("ix_external_agent_connections_tenant_id", "external_agent_connections", ["tenant_id"])

    if "webhook_subscriptions" not in tables:
        op.create_table(
            "webhook_subscriptions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "connection_id",
                sa.String(),
                sa.ForeignKey("external_agent_connections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("filter_json", sa.JSON(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("connection_id", "event_type", name="uq_webhook_sub_conn_event"),
        )
        op.create_index("ix_webhook_subscriptions_connection_id", "webhook_subscriptions", ["connection_id"])
        op.create_index("ix_webhook_subscriptions_tenant_id", "webhook_subscriptions", ["tenant_id"])
        op.create_index("ix_webhook_subscriptions_event_type", "webhook_subscriptions", ["event_type"])

    if "webhook_deliveries" not in tables:
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column(
                "connection_id",
                sa.String(),
                sa.ForeignKey("external_agent_connections.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("correlation_id", sa.String(length=120), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=True, server_default="pending"),
            sa.Column("attempt_count", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_http_status", sa.Integer(), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_webhook_deliveries_tenant_id", "webhook_deliveries", ["tenant_id"])
        op.create_index("ix_webhook_deliveries_connection_id", "webhook_deliveries", ["connection_id"])
        op.create_index("ix_webhook_deliveries_correlation_id", "webhook_deliveries", ["correlation_id"])
        op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])
        op.create_index("ix_webhook_deliveries_next_attempt_at", "webhook_deliveries", ["next_attempt_at"])
        op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"])

    if "controller_commands" not in tables:
        op.create_table(
            "controller_commands",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column(
                "connection_id",
                sa.String(),
                sa.ForeignKey("external_agent_connections.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("correlation_id", sa.String(length=120), nullable=False),
            sa.Column("command", sa.Text(), nullable=False),
            sa.Column("context_json", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=True, server_default="queued"),
            sa.Column("issued_by", sa.String(), nullable=True),
            sa.Column("reply_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("correlation_id", name="uq_controller_commands_correlation_id"),
        )
        op.create_index("ix_controller_commands_tenant_id", "controller_commands", ["tenant_id"])
        op.create_index("ix_controller_commands_connection_id", "controller_commands", ["connection_id"])
        op.create_index("ix_controller_commands_correlation_id", "controller_commands", ["correlation_id"])
        op.create_index("ix_controller_commands_status", "controller_commands", ["status"])
        op.create_index("ix_controller_commands_created_at", "controller_commands", ["created_at"])

    if "activity_events" not in tables:
        op.create_table(
            "activity_events",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("correlation_id", sa.String(length=120), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=True, server_default="controller"),
            sa.Column("actor", sa.String(length=120), nullable=False),
            sa.Column("kind", sa.String(length=40), nullable=True, server_default="status"),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("attachments_json", sa.JSON(), nullable=True),
            sa.Column("data_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )
        op.create_index("ix_activity_events_tenant_id", "activity_events", ["tenant_id"])
        op.create_index("ix_activity_events_correlation_id", "activity_events", ["correlation_id"])
        op.create_index("ix_activity_events_created_at", "activity_events", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    for name in (
        "activity_events",
        "controller_commands",
        "webhook_deliveries",
        "webhook_subscriptions",
        "external_agent_connections",
    ):
        if name in tables:
            op.drop_table(name)
