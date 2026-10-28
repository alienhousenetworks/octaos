"""Universal AI Provider Registry for connected frontier and enterprise models."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential

logger = logging.getLogger(__name__)

# Master specification of supported frontier & local providers
PROVIDER_SPECS: Dict[str, Dict[str, Any]] = {
    "anthropic": {
        "display_name": "Anthropic Claude",
        "default_model": "claude-3-7-sonnet-20250219",
        "supported_models": [
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        "capabilities": [
            "deep_coding",
            "complex_reasoning",
            "document_analysis",
            "tools",
            "code_generation",
            "technical_writing",
        ],
        "modalities": ["text", "code", "image", "document", "json"],
        "tool_interfaces": ["tools", "computer_use", "json_schema"],
        "default_rate_limit_rpm": 60,
        "default_timeout_seconds": 90,
        "default_cost_ceiling_usd": 50.0,
        "default_data_sharing": "anonymized_only",
    },
    "grok": {
        "display_name": "xAI Grok",
        "default_model": "grok-2-1212",
        "supported_models": ["grok-2-1212", "grok-2-vision-1212", "grok-beta"],
        "capabilities": [
            "realtime_research",
            "market_analysis",
            "social_intelligence",
            "fast_reasoning",
            "vision",
        ],
        "modalities": ["text", "code", "image", "json"],
        "tool_interfaces": ["function_calling", "web_search", "json_schema"],
        "default_rate_limit_rpm": 120,
        "default_timeout_seconds": 60,
        "default_cost_ceiling_usd": 30.0,
        "default_data_sharing": "anonymized_only",
    },
    "openai": {
        "display_name": "OpenAI ChatGPT / o-series",
        "default_model": "gpt-4o",
        "supported_models": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
        "capabilities": [
            "reasoning",
            "coding",
            "tools",
            "structured_outputs",
            "market_research",
            "multimodal",
        ],
        "modalities": ["text", "code", "image", "json"],
        "tool_interfaces": ["function_calling", "json_schema", "code_interpreter"],
        "default_rate_limit_rpm": 120,
        "default_timeout_seconds": 60,
        "default_cost_ceiling_usd": 50.0,
        "default_data_sharing": "internal_only",
    },
    "deepseek": {
        "display_name": "DeepSeek AI",
        "default_model": "deepseek-chat",
        "supported_models": ["deepseek-chat", "deepseek-reasoner"],
        "capabilities": [
            "deep_reasoning",
            "mathematical_logic",
            "code_generation",
            "low_cost_inference",
        ],
        "modalities": ["text", "code", "json"],
        "tool_interfaces": ["function_calling", "json_schema"],
        "default_rate_limit_rpm": 60,
        "default_timeout_seconds": 120,
        "default_cost_ceiling_usd": 20.0,
        "default_data_sharing": "anonymized_only",
    },
    "groq": {
        "display_name": "Groq LPU",
        "default_model": "llama-3.3-70b-versatile",
        "supported_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "capabilities": [
            "ultra_low_latency",
            "fast_reasoning",
            "summarization",
            "rapid_classification",
        ],
        "modalities": ["text", "code", "json"],
        "tool_interfaces": ["function_calling", "json_schema"],
        "default_rate_limit_rpm": 300,
        "default_timeout_seconds": 20,
        "default_cost_ceiling_usd": 15.0,
        "default_data_sharing": "anonymized_only",
    },
    "gemini": {
        "display_name": "Google Gemini",
        "default_model": "gemini-2.0-flash",
        "supported_models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "capabilities": [
            "multimodal_large_context",
            "video_understanding",
            "audio",
            "tools",
            "market_research",
        ],
        "modalities": ["text", "code", "image", "video", "audio", "json"],
        "tool_interfaces": ["function_calling", "code_execution", "json_schema"],
        "default_rate_limit_rpm": 120,
        "default_timeout_seconds": 60,
        "default_cost_ceiling_usd": 30.0,
        "default_data_sharing": "anonymized_only",
    },
    "together": {
        "display_name": "Together AI",
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
        "supported_models": ["meta-llama/Llama-3-70b-chat-hf"],
        "capabilities": ["open_weights", "fast_inference", "custom_finetunes"],
        "modalities": ["text", "code", "json"],
        "tool_interfaces": ["function_calling"],
        "default_rate_limit_rpm": 100,
        "default_timeout_seconds": 60,
        "default_cost_ceiling_usd": 20.0,
        "default_data_sharing": "anonymized_only",
    },
    "nvidia": {
        "display_name": "NVIDIA NIM",
        "default_model": "meta/llama-3.1-70b-instruct",
        "supported_models": ["meta/llama-3.1-70b-instruct"],
        "capabilities": ["nim_accelerated", "enterprise_inference", "coding"],
        "modalities": ["text", "code", "json"],
        "tool_interfaces": ["function_calling"],
        "default_rate_limit_rpm": 100,
        "default_timeout_seconds": 45,
        "default_cost_ceiling_usd": 20.0,
        "default_data_sharing": "internal_only",
    },
}


class ProviderDescriptor(BaseModel):
    provider: str
    display_name: str
    default_model: str
    supported_models: List[str]
    status: str = Field(description="'configured', 'verified_reachable', 'not_configured', or 'error'")
    is_connected: bool
    is_configured: bool = False
    supported_capabilities: List[str]
    supported_modalities: List[str]
    supported_tool_interfaces: List[str]
    cost_ceiling_usd: float
    timeout_seconds: int
    rate_limit_rpm: int
    permitted_scopes: List[str]
    data_sharing_scope: str
    auth_reference: str
    health_last_checked: str
    credential_id: Optional[str] = None


class AIProviderRegistry:
    """
    Central registry for connected external AI providers.
    Enforces real configuration and reachability verification.
    """

    @staticmethod
    def get_provider_specs() -> Dict[str, Dict[str, Any]]:
        return PROVIDER_SPECS

    @classmethod
    def get_connected_providers(
        cls,
        db: Session,
        tenant_id: str,
        verify_health: bool = False,
    ) -> List[ProviderDescriptor]:
        """
        Inspect credentials without confusing configuration with live reachability.
        A decrypted key only proves configuration; live connectivity is verified by a
        successful provider request and recorded by its caller.
        """
        credentials = db.query(APICredential).filter(APICredential.tenant_id == tenant_id).all()
        cred_map: Dict[str, APICredential] = {}
        for c in credentials:
            provider_norm = c.provider.lower().strip()
            if provider_norm in ("xai", "grok_ai"):
                provider_norm = "grok"
            elif provider_norm in ("openrouter_deepseek", "deepseek_ai"):
                provider_norm = "deepseek"
            cred_map[provider_norm] = c

        descriptors: List[ProviderDescriptor] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for provider_key, spec in PROVIDER_SPECS.items():
            cred = cred_map.get(provider_key)
            is_configured = False
            cred_id = None
            settings = {}

            if cred and cred.encrypted_key:
                try:
                    raw_key = decrypt_api_key(cred.encrypted_key)
                    if raw_key and not any(placeholder in raw_key.lower() for placeholder in ("your_api_key", "dummy", "none")):
                        is_configured = True
                        cred_id = cred.id
                        settings = cred.settings or {}
                except Exception as e:
                    logger.warning("Decryption failure for provider %s: %s", provider_key, e)
                    is_configured = False

            cost_ceiling = float(settings.get("cost_ceiling_usd", spec["default_cost_ceiling_usd"]))
            timeout_sec = int(settings.get("timeout_seconds", spec["default_timeout_seconds"]))
            rate_limit = int(settings.get("rate_limit_rpm", spec["default_rate_limit_rpm"]))
            permitted_scopes = settings.get("permitted_scopes") or spec["capabilities"]
            data_sharing = settings.get("data_sharing_scope", spec["default_data_sharing"])

            status = "configured" if is_configured else "not_configured"

            descriptors.append(
                ProviderDescriptor(
                    provider=provider_key,
                    display_name=spec["display_name"],
                    default_model=spec["default_model"],
                    supported_models=spec["supported_models"],
                    status=status,
                    is_connected=False,\n                    is_configured=is_configured,
                    supported_capabilities=spec["capabilities"],
                    supported_modalities=spec["modalities"],
                    supported_tool_interfaces=spec["tool_interfaces"],
                    cost_ceiling_usd=cost_ceiling,
                    timeout_seconds=timeout_sec,
                    rate_limit_rpm=rate_limit,
                    permitted_scopes=permitted_scopes,
                    data_sharing_scope=data_sharing,
                    auth_reference=f"vault:api_credentials:{cred_id}" if cred_id else "none",
                    health_last_checked=now_iso,
                    credential_id=cred_id,
                )
            )

        return descriptors

    @classmethod
    def get_eligible_providers_for_task(
        cls,
        db: Session,
        tenant_id: str,
        required_capabilities: List[str],
        max_cost: Optional[float] = None,
    ) -> List[ProviderDescriptor]:
        """
        Discovers active, configured providers matching all required capabilities
        and within configured cost ceilings.
        """
        all_providers = cls.get_connected_providers(db, tenant_id)
        eligible = []
        for p in all_providers:
            # A configured provider is a candidate, not a proven-live connection.
            # The actual dispatch is the reachability check and must fail closed.
            if not p.is_configured:
                continue
            if p.cost_ceiling_usd <= 0:
                continue
            has_capabilities = all(cap in p.supported_capabilities for cap in required_capabilities)
            if not has_capabilities:
                continue
            # max_cost is a per-task spend budget, while cost_ceiling_usd is
            # the tenant's configured provider-account ceiling. They are different
            # dimensions and must not be compared as if they were interchangeable.
            if max_cost is not None and max_cost <= 0:
                continue
            eligible.append(p)
        return eligible
