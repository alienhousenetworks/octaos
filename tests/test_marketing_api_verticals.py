"""Integration tests for Marketing Industry Vertical Endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api import deps
from app.models.base import Base, Tenant, User
from app.models.real_estate import RealEstateProject, RealEstateUnit
from app.models.verticals import BusinessProfile, ContentPost


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

    tenant = Tenant(id="tenant_marketing_api", name="Horizon Living Group")
    user = User(
        id="user_marketing_lead",
        tenant_id="tenant_marketing_api",
        email="cmo@horizon.example",
        name="Elena Rostova",
        hashed_password="pw",
        role="admin",
    )
    profile = BusinessProfile(
        id="prof_1",
        tenant_id="tenant_marketing_api",
        company_name="Horizon Living Group",
        industry="Real estate",
        industry_pack_id="real_estate",
    )
    project = RealEstateProject(
        id="proj_horizon_1",
        tenant_id="tenant_marketing_api",
        name="Horizon Marina Residences",
        code="HMR-01",
        location="Marina Promenade",
        city="Dubai",
        rera_number="RERA-DXB-98765",
        amenities=["Private Yacht Marina", "Sky Deck Lounge", "Valet Concierge"],
        status="active",
    )
    unit = RealEstateUnit(
        id="unit_penthouse_1",
        tenant_id="tenant_marketing_api",
        project_id="proj_horizon_1",
        tower="Tower North",
        unit_number="PH-401",
        unit_type="4BHK Sky Penthouse",
        carpet_sqft=3800.0,
        base_price=1850000.0,
        status="available",
    )
    db.add_all([tenant, user, profile, project, unit])
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return user

    def override_get_current_tenant_id():
        return "tenant_marketing_api"

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id

    client = TestClient(app)
    yield client, db

    app.dependency_overrides.clear()
    db.close()


def test_get_marketing_verticals_list(client_and_db):
    client, _ = client_and_db
    res = client.get("/api/v1/marketing/verticals")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 18
    assert len(data["packs"]) == 18
    pack_ids = [p["id"] for p in data["packs"]]
    assert "real_estate" in pack_ids
    assert "saas" in pack_ids
    assert "banking" in pack_ids


def test_get_active_marketing_vertical(client_and_db):
    client, _ = client_and_db
    res = client.get("/api/v1/marketing/verticals/active")
    assert res.status_code == 200
    data = res.json()
    assert data["selected"] is True
    assert data["pack_id"] == "real_estate"
    assert data["pack"]["name"] == "Real Estate & Property Development"


def test_switch_marketing_vertical(client_and_db):
    client, _ = client_and_db
    # Switch to SaaS pack
    res = client.post("/api/v1/marketing/verticals/active", json={"pack_id": "saas"})
    assert res.status_code == 200
    preview = res.json()
    assert preview["to_pack_id"] == "saas"
    assert preview["to_name"] == "High Tech & B2B SaaS"
    assert "stay" in preview["effect"]

    # Verify active is now saas
    active_res = client.get("/api/v1/marketing/verticals/active")
    assert active_res.status_code == 200
    assert active_res.json()["pack_id"] == "saas"


def test_get_specific_marketing_vertical(client_and_db):
    client, _ = client_and_db
    res = client.get("/api/v1/marketing/verticals/real_estate")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "real_estate"
    assert data["representative"] is True
    assert len(data["content_pillars"]) >= 4


def test_compliance_audit_endpoint(client_and_db):
    client, _ = client_and_db
    # Prohibited Fair Housing discriminatory terms
    body = {
        "content": "Exclusive 3BHK penthouse. No children, adults only community. 100% appreciation guaranteed.",
        "platform": "linkedin",
        "pack_id": "real_estate",
    }
    res = client.post("/api/v1/marketing/verticals/compliance/audit", json=body)
    assert res.status_code == 200
    audit = res.json()
    assert audit["passed"] is False
    assert len(audit["violations"]) > 0


def test_real_estate_projects_list_endpoint(client_and_db):
    client, _ = client_and_db
    res = client.get("/api/v1/marketing/verticals/real-estate/projects")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 1
    assert data["projects"][0]["name"] == "Horizon Marina Residences"
    assert "4BHK Sky Penthouse" in data["projects"][0]["unit_types"]


def test_real_estate_generate_campaign_endpoint(client_and_db):
    client, db = client_and_db
    body = {
        "project_id": "proj_horizon_1",
        "campaign_type": "site_visit_drive",
        "platform": "linkedin",
        "persist_post": True,
    }
    res = client.post("/api/v1/marketing/verticals/real-estate/generate-campaign", json=body)
    assert res.status_code == 200
    data = res.json()
    assert "Horizon Marina Residences" in data["content"]
    assert "RERA-DXB-98765" in data["content"]
    assert data["compliance"]["passed"] is True
    assert data["post_id"] is not None

    # Verify persisted in database
    post = db.query(ContentPost).filter(ContentPost.id == data["post_id"]).first()
    assert post is not None
    assert post.status == "draft"
