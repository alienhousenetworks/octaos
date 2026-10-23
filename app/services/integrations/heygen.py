"""Native HeyGen v3 Video API integration for OctaOS."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.credentials import get_decrypted_credential

logger = logging.getLogger(__name__)


class HeyGenError(Exception):
    """Safe exception for HeyGen operations without leaking upstream secrets."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class HeyGenClient:
    """Asynchronous client for HeyGen v3 Video API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.heygen.com",
        timeout: float = 60.0,
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise HeyGenError("HeyGen API key is missing or empty.", 401)
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute safe HTTP request to HeyGen API."""
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    params=params,
                )
        except httpx.TimeoutException as exc:
            logger.warning(f"[HeyGenClient] Request to {path} timed out.")
            raise HeyGenError("HeyGen request timed out.", 504) from exc
        except httpx.HTTPError as exc:
            logger.error(f"[HeyGenClient] Network connection error for {path}: {exc}")
            raise HeyGenError("Could not connect to HeyGen.", 502) from exc

        if response.status_code >= 400:
            logger.warning(
                f"[HeyGenClient] Upstream returned HTTP {response.status_code} for {path}: {response.text[:200]}"
            )
            if response.status_code == 429:
                raise HeyGenError("HeyGen rate limit reached. Try again later.", 429)
            if response.status_code in (401, 403):
                raise HeyGenError("HeyGen rejected the API key or its permissions.", 401)
            if response.status_code == 404:
                raise HeyGenError("HeyGen resource was not found.", 404)
            raise HeyGenError(f"HeyGen API request failed ({response.status_code}).", 502)

        try:
            payload = response.json()
        except ValueError as exc:
            raise HeyGenError("HeyGen returned invalid JSON.", 502) from exc

        if not isinstance(payload, dict):
            raise HeyGenError("Unexpected HeyGen response format.", 502)

        return payload

    async def validate_key(self) -> Dict[str, Any]:
        """Validate the HeyGen API key via /v3/users/me or fallback /v2/user/me."""
        try:
            result = await self.request("GET", "/v3/users/me")
            data = result.get("data", result)
            return {"valid": True, "user": data}
        except HeyGenError as exc:
            if exc.status_code == 404:
                # Try v2 user endpoint if v3 user is unavailable
                try:
                    result = await self.request("GET", "/v2/user/me")
                    data = result.get("data", result)
                    return {"valid": True, "user": data}
                except Exception:
                    pass
            raise exc

    async def create_video_agent(
        self, prompt: str, mode: str = "generate"
    ) -> Dict[str, Any]:
        """Trigger an AI video agent generation."""
        result = await self.request(
            "POST",
            "/v3/video-agents",
            json={"prompt": prompt, "mode": mode},
        )
        return result.get("data", result)

    async def get_video_agent_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve progress and video ID for a video agent session."""
        result = await self.request("GET", f"/v3/video-agents/{session_id}")
        return result.get("data", result)

    async def get_video(self, video_id: str) -> Dict[str, Any]:
        """Retrieve video render details and final downloadable/streamable URL."""
        result = await self.request("GET", f"/v3/videos/{video_id}")
        return result.get("data", result)


def get_heygen_client(db: Session, tenant_id: str) -> HeyGenClient:
    """Resolve decrypted HeyGen API key for a tenant with system environment fallback."""
    key, _ = get_decrypted_credential(db, tenant_id, "heygen")
    if not key:
        key = settings.HEYGEN_API_KEY
    if not key:
        raise HeyGenError(
            "HeyGen API key is not configured. Please add your HeyGen API key in Settings → API Keys.",
            400,
        )
    return HeyGenClient(api_key=key)
