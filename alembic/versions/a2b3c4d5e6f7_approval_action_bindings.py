"""Persist exact action bindings on human approval records.

Revision ID: a2b3c4d5e6f7
Revises: f9a0b1c2d3e4
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "approval_requests" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("approval_requests")}
    if "action_fingerprint" not in columns:
        op.add_column("approval_requests", sa.Column("action_fingerprint", sa.String(length=64), nullable=True))
    if "action_binding" not in columns:
        op.add_column("approval_requests", sa.Column("action_binding", sa.JSON(), nullable=True))
    if "policy_version" not in columns:
        op.add_column("approval_requests", sa.Column("policy_version", sa.String(length=64), nullable=True))
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("approval_requests")}
    if "ix_approval_requests_action_fingerprint" not in indexes:
        op.create_index("ix_approval_requests_action_fingerprint", "approval_requests", ["action_fingerprint"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "approval_requests" not in inspector.get_table_names():
        return
    indexes = {i["name"] for i in inspector.get_indexes("approval_requests")}
    if "ix_approval_requests_action_fingerprint" in indexes:
        op.drop_index("ix_approval_requests_action_fingerprint", table_name="approval_requests")
    columns = {c["name"] for c in inspector.get_columns("approval_requests")}
    # Only remove columns introduced by this migration. Existing approval rows are preserved.
    for column in ("policy_version", "action_binding", "action_fingerprint"):
        if column in columns:
            op.drop_column("approval_requests", column)
