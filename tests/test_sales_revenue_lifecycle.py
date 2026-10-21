"""Tests for Phase 5: Revenue Lifecycle, Forecasting, Win/Loss Intelligence, and Renewal/Expansion Cohorts."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, Tenant
from app.models.deal_room import DealRoom, BuyingCommitteeMember
from app.services.sales_os.lifecycle.revenue_lifecycle import RevenueLifecycleEngine


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

    tenant = Tenant(id="tenant_lifecycle_test", name="Lifecycle Test Tenant")
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_executive_pipeline_forecast(db_session):
    """Verifies pipeline aggregation, commit & best-case thresholds, and at-risk deal audits."""
    now = datetime.now(timezone.utc)
    old_date = now - timedelta(days=12)

    # 1. High-probability closing deal (Commit & Best Case)
    d1 = DealRoom(
        tenant_id="tenant_lifecycle_test",
        company_name="Alpha Tech",
        domain="alphatech.com",
        stage="closing",
        annual_revenue_usd=50000.0,
        calibrated_win_prob=0.85,
        is_multi_threaded=True,
        last_activity_at=now,
    )

    # 2. Medium-probability meeting deal (Best Case only, but stalled >7d)
    d2 = DealRoom(
        tenant_id="tenant_lifecycle_test",
        company_name="Beta Systems",
        domain="betasystems.com",
        stage="meeting_booked",
        annual_revenue_usd=30000.0,
        calibrated_win_prob=0.55,
        is_multi_threaded=False,
        last_activity_at=old_date,
    )

    # 3. Low-probability early discovery deal
    d3 = DealRoom(
        tenant_id="tenant_lifecycle_test",
        company_name="Gamma Global",
        domain="gammaglobal.com",
        stage="discovered",
        annual_revenue_usd=20000.0,
        calibrated_win_prob=0.10,
        is_multi_threaded=False,
        last_activity_at=now,
    )

    db_session.add_all([d1, d2, d3])
    db_session.commit()

    engine = RevenueLifecycleEngine(db_session, "tenant_lifecycle_test")
    forecast = engine.get_executive_forecast()

    # Total = 50k + 30k + 20k = 100k
    assert forecast["total_pipeline_usd"] == 100000.0
    # Commit (prob >= 0.70) = 50k
    assert forecast["commit_usd"] == 50000.0
    # Best case (prob >= 0.40) = 50k + 30k = 80k
    assert forecast["best_case_usd"] == 80000.0
    assert forecast["active_opportunities_count"] == 3

    # Beta Systems should be flagged for stalled_7_days and single_threaded
    beta_audit = next((d for d in forecast["at_risk_deals"] if d["company_name"] == "Beta Systems"), None)
    assert beta_audit is not None
    assert "stalled_7_days" in beta_audit["risk_factors"]
    assert "single_threaded" in beta_audit["risk_factors"]

    # Monday Brief narrative generated
    assert "Executive Revenue & Pipeline Forecast Brief" in forecast["monday_executive_brief"]
    assert "$100,000.00" in forecast["monday_executive_brief"]


def test_win_loss_intelligence(db_session):
    """Verifies win rate calculation, loss reasons distribution, and competitor records."""
    w1 = DealRoom(
        tenant_id="tenant_lifecycle_test",
        company_name="Won Enterprise 1",
        domain="won1.com",
        stage="won",
        annual_revenue_usd=40000.0,
    )
    w2 = DealRoom(
        tenant_id="tenant_lifecycle_test",
        company_name="Won Enterprise 2",
        domain="won2.com",
        stage="won",
        annual_revenue_usd=60000.0,
    )
    l1 = DealRoom(
        tenant_id="tenant_lifecycle_test",
        company_name="Lost Deal 1",
        domain="lost1.com",
        stage="lost",
        annual_revenue_usd=30000.0,
        account_brief={"loss_reason": "budget_constraint"},
    )

    db_session.add_all([w1, w2, l1])
    db_session.commit()

    engine = RevenueLifecycleEngine(db_session, "tenant_lifecycle_test")
    wl = engine.get_win_loss_intelligence()

    assert wl["total_closed_deals"] == 3
    assert wl["won_count"] == 2
    assert wl["lost_count"] == 1
    assert wl["win_rate_pct"] == round(2 / 3 * 100, 1)
    assert wl["total_won_arr_usd"] == 100000.0
    assert wl["average_deal_size_usd"] == 50000.0

    # Loss reasons
    assert wl["loss_reasons_distribution"]["budget_constraint"] == 1

    # Competitor records and win drivers
    assert len(wl["competitor_records"]) >= 3
    assert len(wl["win_drivers"]) >= 3


def test_renewal_and_expansion_cohorts(db_session):
    """Verifies 30d/60d/90d renewal cohort grouping, health scores, and expansion targets."""
    engine = RevenueLifecycleEngine(db_session, "tenant_lifecycle_test")
    cohorts = engine.get_renewal_and_expansion_cohorts()

    assert cohorts["total_renewable_arr_usd"] > 0
    assert cohorts["net_revenue_retention_pct"] >= 100.0

    # Renewal lists
    assert len(cohorts["renewals_under_30d"]) >= 1
    assert any(r["health_score"] > 80 for r in cohorts["renewals_under_30d"])

    # Expansion targets
    assert len(cohorts["expansion_candidates"]) >= 2
    assert cohorts["total_expansion_pipeline_usd"] > 0
    assert any(c["recommended_sku"] == "OCTA-SALES-SWARM" for c in cohorts["expansion_candidates"])
