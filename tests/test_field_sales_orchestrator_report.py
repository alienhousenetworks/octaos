"""Integration tests for Field Sales Orchestrator Bridge and Executive Analysis Reports."""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api import deps
from app.models.base import Base, Tenant, User
from app.models.real_estate import RealEstateProject, RealEstateSiteVisit, RealEstateUnitHold
from app.models.verticals import Lead
from app.models.field_sales import ConnectorUsageAudit, FieldScheduleRecoveryProposal
from app.services.sales_os.field_sales.orchestrator_bridge import FieldSalesOrchestratorBridge


@pytest.fixture
def orchestrator_test_env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    tenant_id = "tenant_orch_fs"
    tenant = Tenant(id=tenant_id, name="Orchestrator Realty Hub")
    user = User(id="user_orch_agent", tenant_id=tenant_id, email="orch@hub.com", hashed_password="pw")

    project = RealEstateProject(
        id="proj_orch_1",
        tenant_id=tenant_id,
        name="Grand Orchard Residences",
        location="East Corridor",
        latitude=12.9352,
        longitude=77.6245,
    )

    lead1 = Lead(id="l1", tenant_id=tenant_id, name="Rahul Verma", status="meeting_scheduled", score=88)
    lead2 = Lead(id="l2", tenant_id=tenant_id, name="Kavita Iyer", status="closed_won", score=95)

    v1 = RealEstateSiteVisit(
        id="v_comp",
        tenant_id=tenant_id,
        lead_id="l1",
        project_id="proj_orch_1",
        scheduled_at=datetime.now(timezone.utc),
        status="completed",
        assigned_agent="user_orch_agent",
        duration_minutes=60,
        estimated_travel_minutes=25,
        check_in_verified=True,
        buyer_interest_level="high",
        buyer_objections=["Price per sqft above budget"],
    )
    v2 = RealEstateSiteVisit(
        id="v_noshow",
        tenant_id=tenant_id,
        lead_id="l2",
        project_id="proj_orch_1",
        scheduled_at=datetime.now(timezone.utc),
        status="no_show",
        assigned_agent="user_orch_agent",
        duration_minutes=45,
        estimated_travel_minutes=20,
    )

    hold = RealEstateUnitHold(
        id="hold_1",
        tenant_id=tenant_id,
        lead_id="l2",
        unit_id="unit_mock_1",
        status="converted_to_booking",
        concurrency_token="tok_1",
        expires_at=datetime.now(timezone.utc),
    )

    proposal = FieldScheduleRecoveryProposal(
        id="prop_1",
        tenant_id=tenant_id,
        trigger_type="agent_delay",
        status="applied",
        rationale="Traffic delay recovered",
        proposed_changes=[],
    )

    audit = ConnectorUsageAudit(
        id="aud_1",
        tenant_id=tenant_id,
        provider="google_maps",
        endpoint="routes",
        call_count=1,
        cost_estimate_usd=0.005,
        cache_hit=False,
    )

    db.add_all([tenant, user, project, lead1, lead2, v1, v2, hold, proposal, audit])
    db.commit()

    yield db, tenant_id
    db.close()


def test_orchestrator_bridge_generate_analysis_report(orchestrator_test_env):
    db, tenant_id = orchestrator_test_env
    bridge = FieldSalesOrchestratorBridge(db, tenant_id)

    report = bridge.generate_analysis_report(period_days=30)

    # 1. Executive Summary
    summary = report["executive_summary"]
    assert summary["total_scheduled_visits"] == 2
    assert summary["completed_visits"] == 1
    assert summary["no_shows"] == 1
    assert summary["completion_rate_pct"] == 50.0

    # 2. Conversion Funnel
    funnel = report["conversion_funnel"]
    assert funnel["completed_showings"] == 1
    assert funnel["unit_holds"] == 1
    assert funnel["confirmed_bookings"] == 1
    assert funnel["hold_to_booking_pct"] == 100.0

    # 3. Travel & Efficiency
    travel = report["travel_and_efficiency"]
    assert travel["total_transit_minutes"] == 45
    assert travel["total_showing_minutes"] == 60
    assert travel["verified_on_site_check_ins"] == 1

    # 4. Buyer Insights
    insights = report["buyer_insights"]
    assert insights["interest_distribution"]["high"] == 1
    assert len(insights["top_objections"]) >= 1

    # 5. Recovery Health
    recovery = report["recovery_health"]
    assert recovery["delay_incidents"] == 1
    assert recovery["proposals_applied"] == 1
    assert recovery["acceptance_rate_pct"] == 100.0

    # 6. Strategic Recommendations
    assert len(report["strategic_recommendations"]) >= 1


def test_orchestrator_analysis_report_endpoint(orchestrator_test_env):
    db, tenant_id = orchestrator_test_env

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_tenant_id():
        return tenant_id

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id

    client = TestClient(app)
    res = client.get("/api/v1/sales-os/field-sales/analysis-report?period_days=30")
    assert res.status_code == 200
    data = res.json()
    assert data["tenant_id"] == tenant_id
    assert "conversion_funnel" in data
    assert "travel_and_efficiency" in data
    assert "strategic_recommendations" in data

    app.dependency_overrides.clear()
