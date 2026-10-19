import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, APICredential
from app.models.verticals import Lead
from app.models.deal_room import DealRoom, SalesOutboxItem
from app.services.sales.outbox_service import SalesOutboxService
from app.services.sales.bounce_sentinel import BounceSentinel
from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper
from app.services.sales_os.discovery.direct_profiler import DirectProfiler


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create dummy tenant
    tenant = Tenant(id="tenant_test_123", name="Acme Corp")
    session.add(tenant)
    session.commit()

    yield session
    session.close()


def test_sales_outbox_staging_and_stop_on_reply(test_db):
    tenant_id = "tenant_test_123"

    # Create lead
    lead = Lead(
        id="lead_001",
        tenant_id=tenant_id,
        name="Sarah Connor",
        email="sarah@cyberdyne.com",
        company="Cyberdyne Systems",
        status="captured",
    )
    test_db.add(lead)
    test_db.commit()

    outbox_svc = SalesOutboxService(test_db, tenant_id)

    # Multi-step sequence
    schedule = [
        {"day": 1, "channel": "Email", "subject": "Intro", "content": "Hi Sarah, noticed Cyberdyne's growth. Open to a chat?"},
        {"day": 4, "channel": "Email", "subject": "Following up", "content": "Hi Sarah, following up on my previous note."},
        {"day": 8, "channel": "Email", "subject": "Breakup", "content": "Hi Sarah, assume this is not a priority. Best."},
    ]

    staged = outbox_svc.stage_sequence(lead, schedule)
    assert len(staged) == 3

    # Check statuses
    items = test_db.query(SalesOutboxItem).filter_by(lead_id="lead_001").all()
    assert len(items) == 3
    assert all(i.status == "scheduled" for i in items)

    # Simulate an inbound reply from Sarah!
    cancelled_count = outbox_svc.cancel_pending_for_lead(
        lead_id=lead.id,
        recipient_email=lead.email,
        reason="prospect_replied"
    )
    assert cancelled_count == 3

    # Verify all pending items are now CANCELLED
    items_after = test_db.query(SalesOutboxItem).filter_by(lead_id="lead_001").all()
    assert all(i.status == "cancelled" for i in items_after)
    assert all(i.cancellation_reason == "prospect_replied" for i in items_after)


def test_bounce_sentinel_ndr_detection_and_circuit_breaker(test_db):
    tenant_id = "tenant_test_123"

    # Verify NDR detection
    assert BounceSentinel.is_bounce("mailer-daemon@googlemail.com", "Delivery Status Notification (Failure)") is True
    assert BounceSentinel.is_bounce("postmaster@domain.com", "Undelivered Mail Returned to Sender") is True
    assert BounceSentinel.is_bounce("prospect@company.com", "Re: Partnership opportunity") is False

    # Extract bounced email
    ndr_body = """
    This is an automatically generated Delivery Status Notification.
    Delivery to the following recipient failed permanently:
        invalid-user@badtarget.com
    Technical details of permanent failure:
    Google tried to deliver your message, but it was rejected by the server for the recipient domain.
    """
    bounced = BounceSentinel.extract_bounced_email(ndr_body, known_candidate_emails={"invalid-user@badtarget.com"})
    assert bounced == "invalid-user@badtarget.com"

    # Simulate 3 bounces in a row to trip circuit breaker
    # 1st bounce
    res1 = BounceSentinel.record_bounce(test_db, tenant_id, "b1@test.com")
    assert res1["circuit_tripped"] is False
    assert res1["bounce_count_24h"] == 1

    # 2nd bounce
    res2 = BounceSentinel.record_bounce(test_db, tenant_id, "b2@test.com")
    assert res2["circuit_tripped"] is False
    assert res2["bounce_count_24h"] == 2

    # 3rd bounce (reaches 3 bounces threshold)
    res3 = BounceSentinel.record_bounce(test_db, tenant_id, "b3@test.com")
    assert res3["circuit_tripped"] is True
    assert res3["sending_paused"] is True
    assert res3["bounce_rate_24h"] >= 0.03

    # Verify tenant credential shows sending_paused = True
    cred = test_db.query(APICredential).filter_by(tenant_id=tenant_id, provider="sales").first()
    assert cred.settings["sending_paused"] is True
    assert "Circuit breaker tripped" in cred.settings["paused_reason"]


def test_gatekeeper_blocks_ai_tells_and_unrendered_tags():
    # Message with AI tell and unrendered tag
    bad_msg = (
        "Hi {{firstName}},\n\n"
        "I hope this email finds you well! Our company is a game changer in this fast-paced world.\n\n"
        "Best regards,\nThe Team"
    )
    res = PreSendGatekeeper.evaluate("Intro to {company}", bad_msg)
    assert res.is_valid is False
    assert any("game changer" in v for v in res.violations)
    assert any("hope this email finds you well" in v for v in res.violations)
    assert any("unrendered placeholder" in v.lower() for v in res.violations)


def test_direct_profiler_detects_ad_spend_and_agency():
    html = """
    <html>
    <head>
        <script>fbq('init', '111222333');</script>
    </head>
    <body>
        <p>Welcome to our site</p>
        <footer>
            Built by <a href="https://apexdesign.co">Apex Design Studio</a>
        </footer>
    </body>
    </html>
    """
    res = DirectProfiler.parse_html("apex.com", "https://apex.com", html, 200)
    assert res.has_active_ad_spend is True
    assert "meta_pixel" in res.ad_pixels
    assert res.incumbent_agency == "Apex Design Studio"
