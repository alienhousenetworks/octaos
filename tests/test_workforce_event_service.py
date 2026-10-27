from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.workforce_events import WorkforceEvent
from app.services.workforce_event_service import (
    EventConflictError,
    WorkforceEventService,
    decode_cursor,
    encode_cursor,
)


def _tenant_filter_values(expressions):
    values = {}
    for expression in expressions:
        left = getattr(expression, "left", None)
        right = getattr(expression, "right", None)
        if left is not None and right is not None and hasattr(left, "name"):
            values[left.name] = getattr(right, "value", None)
    return values


def test_event_append_is_idempotent_for_same_tenant_key_and_payload():
    db = MagicMock()
    existing = MagicMock(spec=WorkforceEvent)
    existing.event_type = "agent.started"
    existing.payload = {"run": "r-1"}
    db.query.return_value.filter.return_value.first.return_value = existing

    result = WorkforceEventService(db, "tenant-a").append(
        event_key="event-1",
        event_type="agent.started",
        payload={"run": "r-1"},
    )

    assert result is existing
    assert _tenant_filter_values(db.query.return_value.filter.call_args.args)["tenant_id"] == "tenant-a"
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_event_key_reuse_with_different_payload_conflicts():
    db = MagicMock()
    existing = MagicMock(spec=WorkforceEvent)
    existing.event_type = "agent.started"
    existing.payload = {"run": "r-1"}
    db.query.return_value.filter.return_value.first.return_value = existing

    with pytest.raises(EventConflictError):
        WorkforceEventService(db, "tenant-a").append(
            event_key="event-1",
            event_type="agent.started",
            payload={"run": "different"},
        )


def test_event_payload_limit_is_enforced_before_write():
    db = MagicMock()
    with pytest.raises(ValueError, match="64 KiB"):
        WorkforceEventService(db, "tenant-a").append(
            event_key="large",
            event_type="agent.started",
            payload={"data": "x" * (65 * 1024)},
        )
    db.add.assert_not_called()


def test_event_cursor_round_trip():
    timestamp = datetime(2026, 10, 26, 12, 30, tzinfo=timezone.utc)
    cursor = encode_cursor(timestamp, "event-123")
    parsed_timestamp, event_id = decode_cursor(cursor)
    assert parsed_timestamp == timestamp
    assert event_id == "event-123"


def test_invalid_event_cursor_rejected():
    with pytest.raises(ValueError, match="Invalid event cursor"):
        decode_cursor("not-a-valid-cursor")
