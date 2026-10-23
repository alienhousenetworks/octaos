"""Create real estate cost sheets table.

Revision ID: e7f8a9b0c1d2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "real_estate_cost_sheets" not in tables:
        from app.models.base import Base
        import app.models.real_estate  # noqa: F401

        if "real_estate_cost_sheets" in Base.metadata.tables:
            Base.metadata.create_all(
                bind=bind,
                tables=[Base.metadata.tables["real_estate_cost_sheets"]],
                checkfirst=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "real_estate_cost_sheets" in tables:
        op.drop_table("real_estate_cost_sheets")
