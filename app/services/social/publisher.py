"""Unified social media publishing orchestration."""
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.verticals import ContentPost
from app.services.credentials import get_decrypted_credential
from app.services.media.storage import ensure_public_url, resolve_media_bytes
from app.services.social.meta_client import MetaGraphClient
from app.services.social.linkedin_client import LinkedInClient

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    success: bool
    platform: str
    external_id: str = ""
    error: str = ""
    note: str = ""


class SocialPublisher:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def _resolve_image(self, post: ContentPost) -> Tuple[Optional[bytes], str, Optional[str]]:
        resolved = await resolve_media_bytes(post.image_url, default_mime="image/jpeg")
        if resolved:
            return resolved[0], resolved[1], None
        url = await ensure_public_url(post.image_url, prefix="img")
        return None, "image/jpeg", url

    async def _resolve_video(self, post: ContentPost) -> Tuple[Optional[bytes], str, Optional[str]]:
        resolved = await resolve_media_bytes(post.video_url, default_mime="video/mp4")
        if resolved:
            return resolved[0], resolved[1], None
        url = await ensure_public_url(post.video_url, prefix="vid", default_mime="video/mp4")
        return None, "video/mp4", url

    async def publish_post(self, post: ContentPost) -> PublishResult:
        platform = (post.platform or "").lower()

        try:
            if platform == "facebook":
                return await self._publish_facebook(post)
            if platform == "instagram":
                return await self._publish_instagram(post)
            if platform == "linkedin":
                return await self._publish_linkedin(post)
            return PublishResult(False, platform, error=f"Unsupported platform: {platform}")
        except Exception as exc:
            logger.exception("Publish failed for %s post %s", platform, post.id)
            return PublishResult(False, platform, error=str(exc))

    async def _ensure_meta_settings(self, token: str, settings: dict) -> dict:
        resolved = dict(settings or {})
        if resolved.get("page_id") and resolved.get("instagram_account_id"):
            return resolved
        try:
            import httpx
            from app.services.credentials import save_credential

            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(
                    "https://graph.facebook.com/v21.0/me/accounts",
                    params={
                        "access_token": token,
                        "fields": "id,name,access_token,instagram_business_account",
                    },
                )
                if resp.status_code < 400:
                    pages = (resp.json() or {}).get("data") or []
                    if pages:
                        page = pages[0]
                        resolved.setdefault("page_id", page.get("id"))
                        resolved.setdefault("page_name", page.get("name"))
                        if page.get("access_token"):
                            resolved.setdefault("page_access_token", page.get("access_token"))
                        ig = page.get("instagram_business_account") or {}
                        if ig.get("id"):
                            resolved.setdefault("instagram_account_id", ig.get("id"))
                        save_credential(self.db, self.tenant_id, "meta", token, settings=resolved)
        except Exception:
            logger.debug("Could not auto-discover Meta page/Instagram account settings", exc_info=True)
        return resolved

    async def _publish_facebook(self, post: ContentPost) -> PublishResult:
        token, settings = get_decrypted_credential(self.db, self.tenant_id, "meta")
        if not token:
            return PublishResult(False, "facebook", error="Missing Meta Graph API credential.")

        settings = await self._ensure_meta_settings(token, settings)
        img_bytes, img_mime, img_url = await self._resolve_image(post)
        vid_bytes, vid_mime, vid_url = await self._resolve_video(post)

        client = MetaGraphClient(token, settings)
        ext_id = await client.publish_facebook_post(
            post.content or "",
            link=vid_url or img_url if not vid_bytes and not img_bytes else None,
            image_url=img_url if not img_bytes else None,
            image_bytes=img_bytes,
            image_mime=img_mime,
            video_bytes=vid_bytes,
            video_mime=vid_mime,
        )
        return PublishResult(True, "facebook", external_id=ext_id)

    async def _publish_instagram(self, post: ContentPost) -> PublishResult:
        token, settings = get_decrypted_credential(self.db, self.tenant_id, "meta")
        if not token:
            return PublishResult(False, "instagram", error="Missing Meta Graph API credential.")

        settings = await self._ensure_meta_settings(token, settings)
        img_bytes, img_mime, img_url = await self._resolve_image(post)
        vid_bytes, vid_mime, vid_url = await self._resolve_video(post)

        if not img_bytes and not vid_bytes and not img_url and not vid_url:
            return PublishResult(
                False,
                "instagram",
                error="Instagram requires image or video content.",
            )

        client = MetaGraphClient(token, settings)
        ext_id = await client.publish_instagram_post(
            post.content or "",
            image_url=img_url,
            video_url=vid_url,
            image_bytes=img_bytes,
            image_mime=img_mime,
            video_bytes=vid_bytes,
            video_mime=vid_mime,
        )
        return PublishResult(True, "instagram", external_id=ext_id)

    async def _publish_linkedin(self, post: ContentPost) -> PublishResult:
        token, settings = get_decrypted_credential(self.db, self.tenant_id, "linkedin")
        if not token:
            return PublishResult(False, "linkedin", error="Missing LinkedIn API credential.")

        settings = dict(settings or {})
        had_scope = "scope" in settings
        had_author = bool(settings.get("author_urn"))
        img_bytes, img_mime, img_url = await self._resolve_image(post)

        client = LinkedInClient(token, settings)
        try:
            ext_id = await client.publish_post(
                post.content or "",
                image_url=img_url,
                image_bytes=img_bytes,
                image_content_type=img_mime,
            )
            return PublishResult(
                True,
                "linkedin",
                external_id=ext_id,
                note=client.publish_note or "",
            )
        finally:
            updates = {}
            if not had_scope and isinstance(settings.get("scope"), str):
                updates["scope"] = settings["scope"]
            if not had_author and settings.get("author_urn"):
                updates["author_urn"] = settings["author_urn"]
            if updates:
                try:
                    from app.services.credentials import save_credential
                    save_credential(self.db, self.tenant_id, "linkedin", token, settings=updates)
                except Exception:
                    logger.debug("Could not persist LinkedIn token metadata", exc_info=True)


async def publish_content_post(db: Session, post: ContentPost) -> PublishResult:
    publisher = SocialPublisher(db, post.tenant_id)
    return await publisher.publish_post(post)
