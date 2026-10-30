"""Deterministic Media Prompt Compiler.

Workstream C:
- Translates structured CreativeIntentJSON into target-specific syntax
- Custom templates for Midjourney v6.1, FLUX.1, DALL-E 3, Google Imagen 3, and Pika/Veo/Runway
- Enforces anti-samey lexicon sampling and strict negative constraint handling
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.services.marketing.compiler.lexicon import (
    sample_lexicon,
    TARGET_NEGATIVE_PROMPTS,
)


class CreativeIntentJSON(BaseModel):
    """Structured creative intent emitted by small LLM."""
    subject: str = Field(..., description="Primary focal subject or physical product")
    action_or_state: str = Field(..., description="Action, posture, or interaction occurring")
    environment_setting: str = Field(..., description="Physical backdrop, architectural context")
    emotional_mood: str = Field(..., description="Tonal atmosphere (e.g., contemplative, energetic, rigorous)")
    shot_type: str = Field("medium shot", description="Camera framing: macro, low-angle wide, eye-level medium, Dutch angle")
    lighting_intent: str = Field("soft diffused key light", description="Lighting setup description")
    negative_space_direction: str = Field("balanced", description="top, bottom, left_40pct, right_40pct, centered")
    brand_style_id: Optional[str] = Field(None, description="UUID or token identifier from Brand Kit")
    color_accents: List[str] = Field(default_factory=list, description="Specific hex or color tokens")


class VideoShotPlan(BaseModel):
    """Structured video shot specification."""
    scene_description: str
    duration_seconds: int = 5
    camera_movement: str = "slow cinematic dolly forward at 0.5m/s"
    focal_motion: str = "subject subtly turns gaze toward window"
    atmosphere_notes: str = "subtle ambient dust motes catching backlighting"
    aspect_ratio: str = "16:9"
    hook_3s: Optional[str] = None
    voiceover_script: Optional[str] = None
    caption_style: Optional[str] = "kinetic_bold_center"
    audio_direction: Optional[str] = "ambient_tech_rise"


class MediaPromptCompiler:
    """Deterministic compiler transforming CreativeIntentJSON into target-specific media prompts."""

    @staticmethod
    def get_aspect_ratio_for_platform(platform: str, media_type: str = "image") -> str:
        p = platform.lower()
        if media_type == "video":
            if p in ("reels", "tiktok", "shorts", "instagram_story"):
                return "9:16"
            return "16:9"
        
        # Image aspect ratios
        if p in ("instagram", "instagram_feed"):
            return "1:1"
        elif p in ("reels", "stories", "story"):
            return "9:16"
        elif p in ("linkedin", "twitter", "x", "facebook"):
            return "16:9"
        return "1:1"

    @classmethod
    def compile_midjourney(
        cls,
        intent: CreativeIntentJSON,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> str:
        """Compile intent for Midjourney v6.1 syntax."""
        lexicon = sample_lexicon(seed_key)
        cam = lexicon["camera"]
        lighting = lexicon["lighting"]
        film = lexicon["film"]
        arch = lexicon["architecture"]
        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")

        colors = ", ".join(intent.color_accents) if intent.color_accents else "curated brand tones"
        neg_space = f"with {intent.negative_space_direction.replace('_', ' ')} for clean negative space" if intent.negative_space_direction != "balanced" else ""

        # Compose photographic Midjourney prompt
        prompt_parts = [
            f"{intent.shot_type} of {intent.subject}, {intent.action_or_state}",
            f"set within {intent.environment_setting or arch}",
            f"atmosphere is {intent.emotional_mood}",
            f"lighting: {intent.lighting_intent or lighting}",
            f"color palette: {colors}, {film}",
            f"shot on {cam['body']} with {cam['lens']} at {cam['aperture']}, {cam['shutter']}",
            f"ultra-detailed tactile micro-textures, authentic skin pores, subsurface scattering, zero artificial smoothing",
            neg_space,
        ]
        clean_prompt = ", ".join([p.strip() for p in prompt_parts if p.strip()])

        # Midjourney parameters
        ar_param = f"--ar {ar}"
        style_param = "--v 6.1 --style raw"
        no_param = f"--no {TARGET_NEGATIVE_PROMPTS['midjourney']}"

        sref_url = (visual_style or {}).get("sref_url")
        sref_param = f"--sref {sref_url}" if sref_url else ""

        return f"{clean_prompt} {ar_param} {no_param} {sref_param} {style_param}".strip()

    @classmethod
    def compile_flux(
        cls,
        intent: CreativeIntentJSON,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """Compile intent for FLUX.1 Pro natural language descriptive prose."""
        lexicon = sample_lexicon(seed_key)
        cam = lexicon["camera"]
        lighting = lexicon["lighting"]
        film = lexicon["film"]
        arch = lexicon["architecture"]
        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")

        colors = ", ".join(intent.color_accents) if intent.color_accents else "cohesive brand color harmony"
        
        # FLUX excels at cohesive narrative prose
        prose_prompt = (
            f"An editorial photograph in {intent.shot_type}. "
            f"The scene captures {intent.subject}, currently {intent.action_or_state}. "
            f"The environment is {intent.environment_setting or arch}, evoking a {intent.emotional_mood} atmosphere. "
            f"Illumination is characterized by {intent.lighting_intent or lighting}. "
            f"Color grading follows {film}, integrating subtle accents of {colors}. "
            f"Captured on {cam['body']} paired with {cam['lens']} at {cam['aperture']}, "
            f"revealing tactile material micro-textures and natural organic detail without digital over-sharpening."
        )

        return {
            "prompt": prose_prompt,
            "aspect_ratio": ar,
            "guidance_scale": 3.5,
            "model": "flux-1-pro",
        }

    @classmethod
    def compile_dalle3(
        cls,
        intent: CreativeIntentJSON,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """Compile intent for DALL-E 3 (Positive-only framing, zero negative words)."""
        lexicon = sample_lexicon(seed_key)
        cam = lexicon["camera"]
        lighting = lexicon["lighting"]
        arch = lexicon["architecture"]

        # DALL-E 3 must NEVER have negative words (e.g. "no plastic", "no blur" causes DALL-E to add them)
        # Instead, describe what SHOULD be there with pristine physical reality
        positive_prompt = (
            f"A high-end editorial photograph of {intent.subject}, {intent.action_or_state}. "
            f"The backdrop is {intent.environment_setting or arch}. "
            f"Lighting: {intent.lighting_intent or lighting}. "
            f"The mood is {intent.emotional_mood}. "
            f"Composition: {intent.shot_type} with authentic physical textures, realistic fabric weave, "
            f"subtle natural skin details, and clean commercial aesthetic. "
            f"Camera perspective matches an editorial magazine feature shot on {cam['body']}."
        )

        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")
        size = "1024x1024" if ar == "1:1" else ("1792x1024" if ar == "16:9" else "1024x1792")

        return {
            "prompt": positive_prompt,
            "size": size,
            "quality": "hd",
            "style": "natural",
        }

    @classmethod
    def compile_imagen(
        cls,
        intent: CreativeIntentJSON,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """Compile intent for Google Imagen 3 API."""
        lexicon = sample_lexicon(seed_key)
        cam = lexicon["camera"]
        lighting = lexicon["lighting"]
        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")

        structured_prompt = (
            f"{intent.shot_type} photograph of {intent.subject}, {intent.action_or_state}, "
            f"setting: {intent.environment_setting}, mood: {intent.emotional_mood}, "
            f"lighting: {intent.lighting_intent or lighting}, "
            f"shot on {cam['body']} with {cam['lens']}, natural textures and colors."
        )

        return {
            "prompt": structured_prompt,
            "aspect_ratio": ar,
            "negative_prompt": TARGET_NEGATIVE_PROMPTS["imagen"],
        }

    @classmethod
    def compile_video_shot_list(
        cls,
        shot_plan: VideoShotPlan,
        seed_key: str = "default_video_seed",
    ) -> Dict[str, Any]:
        """Compile cinematic video prompt and Reel production metadata for Pika, Wan2.1, MiniMax, or Kling."""
        lexicon = sample_lexicon(seed_key)
        lighting = lexicon["lighting"]

        motion_prompt = (
            f"Cinematic {shot_plan.aspect_ratio} video sequence, {shot_plan.duration_seconds} seconds. "
            f"Scene: {shot_plan.scene_description}. "
            f"Camera movement: {shot_plan.camera_movement}. "
            f"Subject dynamics: {shot_plan.focal_motion}. "
            f"Lighting & atmosphere: {lighting}, {shot_plan.atmosphere_notes}. "
            f"Frame rate: 24fps cinema standard, seamless temporal coherence, steady motion."
        )

        return {
            "prompt": motion_prompt,
            "duration": shot_plan.duration_seconds,
            "aspect_ratio": shot_plan.aspect_ratio,
            "negative_prompt": TARGET_NEGATIVE_PROMPTS["video"],
            "hook_3s": shot_plan.hook_3s,
            "voiceover_script": shot_plan.voiceover_script,
            "caption_style": shot_plan.caption_style or "kinetic_bold_center",
            "audio_direction": shot_plan.audio_direction or "ambient_tech_rise",
        }

    @classmethod
    def compile_carousel_slides(
        cls,
        headline: str,
        takeaways: List[str],
        brand_colors: Optional[List[str]] = None,
        cta: str = "Save & Share this framework",
    ) -> Dict[str, Any]:
        """Compile a 5-slide high-retention carousel blueprint for LinkedIn and Instagram document posts."""
        colors = brand_colors or ["#0F172A", "#38BDF8", "#FFFFFF"]
        slides = [
            {
                "slide_number": 1,
                "role": "hook_cover",
                "title": headline,
                "subtitle": "Swipe for the complete breakdown →",
                "bg_color": colors[0],
                "accent_color": colors[1] if len(colors) > 1 else "#38BDF8",
            }
        ]
        for idx, point in enumerate(takeaways[:4], start=2):
            slides.append({
                "slide_number": idx,
                "role": "content_pillar",
                "step_label": f"0{idx - 1} / 0{min(4, len(takeaways))}",
                "body": point,
                "bg_color": "#F8FAFC",
                "text_color": "#0F172A",
            })
        slides.append({
            "slide_number": len(slides) + 1,
            "role": "save_cta",
            "title": "Save this breakdown for your next strategy session.",
            "subtitle": cta,
            "bg_color": colors[0],
            "accent_color": colors[1] if len(colors) > 1 else "#38BDF8",
        })
        return {
            "format": "carousel_pdf",
            "slide_count": len(slides),
            "slides": slides,
        }

    @classmethod
    def compile_recraft(
        cls,
        intent: CreativeIntentJSON,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """Compile intent for Recraft v3 (vector graphics, clean brand icons, sharp typography)."""
        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")
        colors = ", ".join(intent.color_accents) if intent.color_accents else "brand primary accents"
        prompt = (
            f"High-end corporate graphic design illustration of {intent.subject}, {intent.action_or_state}. "
            f"Style: clean modern editorial vector, pristine vector outlines, palette accents of {colors}. "
            f"Negative space: {intent.negative_space_direction}. Atmosphere: {intent.emotional_mood}. "
            f"Zero clutter, minimalist Swiss design precision."
        )
        return {
            "prompt": prompt,
            "aspect_ratio": ar,
            "style": "vector_illustration",
        }

    @classmethod
    def compile_ideogram(
        cls,
        intent: CreativeIntentJSON,
        headline_text: Optional[str] = None,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """Compile intent for Ideogram v2 (flawless in-image typography and poster layouts)."""
        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")
        lexicon = sample_lexicon(seed_key)
        arch = lexicon["architecture"]
        type_str = f'featuring bold typography text reading "{headline_text[:40]}"' if headline_text else "with clean typographic title space"
        prompt = (
            f"A bold graphic design poster {type_str}. "
            f"Centerpiece: {intent.shot_type} of {intent.subject}, {intent.action_or_state} in {intent.environment_setting or arch}. "
            f"Lighting: {intent.lighting_intent}. Color accents: {', '.join(intent.color_accents)}. "
            f"Modern editorial typography, flawless alignment, clean commercial look."
        )
        return {
            "prompt": prompt,
            "aspect_ratio": ar,
            "style_type": "DESIGN",
        }

    @classmethod
    def compile_image_to_image(
        cls,
        intent: CreativeIntentJSON,
        reference_image_url: str,
        mode: str = "canny",
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """Compile intent for image+text conditioning (FLUX Canny/Redux/Depth)."""
        ar = cls.get_aspect_ratio_for_platform(platform, media_type="image")
        lexicon = sample_lexicon(seed_key)
        cam = lexicon["camera"]
        lighting = lexicon["lighting"]

        if mode == "canny":
            prompt = (
                f"Preserve structural edge contours and exact geometric silhouette from reference image. "
                f"Transform lighting to {intent.lighting_intent or lighting}, set in {intent.environment_setting}, "
                f"shot on {cam['body']} with {cam['lens']}. Atmosphere: {intent.emotional_mood}."
            )
        elif mode == "redux":
            prompt = (
                f"Apply high-fidelity brand visual aesthetic and color palette from reference image to {intent.subject}. "
                f"Action: {intent.action_or_state}. Lighting: {intent.lighting_intent}. Texture: tactile editorial."
            )
        else:
            prompt = (
                f"Depth-guided synthesis maintaining spatial layout from reference. "
                f"{intent.shot_type} of {intent.subject}, {intent.action_or_state}. Setting: {intent.environment_setting}."
            )

        return {
            "prompt": prompt,
            "reference_image_url": reference_image_url,
            "aspect_ratio": ar,
            "mode": mode,
        }

    @classmethod
    def compile_for_target(
        cls,
        target_provider: str,
        intent: CreativeIntentJSON,
        visual_style: Optional[Dict[str, Any]] = None,
        seed_key: str = "default_seed",
        platform: str = "instagram",
        reference_image_url: Optional[str] = None,
        model_slug: Optional[str] = None,
        headline_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Universal dispatcher for capability-driven prompt compilation."""
        provider = (target_provider or "together").lower()
        model_str = (model_slug or "").lower()

        # 1. Reference image conditioning (Image+Text to Image)
        if reference_image_url:
            mode = "canny" if "canny" in model_str else ("redux" if "redux" in model_str else "depth")
            compiled = cls.compile_image_to_image(intent, reference_image_url, mode=mode, visual_style=visual_style, seed_key=seed_key, platform=platform)
            return {"provider": provider, **compiled}

        # 2. Vector / typography specialists
        if "recraft" in provider or "recraft" in model_str:
            compiled = cls.compile_recraft(intent, visual_style, seed_key, platform)
            return {"provider": "openrouter", **compiled}
        elif "ideogram" in provider or "ideogram" in model_str:
            compiled = cls.compile_ideogram(intent, headline_text=headline_text, visual_style=visual_style, seed_key=seed_key, platform=platform)
            return {"provider": "openrouter", **compiled}

        # 3. Standard photorealistic engines
        if "midjourney" in provider:
            return {"provider": "midjourney", "prompt": cls.compile_midjourney(intent, visual_style, seed_key, platform)}
        elif "flux" in provider or "together" in provider or "flux" in model_str:
            compiled = cls.compile_flux(intent, visual_style, seed_key, platform)
            return {"provider": provider, **compiled}
        elif "dalle" in provider or "openai" in provider:
            compiled = cls.compile_dalle3(intent, visual_style, seed_key, platform)
            return {"provider": "openai", **compiled}
        elif "imagen" in provider or "gemini" in provider:
            compiled = cls.compile_imagen(intent, visual_style, seed_key, platform)
            return {"provider": "gemini", **compiled}
        else:
            # Fallback to FLUX style natural language
            compiled = cls.compile_flux(intent, visual_style, seed_key, platform)
            return {"provider": provider, **compiled}
