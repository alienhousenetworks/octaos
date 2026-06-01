import hashlib
import json
import logging
import redis
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback in-memory cache if Redis is down
_in_memory_cache: Dict[str, Dict[str, Any]] = {}

def get_redis_client():
    try:
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=1,
            decode_responses=True,
            socket_timeout=2.0
        )
        # Test ping
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis is unavailable for prompt caching. Falling back to in-memory cache. Error: {e}")
        return None

class PromptOptimizationEngine:
    @staticmethod
    def hashPrompt(prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generates a unique SHA-256 hash representing the full context.
        """
        combined = f"sys:{system_prompt or ''}|user:{prompt}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def providerSupportsNativeCaching(provider: str, model: str) -> bool:
        """
        Determines if the provider supports native caching.
        """
        provider_lower = provider.lower()
        model_lower = model.lower()
        
        # Anthropic supports prompt caching for Claude 3.5 Sonnet / Haiku
        if provider_lower == "anthropic" and ("sonnet" in model_lower or "haiku" in model_lower):
            return True
        # OpenAI caches prompt prefixes automatically (>1024 tokens)
        if provider_lower == "openai":
            return True
        # Gemini 2.5 supports context caching
        if provider_lower == "gemini" and "2.5" in model_lower:
            return True
            
        return False

    @classmethod
    def retrievePrompt(cls, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a cached response if available.
        Returns: {
            "content": str,
            "input_tokens": int,
            "output_tokens": int,
            "provider": str,
            "model": str,
            "cached_tokens": int
        }
        """
        prompt_hash = cls.hashPrompt(prompt, system_prompt)
        client = get_redis_client()
        
        if client:
            try:
                cached_data = client.get(f"prompt_cache:{prompt_hash}")
                if cached_data:
                    logger.info(f"Local Cache Hit (Redis) for hash {prompt_hash}")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Failed to read from Redis cache: {e}")
        
        # In-memory fallback
        if prompt_hash in _in_memory_cache:
            logger.info(f"Local Cache Hit (In-memory) for hash {prompt_hash}")
            return _in_memory_cache[prompt_hash]

        return None

    @classmethod
    def cachePrompt(cls, prompt: str, system_prompt: Optional[str], response_text: str,
                    input_tokens: int, output_tokens: int, provider: str, model: str,
                    ttl_seconds: int = 86400) -> None:
        """
        Saves response in cache.
        """
        prompt_hash = cls.hashPrompt(prompt, system_prompt)
        cache_value = {
            "content": response_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "provider": provider,
            "model": model,
            "cached_tokens": input_tokens # saved all input tokens!
        }
        
        client = get_redis_client()
        if client:
            try:
                client.setex(
                    f"prompt_cache:{prompt_hash}",
                    ttl_seconds,
                    json.dumps(cache_value)
                )
                return
            except Exception as e:
                logger.error(f"Failed to write to Redis cache: {e}")
        
        # In-memory fallback
        _in_memory_cache[prompt_hash] = cache_value

    @classmethod
    def invalidateCache(cls, prompt: str, system_prompt: Optional[str] = None) -> None:
        """
        Invalidates cache for a prompt.
        """
        prompt_hash = cls.hashPrompt(prompt, system_prompt)
        client = get_redis_client()
        if client:
            try:
                client.delete(f"prompt_cache:{prompt_hash}")
            except Exception as e:
                logger.error(f"Failed to delete Redis key: {e}")
        
        if prompt_hash in _in_memory_cache:
            del _in_memory_cache[prompt_hash]

    @classmethod
    def refreshCache(cls, prompt: str, system_prompt: Optional[str], response_text: str,
                     input_tokens: int, output_tokens: int, provider: str, model: str) -> None:
        """
        Refreshes cache TTL and updates values.
        """
        cls.cachePrompt(prompt, system_prompt, response_text, input_tokens, output_tokens, provider, model)

    @classmethod
    def fallbackLocalCaching(cls, prompt: str, system_prompt: Optional[str], response_text: str,
                             input_tokens: int, output_tokens: int, provider: str, model: str) -> None:
        """
        Performs local caching for providers lacking native caching support.
        """
        if not cls.providerSupportsNativeCaching(provider, model):
            logger.info(f"Using fallback local caching for {provider} / {model}")
            cls.cachePrompt(prompt, system_prompt, response_text, input_tokens, output_tokens, provider, model)
