"""Sales intelligence rules, persistence, and the sales-os API."""
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.v1.endpoints.sales_os import router as sales_os_router
from app.core.celery_app import celery_app
from app.models.base import Base, Tenant, User
from app.models.deal_room import AccountSignal, DealRoom
from app.models.sales_intelligence import SalesSignal
from app.models.verticals import Lead
from app.services.sales_os.attribution.allocator import choose_provider, routing_utility
from app.services.sales_os.attribution.source_roi import summarize_roi
from app.services.sales_os.discovery.identity import canonical_domain
from app.services.sales_os.discovery.waterfall import icp_gate, plan_contact_waterfall
from app.services.sales_os.events.dispatcher import SalesEventDispatcher
from app.services.sales_os.orchestration.sales_pipeline import SalesPipeline
from app.services.sales_os.orchestration.store import SalesIntelligenceStore
from app.services.sales_os.providers.base import AccountCandidate, ConnectorEnvelope, RawSignal
from app.services.sales_os.providers.honesty import is_fabricated_contact
from app.services.sales_os.providers.registry import describe_source
from app.services.sales_os.scoring.engine import SCORE_VERSION, score_opportunity
from app.services.sales_os.signals.convergence import convergence_bonus
from app.services.sales_os.signals.decay import effective_strength
from app.services.sales_os.verification.engine import (
    tier0_identity,
    tier1_syntax,
    tier2_deliverability,
    tier3_employment,
    tier4_compliance,
    tier6_state,
)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _passed_tiers():
    return [
        tier0_identity(canonical_domain="acme.com", email="ada@acme.com"),
        tier1_syntax("ada@acme.com"),
        tier2_deliverability({"status": "verified", "verifier": "test"}),
        tier3_employment(has_current_role_evidence=True),
        tier4_compliance(suppressed=False, permission_state="granted"),
    ]


class ScriptedAdapter:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def capabilities(self):
        return {"account_discovery"}

    async def discover_accounts(self, query, api_key, count=5):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        observed = datetime(2026, 10, 1, tzinfo=timezone.utc)
        return ConnectorEnvelope(
            provider_key="hn_hiring",
            request_id="req-fixed",
            status="ok",
            estimated_cost=0.0,
            accounts=[AccountCandidate(display_name="Acme", canonical_domain="acme.com")],
            signals=[
                RawSignal(
                    signal_type="job_opening",
                    summary="Hiring a backend engineer",
                    payload={"role": "backend"},
                    base_strength=80,
                    source_confidence=0.7,
                    observed_at=observed,
                    independent_key="hn:1",
                    source_url="https://news.ycombinator.com/item?id=1",
                )
            ],
        )


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    session.add(Tenant(id="tenant-sales", name="Sales Co", subdomain="sales-co"))
    session.add(Tenant(id="tenant-other", name="Other Co", subdomain="other-co"))
    session.add(
        User(
            id="user-sales",
            tenant_id="tenant-sales",
            email="sales@example.com",
            hashed_password="hashed",
            role="admin",
            is_system_admin=True,
        )
    )
    session.commit()
    yield session
    session.close()


def test_decay_is_deterministic_and_refuses_missing_inputs():
    assert effective_strength(80, 0.5, 45, 45) == 20
    assert effective_strength(80, 0.5, 0, 45) == 40
    assert effective_strength(80, 0.5, -3, 45) == 40
    assert effective_strength(None, 0.5, 0, 45) is None
    assert effective_strength(80, None, 0, 45) is None
    assert effective_strength(80, 0.5, None, 45) is None
    assert effective_strength(80, 0.5, 0, 0) is None


def test_convergence_rewards_independent_evidence_and_caps():
    pair = convergence_bonus([
        {"family": "funding", "independent_key": "fund"},
        {"family": "hiring", "independent_key": "hire"},
    ])
    assert pair["bonus"] == 8
    bundle = convergence_bonus([
        {"family": "funding", "independent_key": "fund"},
        {"family": "hiring", "independent_key": "hire"},
        {"family": "leadership", "independent_key": "lead"},
    ])
    assert bundle["bonus"] == 15
    assert "funding_and_hiring" not in bundle["reasons"]
    migration = convergence_bonus([
        {"family": "funding", "independent_key": "fund"},
        {"family": "hiring", "independent_key": "hire"},
        {"family": "leadership", "independent_key": "lead"},
        {"family": "reviews", "independent_key": "rev"},
        {"family": "technographic", "independent_key": "tech"},
    ])
    assert migration["bonus"] == 25
    assert migration["uncapped_bonus"] == 27
    duplicate = convergence_bonus([
        {"family": "funding", "independent_key": "same"},
        {"family": "hiring", "independent_key": "same"},
    ])
    assert duplicate["bonus"] == 0
    assert duplicate["dropped_duplicates"] == 1


def test_identity_does_not_guess_a_domain():
    assert canonical_domain("acme") is None
    assert canonical_domain("https://www.Acme.com/about") == "acme.com"
    assert canonical_domain("ada@acme.com") == "acme.com"


def test_waterfall_stops_for_qualification_budget_and_verified_data():
    unknown = icp_gate({"industry": None}, {"industries": ["software"]})
    assert unknown["qualified"] is False
    rejected = icp_gate({"industry": "healthcare"}, {"industries": ["software"]})
    assert rejected["status"] == "rejected"
    matched = icp_gate({"industry": "software", "employee_count": 40}, {"industries": ["software"], "employee_min": 10})
    assert matched["qualified"] is True
    blocked = plan_contact_waterfall(qualified=False, providers=["apollo"], costs={"apollo": 0.1}, budget=5)
    assert blocked[0]["reason"] == "account_not_qualified"
    needs_budget = plan_contact_waterfall(qualified=True, providers=["apollo"], costs={"apollo": 0.1}, budget=None)
    assert needs_budget[0]["reason"] == "budget_decision_required"
    verified = plan_contact_waterfall(
        qualified=True, providers=["apollo"], costs={"apollo": 0.1}, budget=5, already_verified=True
    )
    assert verified[0]["reason"] == "sufficient_verified_data"
    over = plan_contact_waterfall(qualified=True, providers=["apollo"], costs={"apollo": 2}, budget=1)
    assert over[0]["reason"] == "budget_exceeded"


def test_scoring_excludes_unknowns_and_reproduces_caps():
    only_icp = score_opportunity({"icp": 80, "intent": None, "timing": None, "problem_fit": None, "account_value": None, "data_confidence": None, "contactability": None, "engagement": None})
    assert only_icp["score"] == 80
    assert only_icp["score_version"] == SCORE_VERSION
    again = score_opportunity({"icp": 80})
    assert again["score"] == only_icp["score"]
    assert again["config_hash"] == only_icp["config_hash"]
    empty = score_opportunity({})
    assert empty["score"] is None
    capped = score_opportunity({"icp": 90}, flags={"single_source": True})
    assert capped["score"] == 70
    with pytest.raises(ValueError):
        score_opportunity({"icp": 80}, weights={"icp": 0.5})


def test_tier6_suppression_and_nurture():
    passed = _passed_tiers()
    assert tier6_state(tiers=passed, score=80, suppressed=False) == "READY"
    assert tier6_state(tiers=passed, score=59, suppressed=False) == "NURTURE"
    assert tier6_state(tiers=passed, score=None, suppressed=False) == "NURTURE"
    suppressed = tier4_compliance(suppressed=True, suppression_reason="unsubscribe")
    assert tier6_state(tiers=[suppressed], score=90, suppressed=True, suppression_reason="unsubscribe") == "SUPPRESSED"
    assert tier6_state(tiers=[suppressed], score=90, suppressed=True, suppression_reason="manual_dnc") == "DO_NOT_CONTACT"
    unknown_identity = [tier0_identity(canonical_domain=None, email=None)]
    assert tier6_state(tiers=unknown_identity, score=90, suppressed=False) == "NEEDS_RESEARCH"


def test_bandit_can_be_disabled_and_rejects_a_bad_override():
    disabled = choose_provider(["hunter", "apollo"], {}, disabled=True)
    assert disabled == {"provider": "hunter", "reason": "bandit_disabled"}
    with pytest.raises(ValueError):
        choose_provider(["hunter"], {}, override="apollo")
    assert routing_utility(expected_yield=1, quality=1, compliance=1, latency_ms=None, cost=1) is None
    assert routing_utility(expected_yield=1, quality=1, compliance=1, latency_ms=10, cost=None) is None


def test_honesty_flags_stub_contacts_and_leaves_real_role_inboxes():
    assert is_fabricated_contact({"email": "careers@acme.com"}) is True
    assert is_fabricated_contact({"email": "hello@acme.com"}) is True
    assert is_fabricated_contact({"email": "info@acme.com"}) is False
    assert is_fabricated_contact({"email": "contact@acme.com"}) is False
    assert is_fabricated_contact({"phone": "+1 800-555-0199"}) is True
    assert is_fabricated_contact({"email": "ada@hn-founder.io"}) is True
    assert is_fabricated_contact({"name": "Head of Talent / VP"}) is True


def test_activation_marks_missing_adapters_and_public_sources():
    greenhouse = describe_source("greenhouse", False)
    assert greenhouse["implementation"] == "live"
    assert greenhouse["activation_status"] == "active"
    assert greenhouse["sales_os_callable"] is True
    assert greenhouse["requires_key"] is False
    assert greenhouse["estimated_cost_usd"] == 0.0
    apollo = describe_source("apollo", False)
    assert apollo["activation_status"] == "missing_credentials"
    assert apollo["sales_os_callable"] is False
    apollo_ready = describe_source("apollo", True)
    assert apollo_ready["activation_status"] == "active"
    assert apollo_ready["estimated_cost_usd"] == 0.10
    hiring = describe_source("hn_hiring", False)
    assert hiring["activation_status"] == "active"
    assert hiring["sales_os_callable"] is True
    assert hiring["estimated_cost_usd"] == 0.0
    gmail = describe_source("gmail", False)
    assert gmail["implementation"] == "live"
    assert gmail["activation_status"] == "missing_credentials"
    assert gmail["sales_os_callable"] is False
    gmail_ready = describe_source("gmail", True)
    assert gmail_ready["sales_os_callable"] is True


def test_roi_is_not_causal_and_missing_money_stays_unknown():
    summary = summarize_roi([], [])
    assert summary["attribution_is_causal"] is False
    assert summary["spend"] is None
    assert summary["revenue"] is None
    known = summarize_roi(
        [{"provider_key": "apollo", "actual_amount": 2.0}],
        [{"provider_key": "apollo", "outcome_type": "meeting"}, {"provider_key": "apollo", "outcome_type": "revenue", "amount": 10, "touch_role": "first"}],
    )
    assert known["spend"] == 2.0
    assert known["cost_per_meeting"] == 2.0
    assert known["attribution_is_causal"] is False


@pytest.mark.asyncio
async def test_pipeline_persists_real_evidence_only(db):
    adapter = ScriptedAdapter()
    pipeline = SalesPipeline(db, "tenant-sales", adapters={"hn_hiring": adapter})
    result = await pipeline.run(
        query="acme.com",
        provider_keys=["hn_hiring", "apollo"],
        credentialed=set(),
        credentials={},
        budget=None,
        execute=True,
    )
    company = SalesIntelligenceStore(db, "tenant-sales").get_company(result["company_id"])
    assert company.industry is None
    assert company.employee_count is None
    assert company.canonical_domain == "acme.com"
    assert db.query(SalesSignal).filter(SalesSignal.tenant_id == "tenant-sales").count() == 1
    again = await pipeline.run(
        query="acme.com",
        provider_keys=["hn_hiring"],
        credentialed=set(),
        credentials={},
        budget=None,
        execute=True,
    )
    assert again["company_id"] == result["company_id"]
    assert db.query(SalesSignal).filter(SalesSignal.tenant_id == "tenant-sales").count() == 1
    apollo_steps = [step for step in result["steps"] if step["provider_key"] == "apollo"]
    assert apollo_steps
    assert apollo_steps[0]["action"] == "skip"
    assert apollo_steps[0]["reason"] == "missing_credentials"
    qualified_gate = pipeline.plan(["apollo"], qualified=False, budget=10, credentialed={"apollo"})
    assert qualified_gate[0]["reason"] == "account_not_qualified"


@pytest.mark.asyncio
async def test_paid_enrichment_is_blocked_without_a_budget_decision(db):
    store = SalesIntelligenceStore(db, "tenant-sales")
    company = store.upsert_company(
        {"canonical_domain": "fit.example", "industry": "Software", "hq_country": "US", "employee_count": 80},
        "manual",
    )
    conflicting = store.upsert_company(
        {"canonical_domain": "fit.example", "industry": "Healthcare"},
        "other",
    )
    assert conflicting.industry == "Software"
    assert any(item["field"] == "industry" for item in conflicting.conflicts)
    pipeline = SalesPipeline(db, "tenant-sales")
    profile = {"industries": ["Software"], "countries": ["US"], "employee_min": 10}
    blocked = pipeline.enrich_contacts(company.id, ["apollo"], None, {"apollo"}, profile)
    assert blocked["executed"] is False
    assert blocked["reason"] == "budget_decision_required"
    unqualified = pipeline.enrich_contacts(company.id, ["apollo"], 10, {"apollo"}, {"industries": ["Healthcare"]})
    assert unqualified["reason"] == "account_not_qualified"
    empty_profile = pipeline.enrich_contacts(company.id, ["apollo"], 10, {"apollo"}, None)
    assert empty_profile["reason"] == "account_not_qualified"


def test_backfill_skips_leads_without_a_domain_and_keeps_tenants_apart(db):
    store = SalesIntelligenceStore(db, "tenant-sales")
    db.add(Lead(id="lead-real", tenant_id="tenant-sales", email="ada@acme.io", name="Ada Lovelace", company="Acme", source="manual"))
    db.add(Lead(id="lead-plain", tenant_id="tenant-sales", email="not-an-email", name="No Domain", company="Mystery"))
    db.commit()
    summary = store.backfill_leads()
    db.commit()
    assert summary["linked_leads"] == 1
    assert summary["skipped_leads"] == 1
    company = store.get_company_by_domain("acme.io")
    assert company.industry is None
    assert company.employee_count is None
    assert company.display_name == "Acme"
    lead = db.query(Lead).filter(Lead.id == "lead-real").first()
    assert lead.sales_company_id == company.id
    other = SalesIntelligenceStore(db, "tenant-other")
    assert other.list_companies() == []
    assert store.upsert_contact(company.id, {"email": None, "full_name": None}, "manual") is None


@pytest.mark.asyncio
async def test_one_provider_failure_does_not_stop_the_run_and_the_circuit_opens(db):
    failing = ScriptedAdapter(fail=True)
    pipeline = SalesPipeline(db, "tenant-sales", adapters={"hn_hiring": failing})
    for _ in range(3):
        result = await pipeline.run(
            query="acme.com",
            provider_keys=["hn_hiring"],
            credentialed=set(),
            credentials={},
            budget=None,
            execute=True,
        )
        assert result["counts"]["errors"] == 1
    opened = await pipeline.run(
        query="acme.com",
        provider_keys=["hn_hiring"],
        credentialed=set(),
        credentials={},
        budget=None,
        execute=True,
    )
    assert opened["counts"]["errors"] == 0
    assert opened["counts"]["skipped"] == 1
    assert failing.calls == 3


@pytest.mark.asyncio
async def test_deal_room_signal_without_confidence_is_not_treated_as_fresh(db):
    room = DealRoom(id="room-1", tenant_id="tenant-sales", company_name="Acme", domain="acme.com", icp_fit_score=0.8)
    db.add(room)
    db.commit()
    dispatcher = SalesEventDispatcher(db, "tenant-sales")
    result = await dispatcher.dispatch_event("SignalDetected", {"deal_room_id": room.id, "signal_type": "funding"})
    signal = db.query(AccountSignal).filter(AccountSignal.id == result["signal_id"]).one()
    assert signal.headline == "funding"
    assert signal.confidence is None
    refreshed = db.query(DealRoom).filter(DealRoom.id == room.id).one()
    assert refreshed.timing_score == 0.0


def test_sales_os_task_is_not_on_the_beat_schedule():
    scheduled = [item["task"] for item in celery_app.conf.beat_schedule.values()]
    assert "run_sales_os_discovery_task" not in scheduled


def test_sales_os_api_plans_without_spending(db):
    def override_db():
        try:
            yield db
        finally:
            pass

    app = FastAPI()
    app.dependency_overrides[deps.get_db] = override_db
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-sales"
    app.dependency_overrides[deps.get_current_user] = lambda: User(
        id="user-sales",
        tenant_id="tenant-sales",
        email="sales@example.com",
        role="admin",
        is_system_admin=True,
        hashed_password="hashed",
    )
    app.include_router(sales_os_router, prefix="/api/v1/sales-os")
    client = TestClient(app)

    planned = client.post(
        "/api/v1/sales-os/discovery/runs",
        json={"query": "acme.com", "provider_keys": ["greenhouse", "hn_hiring", "apollo"], "execute": False},
    )
    assert planned.status_code == 200
    body = planned.json()
    assert body["status"] == "planned"
    reasons = {step["provider_key"]: step for step in body["steps"]}
    assert reasons["greenhouse"]["action"] == "call"
    assert reasons["greenhouse"]["reason"] == "public_or_configured"
    assert reasons["hn_hiring"]["action"] == "call"
    assert reasons["apollo"]["action"] == "skip"
    company = client.get(f"/api/v1/sales-os/companies/{body['company_id']}")
    assert company.status_code == 200
    assert company.json()["industry"] is None
    assert company.json()["canonical_domain"] == "acme.com"
    health = client.get("/api/v1/sales-os/sources/health")
    assert health.status_code == 200
    assert health.json()["sales_os_callable"] >= 2
    roi = client.get("/api/v1/sales-os/attribution/roi")
    assert roi.status_code == 200
    assert roi.json()["attribution_is_causal"] is False
    blocked = client.post(
        f"/api/v1/sales-os/companies/{body['company_id']}/enrich",
        json={"provider_keys": ["apollo"], "execute": False},
    )
    assert blocked.status_code == 200
    assert blocked.json()["executed"] is False
    outcome = client.post(
        "/api/v1/sales-os/outcomes",
        json={"provider_key": "hn_hiring", "outcome_type": "meeting", "touch_role": "first"},
    )
    assert outcome.status_code == 200
    assert outcome.json()["attribution_is_causal"] is False
