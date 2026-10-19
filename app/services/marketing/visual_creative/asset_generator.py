"""Asset Generator (Stage 5 of Universal Visual Creation).

Executes generation or editing via LLMGateway and tracks returned media assets.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AssetGenerator:
    """Dispatches media generation requests through LLMGateway."""

    def __init__(self, db_session, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id

    async def execute_generation(
        self,
        payload: Dict[str, Any],
        deliverable: str = "image",
    ) -> Dict[str, Any]:
        """Call LLMGateway for image or video generation."""
        from app.services.llm_gateway import LLMGateway
        gateway = LLMGateway(self.db, self.tenant_id)

        provider = payload.get("provider", "together")
        model = payload.get("model")
        prompt = payload.get("prompt", "")
        ref_url = payload.get("reference_image_url")
        ar = payload.get("aspect_ratio", "1:1")

        is_video = deliverable in ("video", "reel", "short")

        try:
            if is_video:
                result_url = await gateway.generate_video(
                    prompt=prompt,
                    provider=provider,
                    model=model,
                    reference_image_url=ref_url,
                    aspect_ratio=ar,
                )
            else:
                result_url = await gateway.generate_image(
                    prompt=prompt,
                    provider=provider,
                    model=model,
                    reference_image_url=ref_url,
                    aspect_ratio=ar,
                )

            if not result_url or result_url.startswith("error:"):
                return {
                    "success": False,
                    "url": None,
                    "error": result_url.replace("error:", "") if result_url else "Empty response from media provider",
                    "provider": provider,
                    "model": model,
                }

            return {
                "success": True,
                "url": result_url,
                "error": None,
                "provider": provider,
                "model": model,
            }

        except Exception as e:
            logger.error(f"[AssetGenerator] Media generation failed: {e}")
            return {
                "success": False,
                "url": None,
                "error": str(e),
                "provider": provider,
                "model": model,
            }
