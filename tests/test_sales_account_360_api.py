"""Integration tests for Sales CRM and Account 360 REST endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.api import deps
from app.models.base import Base, Tenant, User
from app.models.sales_intelligence import SalesCompany, AccountContact, SalesOpportunity, SalesSignal
from app.models.deal_room import DealRoom, BuyingCommitteeMember
from app.models.verticals import Lead


@pytest.fixture
def api_test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    tenant = Tenant(id="tenant_crm_test", name="CRM Corp", subdomain="crm-corp", is_active=True)
    user = User(
        id="user_crm_test",
        tenant_id="tenant_crm_test",
        email="salesrep@crm-corp.com",
        hashed_password="hash",
        is_active=True,
        role="admin",
        allowed_sections=["sales", "deal_rooms", "analytics"],
    )
    session.add_all([tenant, user])
    session.commit()

    yield session
    session.close()


@pytest.fixture
def client(api_test_db):
    def override_get_db():
        try:
            yield api_test_db
        finally:
            pass

    def override_get_current_tenant_id():
        return "tenant_crm_test"

    def override_get_current_user():
        return api_test_db.query(User).filter_by(id="user_crm_test").first()

    def override_check_access(section: str):
        def _checker():
            return True
        return _checker

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    app.dependency_overrides[deps.check_access] = override_check_access

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_copilot_is_tenant_scoped_and_pack_switch_keeps_leads(client, api_test_db):
    api_test_db.add_all([
        Lead(
            id="own-lead",
            tenant_id="tenant_crm_test",
            name="Olivia",
            email="olivia@alpha.example",
            company="Alpha Business",
            status="new",
        ),
        Lead(
            id="other-lead",
            tenant_id="other-tenant",
            name="Hidden",
            email="hidden@other.example",
            company="Other Co",
        ),
    ])
    api_test_db.commit()

    denied = client.post(
        "/api/v1/sales-os/copilot/record",
        json={"lead_id": "other-lead", "question": "What is the email?"},
    )
    assert denied.status_code == 404

    allowed = client.post(
        "/api/v1/sales-os/copilot/record",
        json={"lead_id": "own-lead", "question": "What should we do next?"},
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["invented"] is False
    assert "hidden@other.example" not in allowed.text
    assert any("olivia@alpha.example" in item["claim"] for item in body["evidence"])

    switched = client.post("/api/v1/sales-os/verticals/active", json={"pack_id": "manufacturing"})
    assert switched.status_code == 200
    preview = switched.json()
    assert preview["records_deleted"] == 0
    assert preview["records_preserved"] >= 1
    assert api_test_db.query(Lead).filter_by(id="own-lead").one().company == "Alpha Business"

    active = client.get("/api/v1/sales-os/verticals/active")
    assert active.status_code == 200
    assert active.json()["pack"]["id"] == "manufacturing"
    assert active.json()["pack"]["terminology"]["lead"] == "RFQ"


def test_list_canonical_accounts_api(client, api_test_db):
    company = SalesCompany(
        tenant_id="tenant_crm_test",
        display_name="Cyberdyne Systems",
        canonical_domain="cyberdyne.com",
        industry="Robotics",
        employee_count=1200,
        icp_score=92.0,
        intent_score=88.0,
    )
    api_test_db.add(company)
    api_test_db.commit()

    res = client.get("/api/v1/sales-crm/accounts")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["canonical_domain"] == "cyberdyne.com"
    assert data[0]["industry"] == "Robotics"


def test_get_account_360_api(client, api_test_db):
    company = SalesCompany(
        tenant_id="tenant_crm_test",
        display_name="Initech",
        canonical_domain="initech.com",
        industry="Software",
        icp_score=85.0,
        intent_score=75.0,
    )
    api_test_db.add(company)
    api_test_db.commit()

    res = client.get(f"/api/v1/sales-crm/accounts/{company.id}/360")
    assert res.status_code == 200
    body = res.json()
    assert body["company"]["display_name"] == "Initech"
    assert "buying_committee" in body
    assert "agent_recommendation" in body
    assert body["agent_recommendation"]["recommended_action"] == "Expand Buying Committee"


def test_add_committee_member_api(client, api_test_db):
    company = SalesCompany(
        tenant_id="tenant_crm_test",
        display_name="Massive Dynamic",
        canonical_domain="massivedynamic.com",
    )
    api_test_db.add(company)
    api_test_db.commit()

    payload = {
        "name": "William Bell",
        "email": "wbell@massivedynamic.com",
        "title": "Chairman & Founder",
        "role_type": "economic_buyer",
    }
    res = client.post(f"/api/v1/sales-crm/accounts/{company.id}/committee", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    assert data["email"] == "wbell@massivedynamic.com"


def test_reconcile_api(client, api_test_db):
    lead = Lead(
        tenant_id="tenant_crm_test",
        name="Peter Gibbons",
        email="peter@initech.com",
        company="Initech",
        source="apollo",
        status="captured",
    )
    api_test_db.add(lead)
    api_test_db.commit()

    res = client.post("/api/v1/sales-crm/reconcile")
    assert res.status_code == 200
    data = res.json()
    assert data["scanned"] >= 1
    assert data["promoted_to_canonical"] >= 1


def test_agents_run_api(client, api_test_db):
    payload = {
        "goal": "Audit account buying committee and calculate risk",
        "agent_id": "opportunity_strategy_agent",
        "parameters": {"domain": "initech.com"},
    }
    res = client.post("/api/v1/sales-crm/agents/run", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "started"

    list_res = client.get("/api/v1/sales-crm/agents/runs")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
