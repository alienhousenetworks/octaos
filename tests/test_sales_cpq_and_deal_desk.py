"""Tests for Phase 4: CPQ Pricing Engine, Floor Gatekeeper, Proposal Generator, and Stage Gatekeeper."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant, User
from app.models.deal_room import DealRoom, BuyingCommitteeMember, DealActivity
from app.models.sales_intelligence import SalesCompany, SalesOpportunity
from app.models.verticals import Lead
from app.services.sales_os.cpq.pricing_engine import CPQPricingEngine, STANDARD_CATALOG
from app.services.sales_os.cpq.proposal_generator import ProposalDocumentGenerator
from app.services.sales_os.cpq.stage_gatekeeper import StageTransitionGatekeeper


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    tenant = Tenant(id="tenant_cpq_test", name="CPQ Test Tenant")
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_cpq_pricing_engine_calculations_and_discounts():
    """Verifies line items calculation, volume discounts, multi-year commitment, and ROI modeling."""
    items = [
        {"sku": "OCTA-PLATFORM", "name": "Core Platform", "unit_price": 18000.0, "quantity": 1},
        {"sku": "OCTA-SALES-SWARM", "name": "Sales Swarm", "unit_price": 12000.0, "quantity": 2},
    ]
    # Gross = 18000 + 24000 = 42000
    # 24 months commitment -> 5% structural discount
    # 5% additional requested discount -> total 10% discount
    res = CPQPricingEngine.calculate_quote(
        line_items_input=items,
        requested_discount_pct=5.0,
        contract_term_months=24,
        payment_terms="Net 30",
    )

    assert res.gross_total_usd == 42000.0
    assert res.commitment_discount_pct == 5.0
    assert res.additional_discount_pct == 5.0
    assert res.total_discount_pct == 10.0
    # Net = 42000 * 0.9 = 37800
    assert res.net_total_usd == 37800.0
    assert res.floor_violation is False
    assert res.policy_status == "auto_approved"
    assert res.approval_tier == "L2"

    # ROI calculations
    assert res.roi_model.projected_annual_labor_savings_usd == round(42000.0 * 3.4, 2)
    assert res.roi_model.payback_period_months > 0.0
    assert res.roi_model.projected_roi_pct > 0.0


def test_cpq_floor_price_and_discount_cap_gatekeeper():
    """Verifies that discounts ladder correctly and floor violations are blocked."""
    items = [{"sku": "TEST-PROD", "unit_price": 20000.0, "quantity": 1}]

    # Case A: 8% discount -> Auto-Approved (L2)
    q_auto = CPQPricingEngine.calculate_quote(items, requested_discount_pct=8.0, contract_term_months=12)
    assert q_auto.policy_status == "auto_approved"
    assert q_auto.approval_tier == "L2"
    assert q_auto.floor_violation is False

    # Case B: 15% discount -> Requires Manager Approval (L1)
    q_mgr = CPQPricingEngine.calculate_quote(items, requested_discount_pct=15.0, contract_term_months=12)
    assert q_mgr.policy_status == "requires_manager_approval"
    assert q_mgr.approval_tier == "L1"
    assert q_mgr.floor_violation is False

    # Case C: 25% discount -> Requires VP Approval (L0)
    q_vp = CPQPricingEngine.calculate_quote(items, requested_discount_pct=25.0, contract_term_months=12)
    assert q_vp.policy_status == "requires_vp_approval"
    assert q_vp.approval_tier == "L0"
    assert q_vp.floor_violation is False

    # Case D: 40% discount -> Exceeds 35% ceiling -> BLOCKED
    q_blocked_disc = CPQPricingEngine.calculate_quote(items, requested_discount_pct=40.0, contract_term_months=12)
    assert q_blocked_disc.policy_status == "blocked"
    assert q_blocked_disc.approval_tier == "BLOCKED"
    assert q_blocked_disc.floor_violation is True

    # Case E: Deal net total under $5,000 floor -> BLOCKED
    cheap_items = [{"sku": "CHEAP-ITEM", "unit_price": 3000.0, "quantity": 1}]
    q_floor = CPQPricingEngine.calculate_quote(cheap_items, requested_discount_pct=0.0, contract_term_months=12)
    assert q_floor.policy_status == "blocked"
    assert q_floor.floor_violation is True


def test_proposal_document_generator_integrity_hash(db_session):
    """Verifies commercial proposal generation, cryptographic SHA-256 integrity, and activity logging."""
    room = DealRoom(
        tenant_id="tenant_cpq_test",
        company_name="Acme Enterprise Corp",
        domain="acmecorp.com",
        stage="meeting_booked",
    )
    db_session.add(room)
    db_session.commit()

    quote = CPQPricingEngine.calculate_quote(
        line_items_input=[
            {"sku": "OCTA-PLATFORM", "name": "Core Platform", "unit_price": 18000.0, "quantity": 1},
        ],
        requested_discount_pct=10.0,
        contract_term_months=12,
    )

    gen = ProposalDocumentGenerator(db_session, "tenant_cpq_test")
    res = gen.generate_proposal(
        deal_room=room,
        quote=quote,
        client_signatory_name="Jane Doe",
        client_signatory_title="Chief Technology Officer",
    )

    assert res["quote_number"] == quote.quote_number
    assert res["net_total_usd"] == quote.net_total_usd
    assert len(res["terms_hash"]) == 64  # SHA-256 hex length
    assert "Acme Enterprise Corp" in res["proposal_markdown"]
    assert "Jane Doe" in res["proposal_markdown"]
    assert "Chief Technology Officer" in res["proposal_markdown"]

    # DealRoom stage should automatically be updated to 'proposal'
    db_session.refresh(room)
    assert room.stage == "proposal"
    assert room.account_brief["latest_proposal"]["terms_hash"] == res["terms_hash"]

    # Verify DealActivity audit log
    act = (
        db_session.query(DealActivity)
        .filter(DealActivity.deal_room_id == room.id, DealActivity.activity_type == "proposal_generated")
        .first()
    )
    assert act is not None
    assert quote.quote_number in act.subject


def test_stage_transition_gatekeeper_validation_and_sync(db_session):
    """Verifies strict stage entry criteria and atomic synchronization across DealRoom, Opportunity, and Lead."""
    # 1. Setup Company, DealRoom, Opportunity, Lead
    company = SalesCompany(
        tenant_id="tenant_cpq_test",
        canonical_domain="novasystems.ai",
        display_name="Nova Systems",
        industry="Artificial Intelligence",
    )
    db_session.add(company)
    db_session.flush()

    room = DealRoom(
        tenant_id="tenant_cpq_test",
        company_name="Nova Systems",
        domain="novasystems.ai",
        industry="Artificial Intelligence",
        stage="discovered",
        icp_fit_score=0.8,
    )
    db_session.add(room)
    db_session.flush()

    opp = SalesOpportunity(
        tenant_id="tenant_cpq_test",
        company_id=company.id,
        stage="discovered",
    )
    db_session.add(opp)

    lead = Lead(
        tenant_id="tenant_cpq_test",
        company="Nova Systems",
        sales_opportunity_id=opp.id,
        status="new",
        score=75,
    )
    db_session.add(lead)
    db_session.commit()

    gatekeeper = StageTransitionGatekeeper(db_session, "tenant_cpq_test")

    # Advancement A: discovered -> qualified (Allowed because icp_fit_score=0.8)
    res_qual = gatekeeper.execute_transition(room.id, "qualified")
    assert res_qual["success"] is True
    assert res_qual["current_stage"] == "qualified"

    db_session.refresh(room)
    db_session.refresh(opp)
    db_session.refresh(lead)
    assert room.stage == "qualified"
    assert opp.stage == "qualified"
    assert lead.status == "contacted"

    # Advancement B: Try moving to 'closing' without an active approved quote -> Blocked by criteria
    res_close_fail = gatekeeper.execute_transition(room.id, "closing")
    assert res_close_fail["success"] is False
    assert any("requires an active quote" in m for m in res_close_fail["missing_criteria"])

    # Now provide an active quote that is approved
    quote = CPQPricingEngine.calculate_quote(
        line_items_input=[{"sku": "OCTA-PLATFORM", "unit_price": 18000.0, "quantity": 1}],
        requested_discount_pct=5.0,
    )
    room.account_brief = {"latest_quote": quote.dict()}
    db_session.commit()

    # Advancement C: Now moving to 'closing' succeeds
    res_close_ok = gatekeeper.execute_transition(room.id, "closing")
    assert res_close_ok["success"] is True
    assert res_close_ok["current_stage"] == "closing"

    # Advancement D: Moving to 'lost' without reason is blocked
    res_lost_fail = gatekeeper.execute_transition(room.id, "lost")
    assert res_lost_fail["success"] is False

    # Advancement E: Moving to 'lost' with loss_reason succeeds
    res_lost_ok = gatekeeper.execute_transition(room.id, "lost", loss_reason="competitor_chosen", notes="Selected legacy vendor")
    assert res_lost_ok["success"] is True
    assert res_lost_ok["current_stage"] == "lost"
    db_session.refresh(lead)
    assert lead.status == "closed_lost"
