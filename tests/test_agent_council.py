import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant
from app.models.verticals import AgentMeeting
from app.models.deal_room import DealRoom
from app.services.executive_os.agent_council import AgentCouncilService
from app.services.executive_os.strategy_compiler import StrategyCompiler


TEST_DB_URL = "sqlite:///./test_agent_council.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    tenant = Tenant(id="tenant-council-test", name="Council Test Corp", subdomain="council", company_email="ceo@council.com")
    db.add(tenant)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        engine.dispose()
        Base.metadata.drop_all(bind=engine)


def test_agent_council_identification(db_session):
    """
    Test 1: AgentCouncilService correctly identifies required agent personas based on directive.
    """
    service = AgentCouncilService(db_session, "tenant-council-test")

    # Marketing & Sales directive
    agents = service.identify_required_agents("Launch outbound marketing and sales email campaign for $20k", "REVENUE")
    assert "CEO AI" in agents
    assert "CFO AI" in agents
    assert "Marketing AI" in agents
    assert "Sales AI" in agents
    assert "Red Team AI" in agents

    # Hiring directive
    agents_hr = service.identify_required_agents("Recruit and hire 5 software engineers", "TALENT")
    assert "HR AI" in agents_hr
    assert "CFO AI" in agents_hr
    assert "Red Team AI" in agents_hr

    # Customer Support & Retention directive
    agents_support = service.identify_required_agents("Triage support tickets and reduce customer churn rate", "CRISIS")
    assert "Customer Support AI" in agents_support
    assert "CFO AI" in agents_support


def test_agent_council_deliberation_and_roi_scorecard(db_session):
    """
    Test 2: AgentCouncilService summons meeting and computes before/after ROI metrics.
    """
    service = AgentCouncilService(db_session, "tenant-council-test")
    prompt = "Scale B2B SaaS revenue with outbound sales sequence"
    res = service.deliberate_strategy_sync(
        prompt=prompt,
        strategic_pillar="REVENUE",
        budget_cap=15000.0,
        timeline_days=30
    )

    assert res["meeting_id"] is not None
    assert len(res["summoned_agents"]) >= 3
    assert len(res["deliberations"]) >= 3
    
    scorecard = res["roi_scorecard"]
    assert scorecard["initial_roi"] > 0
    assert scorecard["optimized_roi"] > scorecard["initial_roi"]
    assert scorecard["roi_multiplier"] > 1.0
    assert scorecard["payback_months"] > 0
    assert scorecard["projected_return"] > scorecard["estimated_spend"]

    # Verify AgentMeeting was stored in DB
    meeting = db_session.query(AgentMeeting).filter_by(id=res["meeting_id"]).first()
    assert meeting is not None
    assert meeting.trigger_type == "ceo_directive_deliberation"


def test_strategy_compiler_end_to_end_deliberation(db_session):
    """
    Test 3: StrategyCompiler compiles 3 variants with embedded council deliberation and dynamic DAG nodes.
    """
    compiler = StrategyCompiler(db_session, "tenant-council-test")
    prompt = "Launch high-growth outbound marketing and sales acquisition pipeline"
    plans = compiler.compile_plans(
        workflow_id=None,
        prompt=prompt,
        budget_override=20000.0
    )

    assert len(plans) == 3
    variants = {p.strategy_variant: p for p in plans}
    assert "AGGRESSIVE" in variants
    assert "BALANCED" in variants
    assert "CONSERVATIVE" in variants

    balanced = variants["BALANCED"]
    assert balanced.quant_forecast is not None
    assert "roi_scorecard" in balanced.quant_forecast
    assert balanced.quant_forecast["roi_scorecard"]["optimized_roi"] > 0
    assert len(balanced.quant_forecast["council_participants"]) >= 3

    # Verify DAG nodes are domain-specific and assigned to real departments
    from app.models.executive import PlanNode
    nodes = db_session.query(PlanNode).filter_by(plan_version_id=balanced.id).all()
    departments = {n.department for n in nodes}
    assert "Finance" in departments
    assert ("Marketing" in departments or "Sales" in departments)
    assert len(nodes) >= 3
