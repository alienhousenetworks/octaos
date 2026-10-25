"""Create durable Orchestra Data Intelligence run and artifact tables.

Revision ID: c4d5e6f7a8b9
Revises: e8f9a0b1c2d3
Create Date: 2026-10-25

This file kept its original name. Revision f7a8b9c0d1e2 is already used by
f7a8b9c0d1e2_hr_talent_lifecycle.py, which is an ancestor of e6f7a8b9c0d1.
Reusing that id made `alembic upgrade heads` fail:

    Requested revision e8f9a0b1c2d3 overlaps with other requested revisions f7a8b9c0d1e2

The filename stays so this stays a tracked file. scripts/fix_alembic_and_migrate.py
deletes untracked scripts under alembic/versions before upgrading.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "e8f9a0b1c2d3"
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
