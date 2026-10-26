import hashlib
import hmac
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.integrations.webhook_security import verify_timestamped_hmac
from app.api.v1.endpoints import integrations


def _signature(secret, timestamp, body):
    signed = str(timestamp).encode("ascii") + b"." + body
    return "sha256=" + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()


def test_timestamped_webhook_signature_accepts_valid_payload():
    secret = "tenant-specific-webhook-secret"
    timestamp = "1761500000"
    body = b'{"event":"lead.created"}'

    assert verify_timestamped_hmac(
        secret=secret,
        timestamp=timestamp,
        signature=_signature(secret, timestamp, body),
        body=body,
        now=1761500000,
    )


def test_timestamped_webhook_signature_rejects_modified_body():
    secret = "tenant-specific-webhook-secret"
    timestamp = "1761500000"

    assert not verify_timestamped_hmac(
        secret=secret,
        timestamp=timestamp,
        signature=_signature(secret, timestamp, b'{"event":"lead.created"}'),
        body=b'{"event":"lead.deleted"}',
        now=1761500000,
    )


def test_timestamped_webhook_signature_rejects_stale_timestamp():
    secret = "tenant-specific-webhook-secret"
    timestamp = "1761499000"
    body = b"{}"

    assert not verify_timestamped_hmac(
        secret=secret,
        timestamp=timestamp,
        signature=_signature(secret, timestamp, body),
        body=body,
        now=1761500000,
        tolerance_seconds=300,
    )


def test_timestamped_webhook_signature_fails_closed_when_missing():
    assert not verify_timestamped_hmac(
        secret="",
        timestamp=None,
        signature=None,
        body=b"{}",
        now=1761500000,
    )


class _FakeRequest:
    def __init__(self, headers):
        self.headers = headers


def test_production_webhook_ingress_fails_closed_without_secret(monkeypatch):
    monkeypatch.setattr(integrations.settings, "DEV", False)
    monkeypatch.setattr(integrations.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(integrations, "_webhook_secret", lambda db, tenant_id, provider: None)

    with pytest.raises(HTTPException) as exc:
        integrations._require_webhook_signature(
            db=object(),
            tenant_id="tenant-1",
            provider="calendly",
            request=_FakeRequest({}),
            raw_body=b"{}",
        )

    assert exc.value.status_code == 503


def test_production_webhook_ingress_accepts_valid_signed_request(monkeypatch):
    secret = "per-tenant-secret"
    timestamp = str(int(time.time()))
    body = b'{"event":"invitee.created"}'
    monkeypatch.setattr(integrations.settings, "DEV", False)
    monkeypatch.setattr(integrations.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(integrations, "_webhook_secret", lambda db, tenant_id, provider: secret)

    integrations._require_webhook_signature(
        db=object(),
        tenant_id="tenant-1",
        provider="calendly",
        request=_FakeRequest({
            "X-OctaOS-Timestamp": timestamp,
            "X-OctaOS-Signature": _signature(secret, timestamp, body),
        }),
        raw_body=body,
    )


def test_webhook_ingress_rejects_inactive_tenant():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(is_active=False)

    with pytest.raises(HTTPException) as exc:
        integrations._ensure_webhook_tenant_active(db, "suspended-tenant")

    assert exc.value.status_code == 403


def test_webhook_ingress_rejects_unknown_tenant():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        integrations._ensure_webhook_tenant_active(db, "unknown-tenant")

    assert exc.value.status_code == 404


def test_webhook_secret_configuration_is_admin_only():
    user = SimpleNamespace(tenant_id="tenant-1", role="member", is_system_admin=False)

    with pytest.raises(HTTPException) as exc:
        integrations.configure_webhook_security(
            provider="calendly",
            config=integrations.WebhookSecurityConfig(signing_secret="x" * 32),
            db=object(),
            current_user=user,
        )

    assert exc.value.status_code == 403


def test_webhook_secret_configuration_encrypts_verification_token_and_never_returns_secrets(monkeypatch):
    captured = {}
    monkeypatch.setattr(integrations, "save_credential", lambda db, **kwargs: captured.update(kwargs))
    monkeypatch.setattr(integrations, "encrypt_api_key", lambda value: "encrypted:" + value)
    user = SimpleNamespace(tenant_id="tenant-1", role="admin", is_system_admin=False)

    result = integrations.configure_webhook_security(
        provider="googleforms",
        config=integrations.WebhookSecurityConfig(
            signing_secret="signing-secret-long-enough-123",
            verification_token="provider-verification-token",
        ),
        db=object(),
        current_user=user,
    )

    assert captured["tenant_id"] == "tenant-1"
    assert captured["provider"] == "google_forms_webhook"
    assert captured["key"] == "signing-secret-long-enough-123"
    assert captured["settings"]["verification_token_encrypted"] == "encrypted:provider-verification-token"
    assert result == {
        "provider": "google_forms",
        "configured": True,
        "verification_token_configured": True,
    }
    assert "signing-secret-long-enough-123" not in repr(result)
    assert "provider-verification-token" not in repr(result)
