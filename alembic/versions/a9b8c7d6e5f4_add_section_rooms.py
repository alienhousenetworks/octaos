"""Add section_rooms table and room_id foreign keys.

Revision ID: a9b8c7d6e5f4
Revises: f7a8b9c0d1e2
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa


revision = "a9b8c7d6e5f4"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "section_rooms" not in tables:
        op.create_table(
            "section_rooms",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("organization_id", sa.String(), nullable=True, index=True),
            sa.Column("section", sa.String(), nullable=False, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("slug", sa.String(), nullable=False, index=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("visibility", sa.String(), nullable=False, server_default="internal_public"),
            sa.Column("share_token", sa.String(), nullable=True, unique=True, index=True),
            sa.Column("access_list", sa.JSON(), nullable=True, server_default="[]"),
            sa.Column("data", sa.JSON(), nullable=True, server_default="{}"),
            sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "section", "slug", name="uq_tenant_section_room_slug"),
        )

    for tbl in ["candidates", "content_posts", "tickets", "deal_rooms", "leads"]:
        if tbl in tables:
            cols = [c["name"] for c in inspector.get_columns(tbl)]
            if "room_id" not in cols:
                op.add_column(tbl, sa.Column("room_id", sa.String(), sa.ForeignKey("section_rooms.id"), nullable=True, index=True))


def downgrade():
    for tbl in ["candidates", "content_posts", "tickets", "deal_rooms", "leads"]:
        try:
            op.drop_column(tbl, "room_id")
        except Exception:
            pass
    try:
        op.drop_table("section_rooms")
    except Exception:
        pass
