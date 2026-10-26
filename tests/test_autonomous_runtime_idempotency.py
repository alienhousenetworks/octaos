"""Concurrency regression tests for autonomous task idempotency."""
from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

from app.models.autonomous_work import AutonomousTask
from app.services.autonomous_runtime.engine import AutonomousRuntime


def test_concurrent_idempotency_conflict_returns_existing_task():
    db = MagicMock()
    existing = MagicMock(spec=AutonomousTask)
    query = db.query.return_value
    query.filter.return_value.first.side_effect = [None, existing]
    db.flush.side_effect = IntegrityError("INSERT", {}, Exception("duplicate key"))

    result = AutonomousRuntime(db).create_task(
        tenant_id="tenant-a",
        created_by_id="user-a",
        title="Create campaign",
        goal="Create a campaign draft",
        idempotency_key="request-123",
    )

    assert result is existing
    db.rollback.assert_called_once()
    # The losing request must not append a second task-created event.
    db.add.assert_called_once()
