import hashlib
import hmac

from app.services.runtime_governance.tool_policy import authorize_tool_call, verify_hmac_webhook


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


def test_high_risk_tool_requires_approval():
    kwargs = dict(tenant_id="t", request_tenant_id="t", tool_name="email.send",
                  granted_tools=["email.send"], connection_active=True)
    result = authorize_tool_call(**kwargs)
    assert not result.allowed and result.approval_required
    assert authorize_tool_call(**kwargs, approval_status="approved").allowed


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
