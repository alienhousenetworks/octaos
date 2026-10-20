"""NVIDIA NIM provider adapter for multimodal model registry."""
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.services.ai_gateway.providers.base import (
    ProviderAdapter,
    ModelInfo,
    TextReq,
    TextResult,
    ModalityType,
)

logger = logging.getLogger(__name__)


class NvidiaAdapter:
    name: str = "nvidia"

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self, api_key: str) -> List[ModelInfo]:
        """Fetch models from NVIDIA NIM GET /v1/models or return known supported models."""
        url = "https://integrate.api.nvidia.com/v1/models"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self._headers(api_key), timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    models = []
                    for m in data:
                        mid = m.get("id")
                        if mid:
                            models.append(ModelInfo(
                                provider="nvidia",
                                slug=mid,
                                display_name=mid.split("/")[-1].replace("-", " ").title(),
                                modalities=[ModalityType.TEXT_TO_TEXT.value],
                                status="available",
                            ))
                    if models:
                        return models
        except Exception as e:
            logger.debug(f"[NvidiaAdapter] Error listing remote models: {e}")

        # Fallback to known primary NIM models
        return [
            ModelInfo(
                provider="nvidia",
                slug="meta/llama-3.2-11b-vision-instruct",
                display_name="Llama 3.2 11B Vision Instruct",
                modalities=[ModalityType.TEXT_TO_TEXT.value],
                status="available",
            ),
            ModelInfo(
                provider="nvidia",
                slug="meta/llama-3.2-90b-vision-instruct",
                display_name="Llama 3.2 90B Vision Instruct",
                modalities=[ModalityType.TEXT_TO_TEXT.value],
                status="available",
            ),
            ModelInfo(
                provider="nvidia",
                slug="nvidia/llama-3.1-nemotron-70b-instruct",
                display_name="Llama 3.1 Nemotron 70B Instruct",
                modalities=[ModalityType.TEXT_TO_TEXT.value],
                status="available",
            ),
        ]

    async def generate_text(self, req: TextReq, api_key: str) -> TextResult:
        """Call NVIDIA NIM chat completions endpoint."""
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        messages = []
        if req.system_prompt:
            messages.append({"role": "system", "content": req.system_prompt})
        messages.append({"role": "user", "content": req.prompt})

        from app.services.ai_gateway.adapters import resolve_nvidia_model
        clean_model = resolve_nvidia_model(req.model)

        payload = {
            "model": clean_model,
            "messages": messages,
            "temperature": req.temperature or 0.2,
            "max_tokens": req.max_tokens or 1024,
            "stream": False,
        }
        if req.response_format:
            payload["response_format"] = req.response_format

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers(api_key), json=payload, timeout=60.0)
            if resp.status_code != 200:
                raise Exception(f"NVIDIA NIM text generation error ({resp.status_code}): {resp.text}")
            res_json = resp.json()
            choices = res_json.get("choices", [])
            if not choices:
                raise Exception(f"NVIDIA NIM returned no choices: {res_json}")
            content = choices[0].get("message", {}).get("content", "")
            usage = res_json.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)

            return TextResult(
                content=content,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=0.0,
                model_used=clean_model,
                raw_response=res_json,
            )
