import pytest
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

def test_prompt_caching_hashing():
    prompt = "Generate a daily special yelp post for a restaurant."
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
    # If all configured keys fail or are missing, it progress to local/mock fallback
    # Let's mock a tenant db session
    from unittest.mock import MagicMock
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.all.return_value = [] # no credentials configured
    db.query.return_value.filter.return_value.first.return_value = None
    
    # Executing request should succeed using the MockAdapter fallback
    response = await gateway.executeRequest(
        db=db,
        tenant_id="test-tenant",
        prompt="Test prompt",
        provider="openai",
        model="gpt-4o"
    )
    assert "mock" in response.lower()
