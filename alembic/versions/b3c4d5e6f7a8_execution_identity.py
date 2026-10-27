"""Add canonical execution identity aliases across OctaOS runtimes.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
"""
from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "execution_identities" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "execution_identities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("canonical_execution_id", sa.String(), nullable=False),
        sa.Column("source_kind", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "source_kind", "source_id", name="uq_execution_identity_tenant_source"),
    )
    op.create_index("ix_execution_identities_tenant_id", "execution_identities", ["tenant_id"])
    op.create_index("ix_execution_identities_canonical_execution_id", "execution_identities", ["canonical_execution_id"])
    op.create_index("ix_execution_identity_tenant_canonical", "execution_identities", ["tenant_id", "canonical_execution_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if "execution_identities" in sa.inspect(bind).get_table_names():
        op.drop_table("execution_identities")
