import pytest
from app.services.agents.tools import tool_registry
from app.services.agents.section_registry import section_registry
from app.db.session import SessionLocal
from app.models.base import Tenant
from app.models.verticals import ContentPost
import uuid


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_tenant(db_session):
    tenant = db_session.query(Tenant).first()
    if not tenant:
        tenant = Tenant(id=f"test-tenant-{uuid.uuid4().hex[:6]}", name="Test Tenant")
        db_session.add(tenant)
        db_session.commit()
    return tenant


def test_marketing_tools_registered():
    """Verify post.create and post.publish are registered in tool_registry."""
    post_create = tool_registry.get("post.create")
    assert post_create is not None
    assert post_create.name == "post.create"
    assert "platform" in post_create.input_schema["properties"]
    assert "caption" in post_create.input_schema["properties"]
    assert "image_prompt" in post_create.input_schema["properties"]

    post_publish = tool_registry.get("post.publish")
    assert post_publish is not None
    assert post_publish.name == "post.publish"
    assert post_publish.approval_required is True


@pytest.mark.asyncio
async def test_marketing_section_adapter_post_create_and_publish(db_session, test_tenant):
    """Verify post.create creates ContentPost with image, caption, hashtags, and steps."""
    adapter = section_registry.get_adapter("marketing")
    assert adapter is not None

    payload = {
        "platform": "instagram",
        "caption": "Diwali isn't just about lights; it's about illuminating your home with love and warmth. Explore Alienhouse festive collection.",
        "hashtags": ["#AlienhouseDiwali", "#IlluminateYourSpace", "#DiwaliVibes"],
        "image_prompt": "Festive Diwali living room with Alienhouse warm wooden lounge chair surrounded by diyas and glowing fairy lights",
        "generate_image": True,
    }

    res = await adapter.execute_action("post.create", test_tenant.id, payload, db_session)

    assert res["success"] is True
    assert res["post_id"] is not None
    assert res["platform"] == "instagram"
    assert "Diwali" in res["caption"]
    assert len(res["hashtags"]) >= 3
    assert res["image_url"] is not None
    assert len(res["steps"]) >= 4

    # Verify database persistence
    saved = db_session.query(ContentPost).filter_by(id=res["post_id"]).first()
    assert saved is not None
    assert saved.status == "draft"
    assert saved.approval_status == "pending"
    assert saved.image_url == res["image_url"]

    # Test publishing
    pub_res = await adapter.execute_action("post.publish", test_tenant.id, {"post_id": saved.id}, db_session)
    assert pub_res["success"] is True
    assert pub_res["status"] == "published"

    db_session.refresh(saved)
    assert saved.status == "published"
