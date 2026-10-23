"""HeyGen AI Video Provider Adapter for OctaOS AI Gateway."""
from __future__ import annotations

import logging
from typing import List, Optional
from datetime import datetime, timezone

from app.services.ai_gateway.providers.base import (
    ProviderAdapter,
    ModelInfo,
    ModalityType,
    TextReq,
    TextResult,
    ImageReq,
    ImageResult,
    VideoReq,
    JobHandle,
    JobStatus,
)
from app.services.integrations.heygen import HeyGenClient, HeyGenError

logger = logging.getLogger(__name__)


class HeyGenAdapter(ProviderAdapter):
    """Adapter integrating HeyGen v3 Video API into OctaOS Model Registry."""

    name: str = "heygen"

    async def list_models(self, api_key: str) -> List[ModelInfo]:
        """Return curated models for HeyGen."""
        return [
            ModelInfo(
                provider=self.name,
                slug="heygen/v3-video-agent",
                display_name="HeyGen Video Agent",
                modalities=[ModalityType.TEXT_TO_VIDEO.value],
                supports_image_input=False,
                pricing={"per_second_usd": 0.05},
                capabilities={
                    "avatar_presenter": True,
                    "voice_synthesis": True,
                    "aspect_ratios": ["16:9", "9:16", "1:1"],
                },
                status="available",
                source="curated",
                last_verified_at=datetime.now(timezone.utc),
            )
        ]

    async def generate_text(self, req: TextReq, api_key: str) -> TextResult:
        raise NotImplementedError("HeyGen does not provide text-to-text completion.")

    async def generate_image(self, req: ImageReq, api_key: str) -> ImageResult:
        raise NotImplementedError("HeyGen does not provide text-to-image generation.")

    async def submit_video(self, req: VideoReq, api_key: str) -> JobHandle:
        """Submit a video generation brief to HeyGen."""
        client = HeyGenClient(api_key=api_key)
        try:
            res = await client.create_video_agent(prompt=req.prompt, mode="generate")
            session_id = res.get("session_id") or res.get("id") or res.get("video_id")
            if not session_id:
                # Sometimes direct video URL is returned for cached/synced calls
                direct_url = res.get("video_url") or res.get("url")
                if direct_url:
                    session_id = f"direct_{direct_url}"
                else:
                    raise HeyGenError(f"HeyGen did not return a session or video ID: {res}")

            model_name = req.model or "heygen/v3-video-agent"
            return JobHandle(job_id=str(session_id), provider=self.name, model=model_name)
        except HeyGenError:
            raise
        except Exception as exc:
            logger.error(f"[HeyGenAdapter] Error submitting video: {exc}")
            raise HeyGenError(f"Failed to submit video to HeyGen: {exc}") from exc

    async def poll_video(self, handle: JobHandle, api_key: str) -> JobStatus:
        """Poll HeyGen session or video render status."""
        if handle.job_id.startswith("direct_"):
            return JobStatus(
                job_id=handle.job_id,
                status="completed",
                result_url=handle.job_id.replace("direct_", ""),
            )

        client = HeyGenClient(api_key=api_key)
        job_id = handle.job_id

        try:
            # Check if this is a video_id vs session_id
            if job_id.startswith("vid_") or job_id.startswith("video_"):
                data = await client.get_video(job_id)
                raw_status = (data.get("status") or "").lower()
                video_url = data.get("video_url") or data.get("url")
                if raw_status in ("completed", "success", "succeeded", "ready") and video_url:
                    return JobStatus(job_id=job_id, status="completed", result_url=video_url)
                elif raw_status in ("failed", "error"):
                    return JobStatus(
                        job_id=job_id,
                        status="failed",
                        error=data.get("error") or "HeyGen video rendering failed.",
                    )
                return JobStatus(job_id=job_id, status="in_progress")

            # Otherwise poll session
            session_data = await client.get_video_agent_session(job_id)
            raw_status = (session_data.get("status") or "").lower()
            video_info = session_data.get("video") or {}
            video_id = video_info.get("video_id") or session_data.get("video_id")
            video_url = video_info.get("video_url") or session_data.get("video_url")

            if (raw_status in ("completed", "success", "succeeded", "ready") or video_info.get("status") == "completed") and video_url:
                return JobStatus(job_id=job_id, status="completed", result_url=video_url)

            if raw_status in ("failed", "error") or video_info.get("status") == "failed":
                return JobStatus(
                    job_id=job_id,
                    status="failed",
                    error=session_data.get("error") or video_info.get("error") or "HeyGen session failed.",
                )

            # If session generated a video_id but no URL yet, check the video directly
            if video_id and not video_url:
                try:
                    vid_data = await client.get_video(video_id)
                    vid_status = (vid_data.get("status") or "").lower()
                    vid_url = vid_data.get("video_url") or vid_data.get("url")
                    if vid_status in ("completed", "success", "succeeded", "ready") and vid_url:
                        return JobStatus(job_id=job_id, status="completed", result_url=vid_url)
                    elif vid_status in ("failed", "error"):
                        return JobStatus(
                            job_id=job_id,
                            status="failed",
                            error=vid_data.get("error") or "HeyGen video rendering failed.",
                        )
                except Exception:
                    pass

            return JobStatus(job_id=job_id, status="in_progress")

        except HeyGenError as exc:
            return JobStatus(job_id=job_id, status="failed", error=exc.message)
        except Exception as exc:
            logger.error(f"[HeyGenAdapter] Error polling video {job_id}: {exc}")
            return JobStatus(job_id=job_id, status="failed", error=str(exc))
