import hashlib
import hmac

from app.services.runtime_governance.tool_policy import (
    action_fingerprint,
    authorize_tool_call,
    verify_hmac_webhook,
)


def test_tool_policy_rejects_cross_tenant_calls_even_with_grant():
    result = authorize_tool_call(
        tenant_id="tenant-a", request_tenant_id="tenant-b",
        tool_name="lead.read", granted_tools=["lead.read"], connection_active=True,
    )
    assert not result.allowed
    assert result.reason == "TENANT_MISMATCH"


def test_tool_policy_requires_explicit_grant_and_active_connection():
    assert authorize_tool_call(
        tenant_id="t", request_tenant_id="t", tool_name="lead.read",
        granted_tools=[], connection_active=True,
    ).reason == "TOOL_NOT_GRANTED"
    assert authorize_tool_call(
        tenant_id="t", request_tenant_id="t", tool_name="lead.read",
        granted_tools=["lead.read"], connection_active=False,
    ).reason == "CONNECTION_INACTIVE"


def test_high_risk_tool_requires_approval_bound_to_exact_action():
    kwargs = dict(
        tenant_id="t", request_tenant_id="t", tool_name="email.send",
        granted_tools=["email.send"], connection_active=True,
    )
    result = authorize_tool_call(**kwargs)
    assert not result.allowed and result.approval_required
    assert result.reason == "APPROVAL_REQUIRED"

    # A generic "approved" flag is not sufficient.
    result = authorize_tool_call(**kwargs, approval_status="approved")
    assert not result.allowed
    assert result.reason == "APPROVAL_BINDING_REQUIRED"

    binding = action_fingerprint(
        tenant_id="t", run_id="run-1", bot_id="lead-bot",
        tool_name="email.send", target="prospect@example.com",
        payload={"subject": "Hello", "body": "Draft A"}, policy_version="v3",
    )
    assert authorize_tool_call(
        **kwargs, approval_status="approved",
        action_binding=binding, approved_action_binding=binding,
    ).allowed

    modified = action_fingerprint(
        tenant_id="t", run_id="run-1", bot_id="lead-bot",
        tool_name="email.send", target="different@example.com",
        payload={"subject": "Hello", "body": "Draft A"}, policy_version="v3",
    )
    result = authorize_tool_call(
        **kwargs, approval_status="approved",
        action_binding=modified, approved_action_binding=binding,
    )
    assert not result.allowed
    assert result.reason == "APPROVAL_BINDING_MISMATCH"


def test_action_fingerprint_binds_tenant_run_bot_target_payload_and_policy():
    common = dict(
        tenant_id="t", run_id="r", bot_id="b", tool_name="post.publish",
        target="account-1", payload={"text": "Approved copy"}, policy_version="p1",
    )
    original = action_fingerprint(**common)
    assert original == action_fingerprint(**common)
    assert original != action_fingerprint(**{**common, "payload": {"text": "Changed copy"}})
    assert original != action_fingerprint(**{**common, "run_id": "other-run"})
    assert original != action_fingerprint(**{**common, "policy_version": "p2"})


def test_rejected_high_risk_action_never_executes():
    result = authorize_tool_call(
        tenant_id="t", request_tenant_id="t", tool_name="post.publish",
        granted_tools=["post.publish"], connection_active=True, approval_status="rejected",
    )
    assert not result.allowed
    assert result.reason == "APPROVAL_REJECTED"


def test_webhook_hmac_validates_signature_and_timestamp():
    secret, timestamp, body, now = "test-secret", "1700000000", b'{"event":"created"}', 1700000000
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert verify_hmac_webhook(secret=secret, timestamp=timestamp, raw_body=body, signature=signature, now=now)
    assert not verify_hmac_webhook(secret=secret, timestamp=timestamp, raw_body=body, signature="bad", now=now)
    assert not verify_hmac_webhook(secret=secret, timestamp=timestamp, raw_body=body, signature=signature, now=now + 1000)


def test_webhook_accepts_prefixed_signature():
    secret, timestamp, body, now = "test-secret", "1700000000", b"body", 1700000000
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert verify_hmac_webhook(secret=secret, timestamp=timestamp, raw_body=body, signature="sha256=" + signature, now=now)


def test_approval_request_persists_exact_action_binding_fields():
    from app.models.enterprise import ApprovalRequest

    columns = set(ApprovalRequest.__table__.columns.keys())
    assert {"action_fingerprint", "action_binding", "policy_version"}.issubset(columns)


def test_approval_binding_is_invalidated_by_payload_change():
    original = action_fingerprint(
        tenant_id="tenant-a", run_id="run-1", bot_id="bot-1",
        tool_name="email.send", target="customer@example.com",
        payload={"subject": "Approved", "body": "Version 1"}, policy_version="1",
    )
    edited = action_fingerprint(
        tenant_id="tenant-a", run_id="run-1", bot_id="bot-1",
        tool_name="email.send", target="customer@example.com",
        payload={"subject": "Approved", "body": "Version 2"}, policy_version="1",
    )
    assert original != edited
