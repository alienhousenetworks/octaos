import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db, get_current_user, get_current_tenant_id
from app.models.base import Base, Tenant, User
from app.models.rooms import SectionRoom
from app.models.verticals import Candidate, ContentPost, Ticket
from app.models.deal_room import DealRoom


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rooms.db"
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
def test_setup(db):
    tenant = Tenant(id="tenant-alpha", name="Alpha Corp", subdomain="alpha")
    db.add(tenant)

    user_owner = User(
        id="usr-owner",
        tenant_id=tenant.id,
        email="owner@alpha.com",
        name="Alice Owner",
        hashed_password="hash",
        role="member",
        is_active=True,
    )
    user_member = User(
        id="usr-member",
        tenant_id=tenant.id,
        email="bob@alpha.com",
        name="Bob Member",
        hashed_password="hash",
        role="member",
        is_active=True,
    )
    user_admin = User(
        id="usr-admin",
        tenant_id=tenant.id,
        email="admin@alpha.com",
        name="Carol Admin",
        hashed_password="hash",
        role="admin",
        is_active=True,
    )
    db.add_all([user_owner, user_member, user_admin])
    db.commit()

    return {
        "tenant": tenant,
        "owner": user_owner,
        "member": user_member,
        "admin": user_admin,
    }


def test_section_room_crud_and_slug_collision(db, test_setup):
    """Test room creation, auto-slugification, unique collision suffixing, and patching."""
    owner = test_setup["owner"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_current_tenant_id] = lambda: owner.tenant_id

    client = TestClient(app)

    # 1. Create first room in HR
    res1 = client.post(
        "/api/v1/rooms/",
        json={
            "section": "hr",
            "name": "Senior Backend Engineer",
            "description": "Room for hiring Senior Backend Eng",
            "visibility": "internal_public",
            "data": {"role": "Senior Backend", "salary": "$150k"},
        },
    )
    assert res1.status_code == 201
    room1 = res1.json()
    assert room1["slug"] == "senior-backend-engineer"
    assert room1["created_by_user_id"] == owner.id
    assert room1["creator_name"] == "Alice Owner"
    assert room1["visibility"] == "internal_public"

    # 2. Create another room with the identical name in HR -> should get slug collision handled
    res2 = client.post(
        "/api/v1/rooms/",
        json={
            "section": "hr",
            "name": "Senior Backend Engineer",
            "visibility": "internal_public",
        },
    )
    assert res2.status_code == 201
    room2 = res2.json()
    assert room2["slug"] == "senior-backend-engineer-2"

    # 3. Verify slug endpoint
    res_slug = client.get("/api/v1/rooms/verify-slug?section=hr&slug=senior-backend-engineer")
    assert res_slug.status_code == 200
    assert res_slug.json()["available"] is False

    res_avail = client.get("/api/v1/rooms/verify-slug?section=hr&slug=brand-new-role")
    assert res_avail.status_code == 200
    assert res_avail.json()["available"] is True

    # 4. Patch room metadata
    patch_res = client.patch(
        f"/api/v1/rooms/{room1['id']}",
        json={"name": "Lead Backend Architect", "data": {"headcount": 2}},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["name"] == "Lead Backend Architect"
    assert updated["data"]["headcount"] == 2
    assert updated["data"]["role"] == "Senior Backend"

    app.dependency_overrides.clear()


def test_section_room_access_control(db, test_setup):
    """Test private room access restriction, staff sharing, and admin override."""
    owner = test_setup["owner"]
    member = test_setup["member"]
    admin = test_setup["admin"]

    # 1. Owner creates a private room
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_current_tenant_id] = lambda: owner.tenant_id

    client = TestClient(app)

    create_res = client.post(
        "/api/v1/rooms/",
        json={
            "section": "marketing",
            "name": "Secret Project Launch",
            "visibility": "private",
            "description": "Restricted launch room",
        },
    )
    assert create_res.status_code == 201
    room = create_res.json()
    room_id = room["id"]
    slug = room["slug"]

    # 2. Member tries to view/fetch this private room -> should be 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: member
    app.dependency_overrides[get_current_tenant_id] = lambda: member.tenant_id

    res_member = client.get(f"/api/v1/rooms/marketing/{slug}")
    assert res_member.status_code == 403

    # Member lists marketing rooms -> private room should not be included
    list_res = client.get("/api/v1/rooms/?section=marketing")
    assert list_res.status_code == 200
    slugs = [r["slug"] for r in list_res.json()]
    assert slug not in slugs

    # 3. Owner shares room with Member as editor
    app.dependency_overrides[get_current_user] = lambda: owner
    share_res = client.put(
        f"/api/v1/rooms/{room_id}/access",
        json={
            "visibility": "private",
            "access_list": [
                {
                    "user_id": member.id,
                    "name": member.name,
                    "email": member.email,
                    "role": "editor",
                }
            ],
        },
    )
    assert share_res.status_code == 200

    # 4. Now Member accesses the private room -> should be 200 OK
    app.dependency_overrides[get_current_user] = lambda: member
    res_member_ok = client.get(f"/api/v1/rooms/marketing/{slug}")
    assert res_member_ok.status_code == 200
    assert res_member_ok.json()["slug"] == slug

    # 5. Admin can always access the room (Admin override)
    app.dependency_overrides[get_current_user] = lambda: admin
    res_admin = client.get(f"/api/v1/rooms/marketing/{slug}")
    assert res_admin.status_code == 200

    app.dependency_overrides.clear()


def test_auto_seed_default_room_and_counts(db, test_setup):
    """Test that listing an empty section automatically creates a Default Room and calculates counts."""
    owner = test_setup["owner"]
    tenant_id = owner.tenant_id

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    client = TestClient(app)

    # Pre-seed unassigned Candidate in HR
    cand = Candidate(
        tenant_id=tenant_id,
        name="Test Dev",
        email="dev@test.com",
        role="Senior Developer",
        status="sourced",
    )
    db.add(cand)
    db.commit()

    # List HR rooms -> should auto-seed Default Room and backfill candidate
    res = client.get("/api/v1/rooms/?section=hr")
    assert res.status_code == 200
    rooms = res.json()
    assert len(rooms) >= 1
    default_room = next(r for r in rooms if r["slug"] == "default")
    assert default_room["name"] == "General HR"
    assert default_room["counts"]["total"] >= 1

    app.dependency_overrides.clear()


def test_sales_section_rooms_and_lead_scoping(db, test_setup):
    """Test Sales section rooms auto-seeding, lead creation and scoped lead filtering."""
    from app.models.verticals import Lead
    owner = test_setup["owner"]
    tenant_id = owner.tenant_id

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: owner
    app.dependency_overrides[get_current_tenant_id] = lambda: tenant_id

    client = TestClient(app)

    # 1. List Sales rooms -> should auto-seed Default Room for Sales
    res = client.get("/api/v1/rooms/?section=sales")
    assert res.status_code == 200
    rooms = res.json()
    assert len(rooms) >= 1
    sales_default = next(r for r in rooms if r["slug"] == "default")
    assert sales_default["name"] == "General SALES"

    # 2. Create custom Sales room
    res_custom = client.post(
        "/api/v1/rooms/",
        json={
            "section": "sales",
            "name": "Enterprise Q3 Deals",
            "description": "Room for enterprise deals",
            "visibility": "internal_public",
        },
    )
    assert res_custom.status_code == 201
    custom_room = res_custom.json()
    assert custom_room["slug"] == "enterprise-q3-deals"

    # 3. Add leads: one in default, one in enterprise room
    lead1 = Lead(
        tenant_id=tenant_id,
        name="John Enterprise",
        email="john@ent.com",
        company="Acme BigCorp",
        room_id=custom_room["id"],
        status="captured",
    )
    lead2 = Lead(
        tenant_id=tenant_id,
        name="Jane Regular",
        email="jane@reg.com",
        company="Regular Co",
        room_id=sales_default["id"],
        status="captured",
    )
    db.add_all([lead1, lead2])
    db.commit()

    # 4. Filter leads by room_slug
    res_leads_scoped = client.get(f"/api/v1/leads/?room_slug={custom_room['slug']}")
    assert res_leads_scoped.status_code == 200
    leads_custom = res_leads_scoped.json()
    assert len(leads_custom) == 1
    assert leads_custom[0]["name"] == "John Enterprise"

    # 5. Verify room counts reflect the lead
    res_count = client.get("/api/v1/rooms/?section=sales")
    assert res_count.status_code == 200
    rooms_updated = res_count.json()
    r = next(r for r in rooms_updated if r["slug"] == "enterprise-q3-deals")
    assert r["counts"]["total"] >= 1

    app.dependency_overrides.clear()

