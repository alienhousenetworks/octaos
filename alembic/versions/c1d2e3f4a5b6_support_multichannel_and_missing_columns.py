"""Add support multichannel handoff columns and missing model fields.

Revision ID: c1d2e3f4a5b6
Revises: b9c0d1e2f3a4
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Create support_customers and support_customer_identities if not already present
    from app.models.base import Base
    import app.models.verticals  # noqa: F401

    new_tables = ["support_customers", "support_customer_identities"]
    table_objs = [Base.metadata.tables[name] for name in new_tables if name in Base.metadata.tables and name not in tables]
    if table_objs:
        Base.metadata.create_all(bind=bind, tables=table_objs)

    # Tickets columns
    if "tickets" in tables:
        ticket_cols = {c["name"] for c in inspector.get_columns("tickets")}
        with op.batch_alter_table("tickets") as batch_op:
            if "owner_type" not in ticket_cols:
                batch_op.add_column(sa.Column("owner_type", sa.String(), nullable=True, server_default="ai"))
            if "handoff_started_at" not in ticket_cols:
                batch_op.add_column(sa.Column("handoff_started_at", sa.DateTime(timezone=True), nullable=True))
            if "handoff_deadline_at" not in ticket_cols:
                batch_op.add_column(sa.Column("handoff_deadline_at", sa.DateTime(timezone=True), nullable=True))
            if "handoff_generation" not in ticket_cols:
                batch_op.add_column(sa.Column("handoff_generation", sa.Integer(), nullable=True, server_default="0"))
            if "customer_id" not in ticket_cols:
                batch_op.add_column(sa.Column("customer_id", sa.String(), sa.ForeignKey("support_customers.id"), nullable=True))
                batch_op.create_index("ix_tickets_customer_id", ["customer_id"], unique=False)

    # TicketMessage columns
    if "ticket_messages" in tables:
        msg_cols = {c["name"] for c in inspector.get_columns("ticket_messages")}
        with op.batch_alter_table("ticket_messages") as batch_op:
            if "direction" not in msg_cols:
                batch_op.add_column(sa.Column("direction", sa.String(), nullable=True, server_default="inbound"))
            if "channel" not in msg_cols:
                batch_op.add_column(sa.Column("channel", sa.String(), nullable=True))
            if "provider_message_id" not in msg_cols:
                batch_op.add_column(sa.Column("provider_message_id", sa.String(), nullable=True))
                batch_op.create_index("ix_ticket_messages_provider_message_id", ["provider_message_id"], unique=False)
            if "delivery_status" not in msg_cols:
                batch_op.add_column(sa.Column("delivery_status", sa.String(), nullable=True, server_default="sent"))
            if "extra_data" not in msg_cols:
                batch_op.add_column(sa.Column("extra_data", sa.JSON(), nullable=True, server_default="{}"))

    # Candidates columns
    if "candidates" in tables:
        cand_cols = {c["name"] for c in inspector.get_columns("candidates")}
        with op.batch_alter_table("candidates") as batch_op:
            if "phone" not in cand_cols:
                batch_op.add_column(sa.Column("phone", sa.String(), nullable=True))
            if "merged_into_candidate_id" not in cand_cols:
                batch_op.add_column(sa.Column("merged_into_candidate_id", sa.String(), nullable=True))

    # ProviderUsage columns
    if "provider_usage" in tables:
        usage_cols = {c["name"] for c in inspector.get_columns("provider_usage")}
        with op.batch_alter_table("provider_usage") as batch_op:
            if "resource_id" not in usage_cols:
                batch_op.add_column(sa.Column("resource_id", sa.String(), nullable=True))
            if "correlation_id" not in usage_cols:
                batch_op.add_column(sa.Column("correlation_id", sa.String(), nullable=True))

    # DataRetentionPolicies columns
    if "data_retention_policies" in tables:
        ret_cols = {c["name"] for c in inspector.get_columns("data_retention_policies")}
        with op.batch_alter_table("data_retention_policies") as batch_op:
            if "candidates_days" not in ret_cols:
                batch_op.add_column(sa.Column("candidates_days", sa.Integer(), nullable=True))
            if "applications_days" not in ret_cols:
                batch_op.add_column(sa.Column("applications_days", sa.Integer(), nullable=True))
            if "recruiting_docs_days" not in ret_cols:
                batch_op.add_column(sa.Column("recruiting_docs_days", sa.Integer(), nullable=True))
            if "identity_docs_days" not in ret_cols:
                batch_op.add_column(sa.Column("identity_docs_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.drop_index("ix_tickets_customer_id")
        batch_op.drop_column("customer_id")
        batch_op.drop_column("handoff_generation")
        batch_op.drop_column("handoff_deadline_at")
        batch_op.drop_column("handoff_started_at")
        batch_op.drop_column("owner_type")

    with op.batch_alter_table("ticket_messages") as batch_op:
        batch_op.drop_index("ix_ticket_messages_provider_message_id")
        batch_op.drop_column("extra_data")
        batch_op.drop_column("delivery_status")
        batch_op.drop_column("provider_message_id")
        batch_op.drop_column("channel")
        batch_op.drop_column("direction")

    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_column("merged_into_candidate_id")
        batch_op.drop_column("phone")

    with op.batch_alter_table("provider_usage") as batch_op:
        batch_op.drop_column("correlation_id")
        batch_op.drop_column("resource_id")

    with op.batch_alter_table("data_retention_policies") as batch_op:
        batch_op.drop_column("identity_docs_days")
        batch_op.drop_column("recruiting_docs_days")
        batch_op.drop_column("applications_days")
        batch_op.drop_column("candidates_days")
