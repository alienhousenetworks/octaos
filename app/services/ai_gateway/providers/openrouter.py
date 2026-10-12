"""OpenRouter multimodal provider adapter."""
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.services.ai_gateway.providers.base import (
    ProviderAdapter,
    ModelInfo,
    TextReq,
    TextResult,
    ImageReq,
    ImageResult,
    VideoReq,
    JobHandle,
    JobStatus,
)
from app.services.ai_gateway.providers.normalize import normalize_openrouter_model

logger = logging.getLogger(__name__)


class OpenRouterAdapter:
    name: str = "openrouter"

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://octaos.ai",
            "X-Title": "OctaOS Campaign Planner",
        }

    async def list_models(self, api_key: str) -> List[ModelInfo]:
        """Fetch models from OpenRouter GET /api/v1/models and normalize."""
        url = "https://openrouter.ai/api/v1/models"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(api_key), timeout=25.0)
            if resp.status_code != 200:
                raise Exception(f"OpenRouter list_models failed ({resp.status_code}): {resp.text}")
            data = resp.json().get("data", [])
            return [normalize_openrouter_model(m) for m in data if isinstance(m, dict) and m.get("id")]

    async def generate_text(self, req: TextReq, api_key: str) -> TextResult:
        """Call OpenRouter chat completions endpoint."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        messages = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})

        if req.images:
            user_content = [{"type": "text", "text": req.prompt}]
            for img in req.images:
                mime = img.get("mime_type", "image/png")
                b64 = img.get("data", "")
                url_val = img.get("url")
                if url_val:
                    user_content.append({"type": "image_url", "image_url": {"url": url_val}})
                elif b64:
                    user_content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": req.prompt})

        payload: Dict[str, Any] = {
            "model": req.model,
            "messages": messages,
            "temperature": req.temperature,
        }
        if req.max_tokens:
            payload["max_tokens"] = req.max_tokens
        if req.response_format:
            payload["response_format"] = req.response_format

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers(api_key), json=payload, timeout=60.0)
            if resp.status_code != 200:
                raise Exception(f"OpenRouter text generation error ({resp.status_code}): {resp.text}")
            res_json = resp.json()
            choices = res_json.get("choices", [])
            if not choices:
                raise Exception(f"OpenRouter returned no choices: {res_json}")
            content = choices[0].get("message", {}).get("content", "")
            usage = res_json.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
            
            # Approximate cost calculation from usage
            cost = float(usage.get("total_cost", 0.0) or 0.0)

            return TextResult(
                content=content,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=cost,
                model_used=req.model,
                raw_response=res_json,
            )

    async def generate_image(self, req: ImageReq, api_key: str) -> ImageResult:
        """Execute image generation or image-to-image via OpenRouter images endpoint."""
        url = "https://openrouter.ai/api/v1/images"
        payload: Dict[str, Any] = {
            "model": req.model,
            "prompt": req.prompt,
            "aspect_ratio": req.aspect_ratio,
        }
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt
        if req.reference_image_url:
            payload["reference_image"] = req.reference_image_url

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers(api_key), json=payload, timeout=90.0)
            if resp.status_code == 200:
                data = resp.json()
                img_url = ""
                if "data" in data and len(data["data"]) > 0:
                    img_url = data["data"][0].get("url") or data["data"][0].get("b64_json") or ""
                elif "url" in data:
                    img_url = data["url"]
                
                if not img_url:
                    raise Exception(f"OpenRouter image generation returned no URL: {data}")
                
                return ImageResult(
                    image_url=img_url,
                    cost_usd=float(data.get("cost", 0.0) or 0.0),
                    model_used=req.model,
                    raw_response=data,
                )
            else:
                # If images endpoint returned 404 or model is routed via chat
                raise Exception(f"OpenRouter image generation error ({resp.status_code}): {resp.text}")

    async def submit_video(self, req: VideoReq, api_key: str) -> JobHandle:
        """Submit asynchronous video generation request to OpenRouter videos endpoint."""
        url = "https://openrouter.ai/api/v1/videos"
        payload: Dict[str, Any] = {
            "model": req.model,
            "prompt": req.prompt,
            "aspect_ratio": req.aspect_ratio,
            "duration": req.duration_seconds,
        }
        if req.reference_image_url:
            payload["image_url"] = req.reference_image_url
        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers(api_key), json=payload, timeout=40.0)
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                job_id = data.get("id") or data.get("job_id") or data.get("data", {}).get("id")
                if not job_id:
                    # If direct response contained video URL immediately
                    direct_url = data.get("video_url") or data.get("url")
                    if direct_url:
                        job_id = f"direct_{direct_url}"
                    else:
                        raise Exception(f"OpenRouter video submission returned no job ID: {data}")
                return JobHandle(job_id=str(job_id), provider=self.name, model=req.model)
            else:
                raise Exception(f"OpenRouter video submission error ({resp.status_code}): {resp.text}")

    async def poll_video(self, handle: JobHandle, api_key: str) -> JobStatus:
        """Poll status of asynchronous OpenRouter video job."""
        if handle.job_id.startswith("direct_"):
            return JobStatus(
                job_id=handle.job_id,
                status="completed",
                result_url=handle.job_id.replace("direct_", ""),
            )

        url = f"https://openrouter.ai/api/v1/videos/{handle.job_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(api_key), timeout=25.0)
            if resp.status_code != 200:
                return JobStatus(
                    job_id=handle.job_id,
                    status="failed",
                    error=f"HTTP {resp.status_code}: {resp.text}",
                )
            data = resp.json()
            raw_status = (data.get("status") or "").lower()
            if raw_status in ("completed", "succeeded", "success"):
                vid_url = data.get("video_url") or data.get("url") or (data.get("data") or [{}])[0].get("url")
                return JobStatus(job_id=handle.job_id, status="completed", result_url=vid_url)
            elif raw_status in ("failed", "error"):
                return JobStatus(
                    job_id=handle.job_id,
                    status="failed",
                    error=data.get("error", "Video generation failed"),
                )
            else:
                return JobStatus(
                    job_id=handle.job_id,
                    status="in_progress",
                    progress_pct=float(data.get("progress", 0.0) or 0.0),
                )
