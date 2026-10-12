import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base, User, Tenant
from app.api.deps import get_db, get_current_tenant_id, get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_manual_post.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    tenant = Tenant(id="tenant-marketing-test", name="Marketing Co", subdomain="mkt-test")
    session.add(tenant)
    session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    def override_get_current_tenant_id():
        return "tenant-marketing-test"

    def override_get_current_user():
        return User(
            id="test-user-id",
            email="marketer@example.com",
            name="Test Marketer",
            tenant_id="tenant-marketing-test",
            role="admin",
            is_verified=True,
            is_active=True
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_current_tenant_id
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_manual_multi_post_schedule_mode(client):
    """Verify multi-platform scheduling sets status to scheduled and approval_status to approved."""
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    payload = {
        "platforms": ["linkedin", "facebook", "instagram"],
        "content": "Exciting launch news from our engineering team!",
        "tags": ["AI", "Innovation", "Launch"],
        "scheduled_at": future_time,
        "publish_mode": "schedule",
        "day": 2,
        "image_url": "https://example.com/asset.jpg"
    }

    res = client.post("/api/v1/marketing/posts/manual-multi", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) == 3

    platforms = [p["platform"] for p in data]
    assert "linkedin" in platforms
    assert "facebook" in platforms
    assert "instagram" in platforms

    for post in data:
        assert post["approval_status"] == "approved"
        assert post["status"] == "scheduled"
        assert post["image_url"] == "https://example.com/asset.jpg"
        assert "#AI" in post["content"]
        assert "#Innovation" in post["content"]
        assert "#Launch" in post["content"]
        assert post["learning_tags"] == ["AI", "Innovation", "Launch"]

def test_manual_multi_post_draft_mode(client):
    """Verify draft mode sets status to draft and approval_status to pending."""
    payload = {
        "platforms": ["linkedin", "twitter"],
        "content": "Draft idea for review before scheduling.",
        "tags": ["Ideas"],
        "publish_mode": "draft",
        "day": 1
    }

    res = client.post("/api/v1/marketing/posts/manual-multi", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) == 2

    for post in data:
        assert post["approval_status"] == "pending"
        assert post["status"] == "draft"
        assert "#Ideas" in post["content"]
