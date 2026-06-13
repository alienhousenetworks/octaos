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
        email="sysadmin@nexusos.com",
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
