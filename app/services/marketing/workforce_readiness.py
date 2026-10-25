"""Truthful readiness inventory for the OctaOS Marketing AI workforce.

Configured means credentials/settings are present, not that a live provider call has
been verified. This module intentionally does not invent metrics or provider health.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Set

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import APICredential


TEXT_PROVIDERS = {"openai", "anthropic", "openrouter", "gemini", "groq", "grok", "nvidia", "together"}
RESEARCH_PROVIDERS = {"firecrawl", "tavily", "serpapi", "brave_search", "apify", "dataforseo", "semrush", "ahrefs"}
IMAGE_PROVIDERS = {"openai", "openrouter", "together", "replicate", "nvidia"}
VIDEO_PROVIDERS = {"together", "replicate", "heygen", "runway", "luma", "creatomate", "shotstack"}
ANALYTICS_PROVIDERS = {"ga4", "google_analytics", "google_analytics_4", "search_console", "google_search_console", "gsc", "meta", "linkedin", "buffer"}
REVENUE_PROVIDERS = {"hubspot", "salesforce", "shopify", "woocommerce", "stripe", "razorpay"}


def _configured_from_env(names: Iterable[str]) -> Set[str]:
    return {name for name in names if bool(getattr(settings, name, None) or os.getenv(name))}


def _capability(
    capability_id: str,
    label: str,
    status: str,
    configured_providers: list[str],
    components: list[str],
    limitation: str,
) -> Dict[str, Any]:
    return {
        "id": capability_id,
        "label": label,
        "status": status,
        "configured_providers": sorted(set(configured_providers)),
        "components": components,
        "limitation": limitation,
        "live_verified": False,
    }


def get_marketing_workforce_readiness(db: Session, tenant_id: str) -> Dict[str, Any]:
    rows = db.query(APICredential).filter(APICredential.tenant_id == tenant_id).all()
    tenant_providers = {
        (row.provider or "").strip().lower()
        for row in rows
        if row.encrypted_key and row.provider
    }
    global_text = _configured_from_env([
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "GROK_API_KEY",
        "TOGETHER_API_KEY", "NVIDIA_API_KEY",
    ])
    global_research = _configured_from_env(["FIRECRAWL_API_KEY", "APIFY_TOKEN"])
    global_image = _configured_from_env(["OPENAI_API_KEY", "OPENROUTER_API_KEY", "TOGETHER_API_KEY", "NVIDIA_API_KEY"])
    global_video = _configured_from_env(["TOGETHER_API_KEY", "HEYGEN_API_KEY"])
    configured_text = sorted(tenant_providers.intersection(TEXT_PROVIDERS) | {name.lower().replace("_API_KEY", "") for name in global_text})
    configured_research = sorted(tenant_providers.intersection(RESEARCH_PROVIDERS) | {name.lower().replace("_API_KEY", "") for name in global_research})
    configured_image = sorted(tenant_providers.intersection(IMAGE_PROVIDERS) | {name.lower().replace("_API_KEY", "") for name in global_image})
    configured_video = sorted(tenant_providers.intersection(VIDEO_PROVIDERS) | {name.lower().replace("_API_KEY", "") for name in global_video})

    buffer_row = next((row for row in rows if (row.provider or "").lower() == "buffer"), None)
    buffer_settings = dict(buffer_row.settings or {}) if buffer_row else {}
    channel_map = dict(buffer_settings.get("channel_map", {}))
    meta_configured = bool(tenant_providers.intersection({"meta", "facebook", "instagram"}))
    linkedin_configured = "linkedin" in tenant_providers
    analytics_configured = sorted(tenant_providers.intersection(ANALYTICS_PROVIDERS))
    revenue_configured = sorted(tenant_providers.intersection(REVENUE_PROVIDERS))

    capabilities = [
        _capability(
            "brand_product_understanding", "Brand and product understanding", "in_app_component",
            [], ["BrandKnowledgeService", "CompanyContextProjectionEngine"],
            "Requires complete, current tenant product facts, approved claims, brand voice and audience data.",
        ),
        _capability(
            "trend_and_event_research", "Trends, events and market research",
            "configured" if configured_research else "needs_configuration",
            configured_research, ["Context Radar", "NewsRadar", "CalendarEngine", "TrendSynthesizer"],
            "Search coverage depends on configured providers and available sources; this status is not proof of exhaustive internet coverage.",
        ),
        _capability(
            "campaign_strategy_and_copy", "Campaign strategy and copy",
            "configured" if configured_text else "needs_configuration",
            configured_text, ["Campaign OS 15-agent council", "LLMGateway", "MarketingAgent"],
            "Configured credentials have not been live-tested by this endpoint; unsupported claims still require evidence and review.",
        ),
        _capability(
            "image_generation", "Image generation and creative QA",
            "configured" if configured_image else "needs_configuration",
            configured_image, ["Visual Director", "media generation adapters"],
            "Actual model availability, commercial rights, output quality and durable asset hosting require provider-specific checks.",
        ),
        _capability(
            "video_generation", "Video generation and composition",
            "configured" if configured_video else "needs_configuration",
            configured_video, ["Video generation jobs", "media storage"],
            "A key does not guarantee a usable video model, sufficient quota, a completed job or a publicly reachable final asset.",
        ),
        _capability(
            "virtual_influencer", "Virtual influencer concepting",
            "review_required" if configured_text else "needs_configuration",
            configured_text, ["Virtual influencer brief workflow", "image/video generation adapters"],
            "Fictional persona output must be disclosed and reviewed; consistent identity, likeness rights and live publishing require additional controls.",
        ),
        _capability(
            "buffer_publishing", "Buffer publishing",
            "configured" if buffer_row else "needs_connection",
            ["buffer"] if buffer_row else [], ["Buffer OAuth/API key", "scheduled-post worker"],
            "Requires a mapped channel per platform. A Buffer queue receipt is not proof that the social network published the post.",
        ),
        _capability(
            "native_social_publishers", "Native social publisher fallback",
            "configured" if (meta_configured or linkedin_configured) else "needs_configuration",
            sorted(({"meta"} if meta_configured else set()) | ({"linkedin"} if linkedin_configured else set())),
            ["Meta Graph API adapter", "LinkedIn publisher adapter"],
            "Each account's scopes, app review, media requirements and live publish permissions must be checked separately.",
        ),
        _capability(
            "performance_analytics", "Social and website performance analytics",
            "configured" if analytics_configured else "needs_configuration",
            analytics_configured, ["MarketingAnalyticsService", "platform insights adapters"],
            "Configured providers may expose different metrics; missing values must remain unavailable rather than being treated as zero.",
        ),
        _capability(
            "revenue_attribution", "CRM and revenue attribution",
            "configured" if revenue_configured else "needs_configuration",
            revenue_configured, ["CRM/commerce connector adapters", "campaign UTM attribution"],
            "Revenue is not verified until campaign identifiers are connected to actual lead, deal or order records with a documented attribution method.",
        ),
    ]
    return {
        "tenant_id": tenant_id,
        "status": "partial" if any(c["status"] in {"needs_configuration", "needs_connection"} for c in capabilities) else "configured_not_live_verified",
        "capabilities": capabilities,
        "connected_buffer": bool(buffer_row),
        "buffer_channel_map": channel_map,
        "notes": [
            "Configured means a credential or setting is present; it does not mean a live health check passed.",
            "No synthetic performance metrics or revenue figures are generated by this readiness endpoint.",
        ],
    }
