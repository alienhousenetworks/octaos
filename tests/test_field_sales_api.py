"""Integration tests for Field Sales FastAPI Endpoints."""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt

from app.main import app
from app.api import deps
from app.core.config import settings
from app.models.base import Base, Tenant, User
from app.models.real_estate import RealEstateProject, RealEstateSiteVisit
from app.models.verticals import Lead


@pytest.fixture
def client_and_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    tenant = Tenant(id="tenant_api_fs", name="Apex Living Properties")
    user = User(
        id="user_field_agent",
        tenant_id="tenant_api_fs",
        email="agent@apexliving.com",
        name="Marcus Vance",
        hashed_password="pw",
        role="member",
    )
    project = RealEstateProject(
        id="proj_apex_1",
        tenant_id="tenant_api_fs",
        name="Apex Heights",
        location="Indiranagar",
        latitude=12.9784,
        longitude=77.6408,
    )
    lead = Lead(
        id="lead_apex_1",
        tenant_id="tenant_api_fs",
        name="Priya Nair",
        phone="+919811223344",
        email="priya@example.com",
        company="TechCorp",
        source="Google Ads",
        status="meeting_scheduled",
        score=90,
    )
    visit = RealEstateSiteVisit(
        id="visit_apex_1",
        tenant_id="tenant_api_fs",
        lead_id="lead_apex_1",
        project_id="proj_apex_1",
        scheduled_at=datetime.now(timezone.utc),
        assigned_agent="user_field_agent",
        duration_minutes=45,
        status="scheduled",
    )
    db.add_all([tenant, user, project, lead, visit])
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return user

    def override_get_current_tenant_id():
        return "tenant_api_fs"

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id

    client = TestClient(app)
    yield client, db

    app.dependency_overrides.clear()
    db.close()


def test_field_sales_overview_api(client_and_db):
    client, _ = client_and_db
    res = client.get("/api/v1/sales-os/field-sales/overview")
    assert res.status_code == 200
    data = res.json()
    assert "today_scheduled" in data
    assert "connector_budget" in data
    assert data["today_scheduled"] >= 1


def test_dispatch_map_api(client_and_db):
    client, _ = client_and_db
    res = client.get("/api/v1/sales-os/field-sales/dispatch-map")
    assert res.status_code == 200
    data = res.json()
    assert "salespeople" in data
    assert "visits" in data
    assert len(data["visits"]) >= 1
    assert data["visits"][0]["project_name"] == "Apex Heights"


def test_agent_shift_and_location_api(client_and_db):
    client, _ = client_and_db

    # Toggle Shift On
    res_shift = client.post(
        "/api/v1/sales-os/field-sales/agent/shift",
        json={"is_active": True, "status": "available"},
    )
    assert res_shift.status_code == 200
    assert res_shift.json()["is_shift_active"] is True

    # Report GPS Location
    res_loc = client.post(
        "/api/v1/sales-os/field-sales/agent/location",
        json={"latitude": 12.9784, "longitude": 77.6408, "accuracy": 8.0, "battery_level": 92},
    )
    assert res_loc.status_code == 200
    assert res_loc.json()["status"] == "UPDATED"

    # Verify in My Day
    res_my_day = client.get("/api/v1/sales-os/field-sales/agent/my-day")
    assert res_my_day.status_code == 200
    my_day_data = res_my_day.json()
    assert my_day_data["is_shift_active"] is True
    assert len(my_day_data["visits"]) >= 1


def test_gps_check_in_and_geofencing(client_and_db):
    client, db = client_and_db

    # 1. Attempt check-in far away (>250m) without exception reason -> Expect 400
    res_fail = client.post(
        "/api/v1/sales-os/field-sales/visits/visit_apex_1/check-in",
        json={"latitude": 12.9000, "longitude": 77.5000, "accuracy": 10.0},
    )
    assert res_fail.status_code == 400
    assert "geofence radius" in res_fail.json()["detail"]

    # 2. Check-in far away WITH manual exception reason -> Expect 200 with verified=False
    res_exc = client.post(
        "/api/v1/sales-os/field-sales/visits/visit_apex_1/check-in",
        json={
            "latitude": 12.9000,
            "longitude": 77.5000,
            "accuracy": 10.0,
            "manual_exception_reason": "Escorting buyer from nearby transit hub",
        },
    )
    assert res_exc.status_code == 200
    assert res_exc.json()["check_in_verified"] is False
    assert res_exc.json()["exception_logged"] is True

    # 3. Check-in directly at project coordinates -> Expect 200 with verified=True
    res_ok = client.post(
        "/api/v1/sales-os/field-sales/visits/visit_apex_1/check-in",
        json={"latitude": 12.9784, "longitude": 77.6408, "accuracy": 5.0},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["check_in_verified"] is True


def test_record_visit_outcome_api(client_and_db):
    client, _ = client_and_db
    res = client.post(
        "/api/v1/sales-os/field-sales/visits/visit_apex_1/outcome",
        json={
            "status": "completed",
            "tour_feedback": "Customer loved the club house and layout.",
            "buyer_interest_level": "high",
            "buyer_objections": ["Possession timeline delivery"],
            "agreed_next_step": "Hold Unit 402 with refundable deposit",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["buyer_interest_level"] == "high"


def test_offline_batch_sync_api(client_and_db):
    client, _ = client_and_db
    batch_payload = {
        "events": [
            {
                "id": "event_offline_1",
                "type": "check_in",
                "visit_id": "visit_apex_1",
                "latitude": 12.9784,
                "longitude": 77.6408,
                "accuracy": 10.0,
            },
            {
                "id": "event_offline_2",
                "type": "outcome",
                "visit_id": "visit_apex_1",
                "status": "completed",
                "buyer_interest_level": "medium",
                "tour_feedback": "Synced from offline queue",
            },
        ]
    }
    res = client.post("/api/v1/sales-os/field-sales/sync/offline", json=batch_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["synced_count"] == 2
