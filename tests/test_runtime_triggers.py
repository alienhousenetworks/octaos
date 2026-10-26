import pytest

from app.services.runtime_governance.triggers import trigger_idempotency_key


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
