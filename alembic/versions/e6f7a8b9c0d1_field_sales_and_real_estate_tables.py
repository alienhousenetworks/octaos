"""Create field sales and real estate operational tables.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-22
"""
from alembic import op
import sqlalchemy as sa


revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None

FIELD_REAL_ESTATE_TABLES = [
    "field_sales_agent_status",
    "field_schedule_recovery_proposals",
    "connector_usage_audits",
    "real_estate_projects",
    "real_estate_units",
    "real_estate_site_visits",
    "real_estate_unit_holds",
    "real_estate_broker_attributions",
    "real_estate_bookings",
    "real_estate_payment_transactions",
    "real_estate_commission_ledgers",
    "real_estate_project_assignments",
]

FIELD_REAL_ESTATE_DROP_ORDER = [
    "real_estate_commission_ledgers",
    "real_estate_payment_transactions",
    "real_estate_bookings",
    "real_estate_unit_holds",
    "real_estate_site_visits",
    "real_estate_project_assignments",
    "real_estate_broker_attributions",
    "real_estate_units",
    "real_estate_projects",
    "connector_usage_audits",
    "field_schedule_recovery_proposals",
    "field_sales_agent_status",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    from app.models.base import Base
    import app.models.field_sales  # noqa: F401
    import app.models.real_estate  # noqa: F401

    missing = [
        Base.metadata.tables[name]
        for name in FIELD_REAL_ESTATE_TABLES
        if name in Base.metadata.tables and name not in tables
    ]
    if missing:
        Base.metadata.create_all(bind=bind, tables=missing, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for name in FIELD_REAL_ESTATE_DROP_ORDER:
        if name in tables:
            op.drop_table(name)
