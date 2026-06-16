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
    # With no credentials configured and mock adapter removed,
    # the gateway must raise a clear ValueError directing the user to configure keys.
    from unittest.mock import MagicMock
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.all.return_value = [] # no credentials configured
    db.query.return_value.filter.return_value.first.return_value = None

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
