"""Unit tests for Universal Email architecture (Unipile, EmailEngine, Inbound Webhooks, and Fallback)."""
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, APICredential, User
from app.models.verticals import Lead
from app.services.email.universal_provider import (
    UnipileAdapter,
    EmailEngineAdapter,
    AurinkoAdapter,
    get_universal_mailbox_provider,
)
from app.services.email.sender import (
    send_email_with_status,
    check_universal_email_configured,
)


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    tenant = Tenant(
        id="tenant_univ_test",
        name="Universal Mailbox Corp",
        subdomain="univ-mail",
        is_active=True,
    )
    session.add(tenant)
    session.commit()

    lead = Lead(
        id="lead_universal_1",
        tenant_id="tenant_univ_test",
        name="Sarah Connor",
        email="sarah.connor@cyberdyne.io",
        company="Cyberdyne Systems",
        status="contacted",
        data={"conversation": []},
    )
    session.add(lead)
    session.commit()

    yield session
    session.close()


def test_unipile_adapter_webhook_verification():
    secret = "test_webhook_secret_123"
    adapter = UnipileAdapter(api_key="mock_key", webhook_secret=secret)

    payload = b'{"event": "message_received", "data": {"subject": "Re: Partnership"}}'
    valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    assert adapter.verify_webhook(payload, valid_sig) is True
    assert adapter.verify_webhook(payload, "invalid_sig") is False


def test_unipile_adapter_inbound_parsing():
    adapter = UnipileAdapter(api_key="mock_key")
    payload = json.dumps({
        "event": "message_received",
        "data": {
            "id": "msg_unipile_999",
            "thread_id": "thread_abc",
            "from": {"identifier": "sarah.connor@cyberdyne.io", "name": "Sarah Connor"},
            "to": [{"identifier": "sales@octaos.com"}],
            "subject": "Re: AI Platform Demo",
            "body_plain": "Sounds great, let's schedule a call this Friday.",
        }
    }).encode("utf-8")

    parsed = adapter.parse_inbound_webhook(payload, {})
    assert parsed is not None
    assert parsed["sender"] == "sarah.connor@cyberdyne.io"
    assert parsed["subject"] == "Re: AI Platform Demo"
    assert "call this Friday" in parsed["body"]
    assert parsed["message_id"] == "msg_unipile_999"
    assert parsed["thread_id"] == "thread_abc"


def test_emailengine_adapter_inbound_parsing():
    adapter = EmailEngineAdapter(base_url="http://localhost:3000", access_token="token_123")
    payload = json.dumps({
        "event": "messageNew",
        "account": "tenant_univ_test",
        "data": {
            "id": "ee_msg_101",
            "threadId": "ee_thread_202",
            "from": {"address": "sarah.connor@cyberdyne.io", "name": "Sarah"},
            "to": [{"address": "rep@octaos.com"}],
            "subject": "Interested in Pilot",
            "text": "Please send over the contract proposal.",
        }
    }).encode("utf-8")

    parsed = adapter.parse_inbound_webhook(payload, {})
    assert parsed is not None
    assert parsed["sender"] == "sarah.connor@cyberdyne.io"
    assert parsed["subject"] == "Interested in Pilot"
    assert "contract proposal" in parsed["body"]
    assert parsed["message_id"] == "ee_msg_101"


def test_aurinko_adapter_webhook_verification():
    secret = "aurinko_webhook_secret_999"
    adapter = AurinkoAdapter(client_id="mock_id", client_secret="mock_sec", webhook_secret=secret)

    payload = b'{"eventType": "email.message.created", "payload": {"subject": "Test Aurinko"}}'
    valid_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    assert adapter.verify_webhook(payload, valid_sig) is True
    assert adapter.verify_webhook(payload, "invalid_sig") is False


def test_aurinko_adapter_inbound_parsing():
    adapter = AurinkoAdapter(client_id="mock_id", client_secret="mock_sec")
    payload = json.dumps({
        "eventType": "email.message.created",
        "accountId": 88812,
        "payload": {
            "id": "aurinko_msg_555",
            "threadId": "aurinko_thread_777",
            "from": [{"address": "sarah.connor@cyberdyne.io", "name": "Sarah Connor"}],
            "to": [{"address": "sales@octaos.com"}],
            "subject": "Re: Enterprise Pricing Inquiry",
            "body": "We would like to book a demo next Tuesday.",
        }
    }).encode("utf-8")

    parsed = adapter.parse_inbound_webhook(payload, {})
    assert parsed is not None
    assert parsed["provider"] == "aurinko"
    assert parsed["sender"] == "sarah.connor@cyberdyne.io"
    assert parsed["subject"] == "Re: Enterprise Pricing Inquiry"
    assert "book a demo" in parsed["body"]
    assert parsed["message_id"] == "aurinko_msg_555"
    assert parsed["thread_id"] == "aurinko_thread_777"
    assert parsed["account_id"] == 88812


def test_aurinko_adapter_connect_session():
    adapter = AurinkoAdapter(client_id="aurinko_client_abc", client_secret="secret_xyz")
    res = adapter.create_connect_session(
        tenant_id="tenant_univ_test",
        redirect_url="https://app.octaos.com/callback",
        provider_type="microsoft",
    )
    assert res["ok"] is True
    assert "https://api.aurinko.io/v1/auth/authorize" in res["connect_url"]
    assert "clientId=aurinko_client_abc" in res["connect_url"]
    assert "serviceType=Office365" in res["connect_url"]


def test_universal_provider_factory_resolution_aurinko(test_db):
    from app.core.security import encrypt_api_key

    cred = APICredential(
        tenant_id="tenant_univ_test",
        provider="aurinko",
        encrypted_key=encrypt_api_key("aurinko_client_secret_live"),
        settings={"client_id": "aurinko_client_id_live", "webhook_secret": "sec_aurinko"},
    )
    test_db.add(cred)
    test_db.commit()

    provider = get_universal_mailbox_provider(test_db, "tenant_univ_test")
    assert provider is not None
    assert provider.name == "aurinko"
    assert provider.is_configured() is True
    test_db.delete(cred)
    test_db.commit()


def test_universal_provider_factory_resolution(test_db):
    from app.core.security import encrypt_api_key

    # No credential yet
    provider = get_universal_mailbox_provider(test_db, "tenant_univ_test")
    assert provider is None

    # Add Unipile credential
    cred = APICredential(
        tenant_id="tenant_univ_test",
        provider="unipile",
        encrypted_key=encrypt_api_key("unipile_live_key_xyz"),
        settings={"api_url": "https://api1.unipile.com:13142", "webhook_secret": "sec123"},
    )
    test_db.add(cred)
    test_db.commit()

    provider = get_universal_mailbox_provider(test_db, "tenant_univ_test")
    assert provider is not None
    assert provider.name == "unipile"
    assert provider.is_configured() is True


def test_send_email_with_status_prioritizes_universal(test_db):
    from app.core.security import encrypt_api_key

    cred = APICredential(
        tenant_id="tenant_univ_test",
        provider="unipile",
        encrypted_key=encrypt_api_key("unipile_live_key_xyz"),
    )
    test_db.add(cred)
    test_db.commit()

    # Mock universal provider send_email to succeed
    with patch("app.services.email.universal_provider.UnipileAdapter.send_email") as mock_send:
        mock_send.return_value = {
            "sent": True,
            "channel": "unipile",
            "message_id": "msg_univ_123",
            "thread_id": "thread_univ_456",
        }

        res = send_email_with_status(
            db=test_db,
            tenant_id="tenant_univ_test",
            to_email="prospect@target.com",
            subject="Intro to OctaOS",
            body="Hello from OctaOS",
        )

        assert res["sent"] is True
        assert res["channel"] == "universal"
        assert res["provider"] == "unipile"
        mock_send.assert_called_once()


def test_send_email_with_status_fallback_to_smtp(test_db):
    from app.core.security import encrypt_api_key

    # Configure only SMTP
    smtp_url = "smtp://user:pass@smtp.example.com:587"
    cred = APICredential(
        tenant_id="tenant_univ_test",
        provider="smtp",
        encrypted_key=encrypt_api_key(smtp_url),
    )
    test_db.add(cred)
    test_db.commit()

    with patch("app.services.email.sender.send_smtp_email", return_value=True) as mock_smtp:
        res = send_email_with_status(
            db=test_db,
            tenant_id="tenant_univ_test",
            to_email="prospect@target.com",
            subject="Fallback Subject",
            body="Fallback Body",
        )
        assert res["sent"] is True
        assert res["channel"] == "smtp"
        mock_smtp.assert_called_once()


def test_webhook_lead_matching_endpoint(test_db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db

    client = TestClient(app)

    # Inbound email payload matching lead 'sarah.connor@cyberdyne.io'
    webhook_payload = {
        "event": "message_received",
        "data": {
            "id": "webhook_msg_test_888",
            "thread_id": "thread_cyberdyne_1",
            "from": {"identifier": "sarah.connor@cyberdyne.io"},
            "to": [{"identifier": "sales@octaos.com"}],
            "subject": "Re: Partnership Inquiry",
            "body_plain": "Yes, we are definitely interested in the pilot project.",
        }
    }

    with patch("app.core.celery_app.celery_app.send_task") as mock_celery:
        response = client.post(
            "/api/v1/unified-mail/webhook/tenant_univ_test",
            json=webhook_payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued_for_sales"
        assert data["lead_id"] == "lead_universal_1"
        assert data["external_id"] == "webhook_msg_test_888"
        mock_celery.assert_called_once()

    app.dependency_overrides.clear()

