"""Unit tests for Phase 1 of the Autonomous Sales Organization (ASO).

Tests:
1. Pydantic schemas for Agents 11-20 in app/schemas/sales_swarm.py
2. Async SalesEventBus pub/sub, history buffer, and subscriber isolation
3. EnterpriseSalesPolicyEngine commercial discount limits and compliance gates
"""
import pytest
from app.schemas.sales_swarm import (
    RouteStop,
    TerritoryRoutePlan,
    StructuredMeetingNote,
    FieldVisitSummary,
    MEDDPICCDimension,
    DealStrategyReport,
    ProposalQuote,
    LineItem,
    RedlineClause,
    NegotiationStrategy,
    PipelineForecastReport,
    CoachingReport,
    CapacityPlanReport,
    ExpansionRetentionReport,
    LearningReport,
)
from app.services.sales_os.events.bus import (
    SalesEventBus,
    SalesEvent,
    SalesEventType,
)
from app.services.sales_os.governance.enterprise_policy import (
    EnterpriseSalesPolicyEngine,
    PolicyDecision,
)


def test_agent_schemas_instantiation():
    """Verify that all new agent schemas can be cleanly instantiated."""
    # Agent 11: Route Plan
    stop = RouteStop(
        account_id="acc_1",
        company_name="Acme Corp",
        address="123 Market St",
        latitude=37.7749,
        longitude=-122.4194,
        contact_name="Alice Smith",
        contact_phone="+1-555-0100",
        scheduled_window_start="10:00 AM",
        scheduled_window_end="11:00 AM",
        priority_score=0.92,
    )
    plan = TerritoryRoutePlan(
        rep_id="rep_1",
        date="2026-10-15",
        total_travel_distance_km=14.5,
        estimated_travel_time_min=35.0,
        stops=[stop],
    )
    assert len(plan.stops) == 1
    assert plan.stops[0].priority_score == 0.92

    # Agent 13: Deal Strategy
    dim = MEDDPICCDimension(
        dimension="Economic Buyer",
        status="identified",
        evidence_snippet="Spoke with VP Finance on call",
        confidence=0.88,
    )
    report = DealStrategyReport(
        deal_room_id="dr_123",
        meddpicc_score=75.0,
        meddpicc_breakdown=[dim],
        is_single_threaded=True,
    )
    assert report.meddpicc_score == 75.0
    assert report.is_single_threaded is True

    # Agent 14: Proposal & CPQ
    item = LineItem(
        sku="OCTA-ENTERPRISE",
        name="OctaOS Enterprise Annual",
        unit_price=24000.0,
        quantity=1,
        discount_pct=10.0,
        total_price=21600.0,
    )
    quote = ProposalQuote(
        deal_room_id="dr_123",
        quote_number="Q-2026-001",
        line_items=[item],
        gross_total_usd=24000.0,
        effective_discount_pct=10.0,
        net_total_usd=21600.0,
        generated_proposal_markdown="# Proposal",
    )
    assert quote.net_total_usd == 21600.0

    # Agent 15: Negotiation Redlines
    clause = RedlineClause(
        section_name="Limitation of Liability",
        original_text="1x Annual Fees",
        counterparty_proposed_text="Unlimited",
        risk_severity="high",
        playbook_guidance="Cap at 2x max",
        recommended_concession="Counter with 2x annual fee cap",
        trade_off_ask="Increase contract duration to 24 months",
        escalate_to_legal=True,
    )
    neg = NegotiationStrategy(
        deal_room_id="dr_123",
        document_version="v2_redline",
        overall_legal_risk_score=0.85,
        clauses_analyzed=[clause],
        recommended_response_letter="Dear counsel...",
    )
    assert len(neg.clauses_analyzed) == 1
    assert neg.clauses_analyzed[0].escalate_to_legal is True


@pytest.mark.asyncio
async def test_sales_event_bus():
    """Verify pub/sub delivery, global listeners, and history buffering."""
    bus = SalesEventBus(max_history=10)

    delivered_events = []

    async def on_reply(event: SalesEvent):
        delivered_events.append(event)

    bus.subscribe(SalesEventType.PROSPECT_REPLIED, on_reply)

    ev1 = SalesEvent(
        tenant_id="tenant_abc",
        event_type=SalesEventType.PROSPECT_REPLIED,
        deal_room_id="dr_1",
        payload={"inbound_text": "I'm interested, let's talk."},
    )
    ev2 = SalesEvent(
        tenant_id="tenant_abc",
        event_type=SalesEventType.EMAIL_OPENED,
        deal_room_id="dr_1",
        payload={},
    )

    await bus.publish(ev1)
    await bus.publish(ev2)

    # Only ev1 should be in delivered_events
    assert len(delivered_events) == 1
    assert delivered_events[0].event_type == SalesEventType.PROSPECT_REPLIED

    # History should contain both
    history = bus.get_recent_events(tenant_id="tenant_abc")
    assert len(history) == 2


def test_enterprise_policy_engine_pricing():
    """Verify commercial discount ceilings and approval escalation tiers."""
    class DummyDB:
        def query(self, *args):
            class DummyQuery:
                def filter(self, *a):
                    return self
                def first(self):
                    return None
            return DummyQuery()

    engine = EnterpriseSalesPolicyEngine(DummyDB(), "tenant_demo")

    # 1. 5% discount -> L2 Auto-Approved
    d1 = engine.evaluate_pricing_and_discount(5.0)
    assert d1.status == "AUTO_APPROVED_L2"
    assert d1.requires_approval is False

    # 2. 15% discount -> L1 AE Approval Required
    d2 = engine.evaluate_pricing_and_discount(15.0)
    assert d2.status == "APPROVAL_REQUIRED_L1"
    assert d2.requires_approval is True

    # 3. 25% discount -> L0 VP Sales Escalation / Veto
    d3 = engine.evaluate_pricing_and_discount(25.0)
    assert d3.status == "ESCALATE_L0"
    assert d3.requires_approval is True
    assert "hard ceiling" in d3.violations[0]


def test_enterprise_policy_engine_compliance():
    """Verify privacy laws (India TRAI WhatsApp opt-in and US CAN-SPAM)."""
    class DummyDB:
        def query(self, *args):
            class DummyQuery:
                def filter(self, *a):
                    return self
                def first(self):
                    return None
                def filter_by(self, *a, **k):
                    return self
                def all(self):
                    return []
            return DummyQuery()

    engine = EnterpriseSalesPolicyEngine(DummyDB(), "tenant_demo")

    # India WhatsApp without opt-in -> Blocked
    c1 = engine.evaluate_communication_compliance(
        recipient_email="prospect@company.in",
        channel="whatsapp",
        country="IN",
        has_explicit_opt_in=False,
    )
    assert c1.status == "BLOCKED"
    assert "opt-in" in c1.reason

    # US email without unsubscribe notice -> L1 Review
    c2 = engine.evaluate_communication_compliance(
        recipient_email="prospect@company.com",
        channel="email",
        country="US",
        content="Hey, let's meet up tomorrow for a demo.",
        groundedness_score=1.0,
    )
    assert c2.status == "APPROVAL_REQUIRED_L1"
    assert "CAN-SPAM" in c2.reason

    # Low groundedness score -> L1 Review
    c3 = engine.evaluate_communication_compliance(
        recipient_email="prospect@company.com",
        channel="email",
        country="UK",
        content="Hey, unsubscribe here.",
        groundedness_score=0.72,
    )
    assert c3.status == "APPROVAL_REQUIRED_L1"
    assert "Groundedness" in c3.reason
