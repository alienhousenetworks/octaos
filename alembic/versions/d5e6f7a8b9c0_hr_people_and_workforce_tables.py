"""Create the people directory and workforce tables Ask HR reads and writes.

Revision ID: d5e6f7a8b9c0
Revises: c3b4a5d6e7f8
Create Date: 2026-10-21
"""
from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = "c3b4a5d6e7f8"
branch_labels = None
depends_on = None

HR_PEOPLE_TABLES = [
    "hr_departments",
    "hr_employees",
    "hr_company_policies",
    "hr_policy_acknowledgements",
    "hr_service_requests",
    "hr_leave_types",
    "hr_leave_ledger_entries",
    "hr_leave_requests",
    "hr_attendance_records",
    "hr_shift_rosters",
    "hr_shift_assignments",
]

# Child tables first so a downgrade does not trip foreign keys.
HR_PEOPLE_DROP_ORDER = [
    "hr_shift_assignments",
    "hr_shift_rosters",
    "hr_attendance_records",
    "hr_leave_requests",
    "hr_leave_ledger_entries",
    "hr_leave_types",
    "hr_service_requests",
    "hr_policy_acknowledgements",
    "hr_employees",
    "hr_company_policies",
    "hr_departments",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    from app.models.base import Base
    import app.models.hr_core  # noqa: F401
    import app.models.hr_workforce  # noqa: F401

    missing = [
        Base.metadata.tables[name]
        for name in HR_PEOPLE_TABLES
        if name in Base.metadata.tables and name not in tables
    ]
    if missing:
        Base.metadata.create_all(bind=bind, tables=missing, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for name in HR_PEOPLE_DROP_ORDER:
        if name in tables:
            op.drop_table(name)
