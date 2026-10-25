import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base, User, Tenant
from app.models.rooms import SectionRoom
from app.models.verticals import Lead
from app.api.deps import get_db, get_current_tenant_id, get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_lead_capture.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

test_tenant_id = "tenant-lead-capture-test"


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    tenant = Tenant(id=test_tenant_id, name="Lead Test Co", subdomain="lead-test")
    session.add(tenant)

    # Seed default SectionRoom for sales
    default_room = SectionRoom(
        id="room-sales-default-uuid",
        tenant_id=test_tenant_id,
        section="sales",
        name="General Sales",
        slug="default",
        status="active",
        visibility="internal_public",
    )
    session.add(default_room)
    session.commit()

    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    def override_get_current_tenant_id():
        return test_tenant_id

    def override_get_current_user():
        return User(
            id="user-test-1",
            email="sales@example.com",
            name="Sales User",
            tenant_id=test_tenant_id,
            role="admin",
            is_verified=True,
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_unassigned_and_default_room_leads_visible_with_room_slug_default(client, db):
    # 1. Add a lead without room_id (e.g. from background capture or external webhook)
    lead_unassigned = Lead(
        tenant_id=test_tenant_id,
        name="Unassigned Lead",
        company="Company A",
        email="a@example.com",
        status="captured",
        room_id=None,
    )
    # 2. Add a lead with room_id == 'sales-default' (from initial client state)
    lead_placeholder = Lead(
        tenant_id=test_tenant_id,
        name="Placeholder Room Lead",
        company="Company B",
        email="b@example.com",
        status="ready",
        room_id="sales-default",
    )
    # 3. Add a lead assigned to real default room UUID
    lead_assigned = Lead(
        tenant_id=test_tenant_id,
        name="Assigned Lead",
        company="Company C",
        email="c@example.com",
        status="qualified",
        room_id="room-sales-default-uuid",
    )
    db.add_all([lead_unassigned, lead_placeholder, lead_assigned])
    db.commit()

    # Query with room_slug=default
    res = client.get("/api/v1/leads/?room_slug=default")
    assert res.status_code == 200
    leads = res.json()
    lead_names = {l["name"] for l in leads}
    assert "Unassigned Lead" in lead_names
    assert "Placeholder Room Lead" in lead_names
    assert "Assigned Lead" in lead_names
    assert len(leads) == 3


def test_create_lead_resolves_default_room_properly(client, db):
    # Create lead with room_id="sales-default"
    res = client.post("/api/v1/leads/", json={
        "name": "New Inbound Lead",
        "company": "Company New",
        "email": "new@example.com",
        "room_id": "sales-default",
    })
    assert res.status_code == 200
    created = res.json()
    assert created["room_id"] == "room-sales-default-uuid"

    # Verify visible when reading leads for default room
    get_res = client.get("/api/v1/leads/?room_slug=default")
    assert get_res.status_code == 200
    names = [l["name"] for l in get_res.json()]
    assert "New Inbound Lead" in names
