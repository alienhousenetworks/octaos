import hashlib
import hmac

from app.services.integrations.webhook_security import verify_timestamped_hmac


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
