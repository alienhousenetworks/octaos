"""LinkedIn REST API client for member and organization posts."""
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

LINKEDIN_API = "https://api.linkedin.com/rest"
LINKEDIN_VERSION = "202405"


class LinkedInClient:
    def __init__(self, access_token: str, settings: Optional[Dict[str, Any]] = None):
        self.access_token = access_token
        self.settings = settings or {}

    def _headers(self, content_type: str = "application/json") -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": content_type,
            "LinkedIn-Version": LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def _get(self, path: str) -> Dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{LINKEDIN_API}/{path.lstrip('/')}", headers=self._headers())
            if resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn GET {path} failed: {resp.text}")
            return resp.json()

    async def _post(self, path: str, body: Dict) -> Dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{LINKEDIN_API}/{path.lstrip('/')}",
                headers=self._headers(),
                json=body,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn POST {path} failed: {resp.text}")
            if resp.status_code == 201 and resp.headers.get("x-restli-id"):
                return {"id": resp.headers["x-restli-id"]}
            if resp.text:
                return resp.json()
            return {}

    async def resolve_author_urn(self) -> str:
        org_urn = self.settings.get("organization_urn")
        if org_urn:
            return org_urn

        # OpenID userinfo (modern LinkedIn apps)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code == 200:
                sub = resp.json().get("sub")
                if sub:
                    return f"urn:li:person:{sub}"

        # Legacy fallback
        me = await self._get_legacy_me()
        person_id = me.get("id")
        if person_id:
            return f"urn:li:person:{person_id}"
        raise RuntimeError("Could not resolve LinkedIn author URN.")

    async def _get_legacy_me(self) -> Dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn profile lookup failed: {resp.text}")
            return resp.json()

    async def register_image_upload(self, author_urn: str) -> tuple:
        body = {
            "initializeUploadRequest": {
                "owner": author_urn,
            }
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{LINKEDIN_API}/images?action=initializeUpload",
                headers=self._headers(),
                json=body,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn image upload init failed: {resp.text}")
            value = resp.json().get("value", {})
            return value.get("uploadUrl"), value.get("image")

    async def upload_image_binary(self, upload_url: str, image_bytes: bytes, content_type: str) -> None:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.put(
                upload_url,
                content=image_bytes,
                headers={"Content-Type": content_type},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"LinkedIn image binary upload failed: {resp.text}")

    async def publish_post(
        self,
        text: str,
        *,
        image_url: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_content_type: str = "image/jpeg",
    ) -> str:
        author = await self.resolve_author_urn()

        post_body: Dict[str, Any] = {
            "author": author,
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        if image_url or image_bytes:
            upload_url, image_urn = await self.register_image_upload(author)
            if image_bytes:
                await self.upload_image_binary(upload_url, image_bytes, image_content_type)
            elif image_url:
                from app.services.media.storage import download_bytes
                content, mime = await download_bytes(image_url)
                await self.upload_image_binary(upload_url, content, mime)

            post_body["content"] = {
                "media": {
                    "id": image_urn,
                }
            }

        result = await self._post("posts", post_body)
        return result.get("id", "")
