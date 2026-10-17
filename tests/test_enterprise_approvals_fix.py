import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.api import deps
from app.models.base import User, Tenant
from app.models.enterprise import ApprovalRequest
from app.models.verticals import ContentPost

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_tenant_id():
    return "test-tenant-approvals"


def override_get_current_user():
    return User(
        id="test-user-admin",
        email="admin@octaos.com",
        tenant_id="test-tenant-approvals",
        role="admin",
        is_active=True,
    )


app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_tenant_id] = override_get_current_tenant_id
app.dependency_overrides[deps.get_current_user] = override_get_current_user

client = TestClient(app)


def setup_data():
    db = TestingSessionLocal()
    # Create tenant
    t = db.query(Tenant).filter_by(id="test-tenant-approvals").first()
    if not t:
        t = Tenant(id="test-tenant-approvals", name="Test Org")
        db.add(t)

    # Create content post
    post = ContentPost(
        id="post-test-123",
        tenant_id="test-tenant-approvals",
        platform="linkedin",
        content="Exciting product release today!",
        status="draft",
        approval_status="pending",
    )
    db.add(post)

    # Create approval request
    req = ApprovalRequest(
        id="appr-test-123",
        tenant_id="test-tenant-approvals",
        action_type="public_post",
        channel="linkedin",
        agent_name="Marketing AI",
        resource_type="post",
        resource_id="post-test-123",
        title="Approve LinkedIn Launch Post",
        payload={"post_id": "post-test-123", "content": "Exciting product release today!"},
        confidence=0.92,
        status="pending",
        policy_reason="Review required for public LinkedIn post",
    )
    db.add(req)
    db.commit()
    db.close()


def test_approvals_metrics_and_list():
    setup_data()
    # 1. Test metrics
    res_m = client.get("/api/v1/enterprise/approvals/metrics")
    assert res_m.status_code == 200
    metrics = res_m.json()
    assert "pending" in metrics
    assert metrics["pending"] >= 1

    # 2. Test list approvals
    res_l = client.get("/api/v1/enterprise/approvals?status=pending")
    assert res_l.status_code == 200
    items = res_l.json()
    assert len(items) >= 1
    found = [i for i in items if i["id"] == "appr-test-123"]
    assert len(found) == 1
    assert found[0]["title"] == "Approve LinkedIn Launch Post"
    assert found[0]["status"] == "pending"


def test_approval_review_side_effects():
    # 3. Test approving the request
    res_r = client.post(
        "/api/v1/enterprise/approvals/appr-test-123/review",
        json={"approve": True, "note": "Approved via automated test"},
    )
    assert res_r.status_code == 200
    data = res_r.json()
    assert data["status"] == "approved"

    # Verify underlying ContentPost status was updated
    db = TestingSessionLocal()
    post = db.query(ContentPost).filter_by(id="post-test-123").first()
    assert post is not None
    assert post.approval_status == "approved"
    db.close()
