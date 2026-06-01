from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Standard model configurations with costs in USD per 1,000,000 tokens
# Latency values are representative benchmarks (lower is faster)
MODEL_REGISTRY = {
    # OpenAI
    "openai/gpt-4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "complexity": "high",
        "latency": 1.2,
        "input_cost_1m": 5.00,
        "output_cost_1m": 15.00,
        "supports_batch": True,
        "supports_caching": True
    },
    "openai/gpt-4o-mini": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "complexity": "low",
        "latency": 0.4,
        "input_cost_1m": 0.15,
        "output_cost_1m": 0.60,
        "supports_batch": True,
        "supports_caching": True
    },
    # Anthropic
    "anthropic/claude-opus-4-8": {
        "provider": "anthropic",
        "model": "claude-opus-4-8",
        "complexity": "high",
        "latency": 2.0,
        "input_cost_1m": 5.00,
        "output_cost_1m": 25.00,
        "supports_batch": True,
        "supports_caching": True
    },
    "anthropic/claude-sonnet-4-6": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "complexity": "high",
        "latency": 1.2,
        "input_cost_1m": 3.00,
        "output_cost_1m": 15.00,
        "supports_batch": True,
        "supports_caching": True
    },
    "anthropic/claude-haiku-4-5-20251001": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "complexity": "low",
        "latency": 0.4,
        "input_cost_1m": 1.00,
        "output_cost_1m": 5.00,
        "supports_batch": True,
        "supports_caching": True
    },
    # Google Gemini (2.5 series — stable, recommended for most keys)
    "gemini/gemini-2.5-pro": {
        "provider": "gemini",
        "model": "gemini-2.5-pro",
        "complexity": "high",
        "latency": 1.8,
        "input_cost_1m": 1.25,
        "output_cost_1m": 5.00,
        "supports_batch": True,
        "supports_caching": True
    },
    "gemini/gemini-2.5-flash": {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "complexity": "low",
        "latency": 0.35,
        "input_cost_1m": 0.075,
        "output_cost_1m": 0.30,
        "supports_batch": True,
        "supports_caching": True
    },
    # Google Gemini (2.0 series — widely available, fast)
    "gemini/gemini-2.0-flash": {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "complexity": "low",
        "latency": 0.30,
        "input_cost_1m": 0.10,
        "output_cost_1m": 0.40,
        "supports_batch": False,
        "supports_caching": True
    },
    "gemini/gemini-2.0-flash-lite": {
        "provider": "gemini",
        "model": "gemini-2.0-flash-lite",
        "complexity": "low",
        "latency": 0.20,
        "input_cost_1m": 0.075,
        "output_cost_1m": 0.30,
        "supports_batch": False,
        "supports_caching": False
    },
    # Google Gemini (1.5 series — legacy, may not be available on all keys)
    "gemini/gemini-1.5-pro": {
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "complexity": "high",
        "latency": 1.8,
        "input_cost_1m": 1.25,
        "output_cost_1m": 5.00,
        "supports_batch": True,
        "supports_caching": True
    },
    "gemini/gemini-1.5-flash": {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "complexity": "low",
        "latency": 0.35,
        "input_cost_1m": 0.075,
        "output_cost_1m": 0.30,
        "supports_batch": True,
        "supports_caching": True
    },
    # Grok
    "grok/grok-2": {
        "provider": "grok",
        "model": "grok-2",
        "complexity": "high",
        "latency": 1.1,
        "input_cost_1m": 2.00,
        "output_cost_1m": 10.00,
        "supports_batch": False,
        "supports_caching": False
    },
    # Groq
    "groq/llama-3.3-70b-versatile": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "complexity": "high",
        "latency": 0.25,
        "input_cost_1m": 0.59,
        "output_cost_1m": 0.79,
        "supports_batch": False,
        "supports_caching": False
    },
    "groq/llama-3.1-8b-instant": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "complexity": "low",
        "latency": 0.15,
        "input_cost_1m": 0.05,
        "output_cost_1m": 0.08,
        "supports_batch": False,
        "supports_caching": False
    },
    # Mistral
    "mistral/mistral-large-latest": {
        "provider": "mistral",
        "model": "mistral-large-latest",
        "complexity": "high",
        "latency": 1.4,
        "input_cost_1m": 2.00,
        "output_cost_1m": 6.00,
        "supports_batch": True,
        "supports_caching": False
    },
    # Cohere
    "cohere/command-r-plus": {
        "provider": "cohere",
        "model": "command-r-plus",
        "complexity": "high",
        "latency": 1.3,
        "input_cost_1m": 2.50,
        "output_cost_1m": 10.00,
        "supports_batch": False,
        "supports_caching": False
    },
    # Local Inference
    "local/llama3": {
        "provider": "local",
        "model": "llama3",
        "complexity": "medium",
        "latency": 0.6,
        "input_cost_1m": 0.00,
        "output_cost_1m": 0.00,
        "supports_batch": False,
        "supports_caching": False
    },
    # Fallback Mock
    "mock/mock-model": {
        "provider": "mock",
        "model": "mock-model",
        "complexity": "low",
        "latency": 0.05,
        "input_cost_1m": 0.00,
        "output_cost_1m": 0.00,
        "supports_batch": True,
        "supports_caching": True
    }
}

class AIRoutingEngine:
    @staticmethod
    def selectProvider(
        configured_providers: List[str],
        complexity: str = "medium",
        realtime: bool = False,
        bulk: bool = False
    ) -> Tuple[str, str]:
        """
        Dynamically selects the best provider and model based on parameters
        and what API keys the tenant has connected.
        Returns: (provider_name, model_name)
        """
        available_providers = set(p.lower() for p in configured_providers)
        
        # Filter MODEL_REGISTRY for keys that are active
        eligible_models = {
            key: spec for key, spec in MODEL_REGISTRY.items()
            if spec["provider"] in available_providers
        }
        
        if not eligible_models:
            # Fallback to mock and local when no actual key configured
            eligible_models = {
                key: spec for key, spec in MODEL_REGISTRY.items()
                if spec["provider"] in ["mock", "local"]
            }
            
        if not eligible_models:
            return "mock", "mock-model"

        # Apply user's routing logic
        if realtime:
            # LOWEST LATENCY
            best_key = min(eligible_models.keys(), key=lambda k: eligible_models[k]["latency"])
            selected = eligible_models[best_key]
            logger.info(f"Routed for REALTIME (lowest latency): {selected['provider']}/{selected['model']}")
            return selected["provider"], selected["model"]
            
        elif bulk:
            # BATCH-CAPABLE CHEAPEST
            batch_models = {k: v for k, v in eligible_models.items() if v["supports_batch"]}
            source_models = batch_models if batch_models else eligible_models
            
            # Find cheapest by combined token cost (assuming 1:1 input/output token ratio for simplicity)
            best_key = min(source_models.keys(), key=lambda k: source_models[k]["input_cost_1m"] + source_models[k]["output_cost_1m"])
            selected = source_models[best_key]
            logger.info(f"Routed for BULK (cheapest batch/overall): {selected['provider']}/{selected['model']}")
            return selected["provider"], selected["model"]
            
        elif complexity == "high":
            # STRONGEST REASONING MODEL (high complexity rating)
            high_models = {k: v for k, v in eligible_models.items() if v["complexity"] == "high"}
            source_models = high_models if high_models else eligible_models
            
            # Tie break by cost among high models
            best_key = min(source_models.keys(), key=lambda k: source_models[k]["input_cost_1m"] + source_models[k]["output_cost_1m"])
            selected = source_models[best_key]
            logger.info(f"Routed for HIGH COMPLEXITY (strongest reasoning): {selected['provider']}/{selected['model']}")
            return selected["provider"], selected["model"]
            
        else:
            # LOWEST COST VALID
            best_key = min(eligible_models.keys(), key=lambda k: eligible_models[k]["input_cost_1m"] + eligible_models[k]["output_cost_1m"])
            selected = eligible_models[best_key]
            logger.info(f"Routed for DEFAULT (lowest cost): {selected['provider']}/{selected['model']}")
            return selected["provider"], selected["model"]
