"""Governed Dynamic Knowledge Connector Platform tables.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa


revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "knowledge_connectors",
    "connector_secret_references",
    "connector_config_versions",
    "connector_permissions",
    "connector_executions",
    "connector_schema_versions",
    "connector_audit_events",
    "connector_cache_entries",
]


def upgrade() -> None:
    bind = op.get_bind()
    from app.models.base import Base
    from app.models import knowledge_connectors as kc_models  # noqa: F401

    tables = [Base.metadata.tables[name] for name in NEW_TABLES if name in Base.metadata.tables]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for name in reversed(NEW_TABLES):
        if name in inspector.get_table_names():
            op.drop_table(name)
