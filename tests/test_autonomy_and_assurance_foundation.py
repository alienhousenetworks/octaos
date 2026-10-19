import os
os.environ["TESTING"] = "1"

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, User
from app.models.workflows import Workflow
from app.models.executive import PlanVersion, PlanNode
from app.models.objectives import BusinessObjective, ObjectiveMetric
from app.models.decision_cases import DecisionCase, DecisionAlternative, DecisionGrant, DecisionOutcomeReview

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def seed_tenants_and_users(db):
    t1 = Tenant(id="tenant-alpha", name="Alpha Corp")
    t2 = Tenant(id="tenant-beta", name="Beta LLC")
    db.add_all([t1, t2])

    u1 = User(id="user-ceo-1", email="ceo@alpha.com", name="Alpha CEO", hashed_password="pw", tenant_id="tenant-alpha", role="admin")
    u2 = User(id="user-cfo-1", email="cfo@alpha.com", name="Alpha CFO", hashed_password="pw", tenant_id="tenant-alpha", role="admin")
    u3 = User(id="user-lead-1", email="lead@alpha.com", name="Alpha Lead", hashed_password="pw", tenant_id="tenant-alpha", role="member")
    db.add_all([u1, u2, u3])
    db.commit()
    return {"tenant_id": "tenant-alpha", "ceo_id": u1.id, "cfo_id": u2.id, "lead_id": u3.id}


def test_business_objective_lifecycle(db, seed_tenants_and_users):
    tenant_id = seed_tenants_and_users["tenant_id"]
    ceo_id = seed_tenants_and_users["ceo_id"]

    # 1. Create a versioned Business Objective commitment
    deadline = datetime.now(timezone.utc) + timedelta(days=90)
    obj = BusinessObjective(
        tenant_id=tenant_id,
        version=1,
        title="Reduce Customer Churn by 25%",
        description="Enterprise retention initiative across Support and Marketing",
        owner_user_id=ceo_id,
        target_metric="churn_rate",
        baseline_value=8.0,
        target_value=6.0,
        current_value=8.0,
        unit="percent",
        priority=1,
        budget_limit=Decimal("15000.00"),
        consumed_budget=Decimal("0.00"),
        deadline=deadline,
        status="ACTIVE",
        constraints={"max_cac_payback_months": 12, "min_gross_margin": 0.55},
        success_criteria=[{"metric": "churn_rate", "operator": "<=", "target": 6.0}],
    )
    db.add(obj)
    db.commit()

    assert obj.id is not None
    assert obj.version == 1
    assert obj.status == "ACTIVE"
    assert obj.budget_limit == Decimal("15000.00")

    # 2. Add an ObjectiveMetric verification snapshot
    metric_snapshot = ObjectiveMetric(
        tenant_id=tenant_id,
        objective_id=obj.id,
        measured_value=7.2,
        budget_spent_to_date=Decimal("3500.00"),
        evidence_source="stripe_churn_sync",
        evidence_reference_id="sync-2026-q1",
        variance_pct=-0.10,
    )
    db.add(metric_snapshot)
    obj.current_value = 7.2
    obj.consumed_budget = Decimal("3500.00")
    db.commit()

    reloaded = db.query(BusinessObjective).filter_by(id=obj.id).first()
    assert len(reloaded.metric_snapshots) == 1
    assert reloaded.current_value == 7.2
    assert reloaded.consumed_budget == Decimal("3500.00")


def test_plan_version_linked_to_objective_and_contracts(db, seed_tenants_and_users):
    tenant_id = seed_tenants_and_users["tenant_id"]
    ceo_id = seed_tenants_and_users["ceo_id"]

    obj = BusinessObjective(
        tenant_id=tenant_id,
        version=1,
        title="Generate 50 Qualified Enterprise Leads",
        owner_user_id=ceo_id,
        target_metric="qualified_leads",
        baseline_value=0.0,
        target_value=50.0,
        unit="count",
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(obj)
    
    wf = Workflow(tenant_id=tenant_id, name="Enterprise Pipeline Surge", vertical="CEO", status="active")
    db.add(wf)
    db.commit()

    # Link PlanVersion to BusinessObjective
    plan = PlanVersion(
        tenant_id=tenant_id,
        workflow_id=wf.id,
        objective_id=obj.id,
        version_num=1,
        strategy_variant="BALANCED",
        status="APPROVED",
        plan_content_hash="hash-12345",
        objective="Generate 50 Qualified Enterprise Leads",
        executive_summary="Targeted outreach across fintech and healthcare",
        estimated_budget=Decimal("5000.00"),
        max_budget_envelope=Decimal("6000.00"),
        quant_forecast={"expected_leads": 55, "cost_per_lead": 90.9},
    )
    db.add(plan)
    db.commit()

    # PlanNode with typed Execution Contract
    node = PlanNode(
        plan_version_id=plan.id,
        name="Target ICP Lead Sourcing",
        department="SALES",
        capability_id="sales.source_leads",
        capability_version="1.0.0",
        parameters={"count": 50, "industry": "fintech"},
        input_contract_schema={
            "type": "object",
            "properties": {"count": {"type": "integer"}, "industry": {"type": "string"}},
            "required": ["count", "industry"],
        },
        output_contract_schema={
            "type": "object",
            "properties": {"sourced_leads_count": {"type": "integer"}},
            "required": ["sourced_leads_count"],
        },
        evidence_requirements=["lead_provenance_verified", "email_deliverability_score_above_85"],
        max_retries=3,
        timeout_seconds=120,
    )
    db.add(node)
    db.commit()

    reloaded_plan = db.query(PlanVersion).filter_by(id=plan.id).first()
    assert reloaded_plan.objective_rel.title == "Generate 50 Qualified Enterprise Leads"
    assert len(reloaded_plan.nodes) == 1
    assert reloaded_plan.nodes[0].max_retries == 3
    assert "lead_provenance_verified" in reloaded_plan.nodes[0].evidence_requirements


def test_decision_case_assurance_and_grant_lifecycle(db, seed_tenants_and_users):
    tenant_id = seed_tenants_and_users["tenant_id"]
    lead_id = seed_tenants_and_users["lead_id"]
    cfo_id = seed_tenants_and_users["cfo_id"]

    # 1. Propose a DecisionCase
    case = DecisionCase(
        tenant_id=tenant_id,
        case_number="DEC-2026-0001",
        title="Authorize Outbound Enterprise Ad Campaign Spend",
        proposal_summary="Deploy $4,500 across LinkedIn ads for Q1 lead generation",
        business_rationale="Accelerates enterprise qualified pipeline to meet Q1 MRR target",
        risk_class="R3_EXTERNAL_IRREVERSIBLE",
        financial_exposure=Decimal("4500.00"),
        reversibility="LOW",
        cost_of_delay_per_week=Decimal("800.00"),
        decision_owner_user_id=cfo_id,
        requester_user_id=lead_id,  # Requester is the lead
        status="UNDER_ASSURANCE",
        assumptions=["Conversion rate holds at 3.2%", "CAC payback < 6 months"],
        uncertainties=["Ad CPM volatility in late Q1"],
        financial_assessment={
            "downside_p10": -1200,
            "expected_value": 7500,
            "margin_impact_bps": -15,
            "payback_months": 4.2,
        },
        compliance_assessment={
            "passed": True,
            "evaluated_rules_count": 5,
            "violations": [],
        },
        operational_feasibility={
            "credentials_valid": True,
            "capacity_score": 0.98,
        },
    )
    db.add(case)
    db.commit()

    # 2. Add realistic decision alternatives (Do-nothing, Pilot, Full scale)
    alt_a = DecisionAlternative(
        case_id=case.id,
        alternative_code="A",
        title="Do Nothing (Defer to Q2)",
        description="Preserve cash; avoid $4,500 exposure; risk pipeline shortfall",
        is_do_nothing=True,
        financial_model={"cost": 0, "expected_outcome": 0},
        score=4.0,
    )
    alt_b = DecisionAlternative(
        case_id=case.id,
        alternative_code="B",
        title="Pilot Phase ($1,500 Test Run)",
        description="Run 10-day test on highest intent segment to validate conversion before full commit",
        is_pilot=True,
        reversibility="HIGH",
        financial_model={"cost": 1500, "expected_outcome": 3000, "downside_p10": -300},
        score=8.5,
    )
    alt_c = DecisionAlternative(
        case_id=case.id,
        alternative_code="C",
        title="Full Scale Deployment ($4,500)",
        description="Immediate multi-channel burst across LinkedIn and search",
        reversibility="LOW",
        financial_model={"cost": 4500, "expected_outcome": 7500, "downside_p10": -1200},
        score=7.2,
    )
    db.add_all([alt_a, alt_b, alt_c])
    db.commit()

    # 3. Decision Maker selects Alternative B (Pilot) and issues DecisionGrant
    case.selected_alternative_code = "B"
    case.status = "AUTHORIZED"

    grant = DecisionGrant(
        tenant_id=tenant_id,
        case_id=case.id,
        decision="APPROVE",
        granter_user_id=cfo_id,  # CFO approves (different from requester lead_id: anti-self-approval holds)
        granter_role="EXECUTIVE",
        delegation_level="EXECUTIVE_L3",
        action_hash="sha256-payload-test-pilot-hash",
        policy_version="2026.1",
        rationale="Pilot limits downside exposure to $1,500 while testing CAC assumptions",
        conditions=["Halt if CPL exceeds $85 after first $500 spend"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db.add(grant)
    case.active_grant_id = grant.id
    db.commit()

    # 4. Attach Outcome Review with tripwires for post-decision assurance
    review = DecisionOutcomeReview(
        tenant_id=tenant_id,
        case_id=case.id,
        milestone="30d",
        scheduled_for=datetime.now(timezone.utc) + timedelta(days=30),
        tripwires=[{"metric": "cpl", "operator": ">", "threshold": 85.0}],
        predicted_metrics={"cpl": 65.0, "leads": 23},
        actual_metrics={"cpl": 61.5, "leads": 24},
        brier_score=0.08,  # Highly calibrated prediction
        review_notes="Pilot met all target criteria and stayed within budget envelope",
        reviewed_by_user_id=cfo_id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(review)
    db.commit()

    # Verify relationships and assertions
    reloaded_case = db.query(DecisionCase).filter_by(id=case.id).first()
    assert len(reloaded_case.alternatives) == 3
    assert len(reloaded_case.grants) == 1
    assert len(reloaded_case.outcomes) == 1
    assert reloaded_case.status == "AUTHORIZED"
    assert reloaded_case.selected_alternative_code == "B"
    assert reloaded_case.grants[0].granter_user_id == cfo_id
    assert reloaded_case.outcomes[0].brier_score == 0.08
