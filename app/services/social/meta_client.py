"""Meta Graph API client for Facebook Pages and Instagram Business."""
import logging
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"


class MetaGraphClient:
    def __init__(self, access_token: str, settings: Optional[Dict[str, Any]] = None):
        self.access_token = access_token
        self.settings = settings or {}

    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        params = dict(params or {})
        params["access_token"] = self.access_token
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(f"{GRAPH_BASE}/{path.lstrip('/')}", params=params)
            if resp.status_code >= 400:
                raise RuntimeError(f"Meta API GET {path} failed: {resp.text}")
            return resp.json()

    async def _post(
        self,
        path: str,
        data: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: float = 120.0,
    ) -> Dict:
        params = {"access_token": self.access_token}
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{GRAPH_BASE}/{path.lstrip('/')}",
                params=params,
                data=data,
                json=json_body,
                files=files,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Meta API POST {path} failed: {resp.text}")
            return resp.json()

    async def refresh_long_lived_token(self, app_id: str, app_secret: str) -> str:
        data = await self._get(
            "oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": self.access_token,
            },
        )
        return data.get("access_token", self.access_token)

    async def resolve_page_context(self) -> Tuple[str, str, Optional[str]]:
        """Returns (page_id, page_access_token, instagram_business_account_id)."""
        page_id = self.settings.get("page_id")
        ig_id = self.settings.get("instagram_account_id")

        if page_id and self.settings.get("page_access_token"):
            token = self.settings["page_access_token"]
            if not ig_id:
                page = await self._get(f"{page_id}", {"fields": "instagram_business_account"})
                ig = page.get("instagram_business_account") or {}
                ig_id = ig.get("id")
            return page_id, token, ig_id

        accounts = await self._get(
            "me/accounts", {"fields": "id,name,access_token,instagram_business_account"}
        )
        pages = accounts.get("data", [])
        if not pages:
            raise RuntimeError(
                "No Facebook Pages found for this token. Use a Page Access Token with pages_show_list permission."
            )

        preferred_page = page_id
        for page in pages:
            if preferred_page and page.get("id") != preferred_page:
                continue
            token = page.get("access_token")
            if not token:
                continue
            ig = page.get("instagram_business_account") or {}
            return page["id"], token, ig.get("id") or ig_id

        first = pages[0]
        ig = first.get("instagram_business_account") or {}
        return first["id"], first["access_token"], ig.get("id")

    async def _upload_instagram_resumable(
        self,
        ig_id: str,
        page_token: str,
        *,
        media_type: str,
        caption: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> str:
        """
        Instagram direct binary upload via Meta Resumable Upload API.
        No public URL required — bytes go straight to rupload.facebook.com.
        """
        client = MetaGraphClient(page_token, self.settings)
        container = await client._post(
            f"{ig_id}/media",
            data={
                "upload_type": "resumable",
                "media_type": media_type,
                "caption": caption,
            },
        )

        creation_id = container.get("id")
        upload_uri = container.get("uri")
        if not creation_id or not upload_uri:
            raise RuntimeError(f"Instagram resumable container failed: {container}")

        async with httpx.AsyncClient(timeout=300.0) as http:
            upload_resp = await http.post(
                upload_uri,
                content=file_bytes,
                headers={
                    "Authorization": f"OAuth {page_token}",
                    "offset": "0",
                    "file_size": str(len(file_bytes)),
                    "Content-Type": mime_type or "application/octet-stream",
                },
            )
            if upload_resp.status_code >= 400:
                raise RuntimeError(f"Instagram binary upload failed: {upload_resp.text}")

        published = await client._post(
            f"{ig_id}/media_publish",
            data={"creation_id": creation_id},
        )
        return published.get("id", creation_id)

    async def publish_facebook_post(
        self,
        message: str,
        *,
        link: Optional[str] = None,
        image_url: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/jpeg",
        video_bytes: Optional[bytes] = None,
        video_mime: str = "video/mp4",
    ) -> str:
        page_id, page_token, _ = await self.resolve_page_context()
        client = MetaGraphClient(page_token, self.settings)

        # Direct binary photo upload (no public URL needed)
        if image_bytes:
            ext = "jpg" if "jpeg" in image_mime else "png" if "png" in image_mime else "bin"
            result = await client._post(
                f"{page_id}/photos",
                data={"caption": message, "published": "true"},
                files={"source": (f"photo.{ext}", image_bytes, image_mime)},
            )
            return result.get("post_id") or result.get("id", "")

        # Direct binary video upload
        if video_bytes:
            ext = "mp4" if "mp4" in video_mime else "mov"
            result = await client._post(
                f"{page_id}/videos",
                data={"description": message, "published": "true"},
                files={"source": (f"video.{ext}", video_bytes, video_mime)},
                timeout=600.0,
            )
            return result.get("id", "")

        # Fallback: URL-based (when only remote URL available)
        if image_url and not link:
            result = await client._post(
                f"{page_id}/photos",
                data={"url": image_url, "caption": message},
            )
            return result.get("post_id") or result.get("id", "")

        payload: Dict[str, Any] = {"message": message}
        if link:
            payload["link"] = link
        result = await client._post(f"{page_id}/feed", data=payload)
        return result.get("id", "")

    async def publish_instagram_post(
        self,
        caption: str,
        *,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_mime: str = "image/jpeg",
        video_bytes: Optional[bytes] = None,
        video_mime: str = "video/mp4",
    ) -> str:
        _, page_token, ig_id = await self.resolve_page_context()
        if not ig_id:
            raise RuntimeError(
                "No Instagram Business Account linked to the Facebook Page. "
                "Link IG to your Page in Meta Business Suite."
            )

        # Direct binary upload — preferred, no ngrok/public URL needed
        if video_bytes:
            return await self._upload_instagram_resumable(
                ig_id,
                page_token,
                media_type="REELS",
                caption=caption,
                file_bytes=video_bytes,
                mime_type=video_mime,
            )

        if image_bytes:
            return await self._upload_instagram_resumable(
                ig_id,
                page_token,
                media_type="IMAGE",
                caption=caption,
                file_bytes=image_bytes,
                mime_type=image_mime,
            )

        # Fallback: URL-based container (requires Meta-accessible URL)
        client = MetaGraphClient(page_token, self.settings)
        if video_url:
            container = await client._post(
                f"{ig_id}/media",
                data={"media_type": "REELS", "video_url": video_url, "caption": caption},
            )
        elif image_url:
            container = await client._post(
                f"{ig_id}/media",
                data={"image_url": image_url, "caption": caption},
            )
        else:
            raise RuntimeError("Instagram requires image or video content.")

        creation_id = container.get("id")
        if not creation_id:
            raise RuntimeError(f"Instagram media container creation failed: {container}")

        published = await client._post(
            f"{ig_id}/media_publish",
            data={"creation_id": creation_id},
        )
        return published.get("id", "")
