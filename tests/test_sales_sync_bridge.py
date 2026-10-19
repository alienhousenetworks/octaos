"""Unit and Integration Tests for SalesSyncBridge, Suppression Integration, and Split-Brain Remediation."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, User
from app.models.verticals import Lead
from app.models.deal_room import DealRoom, BuyingCommitteeMember, SuppressionRecord
from app.models.sales_intelligence import SalesCompany, AccountContact, SalesOpportunity
from app.services.sales.sync_bridge import SalesSyncBridge
from app.services.sales_os.governance.suppression import SuppressionService


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

    tenant = Tenant(id="tenant_test", name="Test Corp", subdomain="test-corp", is_active=True)
    session.add(tenant)
    session.commit()

    yield session

    session.close()


def test_sales_sync_bridge_lead_entities(test_db):
    """Verify that a standalone Lead is automatically linked to DealRoom, SalesCompany, and SalesOpportunity."""
    bridge = SalesSyncBridge(test_db, "tenant_test")

    lead = Lead(
        tenant_id="tenant_test",
        name="Sarah Connor",
        email="sarah@skynet-defense.com",
        company="Skynet Defense",
        phone="+1234567890",
        source="apollo",
        status="captured",
        score=75,
        data={"website": "https://skynet-defense.com"}
    )
    test_db.add(lead)
    test_db.commit()

    result = bridge.sync_lead_entities(lead, auto_commit=True)

    assert result["deal_room_id"] is not None
    assert result["sales_company_id"] is not None
    assert result["sales_opportunity_id"] is not None
    assert result["sales_contact_id"] is not None

    deal_room = test_db.query(DealRoom).filter_by(id=result["deal_room_id"]).first()
    assert deal_room is not None
    assert deal_room.domain == "skynet-defense.com"
    assert deal_room.company_name == "Skynet Defense"

    sales_company = test_db.query(SalesCompany).filter_by(id=result["sales_company_id"]).first()
    assert sales_company is not None
    assert sales_company.canonical_domain == "skynet-defense.com"
    assert sales_company.deal_room_id == deal_room.id

    bcm = test_db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, email="sarah@skynet-defense.com").first()
    assert bcm is not None
    assert bcm.name == "Sarah Connor"


def test_sync_outreach_sent(test_db):
    """Verify that outreach dispatch advances DealRoom to in_cadence and SalesOpportunity to qualified."""
    bridge = SalesSyncBridge(test_db, "tenant_test")

    lead = Lead(
        tenant_id="tenant_test",
        name="John Matrix",
        email="john@valverde-ops.com",
        company="Valverde Ops",
        status="scored",
        data={"website": "https://valverde-ops.com"}
    )
    test_db.add(lead)
    test_db.commit()

    bridge.sync_outreach_sent(lead, sent_actual=True, auto_commit=True)

    deal_room = test_db.query(DealRoom).filter_by(domain="valverde-ops.com").first()
    assert deal_room.stage == "in_cadence"

    bcm = test_db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, email="john@valverde-ops.com").first()
    assert bcm.engagement_state == "contacted"

    opp = test_db.query(SalesOpportunity).filter_by(id=lead.sales_opportunity_id).first()
    assert opp.stage == "qualified"


def test_sync_reply_received_positive(test_db):
    """Verify that an interested reply advances DealRoom to engaged and SalesOpportunity to evaluating."""
    bridge = SalesSyncBridge(test_db, "tenant_test")

    lead = Lead(
        tenant_id="tenant_test",
        name="Ellen Ripley",
        email="ripley@weyland-yutani.com",
        company="Weyland Yutani",
        status="contacted",
        data={"website": "https://weyland-yutani.com"}
    )
    test_db.add(lead)
    test_db.commit()

    bridge.sync_outreach_sent(lead, sent_actual=True, auto_commit=True)
    bridge.sync_reply_received(lead, intent="interested", reply_text="Yes, we are evaluating solutions. Call me tomorrow.", auto_commit=True)

    assert lead.status == "replied"

    deal_room = test_db.query(DealRoom).filter_by(domain="weyland-yutani.com").first()
    assert deal_room.stage == "engaged"

    bcm = test_db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, email="ripley@weyland-yutani.com").first()
    assert bcm.engagement_state == "engaged"

    opp = test_db.query(SalesOpportunity).filter_by(id=lead.sales_opportunity_id).first()
    assert opp.stage == "evaluating"


def test_sync_reply_received_unsubscribe(test_db):
    """Verify that an unsubscribe reply adds SuppressionRecord, marks Lead opt_out, and DealRoom closed_lost."""
    bridge = SalesSyncBridge(test_db, "tenant_test")

    lead = Lead(
        tenant_id="tenant_test",
        name="Arthur Dent",
        email="arthur@megadodo.com",
        company="Megadodo Publications",
        status="contacted",
        data={"website": "https://megadodo.com"}
    )
    test_db.add(lead)
    test_db.commit()

    bridge.sync_outreach_sent(lead, sent_actual=True, auto_commit=True)
    bridge.sync_reply_received(lead, intent="unsubscribe", reply_text="Please remove me from your mailing list.", auto_commit=True)

    assert lead.status == "opt_out"

    deal_room = test_db.query(DealRoom).filter_by(domain="megadodo.com").first()
    assert deal_room.stage == "closed_lost"

    bcm = test_db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, email="arthur@megadodo.com").first()
    assert bcm.engagement_state == "opt_out"

    # Verify SuppressionRecord was populated
    supp = SuppressionService(test_db, "tenant_test")
    is_supp_email, reason_email = supp.is_suppressed(email="arthur@megadodo.com")
    assert is_supp_email is True
    assert "prospect_unsubscribe_reply" in reason_email

    is_supp_domain, reason_domain = supp.is_suppressed(domain="megadodo.com")
    assert is_supp_domain is True
    assert "prospect_unsubscribe_reply" in reason_domain


def test_sync_meeting_booked(test_db):
    """Verify that booking a meeting transitions DealRoom to evaluating and BCM to champion."""
    bridge = SalesSyncBridge(test_db, "tenant_test")

    lead = Lead(
        tenant_id="tenant_test",
        name="Dana Scully",
        email="dana@fbi-xfiles.gov",
        company="FBI",
        status="replied",
        data={"website": "https://fbi-xfiles.gov"}
    )
    test_db.add(lead)
    test_db.commit()

    bridge.sync_lead_entities(lead, auto_commit=True)
    bridge.sync_meeting_booked(lead, auto_commit=True)

    assert lead.status == "meeting_scheduled"

    deal_room = test_db.query(DealRoom).filter_by(domain="fbi-xfiles.gov").first()
    assert deal_room.stage == "evaluating"

    bcm = test_db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, email="dana@fbi-xfiles.gov").first()
    assert bcm.engagement_state == "champion"
