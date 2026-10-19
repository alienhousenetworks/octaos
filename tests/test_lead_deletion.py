import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base, User, Tenant
from app.models.verticals import Lead
from app.models.sales_intelligence import SourceOutcome
from app.api.deps import get_db, get_current_tenant_id, get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_lead_deletion.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

test_tenant_store = {"tenant_id": "tenant-sales-test", "role": "admin"}


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    tenant1 = Tenant(id="tenant-sales-test", name="Sales Co A", subdomain="sales-a")
    tenant2 = Tenant(id="tenant-other-test", name="Sales Co B", subdomain="sales-b")
    session.add_all([tenant1, tenant2])
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    def override_get_current_tenant_id():
        return test_tenant_store["tenant_id"]

    def override_get_current_user():
        return User(
            id=f"user-{test_tenant_store['tenant_id']}",
            email="sales@example.com",
            name="Sales User",
            tenant_id=test_tenant_store["tenant_id"],
            role=test_tenant_store["role"],
            is_verified=True,
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    test_tenant_store["tenant_id"] = "tenant-sales-test"
    test_tenant_store["role"] = "admin"


def test_delete_single_lead_success(client, db):
    # 1. Create a lead directly in db
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id="tenant-sales-test",
        name="Acme Corp",
        company="Acme Corporation",
        email="contact@acme.com",
        status="captured",
    )
    db.add(lead)
    db.commit()
    lead_id = lead.id

    # 2. Call DELETE endpoint
    resp = client.delete(f"/api/v1/leads/{lead_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["id"] == lead_id

    # 3. Verify lead is gone from database
    db.expire_all()
    in_db = db.query(Lead).filter(Lead.id == lead_id).first()
    assert in_db is None

    # 4. Attempting to delete again yields 404
    resp_again = client.delete(f"/api/v1/leads/{lead_id}")
    assert resp_again.status_code == 404


def test_delete_lead_with_agent_role(client, db):
    # Standard team member (role='agent') can also delete leads
    test_tenant_store["role"] = "agent"

    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id="tenant-sales-test",
        name="Spam Lead",
        company="Spam Inc",
        email="junk@spam.com",
        status="new",
    )
    db.add(lead)
    db.commit()
    lead_id = lead.id

    resp = client.delete(f"/api/v1/leads/{lead_id}")
    assert resp.status_code == 200
    assert db.query(Lead).filter(Lead.id == lead_id).first() is None


def test_bulk_delete_leads(client, db):
    # Create 3 leads
    leads = [
        Lead(
            id=str(uuid.uuid4()),
            tenant_id="tenant-sales-test",
            name=f"Lead {i}",
            company=f"Company {i}",
            email=f"lead{i}@test.com",
            status="captured",
        )
        for i in range(3)
    ]
    db.add_all(leads)
    db.commit()
    lead_ids = [l.id for l in leads]

    resp = client.post("/api/v1/leads/bulk-delete", json={"lead_ids": lead_ids})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["deleted_count"] == 3

    # Verify all are removed from DB
    remaining = db.query(Lead).filter(Lead.id.in_(lead_ids)).count()
    assert remaining == 0


def test_delete_lead_tenant_isolation(client, db):
    # Create lead in tenant B
    lead_b = Lead(
        id=str(uuid.uuid4()),
        tenant_id="tenant-other-test",
        name="Other Corp",
        company="Other Corporation",
        email="other@corp.com",
        status="captured",
    )
    db.add(lead_b)
    db.commit()

    # User in tenant A tries to delete lead from tenant B
    test_tenant_store["tenant_id"] = "tenant-sales-test"
    resp = client.delete(f"/api/v1/leads/{lead_b.id}")
    assert resp.status_code == 404

    # Lead in tenant B still exists
    db.expire_all()
    in_db = db.query(Lead).filter(Lead.id == lead_b.id).first()
    assert in_db is not None
    assert in_db.company == "Other Corporation"


def test_delete_lead_dissociates_attribution_outcomes(client, db):
    # Lead with an attribution outcome
    lead = Lead(
        id=str(uuid.uuid4()),
        tenant_id="tenant-sales-test",
        name="Attribution Lead",
        company="ROI Corp",
        email="roi@corp.com",
        status="contacted",
    )
    db.add(lead)
    db.flush()

    outcome = SourceOutcome(
        id=str(uuid.uuid4()),
        tenant_id="tenant-sales-test",
        provider_key="google_places",
        lead_id=lead.id,
        outcome_type="meeting_booked",
    )
    db.add(outcome)
    db.commit()

    # Delete the lead
    resp = client.delete(f"/api/v1/leads/{lead.id}")
    assert resp.status_code == 200

    # Lead is deleted, but outcome remains with lead_id set to None
    db.expire_all()
    assert db.query(Lead).filter(Lead.id == lead.id).first() is None
    outcome_in_db = db.query(SourceOutcome).filter(SourceOutcome.id == outcome.id).first()
    assert outcome_in_db is not None
    assert outcome_in_db.lead_id is None
