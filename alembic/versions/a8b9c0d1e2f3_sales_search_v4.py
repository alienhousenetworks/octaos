"""Parallel search jobs, cached tasks, and spend ledger.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "search_v4_jobs",
    "search_v4_tasks",
    "search_v4_ledger",
]


def upgrade() -> None:
    bind = op.get_bind()
    from app.models.base import Base
    from app.models import search_v4 as search_v4_models  # noqa: F401

    tables = [Base.metadata.tables[name] for name in NEW_TABLES if name in Base.metadata.tables]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for name in reversed(NEW_TABLES):
        if name in inspector.get_table_names():
            op.drop_table(name)
