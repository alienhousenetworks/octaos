import pytest
import uuid
import secrets
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.deps import get_db, get_current_user, check_access
from app.models.base import Base, User, Tenant, APICredential, Invitation
from app.core.security import get_password_hash, create_access_token
from app.services.ai_gateway.gateway import AIProviderGateway
from app.services.llm_gateway import LLMGateway

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_saas.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
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

def test_api_key_isolation(db):
    # Setup test keys in config settings (mocked by monkeypatch or standard settings)
    from app.core.config import settings
    original_openai_key = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = "global-system-openai-key"
    
    try:
        gateway = AIProviderGateway()
        
        # Test 1: with non-null tenant_id, lookup should NOT fallback to global environment settings
        key = gateway._get_api_key(db, tenant_id="tenant-123", provider="openai")
        assert key == ""
        
        # Test 2: with null/empty tenant_id, lookup should fallback to global environment settings
        key_fallback = gateway._get_api_key(db, tenant_id="", provider="openai")
        assert key_fallback == "global-system-openai-key"
        
        # Test 3: config credential in DB for tenant, lookup should retrieve it
        from app.core.security import encrypt_api_key
        cred = APICredential(
            tenant_id="tenant-123",
            provider="openai",
            encrypted_key=encrypt_api_key("tenant-specific-openai-key")
        )
        db.add(cred)
        db.commit()
        
        key_db = gateway._get_api_key(db, tenant_id="tenant-123", provider="openai")
        assert key_db == "tenant-specific-openai-key"
    finally:
        settings.OPENAI_API_KEY = original_openai_key

def test_llm_gateway_key_isolation(db):
    from app.core.config import settings
    original_openai_key = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = "global-system-openai-key"
    
    try:
        # LLMGateway constructed with a tenant ID
        gateway = LLMGateway(db, tenant_id="tenant-123")
        key = gateway._get_api_key(provider="openai")
        assert key == ""
        
        # LLMGateway constructed without a tenant ID (null)
        gateway_no_tenant = LLMGateway(db, tenant_id="")
        key_fallback = gateway_no_tenant._get_api_key(provider="openai")
        assert key_fallback == "global-system-openai-key"
    finally:
        settings.OPENAI_API_KEY = original_openai_key

def test_section_access_control(db, client):
    # Create tenant & users
    tenant = Tenant(name="Test Tenant", subdomain="test-sub")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # 1. User with role=member and allowed_sections=['sales']
    user_member = User(
        email="member@test.com",
        hashed_password=get_password_hash("secret"),
        tenant_id=tenant.id,
        is_verified=True,
        is_active=True,
        role="member",
        allowed_sections=["sales"]
    )
    db.add(user_member)
    db.commit()
    db.refresh(user_member)
    
    token_member = create_access_token(subject=user_member.id)
    
    # Let's mock a fastAPI route dependency using dependency injection overrides
    # or just test check_access directly
    # We will test check_access dependency helper function directly
    from fastapi import HTTPException
    
    # Access sales (should succeed)
    dep_sales = check_access("sales")
    res = dep_sales(user_member)
    assert res == user_member
    
    # Access marketing (should fail with 403)
    dep_marketing = check_access("marketing")
    with pytest.raises(HTTPException) as exc_info:
        dep_marketing(user_member)
    assert exc_info.value.status_code == 403
    assert "Access denied to section: marketing" in exc_info.value.detail

    # 2. User with role=admin should access anything
    user_admin = User(
        email="admin@test.com",
        hashed_password=get_password_hash("secret"),
        tenant_id=tenant.id,
        is_verified=True,
        is_active=True,
        role="admin",
        allowed_sections=[] # empty allowed, but role is admin
    )
    db.add(user_admin)
    db.commit()
    db.refresh(user_admin)
    
    dep_any = check_access("marketing")
    res_admin = dep_any(user_admin)
    assert res_admin == user_admin

def test_invitation_flow(db, client):
    # Create tenant and admin
    tenant = Tenant(name="Test Co")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    admin = User(
        email="admin@testco.com",
        hashed_password=get_password_hash("secret"),
        tenant_id=tenant.id,
        is_verified=True,
        is_active=True,
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    admin_token = create_access_token(subject=admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Create invitation
    invite_res = client.post(
        "/api/v1/auth/invite",
        json={"email": "newmember@testco.com"},
        headers=headers
    )
    assert invite_res.status_code == 200
    invite_data = invite_res.json()
    assert "token" in invite_data
    token = invite_data["token"]
    
    # 2. Verify invitation
    verify_res = client.get(f"/api/v1/auth/invite/verify?token={token}")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["company_name"] == "Test Co"
    assert verify_data["email"] == "newmember@testco.com"
    
    # 3. Accept invitation
    accept_res = client.post(
        "/api/v1/auth/invite/accept",
        json={
            "token": token,
            "name": "New Member",
            "email": "newmember@testco.com",
            "password": "newpassword"
        }
    )
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    assert "access_token" in accept_data
    
    # Verify new user was created correctly
    new_user = db.query(User).filter(User.email == "newmember@testco.com").first()
    assert new_user is not None
    assert new_user.role == "member"
    assert new_user.tenant_id == tenant.id
    
    # 4. Verify invite is now used (subsequent verify should fail)
    verify_again = client.get(f"/api/v1/auth/invite/verify?token={token}")
    assert verify_again.status_code == 400

def test_system_admin_endpoints(db, client):
    # Setup standard tenant, company admin, and global system admin
    tenant = Tenant(name="Acme Corp")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    sys_admin = User(
        email="sysadmin@octaos.com",
        hashed_password=get_password_hash("secret"),
        tenant_id=tenant.id,
        is_verified=True,
        is_active=True,
        is_system_admin=True
    )
    company_admin = User(
        email="admin@acme.com",
        hashed_password=get_password_hash("secret"),
        tenant_id=tenant.id,
        is_verified=True,
        is_active=True,
        role="admin",
        is_system_admin=False
    )
    db.add(sys_admin)
    db.add(company_admin)
    db.commit()
    
    sys_token = create_access_token(subject=sys_admin.id)
    comp_token = create_access_token(subject=company_admin.id)
    
    # Test 1: Company Admin tries to access stats (403 Forbidden)
    res1 = client.get("/api/v1/system-admin/stats", headers={"Authorization": f"Bearer {comp_token}"})
    assert res1.status_code == 403
    
    # Test 2: System Admin accesses stats (200 OK)
    res2 = client.get("/api/v1/system-admin/stats", headers={"Authorization": f"Bearer {sys_token}"})
    assert res2.status_code == 200
    stats = res2.json()
    assert stats["tenants_count"] == 1
    assert stats["users_count"] == 2
    
    # Test 3: System Admin toggles tenant active status
    assert tenant.is_active is True
    res3 = client.post(f"/api/v1/system-admin/tenants/{tenant.id}/toggle-active", headers={"Authorization": f"Bearer {sys_token}"})
    assert res3.status_code == 200
    assert res3.json()["is_active"] is False
    
    # Test 4: Suspended tenant user gets locked out (400 Bad Request)
    res4 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {comp_token}"})
    assert res4.status_code == 400
    assert "Tenant organization is suspended" in res4.json()["detail"]


def test_audit_logging_and_usage(db, client):
    # Setup tenant & user
    tenant = Tenant(name="Acme Corp")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    admin = User(
        email="admin@acme.com",
        hashed_password=get_password_hash("secret"),
        tenant_id=tenant.id,
        is_verified=True,
        is_active=True,
        role="admin"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    admin_token = create_access_token(subject=admin.id)
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Test Audit Logging Service & Endpoint
    from app.services.audit_service import AuditService
    AuditService.log_event(
        db=db,
        action="update_settings",
        tenant_id=tenant.id,
        user_id=admin.id,
        resource="settings",
        resource_id="general_config",
        details={"theme": "dark"}
    )
    
    audit_res = client.get("/api/v1/audit/", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) == 1
    assert logs[0]["action"] == "update_settings"
    assert logs[0]["user_id"] == admin.id
    assert logs[0]["resource"] == "settings"
    assert logs[0]["details"] == {"theme": "dark"}
    
    # 2. Test Usage Service & Endpoints
    from app.models.base import ProviderUsage
    usage1 = ProviderUsage(
        tenant_id=tenant.id,
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        cost=0.0125,
        cache_hit=False
    )
    usage2 = ProviderUsage(
        tenant_id=tenant.id,
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        cost=0.0,
        cache_hit=True,
        cached_tokens=1000
    )
    db.add_all([usage1, usage2])
    db.commit()
    
    summary_res = client.get("/api/v1/usage/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_cost"] == 0.0125
    assert summary["total_input_tokens"] == 2000
    assert summary["total_output_tokens"] == 1000
    assert summary["total_calls"] == 2
    
    providers_res = client.get("/api/v1/usage/providers", headers=headers)
    assert providers_res.status_code == 200
    providers = providers_res.json()
    assert len(providers) == 1
    assert providers[0]["provider"] == "openai"
    assert providers[0]["cost"] == 0.0125
    
    cache_res = client.get("/api/v1/usage/cache-efficiency", headers=headers)
    assert cache_res.status_code == 200
    cache = cache_res.json()
    assert cache["total_calls"] == 2
    assert cache["cache_hits"] == 1
    assert cache["cache_misses"] == 1
    assert cache["hit_rate"] == 0.5
    assert cache["total_cached_tokens"] == 1000


def test_observability_endpoint(client):
    # Make a dummy request with a trace ID
    trace_id = "test-trace-12345"
    response = client.get("/", headers={"X-Trace-ID": trace_id})
    assert response.status_code == 200
    assert response.headers.get("X-Trace-ID") == trace_id

    # Retrieve metrics
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    assert "text/plain" in metrics_res.headers.get("content-type", "")
    metrics_text = metrics_res.text
    
    assert "http_requests_total" in metrics_text
    assert "http_request_duration_seconds_sum" in metrics_text
    assert "http_request_duration_seconds_count" in metrics_text


def test_v2_api_versioning(client):
    response = client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v2"
    assert data["enterprise_hardened"] is True


def test_login_rate_limiting(client):
    # Clear in-memory rate limiter cache to prevent leakage from other tests
    from app.core.rate_limiter import _in_memory_windows
    _in_memory_windows.clear()

    # Perform 5 login requests (will get 400/401 due to bad credentials, but passes rate limiter)
    for _ in range(5):
        res = client.post("/api/v1/auth/login", data={"username": "wrong@user.com", "password": "bad"})
        assert res.status_code in (400, 401)
        
    # The 6th request should exceed the limit of 5 and return 429 Too Many Requests
    res_exceeded = client.post("/api/v1/auth/login", data={"username": "wrong@user.com", "password": "bad"})
    assert res_exceeded.status_code == 429
    assert "Rate limit exceeded" in res_exceeded.json()["detail"]




