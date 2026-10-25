"""Idempotent schema rollout for HR enterprise models.

Run during a maintenance window after taking a database backup:
    python scripts/migrate_hr_enterprise_schema.py

This guarded rollout script is used for the HR-only additive schema until the deployment
owner confirms the repository's active Alembic head and adopts an ordered revision. It
creates the listed new HR tables and the partial unique leave-ledger index. It refuses to proceed if
existing ledger rows violate the new uniqueness rule.
"""
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.base import Base
from app.models import hr_core as _hr_core  # noqa: F401
from app.models import hr_workforce as _hr_workforce  # noqa: F401


NEW_TABLES = (
    "hr_attendance_audit_events",
    "hr_employee_availability",
    "hr_shift_demands",
    "hr_performance_reviews",
    "hr_compensation_changes",
    "hr_lifecycle_tasks",
    "hr_lifecycle_cases",
    "hr_labor_rules",
)
LEDGER_INDEX = "uq_leave_ledger_reference_once"


def main() -> None:
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    try:
        with engine.begin() as connection:
            duplicates = connection.execute(text(
                """
                SELECT tenant_id, transaction_type, reference_id, COUNT(*) AS row_count
                FROM hr_leave_ledger_entries
                WHERE reference_id IS NOT NULL
                GROUP BY tenant_id, transaction_type, reference_id
                HAVING COUNT(*) > 1
                LIMIT 20
                """
            )).mappings().all()
            if duplicates:
                raise RuntimeError(
                    "Migration stopped: duplicate leave-ledger references exist. "
                    "Reconcile these rows manually before retrying: "
                    + repr([dict(row) for row in duplicates])
                )

            tables = [Base.metadata.tables[name] for name in NEW_TABLES]
            Base.metadata.create_all(bind=connection, tables=tables, checkfirst=True)

            ledger_table = Base.metadata.tables["hr_leave_ledger_entries"]
            index = next((item for item in ledger_table.indexes if item.name == LEDGER_INDEX), None)
            if index is None:
                raise RuntimeError(f"Expected model index {LEDGER_INDEX!r} is not registered.")
            index.create(bind=connection, checkfirst=True)
        print("HR enterprise schema migration completed.")
        print("Created/verified tables: " + ", ".join(NEW_TABLES))
        print("Created/verified partial unique index: " + LEDGER_INDEX)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
