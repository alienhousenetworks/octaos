"""campaign studio artifact versions and virtual influencer profiles

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "virtual_influencer_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft_requires_review"),
        sa.Column("brief", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_virtual_influencer_profiles_id", "virtual_influencer_profiles", ["id"])
    op.create_index("ix_virtual_influencer_profiles_tenant_id", "virtual_influencer_profiles", ["tenant_id"])
    op.create_index("ix_virtual_influencer_profiles_status", "virtual_influencer_profiles", ["status"])

    op.create_table(
        "campaign_artifacts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("campaign_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_campaign_artifacts_id", "campaign_artifacts", ["id"])
    op.create_index("ix_campaign_artifacts_tenant_id", "campaign_artifacts", ["tenant_id"])
    op.create_index("ix_campaign_artifacts_campaign_id", "campaign_artifacts", ["campaign_id"])
    op.create_index("ix_campaign_artifacts_artifact_type", "campaign_artifacts", ["artifact_type"])
    op.create_index("ix_campaign_artifacts_status", "campaign_artifacts", ["status"])

    op.create_table(
        "campaign_artifact_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("artifact_id", sa.String(), sa.ForeignKey("campaign_artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("reviewed_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("artifact_id", "version", name="uq_campaign_artifact_version"),
    )
    op.create_index("ix_campaign_artifact_versions_id", "campaign_artifact_versions", ["id"])
    op.create_index("ix_campaign_artifact_versions_tenant_id", "campaign_artifact_versions", ["tenant_id"])
    op.create_index("ix_campaign_artifact_versions_artifact_id", "campaign_artifact_versions", ["artifact_id"])
    op.create_index("ix_campaign_artifact_versions_content_hash", "campaign_artifact_versions", ["content_hash"])
    op.create_index("ix_campaign_artifact_versions_review_status", "campaign_artifact_versions", ["review_status"])


def downgrade() -> None:
    op.drop_table("campaign_artifact_versions")
    op.drop_table("campaign_artifacts")
    op.drop_table("virtual_influencer_profiles")
