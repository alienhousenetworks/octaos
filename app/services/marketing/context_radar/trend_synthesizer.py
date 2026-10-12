"""Trend Synthesizer — The Human Marketer Angle Engine.

Connects the dots between:
  - Brand/Product Knowledge (what we sell and why it matters)
  - Calendar Events (when the world is paying attention)
  - Industry News Signals (what's trending and relevant)

Produces creative briefs that represent how a senior human marketer would
intersect the brand's story with the moment in culture or industry.

Usage:
    synthesizer = TrendSynthesizer(db, tenant_id, llm_gateway)
    brief = await synthesizer.synthesize_angle(
        brand_knowledge=...,
        calendar_events=...,
        news_signals=...,
        platform="linkedin",
    )
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Video model defaults per platform aspect ratio
_PLATFORM_VIDEO_DEFAULTS = {
    "linkedin":  {"aspect_ratio": "16:9", "provider": "together", "model": "minimax/video-01"},
    "instagram": {"aspect_ratio": "9:16",  "provider": "together", "model": "Wan-AI/Wan2.1-T2V-14B"},
    "facebook":  {"aspect_ratio": "1:1",   "provider": "together", "model": "minimax/video-01"},
    "twitter":   {"aspect_ratio": "16:9", "provider": "together", "model": "Lightricks/LTX-Video"},
    "youtube":   {"aspect_ratio": "16:9", "provider": "openrouter", "model": "luma/ray-2"},
    "tiktok":    {"aspect_ratio": "9:16",  "provider": "together", "model": "Wan-AI/Wan2.1-T2V-14B"},
}
_PLATFORM_IMAGE_DEFAULTS = {
    "linkedin":  {"provider": "together", "model": "black-forest-labs/FLUX.1-dev"},
    "instagram": {"provider": "together", "model": "black-forest-labs/FLUX.1-dev"},
    "facebook":  {"provider": "together", "model": "black-forest-labs/FLUX.1-schnell"},
    "twitter":   {"provider": "openrouter", "model": "ideogram/ideogram-v2"},
}


class CreativeBrief:
    """Structured creative brief from the Trend Synthesizer."""

    def __init__(self, data: Dict[str, Any]):
        self.topic: str = data.get("topic", "Brand Innovation")
        self.hook: str = data.get("hook", "")
        self.narrative_angle: str = data.get("narrative_angle", "")
        self.call_to_action: str = data.get("call_to_action", "Learn more")
        self.media_type: str = data.get("media_type", "image")  # image | video
        self.image_prompt: Optional[str] = data.get("image_prompt")
        self.video_prompt: Optional[str] = data.get("video_prompt")
        self.video_provider: str = data.get("video_provider", "together")
        self.video_model: Optional[str] = data.get("video_model")
        self.image_provider: str = data.get("image_provider", "together")
        self.image_model: Optional[str] = data.get("image_model")
        self.aspect_ratio: str = data.get("aspect_ratio", "1:1")
        self.context_trigger: str = data.get("context_trigger", "general")  # calendar | news | general
        self.trigger_name: str = data.get("trigger_name", "")
        self.hashtags: List[str] = data.get("hashtags", [])

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


class TrendSynthesizer:
    """
    Produces creative briefs by connecting brand knowledge with real-world context.
    Uses the LLM to generate the human-marketer-style angle.
    """

    def __init__(self, db: Session, tenant_id: str, llm_gateway: Any):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = llm_gateway

    async def synthesize_angle(
        self,
        brand_knowledge: Dict[str, Any],
        calendar_events: List[Dict[str, Any]],
        news_signals: List[Dict[str, Any]],
        platform: str = "linkedin",
        generate_video: bool = True,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> CreativeBrief:
        """
        Core method: build the creative brief for the auto-mode post.
        
        Priority: calendar event > news signal > general brand moment.
        """
        # ── Determine the primary context trigger ─────────────────────
        trigger_type = "general"
        trigger_name = ""
        trigger_hook = ""

        if calendar_events:
            nearest = calendar_events[0]
            trigger_type = "calendar"
            trigger_name = nearest.get("name", "Event")
            trigger_hook = nearest.get("hook", "")
        elif news_signals:
            top_signal = news_signals[0]
            trigger_type = "news"
            trigger_name = top_signal.get("topic", "News")
            trigger_hook = str(top_signal.get("signal", ""))[:200]

        # ── Resolve media defaults for this platform ───────────────────
        vid_defaults = _PLATFORM_VIDEO_DEFAULTS.get(platform.lower(), _PLATFORM_VIDEO_DEFAULTS["linkedin"])
        img_defaults = _PLATFORM_IMAGE_DEFAULTS.get(platform.lower(), _PLATFORM_IMAGE_DEFAULTS["linkedin"])
        aspect_ratio = vid_defaults["aspect_ratio"]

        # ── Build LLM prompt ───────────────────────────────────────────
        company_name = brand_knowledge.get("company_name", "Brand")
        industry = brand_knowledge.get("industry", "Technology")
        usp = brand_knowledge.get("brand_identity", {}).get("usp", "")
        products = brand_knowledge.get("products_catalog", [])
        product_names = ", ".join([p.get("name", "") for p in products[:3]])
        motion_tokens = brand_knowledge.get("motion_tokens", {})
        compliance_rules = brand_knowledge.get("compliance_rules", [])

        calendar_context = ""
        if calendar_events:
            cal_lines = [
                f"• {e.get('name', 'Event')} ({e.get('date', 'Upcoming')}, {e.get('days_away', e.get('days_until', 0))} days away): {e.get('hook', '')}"
                for e in calendar_events[:3]
            ]
            calendar_context = "Upcoming Calendar Moments:\n" + "\n".join(cal_lines)

        news_context = ""
        if news_signals:
            news_lines = [f"• {s['topic']}: {s['signal'][:120]}" for s in news_signals[:3]]
            news_context = "Industry Innovation Signals:\n" + "\n".join(news_lines)

        platform_guidance = {
            "linkedin": "Long-form thought leadership, professional tone, B2B value focus, max 2-3 hashtags",
            "instagram": "Visual-first storytelling, aspirational tone, 5-10 hashtags, short punchy caption",
            "facebook": "Community-focused, conversational, moderate length, 2-4 hashtags",
            "twitter": "Concise and punchy, under 280 chars for tweet hook, 1-2 hashtags",
        }.get(platform.lower(), "Professional, engaging, brand-aligned")

        media_instruction = (
            "Generate both an image_prompt AND a video_prompt."
            if generate_video
            else "Generate only an image_prompt."
        )

        prompt = f"""You are a Senior Marketing Strategist at {company_name}.

BRAND CONTEXT:
- Company: {company_name} | Industry: {industry}
- Products/Services: {product_names}
- USP: {usp[:200] if usp else 'Industry-leading automation and intelligence platform'}
- Brand Tone: {brand_knowledge.get('brand_identity', {}).get('tone', 'Professional, innovative, authoritative')}

REAL-WORLD CONTEXT (today's marketing intelligence):
{calendar_context}
{news_context}

TARGET PLATFORM: {platform.upper()} — {platform_guidance}

YOUR TASK:
Create a strategic marketing creative brief that connects {company_name}'s brand story 
with the most relevant context above. Think like a human senior marketer who knows 
when to trend-jack, when to be thoughtful, and how to tie the company's products 
to the moment in a way that feels authentic — not forced.

{media_instruction}

For the image_prompt: Write a detailed visual scene description (cinematic, commercial-grade).
  Style: {motion_tokens.get('video_aesthetic', 'modern minimal cinematic')}
  Colors: primary {motion_tokens.get('primary_color', '#059669')}, accent {motion_tokens.get('accent_color', '#38BDF8')}

For the video_prompt (if needed): Describe a 6-8 second cinematic scene with motion, camera direction, and emotional tone.
  The video should work for {platform.upper()} in {aspect_ratio} aspect ratio.

COMPLIANCE RULES (never violate):
{chr(10).join(f'- {r}' for r in compliance_rules[:5])}

Return JSON with exactly these keys:
{{
  "topic": "Campaign topic in 5-8 words",
  "hook": "The opening sentence / headline — the most compelling line that stops the scroll",
  "narrative_angle": "2-3 sentence body copy explaining the connection between brand and context",
  "call_to_action": "Specific CTA (e.g. 'Book a free demo', 'Comment your thoughts', 'Share this with your team')",
  "image_prompt": "Detailed visual prompt for AI image generation",
  "video_prompt": "Detailed cinematic scene for AI video generation (or null if not needed)",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}"""

        try:
            from app.services.knowledge_os.entity_extractor import extract_json_safe
            raw = await self.llm.complete(
                prompt=prompt,
                system_prompt="You are a JSON-generating marketing AI. Output ONLY raw JSON.",
                provider=provider or "openrouter",
                model=model,
                max_tokens=1500,
            )
            data = extract_json_safe(raw)
            if not isinstance(data, dict) or not data.get("hook"):
                raise ValueError("Invalid response from trend synthesizer LLM")

            # Attach media routing defaults
            data["context_trigger"] = trigger_type
            data["trigger_name"] = trigger_name
            data["aspect_ratio"] = aspect_ratio
            if generate_video:
                data["media_type"] = "video"
                data["video_provider"] = vid_defaults["provider"]
                data["video_model"] = vid_defaults["model"]
            else:
                data["media_type"] = "image"
            data["image_provider"] = img_defaults["provider"]
            data["image_model"] = img_defaults["model"]

            return CreativeBrief(data)

        except Exception as exc:
            logger.error(f"[TrendSynthesizer] LLM failed: {exc}")
            # Graceful fallback brief
            fallback_hook = trigger_hook or f"{company_name} is transforming {industry}."
            return CreativeBrief({
                "topic": f"{company_name} × {trigger_name or 'Innovation'}",
                "hook": fallback_hook[:120],
                "narrative_angle": f"{company_name} helps {industry} teams achieve more with less effort.",
                "call_to_action": "Learn more about what we do",
                "image_prompt": f"Cinematic commercial photography for {company_name}, {motion_tokens.get('video_aesthetic', 'modern minimal')}, {motion_tokens.get('primary_color', '#059669')} accents, professional studio lighting",
                "video_prompt": f"6-second cinematic product showcase for {company_name}, smooth camera dolly forward, {motion_tokens.get('video_aesthetic', 'minimal tech')}, {aspect_ratio} aspect ratio",
                "hashtags": ["#Innovation", f"#{industry.replace(' ', '')}"],
                "context_trigger": trigger_type,
                "trigger_name": trigger_name,
                "aspect_ratio": aspect_ratio,
                "media_type": "video" if generate_video else "image",
                "video_provider": vid_defaults["provider"],
                "video_model": vid_defaults["model"],
                "image_provider": img_defaults["provider"],
                "image_model": img_defaults["model"],
            })
