"""
Unit and integration tests for Django-style RBAC (Groups, Permissions, M2M mappings,
departmental isolation between HR and Sales, and RBAC API endpoints).
"""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db, get_current_user
from app.models.base import Base, Tenant, User
from app.models.rbac import Group, Permission
from app.models.field_sales import SalespersonFieldStatus
from app.services.rbac_service import (
    ensure_system_permissions,
    ensure_tenant_default_groups,
    get_user_all_permissions,
    user_has_perm,
    user_is_salesperson,
    user_is_hr,
)
from app.services.sales_os.real_estate.project_assignment_service import ProjectAssignmentService
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    # Create test tenant
    tenant = Tenant(id="tenant_rbac_test", name="OctaCorp Global")
    session.add(tenant)

    # Create admin user
    admin = User(
        id="user_admin_1",
        tenant_id="tenant_rbac_test",
        name="Elena Rostova",
        email="elena.admin@octacorp.com",
        role="admin",
        is_staff=True,
        is_superuser=True,
        is_active=True,
        is_verified=True,
        hashed_password=get_password_hash("Secret123!"),
    )
    session.add(admin)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return db.query(User).filter(User.id == "user_admin_1").first()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_permission_catalog_and_default_groups(db):
    """Verify system permissions and default groups are seeded correctly."""
    perms = ensure_system_permissions(db)
    assert len(perms) >= 20
    assert "sales.view_leads" in perms
    assert "hr.manage_employees" in perms
    assert "marketing.publish_content" in perms

    groups = ensure_tenant_default_groups(db, "tenant_rbac_test")
    assert len(groups) >= 5
    group_names = {g.name for g in groups}
    assert "Administrators" in group_names
    assert "Sales Team" in group_names
    assert "HR & Talent Team" in group_names
    assert "Marketing Ops" in group_names

    # Check Sales Team group has sales permissions
    sales_group = next(g for g in groups if g.name == "Sales Team")
    sales_codenames = {p.codename for p in sales_group.permissions}
    assert "sales.view_leads" in sales_codenames
    assert "sales.field_visits" in sales_codenames
    assert "hr.manage_employees" not in sales_codenames


def test_permission_resolution_with_groups_and_direct_overrides(db):
    """Test Django-style permission resolution (superuser, group perms, direct perms)."""
    ensure_system_permissions(db)
    ensure_tenant_default_groups(db, "tenant_rbac_test")

    # Regular user assigned to HR & Talent Team
    hr_group = db.query(Group).filter(Group.tenant_id == "tenant_rbac_test", Group.name == "HR & Talent Team").first()
    hr_user = User(
        id="user_hr_1",
        tenant_id="tenant_rbac_test",
        name="Priya Sharma",
        email="priya.hr@octacorp.com",
        role="member",
        department="HR",
        is_active=True,
        hashed_password=get_password_hash("pass"),
    )
    hr_user.groups.append(hr_group)
    db.add(hr_user)
    db.commit()

    # User should have HR permissions, but not sales permissions
    assert user_has_perm(db, hr_user, "hr.view_employees") is True
    assert user_has_perm(db, hr_user, "hr.manage_candidates") is False or user_has_perm(db, hr_user, "hr.view_candidates") is True
    assert user_has_perm(db, hr_user, "sales.field_visits") is False

    # Grant direct user permission override (e.g. Can view leads)
    sales_view_perm = db.query(Permission).filter(Permission.codename == "sales.view_leads").first()
    hr_user.user_permissions.append(sales_view_perm)
    db.commit()

    assert user_has_perm(db, hr_user, "sales.view_leads") is True
    assert user_has_perm(db, hr_user, "sales.field_visits") is False

    # Superuser has all permissions
    admin_user = db.query(User).filter(User.id == "user_admin_1").first()
    assert user_has_perm(db, admin_user, "sales.field_visits") is True
    assert user_has_perm(db, admin_user, "hr.manage_offers") is True


def test_departmental_isolation_in_salespeople_listing(db):
    """Verify that HR personnel are NEVER listed as salespeople."""
    ensure_system_permissions(db)
    groups = ensure_tenant_default_groups(db, "tenant_rbac_test")
    sales_group = next(g for g in groups if g.name == "Sales Team")
    hr_group = next(g for g in groups if g.name == "HR & Talent Team")

    # 1. Add an HR Manager
    hr_user = User(
        id="emp_hr_sarah",
        tenant_id="tenant_rbac_test",
        name="Sarah Jenkins",
        email="sarah.j@octacorp.com",
        role="member",
        department="HR",
        is_active=True,
        hashed_password=get_password_hash("pass"),
    )
    hr_user.groups.append(hr_group)
    db.add(hr_user)

    # 2. Add a Sales Agent
    sales_user = User(
        id="emp_sales_raj",
        tenant_id="tenant_rbac_test",
        name="Rajesh Kumar",
        email="rajesh.k@octacorp.com",
        role="sales_agent",
        department="Sales",
        is_active=True,
        hashed_password=get_password_hash("pass"),
    )
    sales_user.groups.append(sales_group)
    db.add(sales_user)

    # Add field status for sales user
    status_entry = SalespersonFieldStatus(
        tenant_id="tenant_rbac_test",
        user_id="emp_sales_raj",
        is_shift_active=True,
        status="available",
    )
    db.add(status_entry)
    db.commit()

    # Query salespeople via ProjectAssignmentService
    service = ProjectAssignmentService(db, "tenant_rbac_test")
    salespeople = service.list_salespeople()

    sales_emails = [sp["email"] for sp in salespeople]
    assert "rajesh.k@octacorp.com" in sales_emails
    assert "sarah.j@octacorp.com" not in sales_emails, "HR employee must NOT be returned in list_salespeople"


def test_rbac_api_endpoints(client, db):
    """Verify RBAC REST endpoints: permissions, groups, users, and bulk actions."""
    # 1. Get permissions
    res = client.get("/api/v1/rbac/permissions")
    assert res.status_code == 200
    data = res.json()
    assert "permissions" in data
    assert "grouped" in data
    assert len(data["permissions"]) > 0

    # 2. Get groups
    res = client.get("/api/v1/rbac/groups")
    assert res.status_code == 200
    groups = res.json()
    assert len(groups) >= 5

    # 3. Create custom group
    res = client.post("/api/v1/rbac/groups", json={
        "name": "Field Operations Special Unit",
        "description": "Mobile unit for property inspections",
        "permission_ids": [data["permissions"][0]["id"]],
    })
    assert res.status_code == 200
    created_group = res.json()
    assert created_group["name"] == "Field Operations Special Unit"
    assert created_group["permissions_count"] == 1

    # 4. List users
    res = client.get("/api/v1/rbac/users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 1

    # 5. Update user RBAC profile
    target_user_id = users[0]["id"]
    res = client.put(f"/api/v1/rbac/users/{target_user_id}", json={
        "department": "Executive",
        "is_staff": True,
        "group_ids": [created_group["id"]],
    })
    assert res.status_code == 200
    updated_user = res.json()
    assert updated_user["department"] == "Executive"
    assert created_group["id"] in updated_user["group_ids"]

    # 6. Bulk action (activate/deactivate)
    res = client.post("/api/v1/rbac/users/bulk-action", json={
        "user_ids": [target_user_id],
        "action": "assign_group",
        "group_id": created_group["id"],
    })
    assert res.status_code == 200
    assert "affected" in res.json()
