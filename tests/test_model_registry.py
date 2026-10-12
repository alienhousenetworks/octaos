"""Unit tests for Multimodal Model Registry, live validation, and fallback resolution."""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_gateway.registry import ModelRegistry
from app.services.ai_gateway.providers.base import ModelInfo, ModalityType


@pytest.fixture
def registry():
    return ModelRegistry.get_instance()


def test_registry_singleton(registry):
    assert registry is not None
    assert ModelRegistry.get_instance() is registry
    assert "openrouter" in registry.adapters
    assert "together" in registry.adapters


def test_load_curated_models(registry):
    curated = registry.load_curated_models()
    assert "text" in curated
    assert "image" in curated
    assert "video" in curated
    assert len(curated["text"]) >= 5
    assert len(curated["image"]) >= 5
    assert len(curated["video"]) >= 5

    # Check that Top 10 models are present
    slugs = [m["slug"] for m in curated["text"]]
    assert any("claude" in s for s in slugs)
    assert any("deepseek" in s for s in slugs)
    assert any("gpt-4o" in s for s in slugs)


@pytest.mark.asyncio
async def test_validate_model_no_key(registry):
    mock_db = AsyncMock()
    with patch.object(registry, "_get_api_key", return_value=""):
        res = await registry.validate_model(
            db=mock_db,
            tenant_id="test-tenant",
            provider="together",
            modality="image",
            model_slug="black-forest-labs/FLUX.1-dev",
        )
        assert res["status"] == "no_key"
        assert "API key" in res["message"]


@pytest.mark.asyncio
async def test_validate_model_available(registry):
    mock_db = AsyncMock()
    fake_catalog = [
        ModelInfo(
            provider="together",
            slug="black-forest-labs/FLUX.1-dev",
            display_name="FLUX.1 Dev",
            modalities=["text_to_image"],
            status="available",
        ),
        ModelInfo(
            provider="together",
            slug="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            display_name="Llama 3.3 70B",
            modalities=["text_to_text"],
            status="available",
        ),
    ]

    with patch.object(registry, "_get_api_key", return_value="dummy_key"), \
         patch.object(registry, "get_provider_catalog", return_value=fake_catalog):
        
        # Valid image model
        res = await registry.validate_model(
            db=mock_db,
            tenant_id="test-tenant",
            provider="together",
            modality="text_to_image",
            model_slug="black-forest-labs/FLUX.1-dev",
        )
        assert res["status"] == "available"

        # Incompatible modality (text model in image modality)
        res_incomp = await registry.validate_model(
            db=mock_db,
            tenant_id="test-tenant",
            provider="together",
            modality="text_to_image",
            model_slug="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        )
        assert res_incomp["status"] == "incompatible"
        assert "does not support text_to_image" in res_incomp["message"]

        # Not found with fuzzy match
        res_fuzzy = await registry.validate_model(
            db=mock_db,
            tenant_id="test-tenant",
            provider="together",
            modality="text_to_image",
            model_slug="black-forest-labs/FLUX.1-deev",
        )
        assert res_fuzzy["status"] == "not_found"
        assert "black-forest-labs/FLUX.1-dev" in res_fuzzy.get("suggestions", [])
