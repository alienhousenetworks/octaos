import pytest
from datetime import datetime, timezone, timedelta

from app.models.schedules import ScheduledTrigger
from app.services.runtime_governance.triggers import (
    complete_scheduled_trigger,
    lease_scheduled_trigger,
    trigger_idempotency_key,
)


def test_trigger_delivery_key_is_stable_and_bounded():
    a = trigger_idempotency_key("trigger-1", "provider-event-123")
    b = trigger_idempotency_key("trigger-1", "provider-event-123")
    c = trigger_idempotency_key("trigger-1", "provider-event-456")
    assert a == b
    assert a != c
    assert len(a) < 160


@pytest.mark.parametrize("trigger_id,delivery_id", [
    ("", "event"), ("trigger", ""), ("../bad", "event"), ("trigger", "bad event"),
])
def test_trigger_key_rejects_untrusted_identifier_shapes(trigger_id, delivery_id):
    with pytest.raises(ValueError):
        trigger_idempotency_key(trigger_id, delivery_id)



def test_schedule_lease_and_failure_recovery_are_bounded():
    now = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
    trigger = ScheduledTrigger(
        tenant_id="tenant-a",
        target_type="campaign_planner",
        frequency="daily",
        time_of_day="15:00",
        is_active=True,
    )
    lease_scheduled_trigger(trigger, now=now, lease_seconds=90)
    assert trigger.last_status == "running"
    assert trigger.next_run_at == now + timedelta(seconds=90)

    complete_scheduled_trigger(trigger, now=now, succeeded=False, error="worker unavailable")
    assert trigger.last_status == "failed"
    assert trigger.last_error == "worker unavailable"
    assert trigger.next_run_at == now + timedelta(minutes=1)
    assert trigger.is_active is True


def test_successful_once_schedule_deactivates_and_clears_next_run():
    now = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)
    trigger = ScheduledTrigger(
        tenant_id="tenant-a",
        target_type="campaign_planner",
        frequency="once",
        time_of_day="09:00",
        is_active=True,
    )
    complete_scheduled_trigger(trigger, now=now, succeeded=True)
    assert trigger.last_status == "success"
    assert trigger.is_active is False
    assert trigger.next_run_at is None
