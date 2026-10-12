"""Normalization logic mapping raw provider payloads to standardized ModelInfo."""
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.services.ai_gateway.providers.base import ModelInfo, ModalityType


def normalize_openrouter_model(raw: Dict[str, Any]) -> ModelInfo:
    """Normalize OpenRouter model entry from GET /api/v1/models."""
    slug = raw.get("id", "")
    name = raw.get("name") or slug.split("/")[-1].replace("-", " ").title()
    architecture = raw.get("architecture") or {}
    raw_modality = str(architecture.get("modality", "")).lower()

    modalities: List[str] = []
    supports_image_input = False

    # Check modalities from architecture
    if "image->image" in raw_modality or "text+image->image" in raw_modality:
        modalities.extend([ModalityType.TEXT_TO_IMAGE.value, ModalityType.IMAGE_TO_IMAGE.value])
    elif "image" in raw_modality and "text" not in raw_modality:
        modalities.append(ModalityType.TEXT_TO_IMAGE.value)
    elif "text->image" in raw_modality:
        modalities.append(ModalityType.TEXT_TO_IMAGE.value)

    if "video" in raw_modality:
        modalities.append(ModalityType.TEXT_TO_VIDEO.value)
        if "image" in raw_modality:
            modalities.append(ModalityType.IMAGE_TO_VIDEO.value)

    # Check if text model supports multimodal vision input
    if "image->text" in raw_modality or "text+image->text" in raw_modality:
        supports_image_input = True
        modalities.append(ModalityType.TEXT_TO_TEXT.value)
    elif "text->text" in raw_modality or "text" in raw_modality:
        modalities.append(ModalityType.TEXT_TO_TEXT.value)

    # Heuristic for known video / image models if OpenRouter modality string is generic
    slug_lower = slug.lower()
    if any(k in slug_lower for k in ["video", "kling", "luma", "runway", "minimax"]):
        if ModalityType.TEXT_TO_VIDEO.value not in modalities:
            modalities.append(ModalityType.TEXT_TO_VIDEO.value)
        if ModalityType.IMAGE_TO_VIDEO.value not in modalities:
            modalities.append(ModalityType.IMAGE_TO_VIDEO.value)
    elif any(k in slug_lower for k in ["flux", "recraft", "ideogram", "dall-e", "midjourney", "seedream", "imagen"]):
        if ModalityType.TEXT_TO_IMAGE.value not in modalities:
            modalities.append(ModalityType.TEXT_TO_IMAGE.value)
        if any(k in slug_lower for k in ["canny", "redux", "depth", "edit"]):
            modalities.append(ModalityType.IMAGE_TO_IMAGE.value)

    if not modalities:
        modalities.append(ModalityType.TEXT_TO_TEXT.value)

    # Pricing
    pricing = raw.get("pricing") or {}
    prompt_price = float(pricing.get("prompt") or 0.0)
    completion_price = float(pricing.get("completion") or 0.0)
    image_price = float(pricing.get("image") or 0.0)

    capabilities: Dict[str, Any] = {
        "supports_typography": any(k in slug_lower for k in ["ideogram", "recraft", "flux"]),
        "supports_negative_prompt": "dall-e" not in slug_lower,
        "max_aspect_ratios": ["1:1", "16:9", "9:16", "4:5"],
        "tokenizer": architecture.get("tokenizer", ""),
    }

    return ModelInfo(
        provider="openrouter",
        slug=slug,
        display_name=name,
        modalities=list(set(modalities)),
        supports_image_input=supports_image_input or "vision" in slug_lower or "4o" in slug_lower,
        context_length=raw.get("context_length"),
        pricing={
            "prompt_per_1k": prompt_price * 1000.0,
            "completion_per_1k": completion_price * 1000.0,
            "image_unit": image_price,
        },
        capabilities=capabilities,
        status="available",
        source="curated" if any(p in slug_lower for p in ["anthropic", "openai", "deepseek", "meta-llama", "qwen", "google", "flux"]) else "custom",
        last_verified_at=datetime.now(timezone.utc),
    )


def normalize_together_model(raw: Dict[str, Any]) -> ModelInfo:
    """Normalize Together AI model entry from GET /v1/models."""
    slug = raw.get("id", "")
    name = raw.get("display_name") or slug.split("/")[-1].replace("-", " ").title()
    m_type = str(raw.get("type", "")).lower()
    slug_lower = slug.lower()

    modalities: List[str] = []
    supports_image_input = False

    if m_type == "image" or "flux" in slug_lower or "stable-diffusion" in slug_lower or "sdxl" in slug_lower:
        modalities.append(ModalityType.TEXT_TO_IMAGE.value)
        if any(k in slug_lower for k in ["canny", "redux", "depth"]):
            modalities.append(ModalityType.IMAGE_TO_IMAGE.value)

    if m_type == "video" or any(k in slug_lower for k in ["video", "minimax", "wan", "cogvideo", "ltx"]):
        modalities.append(ModalityType.TEXT_TO_VIDEO.value)
        modalities.append(ModalityType.IMAGE_TO_VIDEO.value)

    if m_type in ("chat", "language") or not modalities:
        modalities.append(ModalityType.TEXT_TO_TEXT.value)
        if "vision" in slug_lower or "vl" in slug_lower:
            supports_image_input = True

    # Pricing
    pricing = raw.get("pricing") or {}
    input_price = float(pricing.get("input") or 0.0)
    output_price = float(pricing.get("output") or 0.0)

    capabilities: Dict[str, Any] = {
        "supports_typography": "flux" in slug_lower,
        "supports_negative_prompt": True,
        "max_aspect_ratios": ["1:1", "16:9", "9:16", "4:3"],
    }

    return ModelInfo(
        provider="together",
        slug=slug,
        display_name=name,
        modalities=list(set(modalities)),
        supports_image_input=supports_image_input,
        context_length=raw.get("context_length"),
        pricing={
            "prompt_per_1k": input_price * 1000.0,
            "completion_per_1k": output_price * 1000.0,
        },
        capabilities=capabilities,
        status="available",
        source="curated" if any(p in slug_lower for p in ["meta-llama", "deepseek", "qwen", "mistral", "black-forest-labs", "minimax", "wan"]) else "custom",
        last_verified_at=datetime.now(timezone.utc),
    )
