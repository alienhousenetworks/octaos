"""Create durable Orchestra Data Intelligence run and artifact tables.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-25
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None

TABLES = ("data_analysis_runs", "data_analysis_artifacts")


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    from app.models.base import Base
    from app.models import data_intelligence  # noqa: F401 — registers table metadata
    missing = [Base.metadata.tables[name] for name in TABLES
               if name in Base.metadata.tables and name not in existing]
    if missing:
        Base.metadata.create_all(bind=bind, tables=missing, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    # Drop child table before parent to respect the foreign key.
    for name in ("data_analysis_artifacts", "data_analysis_runs"):
        if name in existing:
            op.drop_table(name)
