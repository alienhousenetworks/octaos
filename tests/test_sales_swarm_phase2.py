"""Unit tests for Phase 2 AE and Sales Manager agents.

Tests:
1. Agent 13 (DealStrategistAgent): MEDDPICC scoring, single-threading detection, Next Best Action
2. Agent 14 (ProposalCPQAgent): Line items, commercial discount policy enforcement, ROI synthesis
3. Agent 16 (PipelineForecasterAgent): Probabilistic commit/best-case modeling, risk flags, Monday brief
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.models.deal_room import DealRoom, BuyingCommitteeMember, CompanySalesContext
from app.services.sales_os.agents.deal_strategist import DealStrategistAgent
from app.services.sales_os.agents.proposal_cpq import ProposalCPQAgent
from app.services.sales_os.agents.pipeline_forecaster import PipelineForecasterAgent


class MockQuery:
    def __init__(self, data):
        self._data = list(data) if isinstance(data, list) else ([data] if data else [])

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def first(self):
        return self._data[0] if self._data else None

    def all(self):
        return self._data

    def count(self):
        return len(self._data)


class MockDB:
    def __init__(self, rooms=None, committee=None, context=None):
        self.rooms = rooms or []
        self.committee = committee or []
        self.context = context or []
        self.committed = False

    def query(self, model):
        if model == DealRoom:
            return MockQuery(self.rooms)
        elif model == BuyingCommitteeMember:
            return MockQuery(self.committee)
        elif model == CompanySalesContext:
            return MockQuery(self.context)
        return MockQuery([])

    def commit(self):
        self.committed = True

    def flush(self):
        pass


@pytest.mark.asyncio
async def test_deal_strategist_single_threaded():
    """Verify Agent 13 flags single-threading and suggests EB multi-threading."""
    deal_room = DealRoom(
        id="dr_101",
        tenant_id="tenant_test",
        company_name="CloudCorp",
        domain="cloudcorp.com",
        stage="proposal",
        tech_stack=["AWS", "Kubernetes"],
        pain_hypotheses=[{"signal": "Job posting for SRE", "inference": "High cloud bills"}],
    )
    # Only 1 committee member (not an economic buyer)
    member = BuyingCommitteeMember(
        id="m_1",
        deal_room_id="dr_101",
        tenant_id="tenant_test",
        name="Bob Dev",
        email="bob@cloudcorp.com",
        title="Software Engineer",
        role_type="influencer",
    )

    db = MockDB(rooms=[deal_room], committee=[member])
    agent = DealStrategistAgent(db, "tenant_test")

    result = await agent.execute("dr_101")
    assert result.decision == "action_required"
    assert result.data.is_single_threaded is True
    assert "Economic Buyer" in result.data.missing_critical_roles
    assert result.data.daily_next_best_action["action"] == "multi_thread_economic_buyer"


@pytest.mark.asyncio
async def test_proposal_cpq_policy_discount_capping():
    """Verify Agent 14 generates quotes and flags manager approval on 15% discount."""
    deal_room = DealRoom(
        id="dr_202",
        tenant_id="tenant_test",
        company_name="EnterpriseX",
        domain="enterprisex.com",
    )
    context = CompanySalesContext(
        tenant_id="tenant_test",
        is_active=True,
        products_catalog=[
            {"sku": "CORE", "name": "Core Platform", "price": 20000.0},
            {"sku": "ADDON", "name": "AI Module", "price": 10000.0},
        ],
    )

    db = MockDB(rooms=[deal_room], context=[context])
    agent = ProposalCPQAgent(db, "tenant_test")

    # Request 15% discount (requires AE approval)
    result = await agent.execute("dr_202", {"requested_discount_pct": 15.0, "tier": "growth"})

    assert result.decision == "action_required"
    quote = result.data
    assert quote.gross_total_usd == 30000.0
    assert quote.policy_approval_status == "pending_manager_approval"
    assert quote.roi_model["payback_period_months"] > 0
    assert "Commercial Proposal for EnterpriseX" in quote.generated_proposal_markdown


@pytest.mark.asyncio
async def test_pipeline_forecaster_probabilistic_audit():
    """Verify Agent 16 calculates probabilistic commit, best-case, and risks."""
    now = datetime.now(timezone.utc)
    room1 = DealRoom(
        id="dr_301",
        tenant_id="tenant_test",
        company_name="MegaBank",
        stage="closing",
        annual_revenue_usd=100000.0,
        calibrated_win_prob=0.85,
        created_at=now - timedelta(days=20),
        last_activity_at=now - timedelta(days=2),
        is_multi_threaded=True,
    )
    room2 = DealRoom(
        id="dr_302",
        tenant_id="tenant_test",
        company_name="StalledLLC",
        stage="proposal",
        annual_revenue_usd=50000.0,
        calibrated_win_prob=0.50,
        created_at=now - timedelta(days=40),
        last_activity_at=now - timedelta(days=10),  # Stalled > 7 days
        is_multi_threaded=False,                   # Single-threaded
    )

    db = MockDB(rooms=[room1, room2])
    agent = PipelineForecasterAgent(db, "tenant_test")

    result = await agent.execute()
    assert result.decision == "ready"
    forecast = result.data

    # room1 is commit (0.85 >= 0.70)
    assert forecast.commit_usd == 100000.0
    # both room1 and room2 are best case (prob >= 0.40)
    assert forecast.best_case_usd == 150000.0
    assert forecast.total_pipeline_usd == 150000.0

    # Verify stalled deal risk flag
    stalled_audits = [c for c in forecast.key_deal_changes if c["deal_room_id"] == "dr_302"]
    assert len(stalled_audits) == 1
    assert "stalled_7_days" in stalled_audits[0]["risk_factors"]
    assert "single_threaded" in stalled_audits[0]["risk_factors"]
    assert "Monday Executive Pipeline Brief" in forecast.executive_monday_brief
