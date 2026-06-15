import time
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.base import APICredential, ProviderUsage, AIBatchJob
from app.core.config import settings
from app.core.security import decrypt_api_key

from app.services.ai_gateway.adapters import (
    BaseProviderAdapter, OpenAIAdapter, AnthropicAdapter, GeminiAdapter,
    GrokAdapter, GroqAdapter, MistralAdapter, CohereAdapter, LocalAdapter, MockAdapter
)
from app.services.ai_gateway.caching import PromptOptimizationEngine
from app.services.ai_gateway.routing import AIRoutingEngine
from app.services.ai_gateway.cost_optimizer import AICostOptimizer
from app.services.ai_gateway.batching import BatchExecutionEngine

logger = logging.getLogger(__name__)

class AIProviderGateway:
    def __init__(self):
        self.adapters: Dict[str, BaseProviderAdapter] = {}
        self._initialize_adapters()

    def _initialize_adapters(self):
        # We will dynamically instantiate adapters with keys in executeRequest
        pass

    def _get_adapter(self, provider: str, api_key: str) -> BaseProviderAdapter:
        # Returns or instantiates the adapter for the given provider
        provider_lower = provider.lower()
        if provider_lower == "openai":
            return OpenAIAdapter(api_key=api_key)
        elif provider_lower == "anthropic":
            return AnthropicAdapter(api_key=api_key)
        elif provider_lower == "gemini":
            return GeminiAdapter(api_key=api_key)
        elif provider_lower == "grok":
            return GrokAdapter(api_key=api_key)
        elif provider_lower == "groq":
            return GroqAdapter(api_key=api_key)
        elif provider_lower == "mistral":
            return MistralAdapter(api_key=api_key)
        elif provider_lower == "cohere":
            return CohereAdapter(api_key=api_key)
        elif provider_lower == "local":
            return LocalAdapter(api_key=api_key)
        else:
            raise ValueError(f"Provider '{provider}' is not supported. Please configure a valid API key.")

    def registerProvider(self, provider_name: str, adapter: BaseProviderAdapter) -> None:
        self.adapters[provider_name.lower()] = adapter

    def selectProvider(
        self,
        configured_providers: List[str],
        complexity: str = "medium",
        realtime: bool = False,
        bulk: bool = False
    ) -> tuple:
        return AIRoutingEngine.selectProvider(configured_providers, complexity, realtime, bulk)

    def _get_api_key(self, db: Session, tenant_id: str, provider: str) -> str:
        # Lookup key from database APICredential
        if tenant_id:
            cred = db.query(APICredential).filter(
                APICredential.tenant_id == tenant_id,
                APICredential.provider == provider
            ).first()
            if cred:
                return decrypt_api_key(cred.encrypted_key)
            return ""
        
        # System settings keys fallback
        if provider == "anthropic":
            return settings.SHARED_CLAUDE_KEY or settings.ANTHROPIC_API_KEY or ""
        elif provider == "openai":
            return settings.OPENAI_API_KEY or ""
        elif provider == "gemini":
            import os
            return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        elif provider == "grok":
            import os
            return os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or ""
        elif provider == "groq":
            import os
            return os.getenv("GROQ_API_KEY") or ""
        elif provider == "mistral":
            import os
            return os.getenv("MISTRAL_API_KEY") or ""
        elif provider == "cohere":
            import os
            return os.getenv("COHERE_API_KEY") or ""
        return ""

    def _get_configured_providers(self, db: Session, tenant_id: str) -> List[str]:
        if tenant_id:
            creds = db.query(APICredential).filter(APICredential.tenant_id == tenant_id).all()
            return list(set([c.provider.lower() for c in creds if c.encrypted_key]))
            
        configured = []
        
        # Check system/env config too
        if settings.ANTHROPIC_API_KEY or settings.SHARED_CLAUDE_KEY:
            configured.append("anthropic")
        if settings.OPENAI_API_KEY:
            configured.append("openai")
            
        import os
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            configured.append("gemini")
        if os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"):
            configured.append("grok")
        if os.getenv("GROQ_API_KEY"):
            configured.append("groq")
        if os.getenv("MISTRAL_API_KEY"):
            configured.append("mistral")
        if os.getenv("COHERE_API_KEY"):
            configured.append("cohere")
            
        return list(set(configured))

    async def executeRequest(
        self,
        db: Session,
        tenant_id: str,
        prompt: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        task_type: str = "general",
        realtime: bool = False,
        complexity: str = "medium",
        bulk: bool = False,
        **kwargs
    ) -> str:
        """
        Main execution point for standard completions.
        Handles: Dynamic Routing, Multi-Provider Failover, Cost tracking, and DB logging.
        """
        configured = self._get_configured_providers(db, tenant_id)
        if not configured:
            req_prov = provider or "anthropic"
            raise ValueError(f"No API key configured for provider '{req_prov}'. Please configure your API key under Platform Setup -> API Settings.")
        
        # 1. Routing Decision
        if not provider or not model:
            provider, model = self.selectProvider(configured, complexity, realtime, bulk)
            
        # Keep track of tried providers for failover chain
        tried_providers = []
        current_provider = provider
        current_model = model
        
        # Default chain of fallback providers (exclude mock/local)
        fallback_chain = ["openai", "anthropic", "gemini", "grok", "groq"]
        
        while current_provider:
            tried_providers.append(current_provider)
            api_key = self._get_api_key(db, tenant_id, current_provider)
            
            # Determine failover source if applicable
            failover_from = tried_providers[-2] if len(tried_providers) > 1 else None
            
            # If no API key, trigger failover to next configured provider or raise error
            if not api_key:
                logger.warning(f"Provider {current_provider} API key missing. Failover triggered.")
                
                # Log failed attempt
                usage_failed = ProviderUsage(
                    tenant_id=tenant_id,
                    provider=current_provider,
                    model=current_model,
                    input_tokens=0,
                    output_tokens=0,
                    cost=0.0,
                    latency=0.0,
                    status="failed",
                    task_type=task_type,
                    error_message="API key missing",
                    failover_from=failover_from
                )
                db.add(usage_failed)
                db.commit()
                
                # Find other configured providers not tried yet
                configured_remaining = [p for p in configured if p not in tried_providers]
                if not configured_remaining:
                    raise ValueError(f"No API key configured for provider '{current_provider}'. Please configure your API key under Platform Setup -> API Settings.")
                
                current_provider = configured_remaining[0]
                if current_provider == "openai":
                    current_model = "gpt-4o-mini"
                elif current_provider == "anthropic":
                    current_model = "claude-haiku-4-5-20251001"
                elif current_provider == "gemini":
                    current_model = "gemini-2.5-flash"
                elif current_provider == "grok":
                    current_model = "grok-2"
                elif current_provider == "groq":
                    current_model = "llama-3.1-8b-instant"
                else:
                    current_model = "default-model"
                continue
                
            try:
                start_time = time.time()
                adapter = self._get_adapter(current_provider, api_key)
                
                logger.info(f"Executing request via provider={current_provider}, model={current_model}")
                response_data = await adapter.execute_request(
                    prompt=prompt,
                    model=current_model,
                    system_prompt=system_prompt,
                    **kwargs
                )
                latency = time.time() - start_time
                
                content = response_data["content"]
                input_tokens = response_data["input_tokens"]
                output_tokens = response_data["output_tokens"]
                cached_tokens = response_data.get("cached_tokens", 0)
                
                # Calculate actual cost and savings
                cost_calc = AICostOptimizer.calculate_actual_cost(
                    provider=current_provider,
                    model=current_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_tokens=cached_tokens,
                    is_batch=bulk,
                    cache_hit=False
                )
                
                # Log successful usage
                usage = ProviderUsage(
                    tenant_id=tenant_id,
                    provider=current_provider,
                    model=current_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost_calc["cost"],
                    latency=latency,
                    status="success" if not failover_from else "failover",
                    task_type=task_type,
                    cached_tokens=cached_tokens,
                    is_batch=bulk,
                    failover_from=failover_from
                )
                db.add(usage)
                db.commit()
                
                # Auto-cache locally if provider lacks native caching
                PromptOptimizationEngine.fallbackLocalCaching(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response_text=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    provider=current_provider,
                    model=current_model
                )
                
                return content
                
            except Exception as e:
                latency = time.time() - start_time
                logger.error(f"Execution failed on {current_provider}: {e}. Activating failover.")
                
                # Log failed attempt
                usage_failed = ProviderUsage(
                    tenant_id=tenant_id,
                    provider=current_provider,
                    model=current_model,
                    input_tokens=0,
                    output_tokens=0,
                    cost=0.0,
                    latency=latency,
                    status="failed",
                    task_type=task_type,
                    error_message=str(e),
                    failover_from=failover_from
                )
                db.add(usage_failed)
                db.commit()
                
                # Find other configured providers not tried yet
                configured_remaining = [p for p in configured if p not in tried_providers]
                if not configured_remaining:
                    raise ValueError(f"No API key configured for provider '{current_provider}'. Please configure your API key under Platform Setup -> API Settings.")
                
                current_provider = configured_remaining[0]
                if current_provider == "openai":
                    current_model = "gpt-4o-mini"
                elif current_provider == "anthropic":
                    current_model = "claude-haiku-4-5-20251001"
                elif current_provider == "gemini":
                    current_model = "gemini-2.5-flash"
                elif current_provider == "grok":
                    current_model = "grok-2"
                elif current_provider == "groq":
                    current_model = "llama-3.1-8b-instant"
                else:
                    current_model = "default-model"
                continue

        raise Exception("All configured providers failed.")

    def failoverProvider(self, tried_providers: List[str], fallback_chain: List[str]) -> tuple:
        """
        Implements primary -> secondary -> local fallback progression.
        """
        for p in fallback_chain:
            if p not in tried_providers:
                # Select a default model for this provider
                if p == "openai":
                    return "openai", "gpt-4o-mini"
                elif p == "anthropic":
                    return "anthropic", "claude-haiku-4-5-20251001"
                elif p == "gemini":
                    return "gemini", "gemini-2.5-flash"
                elif p == "grok":
                    return "grok", "grok-2"
                elif p == "groq":
                    return "groq", "llama-3.1-8b-instant"
                elif p == "local":
                    return "local", "llama3"
                elif p == "mock":
                    return "mock", "mock-model"
                    
        return "mock", "mock-model"

    async def executeCached(
        self,
        db: Session,
        tenant_id: str,
        prompt: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
        task_type: str = "general",
        realtime: bool = False,
        complexity: str = "medium",
        bulk: bool = False,
        **kwargs
    ) -> str:
        """
        Executes request with universal prompt caching logic.
        """
        # Check universal cache engine first
        cached_result = PromptOptimizationEngine.retrievePrompt(prompt, system_prompt)
        if cached_result:
            # Cache hit!
            logger.info("Universal Cache Hit! Bypassing provider execution.")
            
            # Log usage as cache hit (saves cost & latency)
            usage = ProviderUsage(
                tenant_id=tenant_id,
                provider=cached_result["provider"],
                model=cached_result["model"],
                input_tokens=cached_result["input_tokens"],
                output_tokens=cached_result["output_tokens"],
                cost=0.0, # 100% free!
                latency=0.005, # negligible
                status="success",
                task_type=task_type,
                cache_hit=True,
                cached_tokens=cached_result["input_tokens"],
                is_batch=bulk
            )
            db.add(usage)
            db.commit()
            return cached_result["content"]
            
        # Cache miss: execute standard request
        content = await self.executeRequest(
            db=db,
            tenant_id=tenant_id,
            prompt=prompt,
            model=model,
            provider=provider,
            system_prompt=system_prompt,
            task_type=task_type,
            realtime=realtime,
            complexity=complexity,
            bulk=bulk,
            **kwargs
        )
        
        # Populate cache (executeRequest already calls PromptOptimizationEngine.fallbackLocalCaching internally,
        # but we also explicitly populate it for native caching models here just in case)
        # Note: we need to lookup provider and model if not supplied, which is done during executeRequest.
        # So executeRequest is the best place to cache the successful response.
        
        return content

    async def executeBatch(
        self,
        db: Session,
        tenant_id: str,
        tasks: List[Dict[str, Any]],
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> AIBatchJob:
        """
        Main execution point for batches.
        """
        configured = self._get_configured_providers(db, tenant_id)
        if not provider or not model:
            provider, model = self.selectProvider(configured, bulk=True)
            
        # Create database batch job record
        job = BatchExecutionEngine.createBatch(db, tenant_id, provider, model, tasks)
        
        # Get adapter to submit
        api_key = self._get_api_key(db, tenant_id, provider)
        adapter = self._get_adapter(provider, api_key)
        
        # Submit
        await BatchExecutionEngine.submitToProvider(db, job.id, adapter)
        
        return job

    def estimateCost(self, prompt: str, model: str, system_prompt: Optional[str] = None, provider: str = "openai") -> float:
        return AICostOptimizer.estimateCost(prompt, model, system_prompt, provider)
