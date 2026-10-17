import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db
from app.models.base import Base, User, Tenant
from app.models.enterprise import SubscriptionPlan, TenantSubscription
from app.core.security import get_password_hash, create_access_token
from app.services.subscription_service import SubscriptionService, AGENT_CATALOG

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_modular_sub.db"
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
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_seed_plans_and_agent_catalog(db):
    svc = SubscriptionService(db)
    plans = svc.seed_plans()
    assert len(plans) >= 6

    catalog = svc.get_agent_catalog()
    assert len(catalog) == 4
    agent_ids = [c["id"] for c in catalog]
    assert "marketing" in agent_ids
    assert "sales" in agent_ids
    assert "hr" in agent_ids
    assert "support" in agent_ids


def test_standalone_campaign_planner_isolation(db):
    tenant = Tenant(name="Acme Marketing Only", subdomain="acme-mkt")
    db.add(tenant)
    db.commit()

    svc = SubscriptionService(db)
    # Switch tenant to standalone campaign planner
    svc.change_plan(tenant.id, "campaign_planner")

    ent = svc.entitlements(tenant.id)
    assert ent["allowed_agents"] == ["marketing"]

    # Isolation assertions: Only marketing allowed
    assert svc.agent_allowed(tenant.id, "marketing") is True
    assert svc.agent_allowed(tenant.id, "sales") is False
    assert svc.agent_allowed(tenant.id, "hr") is False
    assert svc.agent_allowed(tenant.id, "support") is False


def test_standalone_sales_ai_isolation(db):
    tenant = Tenant(name="Acme Sales Only", subdomain="acme-sales")
    db.add(tenant)
    db.commit()

    svc = SubscriptionService(db)
    svc.change_plan(tenant.id, "sales_ai")

    ent = svc.entitlements(tenant.id)
    assert ent["allowed_agents"] == ["sales"]

    assert svc.agent_allowed(tenant.id, "sales") is True
    assert svc.agent_allowed(tenant.id, "marketing") is False
    assert svc.agent_allowed(tenant.id, "hr") is False
    assert svc.agent_allowed(tenant.id, "support") is False


def test_custom_multi_agent_bundle(db):
    tenant = Tenant(name="Acme Custom Bundle", subdomain="acme-bundle")
    db.add(tenant)
    db.commit()

    svc = SubscriptionService(db)
    # Customer buys Campaign Planner + Customer Support
    ent = svc.subscribe_agents(tenant.id, ["marketing", "support"])

    assert "marketing" in ent["allowed_agents"]
    assert "support" in ent["allowed_agents"]
    assert "sales" not in ent["allowed_agents"]
    assert "hr" not in ent["allowed_agents"]

    assert svc.agent_allowed(tenant.id, "marketing") is True
    assert svc.agent_allowed(tenant.id, "support") is True
    assert svc.agent_allowed(tenant.id, "sales") is False
    assert svc.agent_allowed(tenant.id, "hr") is False


def test_all_in_one_workforce_access(db):
    tenant = Tenant(name="Acme Full Access", subdomain="acme-all")
    db.add(tenant)
    db.commit()

    svc = SubscriptionService(db)
    svc.change_plan(tenant.id, "all_access")

    assert svc.agent_allowed(tenant.id, "marketing") is True
    assert svc.agent_allowed(tenant.id, "sales") is True
    assert svc.agent_allowed(tenant.id, "hr") is True
    assert svc.agent_allowed(tenant.id, "support") is True


def test_api_catalog_and_auth_me_integration(db, client):
    tenant = Tenant(name="Acme Corp", subdomain="acme-corp")
    db.add(tenant)
    db.commit()

    user = User(
        email="founder@acme.com",
        hashed_password=get_password_hash("password123"),
        tenant_id=tenant.id,
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()

    # Subscribe to Sales AI only
    svc = SubscriptionService(db)
    svc.change_plan(tenant.id, "sales_ai")

    token = create_access_token(subject=user.id, tenant_id=tenant.id)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Verify Catalog API
    res_catalog = client.get("/api/v1/enterprise/billing/agent-catalog")
    assert res_catalog.status_code == 200
    catalog = res_catalog.json()
    assert len(catalog) == 4

    # 2. Verify /auth/me returns tenant's allowed_agents
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["allowed_agents"] == ["sales"]
    assert me_data["plan"]["code"] == "sales_ai"

    # 3. Direct multi-agent subscription endpoint
    res_sub = client.post(
        "/api/v1/enterprise/billing/subscribe-agents",
        headers=headers,
        json={"agent_codes": ["sales", "marketing"]},
    )
    assert res_sub.status_code == 200
    sub_data = res_sub.json()
    assert "sales" in sub_data["allowed_agents"]
    assert "marketing" in sub_data["allowed_agents"]
    assert "hr" not in sub_data["allowed_agents"]
