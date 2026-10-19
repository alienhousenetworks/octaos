"""Multimodal Model Registry, Catalog Cache, BYOM Validation, and Fallback Engine."""
import json
import os
import difflib
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.services.ai_gateway.providers.base import (
    ProviderAdapter,
    ModelInfo,
    ModalityType,
)
from app.services.ai_gateway.providers.openrouter import OpenRouterAdapter
from app.services.ai_gateway.providers.together import TogetherAdapter
from app.services.ai_gateway.providers.nvidia import NvidiaAdapter

logger = logging.getLogger(__name__)

CURATED_PATH = os.path.join(os.path.dirname(__file__), "providers", "curated_models.json")


class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None
    _catalog_cache: Dict[str, Tuple[datetime, List[ModelInfo]]] = {}
    _cache_ttl = timedelta(hours=6)

    def __init__(self):
        self.adapters: Dict[str, ProviderAdapter] = {
            "openrouter": OpenRouterAdapter(),
            "together": TogetherAdapter(),
            "nvidia": NvidiaAdapter(),
        }

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_adapter(self, provider: str) -> Optional[ProviderAdapter]:
        p = (provider or "").lower().strip()
        if p in ("togetherai", "together_ai", "togetherapi"):
            p = "together"
        elif p in ("nim", "nvidia_nim"):
            p = "nvidia"
        return self.adapters.get(p)

    def _get_api_key(self, db: Session, tenant_id: str, provider: str) -> str:
        from app.services.ai_gateway import ai_gateway
        return ai_gateway._get_api_key(db, tenant_id, provider)

    def _get_cache_key(self, provider: str, api_key: str) -> str:
        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16] if api_key else "nokey"
        return f"catalog:{provider}:{key_hash}"

    async def get_provider_catalog(
        self,
        db: Session,
        tenant_id: str,
        provider: str,
        force_refresh: bool = False,
    ) -> List[ModelInfo]:
        """Get live or cached models list from provider."""
        adapter = self.get_adapter(provider)
        if not adapter:
            return []

        api_key = self._get_api_key(db, tenant_id, provider)
        if not api_key:
            return []

        cache_key = self._get_cache_key(adapter.name, api_key)
        now = datetime.now(timezone.utc)

        if not force_refresh and cache_key in self._catalog_cache:
            cached_time, models = self._catalog_cache[cache_key]
            if now - cached_time < self._cache_ttl:
                return models

        try:
            models = await adapter.list_models(api_key)
            self._catalog_cache[cache_key] = (now, models)
            return models
        except Exception as e:
            logger.warning(f"[ModelRegistry] Failed to fetch catalog for {provider}: {e}")
            # Fall back to stale cache if present
            if cache_key in self._catalog_cache:
                return self._catalog_cache[cache_key][1]
            return []

    async def validate_model(
        self,
        db: Session,
        tenant_id: str,
        provider: str,
        modality: str,
        model_slug: str,
        mode: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Validate a model slug against provider live catalog and compatibility rules."""
        provider_norm = provider.lower().strip()
        if provider_norm in ("togetherai", "together_ai", "togetherapi"):
            provider_norm = "together"
        elif provider_norm in ("nim", "nvidia_nim"):
            provider_norm = "nvidia"

        adapter = self.get_adapter(provider_norm)
        if not adapter:
            return {
                "status": "incompatible",
                "message": f"Provider '{provider}' is not supported. Use OpenRouter, Together AI, or NVIDIA NIM.",
                "capabilities": {},
                "pricing": {},
                "suggestions": [],
            }

        api_key = self._get_api_key(db, tenant_id, provider_norm)
        if not api_key:
            return {
                "status": "no_key",
                "message": f"API key for {provider_norm.title()} is not configured.",
                "link": "/settings?tab=integrations",
                "capabilities": {},
                "pricing": {},
                "suggestions": [],
            }

        catalog = await self.get_provider_catalog(db, tenant_id, provider_norm, force_refresh=force_refresh)
        if not catalog and not force_refresh:
            # Try once with force refresh
            catalog = await self.get_provider_catalog(db, tenant_id, provider_norm, force_refresh=True)

        if not catalog:
            return {
                "status": "unverified",
                "message": f"Could not connect to {provider_norm.title()} catalog. You may proceed at your own risk.",
                "capabilities": {},
                "pricing": {},
                "suggestions": [],
            }

        # Look for exact slug or case-insensitive match
        matched_model: Optional[ModelInfo] = None
        all_slugs = [m.slug for m in catalog]

        for m in catalog:
            if m.slug == model_slug or m.slug.lower() == model_slug.lower():
                matched_model = m
                break

        if not matched_model:
            # Fuzzy suggestions
            close_matches = difflib.get_close_matches(model_slug, all_slugs, n=3, cutoff=0.4)
            return {
                "status": "not_found",
                "message": f"Model '{model_slug}' not found in {provider_norm.title()} catalog.",
                "suggestions": close_matches,
                "capabilities": {},
                "pricing": {},
            }

        # Check modality compatibility (support both short names 'text', 'image', 'video' and full enum values)
        target_raw = modality.lower().strip()
        modality_aliases = {
            "text": {ModalityType.TEXT_TO_TEXT.value, "text", "text_to_text"},
            "image": {ModalityType.TEXT_TO_IMAGE.value, ModalityType.IMAGE_TO_IMAGE.value, "image", "text_to_image"},
            "video": {ModalityType.TEXT_TO_VIDEO.value, ModalityType.IMAGE_TO_VIDEO.value, "video", "text_to_video"},
            "text_to_text": {ModalityType.TEXT_TO_TEXT.value, "text", "text_to_text"},
            "text_to_image": {ModalityType.TEXT_TO_IMAGE.value, "text_to_image"},
            "image_to_image": {ModalityType.IMAGE_TO_IMAGE.value, "image_to_image"},
            "text_to_video": {ModalityType.TEXT_TO_VIDEO.value, "text_to_video"},
            "image_to_video": {ModalityType.IMAGE_TO_VIDEO.value, "image_to_video"},
        }

        expected_modalities = modality_aliases.get(target_raw, {target_raw})
        is_compatible = any(m in expected_modalities for m in matched_model.modalities)
        if not is_compatible and mode:
            is_compatible = mode.lower().strip() in matched_model.modalities

        if not is_compatible:
            # Incompatible modality
            compatible_suggestions = [
                m.slug for m in catalog if any(mod in expected_modalities for mod in m.modalities)
            ][:3]
            return {
                "status": "incompatible",
                "message": (
                    f"Model '{model_slug}' does not support {target_raw}. "
                    f"Supported modalities: {', '.join(matched_model.modalities)}."
                ),
                "capabilities": matched_model.capabilities,
                "pricing": matched_model.pricing,
                "suggestions": compatible_suggestions,
            }

        # Check mode compatibility (e.g. image_to_image or image_to_video)
        if mode == "image_to_image" and ModalityType.IMAGE_TO_IMAGE.value not in matched_model.modalities:
            return {
                "status": "incompatible",
                "message": f"Model '{model_slug}' does not support image-to-image conditioning.",
                "capabilities": matched_model.capabilities,
                "pricing": matched_model.pricing,
                "suggestions": ["black-forest-labs/FLUX.1-canny", "black-forest-labs/FLUX.1-redux"],
            }

        return {
            "status": "available",
            "message": f"Model '{model_slug}' is available and compatible.",
            "display_name": matched_model.display_name,
            "capabilities": matched_model.capabilities,
            "pricing": matched_model.pricing,
            "context_length": matched_model.context_length,
            "suggestions": [],
        }

    def load_curated_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load curated preference model lists from JSON configuration."""
        if not os.path.exists(CURATED_PATH):
            return {"text": [], "image": [], "video": []}
        try:
            with open(CURATED_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[ModelRegistry] Failed to load curated models: {e}")
            return {"text": [], "image": [], "video": []}

    async def get_curated_models_with_availability(
        self,
        db: Session,
        tenant_id: str,
        provider: Optional[str] = None,
        modality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return curated models filtered by active tenant availability."""
        curated_data = self.load_curated_models()
        results: List[Dict[str, Any]] = []

        mod_keys = [modality.lower()] if modality and modality.lower() in curated_data else ["text", "image", "video"]

        for m_key in mod_keys:
            items = curated_data.get(m_key, [])
            for item in items:
                p = item.get("provider", "").lower()
                if provider and provider.lower() not in ("auto", "all") and p != provider.lower():
                    continue

                item_copy = dict(item)
                item_copy["modality"] = m_key
                # Check if tenant has API key configured
                has_key = bool(self._get_api_key(db, tenant_id, p))
                item_copy["has_api_key"] = has_key
                results.append(item_copy)

        return results

    async def resolve_model(
        self,
        db: Session,
        tenant_id: str,
        modality: str,  # "text", "image", "video"
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> Tuple[str, str, Optional[str]]:
        """Resolve concrete (provider, model) with resilient fallback ordering.
        
        Returns: (provider, model, fallback_reason)
        """
        p = (preferred_provider or "auto").lower().strip()
        m = (preferred_model or "").strip()

        # Check tenant keys
        has_openrouter = bool(self._get_api_key(db, tenant_id, "openrouter"))
        has_together = bool(self._get_api_key(db, tenant_id, "together"))
        has_nvidia = bool(self._get_api_key(db, tenant_id, "nvidia"))

        # Default fallbacks per modality
        defaults = {
            "text": {
                "openrouter": "meta-llama/llama-3.3-70b-instruct",
                "together": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "nvidia": "meta/llama-3.2-11b-vision-instruct",
            },
            "image": {
                "openrouter": "recraft/recraft-v3",
                "together": "black-forest-labs/FLUX.1-dev",
            },
            "video": {
                "openrouter": "kling-ai/kling-v1.5",
                "together": "minimax/video-01",
            },
        }

        # 1. If explicit provider and model specified
        if p in ("openrouter", "together", "nvidia") and m:
            api_key = self._get_api_key(db, tenant_id, p)
            if api_key:
                # Fast check if model is usable
                val = await self.validate_model(db, tenant_id, p, f"{modality}_to_{modality}" if modality == "text" else f"text_to_{modality}", m)
                if val.get("status") in ("available", "unverified"):
                    return p, m, None
                elif not allow_fallback:
                    raise Exception(f"Selected model '{m}' on '{p}' is not available: {val.get('message')}")
                fallback_reason = f"Preferred model '{m}' on '{p}' unavailable ({val.get('message')})."
            else:
                fallback_reason = f"No API key for preferred provider '{p}'."
        else:
            fallback_reason = None

        # 2. Determine best provider
        target_provider = None
        if p in ("openrouter", "together", "nvidia"):
            if p == "nvidia" and has_nvidia:
                target_provider = "nvidia"
            elif p == "together" and has_together:
                target_provider = "together"
            elif p == "openrouter" and has_openrouter:
                target_provider = "openrouter"

        if not target_provider:
            if has_together and modality in ("image", "video"):
                target_provider = "together"
            elif has_nvidia and modality == "text":
                target_provider = "nvidia"
            elif has_openrouter:
                target_provider = "openrouter"
            elif has_together:
                target_provider = "together"
            elif has_nvidia:
                target_provider = "nvidia"
            else:
                # Last resort
                target_provider = "openrouter"

        # 3. Pick default curated model for this provider and modality
        mod_defaults = defaults.get(modality, {})
        resolved_model = mod_defaults.get(target_provider) or ("meta-llama/llama-3.3-70b-instruct" if modality == "text" else "flux")

        return target_provider, resolved_model, fallback_reason
