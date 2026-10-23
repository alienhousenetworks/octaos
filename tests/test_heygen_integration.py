"""Unit and integration tests for HeyGen Video AI integration in OctaOS."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base, User, APICredential, Tenant
from app.models.verticals import BusinessProfile, ContentPost, GenerationJob
from app.services.integrations.heygen import (
    HeyGenClient,
    HeyGenError,
    get_heygen_client,
)
from app.services.ai_gateway.providers.base import VideoReq, JobHandle
from app.services.ai_gateway.providers.heygen import HeyGenAdapter
from app.services.ai_gateway.registry import ModelRegistry
from app.api import deps
from app.core.security import encrypt_api_key


@pytest.fixture(scope="module")
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    tenant = Tenant(id="tenant-test-heygen", name="Acme AI Corp")
    session.add(tenant)
    user = User(
        id="user-test-heygen",
        tenant_id="tenant-test-heygen",
        email="marketer@acme.ai",
        hashed_password="mock",
        is_active=True,
        is_verified=True,
        role="admin",
    )
    session.add(user)

    profile = BusinessProfile(
        tenant_id="tenant-test-heygen",
        company_name="Acme Enterprise AI",
        industry="Enterprise Operations",
        usp="Deterministic autonomous agent orchestrations",
    )
    session.add(profile)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def mock_user():
    return User(
        id="user-test-heygen",
        tenant_id="tenant-test-heygen",
        email="marketer@acme.ai",
        is_active=True,
        is_verified=True,
        role="admin",
    )


# ─── 1. CLIENT & ERROR HANDLING TESTS ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_heygen_client_missing_key():
    client = HeyGenClient(api_key="")
    with pytest.raises(HeyGenError) as exc_info:
        await client.request("GET", "/v3/users/me")
    assert exc_info.value.status_code == 401
    assert "missing or empty" in exc_info.value.message


@pytest.mark.asyncio
async def test_heygen_client_validate_key_success():
    client = HeyGenClient(api_key="valid-mock-key")
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"data": {"username": "acme_ai", "remaining_quota": 50}}
        result = await client.validate_key()
        assert result["valid"] is True
        assert result["user"]["username"] == "acme_ai"


@pytest.mark.asyncio
async def test_heygen_client_create_video_agent():
    client = HeyGenClient(api_key="valid-mock-key")
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {
            "data": {
                "session_id": "sess_123456",
                "video_id": "vid_abcdef",
                "status": "processing",
            }
        }
        res = await client.create_video_agent("Test brand prompt")
        assert res["session_id"] == "sess_123456"
        assert res["video_id"] == "vid_abcdef"


@pytest.mark.asyncio
async def test_heygen_client_get_video_url():
    client = HeyGenClient(api_key="valid-mock-key")
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {
            "data": {
                "video_id": "vid_abcdef",
                "status": "completed",
                "video_url": "https://resource.heygen.com/videos/vid_abcdef.mp4",
            }
        }
        res = await client.get_video("vid_abcdef")
        assert res["status"] == "completed"
        assert "resource.heygen.com" in res["video_url"]


# ─── 2. MULTI-TENANT CREDENTIAL RESOLUTION ─────────────────────────────────────

def test_get_heygen_client_from_db(test_db):
    cred = APICredential(
        tenant_id="tenant-test-heygen",
        provider="heygen",
        encrypted_key=encrypt_api_key("tenant-heygen-secret-key"),
    )
    test_db.add(cred)
    test_db.commit()

    client = get_heygen_client(test_db, "tenant-test-heygen")
    assert client.api_key == "tenant-heygen-secret-key"


def test_get_heygen_client_fallback_to_settings(test_db):
    with patch("app.services.integrations.heygen.settings.HEYGEN_API_KEY", "system-env-heygen-key"):
        client = get_heygen_client(test_db, "tenant-without-key")
        assert client.api_key == "system-env-heygen-key"


# ─── 3. AI GATEWAY ADAPTER & REGISTRY ──────────────────────────────────────────

def test_registry_contains_heygen():
    reg = ModelRegistry.get_instance()
    adapter = reg.get_adapter("heygen")
    assert adapter is not None
    assert adapter.name == "heygen"


@pytest.mark.asyncio
async def test_heygen_adapter_submit_and_poll():
    adapter = HeyGenAdapter()
    req = VideoReq(
        model="heygen/v3-video-agent",
        prompt="A professional spokesperson in modern corporate setting delivering Q3 update.",
        aspect_ratio="16:9",
    )

    with patch("app.services.ai_gateway.providers.heygen.HeyGenClient.create_video_agent", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {"session_id": "sess_999", "status": "processing"}
        handle = await adapter.submit_video(req, api_key="test-key")
        assert handle.job_id == "sess_999"
        assert handle.provider == "heygen"

    with patch("app.services.ai_gateway.providers.heygen.HeyGenClient.get_video_agent_session", new_callable=AsyncMock) as mock_poll:
        mock_poll.return_value = {
            "status": "completed",
            "video": {
                "video_id": "vid_999",
                "video_url": "https://resource.heygen.com/videos/output.mp4",
                "status": "completed",
            },
        }
        status = await adapter.poll_video(handle, api_key="test-key")
        assert status.status == "completed"
        assert status.result_url == "https://resource.heygen.com/videos/output.mp4"


# ─── 4. FASTAPI ENDPOINTS & TENANT AUTH ────────────────────────────────────────

def test_heygen_health_endpoint(test_db, mock_user):
    def override_get_db():
        yield test_db

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-test-heygen"
    app.dependency_overrides[deps.get_current_user] = lambda: mock_user

    client = TestClient(app)
    with patch("app.services.integrations.heygen.HeyGenClient.validate_key", new_callable=AsyncMock) as mock_val:
        mock_val.return_value = {"valid": True, "user": {"id": "hg_1", "email": "test@heygen.com"}}
        resp = client.get("/api/v1/integrations/heygen/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "heygen"
        assert data["connected"] is True

    app.dependency_overrides.clear()


def test_heygen_create_video_endpoint(test_db, mock_user):
    def override_get_db():
        yield test_db

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-test-heygen"
    app.dependency_overrides[deps.get_current_user] = lambda: mock_user

    # Add dummy post
    post = ContentPost(
        id="post-test-1",
        tenant_id="tenant-test-heygen",
        platform="linkedin",
        content="Exciting updates on autonomous operations.",
    )
    test_db.add(post)
    test_db.commit()

    client = TestClient(app)
    with patch("app.services.integrations.heygen.HeyGenClient.create_video_agent", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "session_id": "sess_endpoint_123",
            "video_id": "vid_endpoint_123",
            "status": "submitted",
        }
        resp = client.post(
            "/api/v1/integrations/heygen/videos",
            json={
                "prompt": "Create an executive product explainer featuring our enterprise agent workflows.",
                "post_id": "post-test-1",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess_endpoint_123"
        assert data["job_id"] is not None

        # Verify GenerationJob was created in DB
        job = test_db.query(GenerationJob).filter(GenerationJob.id == data["job_id"]).first()
        assert job is not None
        assert job.provider == "heygen"
        assert job.kind == "video"

    app.dependency_overrides.clear()


# ─── 5. BRAND-PERSPECTIVE PROMPT SYNTHESIS ─────────────────────────────────────

def test_suggest_prompt_with_brand_perspective_for_heygen(test_db, mock_user):
    def override_get_db():
        yield test_db

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-test-heygen"
    app.dependency_overrides[deps.get_current_user] = lambda: mock_user

    client = TestClient(app)
    with patch("app.services.llm_gateway.LLMGateway.complete", new_callable=AsyncMock) as mock_complete:
        mock_complete.return_value = (
            "A poised Acme Enterprise AI spokesperson in sharp navy corporate attire, "
            "standing in a modern glass studio with subtle emerald lighting accents, "
            "delivering: 'Deterministic autonomous agent orchestrations are reshaping enterprise pipelines.'"
        )
        resp = client.post(
            "/api/v1/marketing/suggest-prompt",
            json={
                "content": "Why multi-agent systems will replace traditional RPA pipelines.",
                "media_type": "video",
                "provider": "heygen",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "spokesperson" in data["prompt"].lower() or "acme" in data["prompt"].lower()

        # Check prompt sent to LLM included company name and brand perspective
        call_args = mock_complete.call_args
        prompt_sent = call_args[1]["prompt"] if "prompt" in call_args[1] else call_args[0][0]
        assert "Acme Enterprise AI" in prompt_sent
        assert "BRAND PERSPECTIVE" in prompt_sent

    app.dependency_overrides.clear()
