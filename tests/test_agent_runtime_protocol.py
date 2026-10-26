from app.services.agent_runtime.protocol import (
    AgentEvent, AgentEventType, AgentOutcome, verify_acceptance, sanitize_public_text
)


def test_public_event_redacts_credentials_and_private_reasoning():
    event = AgentEvent(
        tenant_id="tenant-1",
        run_id="run-1",
        event_type=AgentEventType.PROGRESS,
        message="Started with api_key=abc123",
        payload={"chain_of_thought": "hidden", "status": "Running", "detail": "Bearer abc.def"},
    )
    public = event.to_public_dict()
    assert "abc123" not in public["message"]
    assert "chain_of_thought" not in public["payload"]
    assert "abc.def" not in public["payload"]["detail"]


def test_agent_outcome_rejects_unverified_empty_completion():
    import pytest
    with pytest.raises(ValueError):
        AgentOutcome(status="completed")


def test_success_requires_evidence_by_default():
    outcome = AgentOutcome(status="completed", output="I did it")
    assert not verify_acceptance(outcome)
    assert verify_acceptance(AgentOutcome(status="completed", evidence=[{"type": "receipt", "id": "r1"}]))


def test_outcome_rejects_negative_usage():
    import pytest
    with pytest.raises(ValueError):
        AgentOutcome(status="failed", input_tokens=-1)


def test_sanitize_public_text_bounds_output():
    assert len(sanitize_public_text("x" * 5000)) == 2000
