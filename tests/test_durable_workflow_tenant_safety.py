from unittest.mock import MagicMock

import pytest

from app.models.enterprise import WorkflowCheckpoint
from app.services.durable_workflows import (
    DurableWorkflowService,
    _scoped_idempotency_key,
)


def _column_values(expressions):
    values = {}
    for expression in expressions:
        left = getattr(expression, "left", None)
        right = getattr(expression, "right", None)
        if left is not None and right is not None and hasattr(left, "name"):
            values[left.name] = getattr(right, "value", None)
    return values


def test_idempotency_key_is_tenant_scoped_and_not_raw_input():
    raw_key = "same-client-request-key"
    a = _scoped_idempotency_key("tenant-a", raw_key)
    b = _scoped_idempotency_key("tenant-b", raw_key)

    assert a != b
    assert raw_key not in a
    assert a == _scoped_idempotency_key("tenant-a", raw_key)


def test_start_run_idempotency_lookup_is_tenant_scoped():
    db = MagicMock()
    existing = MagicMock(spec=WorkflowCheckpoint)
    db.query.return_value.filter.return_value.first.return_value = existing

    result = DurableWorkflowService(db, "tenant-a").start_run(
        "demo", "run-2", idempotency_key="client-key"
    )

    assert result is existing
    expressions = db.query.return_value.filter.call_args.args
    assert _column_values(expressions)["tenant_id"] == "tenant-a"
    db.add.assert_not_called()


def test_checkpoint_rejects_step_regression():
    db = MagicMock()
    checkpoint = MagicMock(spec=WorkflowCheckpoint)
    checkpoint.status = "running"
    checkpoint.step_index = 4
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = checkpoint

    service = DurableWorkflowService(db, "tenant-a")
    with pytest.raises(ValueError, match="cannot move backwards"):
        service.checkpoint(
            "run-1", step_index=3, step_name="old-step", state={}, status="running"
        )
    db.commit.assert_not_called()


def test_checkpoint_rejects_terminal_state_transition():
    db = MagicMock()
    checkpoint = MagicMock(spec=WorkflowCheckpoint)
    checkpoint.status = "completed"
    checkpoint.step_index = 2
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = checkpoint

    service = DurableWorkflowService(db, "tenant-a")
    with pytest.raises(ValueError, match="Invalid workflow status transition"):
        service.checkpoint(
            "run-1", step_index=3, step_name="after-complete", state={}, status="running"
        )
    db.commit.assert_not_called()


def test_checkpoint_rejects_missing_run_in_tenant_scope():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    service = DurableWorkflowService(db, "tenant-a")
    with pytest.raises(ValueError, match="Run not found"):
        service.checkpoint(
            "run-other-tenant", step_index=1, step_name="step", state={}, status="running"
        )
