"""Visual Intent & Media Analyzer (Stage 1 & 2 of Universal Visual Creation).

Deconstructs raw user or campaign prompt into structured creative intent,
classifying deliverables, archetypes, constraints, and reference locks.
"""
from typing import Dict, Any, List, Optional
import uuid
import re

from app.services.marketing.visual_creative.contracts import VisualIntentInputContract


class VisualIntentAnalyzer:
    """Understands user creative intent and normalizes to the Input Contract."""

    ARCHETYPES = {
        "luxury_product": ["luxury", "perfume", "watch", "jewelry", "cosmetics", "product launch", "bottle", "packaging"],
        "fine_art": ["painting", "watercolor", "oil painting", "canvas", "brushwork", "charcoal", "sketch", "fine art", "impressionist"],
        "cinematic_video": ["film", "cinematic", "movie", "teaser", "trailer", "shot list", "commercial film", "video"],
        "social_creator": ["ugc", "influencer", "tiktok", "reel", "creator", "selfie", "vlog", "social clip", "short"],
        "editorial_poster": ["poster", "cover", "typography", "magazine", "editorial layout", "banner", "headline", "flyer"],
        "infographic": ["diagram", "infographic", "chart", "instructional", "data visual", "architecture schematic"],
        "asset_edit": ["retouch", "upscale", "edit", "replace background", "fix", "inpaint", "restyle"]
    }

    @classmethod
    def classify_archetype(cls, text: str, deliverable: str = "image") -> str:
        """Categorize creative domain to govern specialist assembly."""
        lowered = text.lower()
        if deliverable in ("video", "reel", "short") or any(k in lowered for k in cls.ARCHETYPES["cinematic_video"]):
            if any(k in lowered for k in cls.ARCHETYPES["social_creator"]):
                return "social_creator"
            return "cinematic_video"

        for archetype, keywords in cls.ARCHETYPES.items():
            if any(k in lowered for k in keywords):
                return archetype

        return "commercial_photography"

    @classmethod
    def infer_aspect_ratio(cls, platform: str, deliverable: str = "image") -> str:
        p = (platform or "instagram").lower()
        if deliverable in ("video", "reel", "short"):
            if p in ("reels", "tiktok", "shorts", "story", "stories", "instagram_story"):
                return "9:16"
            return "16:9"

        if p in ("instagram", "instagram_feed"):
            return "1:1"
        elif p in ("reels", "stories", "story", "tiktok"):
            return "9:16"
        elif p in ("linkedin", "twitter", "x", "facebook", "youtube"):
            return "16:9"
        elif p in ("pinterest",):
            return "2:3"
        return "1:1"

    @classmethod
    def analyze(
        cls,
        raw_prompt: str,
        deliverable: Optional[str] = None,
        platform: Optional[str] = None,
        reference_assets: Optional[List[str]] = None,
        brand_tokens: Optional[Dict[str, Any]] = None,
        aspect_ratio: Optional[str] = None,
        must_preserve: Optional[List[str]] = None,
    ) -> VisualIntentInputContract:
        """Convert unstructured creative request into normalized VisualIntentInputContract."""
        clean_prompt = (raw_prompt or "").strip()
        ref_list = reference_assets or []
        b_tokens = brand_tokens or {}

        # Determine deliverable
        inferred_deliverable = deliverable or ("video" if any(w in clean_prompt.lower() for w in ["video", "clip", "reel", "animation", "motion"]) else "image")
        inferred_platform = platform or "instagram"
        inferred_ar = aspect_ratio or cls.infer_aspect_ratio(inferred_platform, inferred_deliverable)

        # Extract subject from prompt
        subject = clean_prompt
        # Clean common directive prefixes
        for prefix in ["create an image of", "generate a photo of", "create a video of", "make a picture of", "produce a"]:
            if clean_prompt.lower().startswith(prefix):
                subject = clean_prompt[len(prefix):].strip()
                break

        # Identify archetype
        archetype = cls.classify_archetype(clean_prompt, deliverable=inferred_deliverable)

        # Style direction from brand tokens or archetype
        style_direction = []
        if b_tokens.get("aesthetic_mood"):
            style_direction.append(b_tokens["aesthetic_mood"])
        if archetype == "luxury_product":
            style_direction.extend(["high-end commercial lighting", "accurate reflections", "pristine material finishes"])
        elif archetype == "fine_art":
            style_direction.extend(["visible tactile brushwork", "pigment layering", "classical painterly composition"])
        elif archetype == "social_creator":
            style_direction.extend(["authentic UGC framing", "natural ambient lighting", "native smartphone realism"])
        elif archetype == "cinematic_video":
            style_direction.extend(["deliberate camera kinematics", "24fps cinema grading", "motivated lighting"])

        # Preserved items
        preserves = list(must_preserve or [])
        if ref_list:
            preserves.append("Subject silhouette and primary identity from reference asset")
        if b_tokens.get("company_name"):
            preserves.append(f"Brand identity: {b_tokens['company_name']}")

        # Avoidances (anti-AI defaults + specifics)
        avoids = [
            "plastic over-smoothed skin",
            "impossible geometry",
            "duplicated limbs or malformed hands",
            "fake illegible text labels",
            "excessive teal-orange color grading",
            "watermarks or stock photo artifacts"
        ]

        duration = 5 if inferred_deliverable == "video" else None

        return VisualIntentInputContract(
            request_id=str(uuid.uuid4()),
            deliverable=inferred_deliverable,
            subject=subject or "Commercial brand focal centerpiece",
            purpose=b_tokens.get("promo_goal") or "Brand visual elevation",
            audience=b_tokens.get("target_persona") or "Target customer",
            platform=inferred_platform,
            style_direction=style_direction,
            emotion=b_tokens.get("tone") or "authoritative and premium",
            must_preserve=preserves,
            must_include=[b_tokens["primary_color"]] if b_tokens.get("primary_color") else [],
            must_avoid=avoids,
            aspect_ratio=inferred_ar,
            duration_seconds=duration,
            reference_assets=ref_list,
            brand_constraints=b_tokens,
            assumptions=[f"Inferred media archetype: {archetype}"]
        )
