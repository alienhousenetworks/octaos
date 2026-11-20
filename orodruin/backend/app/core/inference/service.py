"""Unified Local-First Inference Service.

Fixed configuration driven by environment variables (no Model Manager UI or
runtime switching). Calls OpenAI-compatible local text/vision endpoints and
dedicated image/video worker HTTP services. Zero model weights are downloaded
or loaded inside the API process.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from app.config import settings


class InferenceError(RuntimeError):
    """Raised when a local inference worker is unreachable or returns an error."""


class InferenceService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        text_model: Optional[str] = None,
        vision_model: Optional[str] = None,
        image_worker_url: Optional[str] = None,
        image_model: Optional[str] = None,
        video_worker_url: Optional[str] = None,
        video_model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.base_url = (base_url or settings.ai_base_url).rstrip("/")
        self.text_model = text_model or settings.ai_text_model
        self.vision_model = vision_model or settings.ai_vision_model
        self.image_worker_url = (image_worker_url or settings.image_worker_url).rstrip("/")
        self.image_model = image_model or settings.image_model
        self.video_worker_url = (video_worker_url or settings.video_worker_url).rstrip("/")
        self.video_model = video_model or settings.video_model
        self.timeout = timeout

    def config_summary(self) -> dict[str, Any]:
        return {
            "provider": settings.ai_provider,
            "base_url": self.base_url,
            "text_model": self.text_model,
            "vision_model": self.vision_model,
            "image_model": self.image_model,
            "video_model": self.video_model,
            "external_llm_enabled": settings.enable_external_llm,
        }

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.text_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                raise InferenceError(f"Text inference failed ({self.text_model}): {exc}") from exc

    async def generate_structured(
        self,
        prompt: str,
        schema_hint: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        sys_msg = (
            f"{system_prompt or 'You are a precise analytical engine.'}\n"
            f"Return ONLY valid JSON matching this schema:\n{schema_hint}"
        )
        raw = await self.generate_text(
            prompt=prompt,
            system_prompt=sys_msg,
            temperature=temperature,
            max_tokens=1500,
        )
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                raise ValueError("Expected JSON object.")
            return parsed
        except Exception as exc:
            raise InferenceError(f"Structured JSON parse failed: {exc}") from exc

    async def analyze_image(
        self,
        image_url_or_b64: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> str:
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url_or_b64}},
                    ],
                }
            ],
            "temperature": temperature,
            "max_tokens": 800,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(f"{self.base_url}/chat/completions", json=payload)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                raise InferenceError(f"Vision inference failed ({self.vision_model}): {exc}") from exc

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
    ) -> dict[str, Any]:
        payload = {
            "model": self.image_model,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(f"{self.image_worker_url}/generate", json=payload)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                raise InferenceError(f"Image worker failed ({self.image_model}): {exc}") from exc

    async def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        num_frames: int = 49,
        fps: int = 16,
    ) -> dict[str, Any]:
        payload = {
            "model": self.video_model,
            "prompt": prompt,
            "image_url": image_url,
            "num_frames": num_frames,
            "fps": fps,
        }
        async with httpx.AsyncClient(timeout=max(self.timeout, 300.0)) as client:
            try:
                resp = await client.post(f"{self.video_worker_url}/generate", json=payload)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                raise InferenceError(f"Video worker failed ({self.video_model}): {exc}") from exc
