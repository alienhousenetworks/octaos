import pytest
from unittest.mock import patch
from app.services.ai_gateway.routing import AIRoutingEngine
from app.services.ai_gateway.caching import PromptOptimizationEngine
from app.services.ai_gateway.cost_optimizer import AICostOptimizer
from app.services.ai_gateway.gateway import AIProviderGateway
from sqlalchemy.orm import Session
import os

def test_dynamic_routing_complexity():
    # High complexity should route to a reasoning model (like sonnet or gpt-4o) if available
    provider, model = AIRoutingEngine.selectProvider(
        configured_providers=["openai", "anthropic"],
        complexity="high",
        realtime=False,
        bulk=False
    )
    assert provider in ["anthropic", "openai"]
    assert "sonnet" in model or "gpt-4o" in model

def test_dynamic_routing_realtime():
    # Realtime should route to lowest latency provider
    provider, model = AIRoutingEngine.selectProvider(
        configured_providers=["openai", "anthropic", "gemini", "groq"],
        complexity="low",
        realtime=True,
        bulk=False
    )
    # Groq has low benchmark latencies in our registry
    assert provider == "groq"
    assert "llama" in model

def test_dynamic_routing_bulk():
    # Bulk should route to cheapest batch-enabled provider
    provider, model = AIRoutingEngine.selectProvider(
        configured_providers=["openai", "gemini"],
        complexity="low",
        realtime=False,
        bulk=True
    )
    # Gemini has lower cost than OpenAI in registry
    assert provider == "gemini"
    assert "flash" in model

def test_default_model_selection_llama_70b():
    from unittest.mock import patch
    from app.core.config import settings
    with patch.object(settings, "DEFAULT_AI_PROVIDER", "openrouter"), patch.object(settings, "DEFAULT_AI_MODEL", "meta-llama/llama-3.3-70b-instruct"):
        provider, model = AIRoutingEngine.selectProvider(
            configured_providers=["openrouter", "openai", "anthropic"],
            complexity="medium",
            realtime=False,
            bulk=False
        )
        assert provider == "openrouter"
        assert model == "meta-llama/llama-3.3-70b-instruct"

    with patch.object(settings, "DEFAULT_AI_PROVIDER", "nvidia"), patch.object(settings, "DEFAULT_AI_MODEL", "meta/llama-3.3-70b-instruct"):
        provider_nv, model_nv = AIRoutingEngine.selectProvider(
            configured_providers=["nvidia", "openrouter"],
            complexity="medium",
            realtime=False,
            bulk=False
        )
        assert provider_nv == "nvidia"
        assert model_nv == "meta/llama-3.3-70b-instruct"

def test_prompt_caching_hashing():
    prompt = "Generate a daily special post for a restaurant."
    sys_prompt = "You are a marketing AI."
    
    hash1 = PromptOptimizationEngine.hashPrompt(prompt, sys_prompt)
    hash2 = PromptOptimizationEngine.hashPrompt(prompt, sys_prompt)
    hash3 = PromptOptimizationEngine.hashPrompt(prompt, "Different system prompt")
    
    assert hash1 == hash2
    assert hash1 != hash3

def test_prompt_caching_fallback():
    prompt = "Test local caching"
    sys_prompt = "System prompt"
    
    PromptOptimizationEngine.cachePrompt(prompt, sys_prompt, "Cached Reply", 10, 15, "mock", "mock-model")
    cached = PromptOptimizationEngine.retrievePrompt(prompt, sys_prompt)
    
    assert cached is not None
    assert cached["content"] == "Cached Reply"
    assert cached["provider"] == "mock"
    assert cached["model"] == "mock-model"

def test_cost_optimizer_estimate():
    prompt = "Estimate this task cost"
    sys_prompt = "Preamble code text"
    
    cost = AICostOptimizer.estimateCost(prompt, "gpt-4o", sys_prompt, "openai")
    assert cost > 0.0

def test_cost_optimizer_actual():
    # Test local cache hit saves 100%
    result_cache = AICostOptimizer.calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        cache_hit=True
    )
    assert result_cache["cost"] == 0.0
    assert result_cache["savings"] > 0.0

    # Test normal pricing calculation
    result_normal = AICostOptimizer.calculate_actual_cost(
        provider="openai",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        cache_hit=False
    )
    # gpt-4o cost: $5/1M input, $15/1M output
    # Input: 1000 * 5.0 / 1,000,000 = 0.005
    # Output: 500 * 15.0 / 1,000,000 = 0.0075
    # Total: 0.0125
    assert pytest.approx(result_normal["cost"]) == 0.0125
    assert result_normal["savings"] == 0.0

@pytest.mark.asyncio
async def test_gateway_failover_sequence(db_session=None):
    gateway = AIProviderGateway()
    # With no credentials configured and mock adapter removed,
    # the gateway must raise a clear ValueError directing the user to configure keys.
    from unittest.mock import MagicMock
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.all.return_value = [] # no credentials configured
    db.query.return_value.filter.return_value.first.return_value = None
    gateway._get_configured_providers = MagicMock(return_value=[])

    with pytest.raises(ValueError) as exc_info:
        await gateway.executeRequest(
            db=db,
            tenant_id="test-tenant",
            prompt="Test prompt",
            provider="openai",
            model="gpt-4o"
        )
    assert "API key" in str(exc_info.value) or "provider" in str(exc_info.value).lower()

@pytest.mark.asyncio
@patch("app.services.ai_gateway.ai_gateway.executeCached")
async def test_llm_gateway_knowledge_injection(mock_execute_cached):
    from app.services.llm_gateway import LLMGateway
    from app.models.agents import KnowledgeDocument
    from unittest.mock import MagicMock, patch
    
    mock_db = MagicMock(spec=Session)
    mock_doc = MagicMock(spec=KnowledgeDocument)
    mock_doc.doc_type = "Standard Operating Procedure"
    mock_doc.department = "Marketing"
    mock_doc.content = "Always use brand colors."
    
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [mock_doc]
    
    gateway = LLMGateway(mock_db, "test-tenant-id")
    mock_execute_cached.return_value = "Mock response"
    
    response = await gateway.complete(
        prompt="Create a marketing campaign post for Instagram",
        system_prompt="You are a creative writer."
    )
    
    assert mock_execute_cached.called
    kwargs = mock_execute_cached.call_args.kwargs
    
    assert "You are a creative writer." in kwargs["system_prompt"]
    assert "Always use brand colors." in kwargs["system_prompt"]
    assert "Standard Operating Procedure" in kwargs["system_prompt"]


@pytest.mark.asyncio
async def test_openrouter_adapter_execution():
    from app.services.ai_gateway.adapters import OpenRouterAdapter
    from unittest.mock import AsyncMock, MagicMock
    import httpx

    adapter = OpenRouterAdapter(api_key="sk-or-v1-testkey123456789")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from OpenRouter"}}],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "prompt_tokens_details": {"cached_tokens": 4}
        }
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        res = await adapter.execute_request("Hi", "google/gemini-2.5-flash", system_prompt="You are helpful")
        assert res["content"] == "Hello from OpenRouter"
        assert res["input_tokens"] == 12
        assert res["output_tokens"] == 8
        assert res["cached_tokens"] == 4


@pytest.mark.asyncio
async def test_together_adapter_execution():
    from app.services.ai_gateway.adapters import TogetherAdapter
    from unittest.mock import AsyncMock, MagicMock

    adapter = TogetherAdapter(api_key="together-test-key-12345678")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from Together AI"}}],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 15
        }
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        res = await adapter.execute_request("Hi", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
        assert res["content"] == "Hello from Together AI"
        assert res["input_tokens"] == 20
        assert res["output_tokens"] == 15


def test_get_provider_models_dynamic_env():
    from app.services.ai_gateway.routing import get_provider_models
    from app.core.config import settings

    original_or_models = settings.OPENROUTER_MODELS
    settings.OPENROUTER_MODELS = "custom/test-model-1,custom/test-model-2"
    try:
        models = get_provider_models("openrouter")
        model_names = [m["model"] for m in models]
        assert "google/gemini-2.5-flash" in model_names
        assert "custom/test-model-1" in model_names
        assert "custom/test-model-2" in model_names
    finally:
        settings.OPENROUTER_MODELS = original_or_models


def test_inbuilt_vs_byok_mode():
    from app.services.ai_gateway.gateway import AIProviderGateway
    from app.models.base import APICredential
    from unittest.mock import MagicMock
    from app.core.config import settings

    db = MagicMock(spec=Session)
    gateway = AIProviderGateway()

    # 1. Test Inbuilt mode returns server env key
    original_or_key = settings.OPENROUTER_API_KEY
    settings.OPENROUTER_API_KEY = "server-openrouter-key"
    try:
        # Mock mode as inbuilt
        db.query.return_value.filter.return_value.first.return_value = None
        key = gateway._get_api_key(db, tenant_id="tenant-abc", provider="openrouter")
        assert key == "server-openrouter-key"

        # 2. Test BYOK mode returns tenant key
        mock_ai_mode = MagicMock(provider="ai_mode", settings={"mode": "byok"})
        mock_cred = MagicMock(provider="openrouter", encrypted_key="mock_enc")
        
        def mock_query_filter(*args, **kwargs):
            m = MagicMock()
            # If query is for ai_mode
            def mock_first():
                return mock_ai_mode
            m.first = mock_first
            return m

        with patch("app.services.ai_gateway.gateway.decrypt_api_key", return_value="decrypted-user-key"):
            db.query.return_value.filter.side_effect = [
                MagicMock(first=lambda: mock_ai_mode),
                MagicMock(first=lambda: mock_cred)
            ]
            key_byok = gateway._get_api_key(db, tenant_id="tenant-abc", provider="openrouter")
            assert key_byok == "decrypted-user-key"
    finally:
        settings.OPENROUTER_API_KEY = original_or_key


def test_configured_providers_ignores_non_ai_credentials():
    from app.services.ai_gateway.gateway import AIProviderGateway
    from app.models.base import APICredential
    from unittest.mock import MagicMock

    db = MagicMock(spec=Session)
    gateway = AIProviderGateway()

    # Simulate tenant having credentials for 'sales', 'smtp', and 'anthropic'
    cred_sales = MagicMock(provider="sales", encrypted_key="enc1")
    cred_smtp = MagicMock(provider="smtp", encrypted_key="enc2")
    cred_anthropic = MagicMock(provider="anthropic", encrypted_key="enc3")

    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [cred_sales, cred_smtp, cred_anthropic]
    mock_query.filter.return_value.first.return_value = None
    db.query.return_value = mock_query

    configured = gateway._get_configured_providers(db, tenant_id="tenant-123")
    assert "anthropic" in configured
    assert "sales" not in configured
    assert "smtp" not in configured


@pytest.mark.asyncio
async def test_per_provider_circuit_breaker_failover():
    from app.services.ai_gateway.gateway import AIProviderGateway
    from app.core.resilience import get_llm_breaker
    from unittest.mock import MagicMock, AsyncMock, patch

    gateway = AIProviderGateway()
    db = MagicMock(spec=Session)

    # Trip the anthropic breaker manually
    anthropic_breaker = get_llm_breaker("anthropic")
    # Simulate breaker being open
    anthropic_breaker.half_open()
    try:
        # Trip it to open state
        for _ in range(5):
            try:
                with anthropic_breaker.calling():
                    raise RuntimeError("Anthropic outage")
            except Exception:
                pass
    except Exception:
        pass

    # Verify anthropic breaker is open
    assert anthropic_breaker.current_state == "open"
    # Verify openrouter breaker is closed
    or_breaker = get_llm_breaker("openrouter")
    assert or_breaker.current_state == "closed"

    # Gateway configured with anthropic and openrouter
    with patch.object(gateway, "_get_configured_providers", return_value=["anthropic", "openrouter"]):
        with patch.object(gateway, "_get_api_key", return_value="dummy-key"):
            mock_adapter = MagicMock()
            mock_adapter.execute_request = AsyncMock(return_value={
                "content": "Failover success from OpenRouter",
                "input_tokens": 10,
                "output_tokens": 20,
            })
            with patch.object(gateway, "_get_adapter", return_value=mock_adapter):
                result = await gateway.executeRequest(
                    db=db,
                    tenant_id="tenant-123",
                    prompt="Hello",
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                )
                assert result == "Failover success from OpenRouter"


