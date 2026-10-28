"""Visual Model Router & Target-Syntax Compiler (Stage 4 of Universal Visual Creation).

Selects optimal model/adapter based on capabilities (aspect ratio, typography,
reference conditioning, video duration) and formats prompts into strict provider syntax.
"""
from typing import Dict, Any, Optional, Tuple
from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
)
from app.services.marketing.compiler.prompt_compiler import (
    MediaPromptCompiler,
    CreativeIntentJSON,
    VideoShotPlan,
)


class VisualModelRouter:
    """Routes creative brief to the best supported provider and compiles target syntax."""

    @classmethod
    def select_model(
        cls,
        intent: VisualIntentInputContract,
        brief: CreativeBrief,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        db_session: Optional[Any] = None,
        tenant_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Select provider and model slug matching capability requirements with key fallbacks."""
        is_video = intent.deliverable in ("video", "reel", "short")
        has_ref = len(intent.reference_assets) > 0

        # Video Routing
        if is_video:
            provider = (preferred_provider or "together").lower()
            if preferred_model:
                model = preferred_model
            elif provider == "together":
                model = "Wan-AI/Wan2.1-I2V-14B" if has_ref else "minimax/video-01"
            else:
                model = "kling-ai/kling-v1.5"

            # Provider fallback if selected provider is not configured
            if db_session and tenant_id and not preferred_provider:
                from app.services.llm_gateway import LLMGateway
                gw = LLMGateway(db_session, tenant_id)
                if not gw._get_api_key(provider):
                    for alt in ["together", "openrouter", "heygen"]:
                        if gw._get_api_key(alt):
                            provider = alt
                            model = "Wan-AI/Wan2.1-I2V-14B" if has_ref else "minimax/video-01" if alt == "together" else "kling-ai/kling-v1.5"
                            break
            return provider, model

        # Image Routing
        provider = (preferred_provider or "together").lower()
        if preferred_model:
            return provider, preferred_model

        # Check for typography/poster requirement
        lowered = f"{intent.subject} {brief.concept}".lower()
        if "poster" in lowered or "typography" in lowered or "headline" in lowered:
            provider, model = "openrouter", "ideogram/ideogram-v2"
        # Check for vector/graphic design
        elif "vector" in lowered or "icon" in lowered or "illustration" in lowered:
            provider, model = "openrouter", "recraft/recraft-v3"
        # Photorealistic / Standard
        elif provider == "openai":
            provider, model = "openai", "dall-e-3"
        elif provider == "gemini":
            provider, model = "gemini", "imagen-3.0-generate-002"
        elif provider == "together":
            model = "black-forest-labs/FLUX.1-canny" if has_ref else "black-forest-labs/FLUX.1-dev"
            provider, model = "together", model
        else:
            provider, model = provider, "black-forest-labs/FLUX.1-dev"

        # Provider fallback if selected provider is not configured
        if db_session and tenant_id and not preferred_provider:
            from app.services.llm_gateway import LLMGateway
            gw = LLMGateway(db_session, tenant_id)
            if not gw._get_api_key(provider):
                for alt in ["together", "openai", "openrouter"]:
                    if gw._get_api_key(alt):
                        provider = alt
                        if alt == "together":
                            model = "black-forest-labs/FLUX.1-canny" if has_ref else "black-forest-labs/FLUX.1-dev"
                        elif alt == "openai":
                            model = "dall-e-3"
                        else:
                            model = "recraft/recraft-v3"
                        break

        return provider, model

    @classmethod
    def compile_payload(
        cls,
        intent: VisualIntentInputContract,
        brief: CreativeBrief,
        provider: str,
        model: str,
        headline_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compile the creative brief into provider-specific syntax."""
        ref_url = intent.reference_assets[0] if intent.reference_assets else None

        # Build intermediate CreativeIntentJSON for prompt compiler
        intent_json = CreativeIntentJSON(
            subject=intent.subject,
            action_or_state="staged and composed with deliberate artistic intent",
            environment_setting=brief.lighting_setup,
            emotional_mood=brief.emotional_mood,
            shot_type=brief.camera_viewpoint,
            lighting_intent=brief.lighting_setup,
            negative_space_direction="right_40pct" if intent.aspect_ratio == "16:9" else "balanced",
            color_accents=brief.color_palette,
        )

        if intent.deliverable in ("video", "reel", "short"):
            shot_plan = VideoShotPlan(
                scene_description=brief.concept,
                duration_seconds=intent.duration_seconds or 5,
                camera_movement=brief.camera_viewpoint,
                focal_motion=f"{intent.subject} maintains physical coherence with natural dynamics",
                atmosphere_notes=brief.materials_and_surfaces,
                aspect_ratio=intent.aspect_ratio,
            )
            compiled = MediaPromptCompiler.compile_video_shot_list(
                shot_plan=shot_plan,
                seed_key=intent.request_id,
            )
            return {
                "provider": provider,
                "model": model,
                "prompt": compiled.get("prompt"),
                "aspect_ratio": intent.aspect_ratio,
                "duration": intent.duration_seconds or 5,
                "reference_image_url": ref_url,
            }

        compiled = MediaPromptCompiler.compile_for_target(
            target_provider=provider,
            intent=intent_json,
            visual_style={"palette": brief.color_palette},
            seed_key=intent.request_id,
            platform=intent.platform,
            reference_image_url=ref_url,
            model_slug=model,
            headline_text=headline_text or intent.subject,
        )

        return {
            "provider": provider,
            "model": model,
            "prompt": compiled.get("prompt") or brief.positive_prompt_blueprint,
            "aspect_ratio": intent.aspect_ratio,
            "reference_image_url": ref_url,
            **{k: v for k, v in compiled.items() if k not in ("provider", "prompt")},
        }
