import os
import logging
from typing import Any, Dict, Optional

from datetime import datetime, timezone, timedelta
import httpx

logger = logging.getLogger(__name__)

LINKEDIN_API = "https://api.linkedin.com/rest"
ORG_SCOPE = "w_organization_social"


class LinkedInOrgPermissionError(RuntimeError):
    """The token cannot publish as an organization."""


def parse_linkedin_scopes(raw: Optional[str]) -> set[str]:
    if not raw:
        return set()
    return {part for part in str(raw).replace(",", " ").split() if part}


def member_reauth_message(scopes: set[str], org_urn: Optional[str]) -> str:
    granted = " ".join(sorted(scopes)) or "none"
    if org_urn:
        return (
            "LinkedIn refused the company page because this token cannot post as an organization "
            f"(granted scopes: {granted}). "
            "Re-authorize in Settings → APIs & Integrations. "
            "Personal profile publishing needs openid, profile, and w_member_social. "
            "Company page publishing also needs the Community Management API product "
            "and the w_organization_social scope."
        )
    return (
        "LinkedIn token cannot identify the member to post as "
        f"(granted scopes: {granted}). "
        "Re-authorize in Settings → APIs & Integrations so the token includes "
        "openid, profile, and w_member_social."
    )


def select_linkedin_author(
    scopes: Optional[set[str]],
    *,
    org_urn: Optional[str],
    person_urn: Optional[str],
) -> str:
    """Choose the post author.

    ``scopes is None`` means the grants are unknown, so a configured organization
    is still attempted and the caller can fall back if LinkedIn rejects it.
    A known grant uses the organization only when ``w_organization_social`` is present.
    """
    if scopes is not None and ORG_SCOPE not in scopes:
        if person_urn:
            return person_urn
        raise RuntimeError(member_reauth_message(scopes, org_urn))
    if org_urn:
        return org_urn
    if person_urn:
        return person_urn
    raise RuntimeError(
        "Could not resolve a LinkedIn author. Re-authorize in Settings → APIs & Integrations."
    )


class LinkedInClient:
    _cached_working_version: Optional[str] = None

    def __init__(self, access_token: str, settings: Optional[Dict[str, Any]] = None):
        self.access_token = access_token
        self.settings = settings or {}
        self.publish_note = ""

    def _get_candidate_versions(self) -> list:
        now = datetime.now(timezone.utc)
        candidates = []
        if self.settings.get("linkedin_version"):
            candidates.append(str(self.settings["linkedin_version"]).strip())
        if os.environ.get("LINKEDIN_VERSION"):
            candidates.append(str(os.environ["LINKEDIN_VERSION"]).strip())
        if LinkedInClient._cached_working_version:
            candidates.append(LinkedInClient._cached_working_version)
        # Current month, previous months in UTC
        candidates.append(now.strftime("%Y%m"))
        candidates.append((now - timedelta(days=30)).strftime("%Y%m"))
        candidates.append((now - timedelta(days=60)).strftime("%Y%m"))
        candidates.extend(["202610", "202609", "202608", "202607", "202606", "202605", "202604", "202603", "202602", "202601", "202512", "202511", "202510"])
        seen = set()
        deduped = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        return deduped

    def _headers(self, content_type: str = "application/json", version: Optional[str] = None) -> Dict[str, str]:
        v = version or LinkedInClient._cached_working_version or self._get_candidate_versions()[0]
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": content_type,
            "LinkedIn-Version": v,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def _get(self, path: str) -> Dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            versions = self._get_candidate_versions()
            last_err = None
            for v in versions:
                resp = await client.get(f"{LINKEDIN_API}/{path.lstrip('/')}", headers=self._headers(version=v))
                if resp.status_code == 426 and "NONEXISTENT_VERSION" in resp.text:
                    logger.warning(f"LinkedIn API version {v} not active (426). Trying next version...")
                    last_err = resp.text
                    continue
                LinkedInClient._cached_working_version = v
                if resp.status_code >= 400:
                    raise RuntimeError(f"LinkedIn GET {path} failed: {resp.text}")
                return resp.json()
            raise RuntimeError(f"LinkedIn GET {path} failed (no active version): {last_err}")

    async def _post(self, path: str, body: Dict) -> Dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            versions = self._get_candidate_versions()
            last_err = None
            for v in versions:
                resp = await client.post(
                    f"{LINKEDIN_API}/{path.lstrip('/')}",
                    headers=self._headers(version=v),
                    json=body,
                )
                if resp.status_code == 426 and "NONEXISTENT_VERSION" in resp.text:
                    logger.warning(f"LinkedIn API version {v} not active (426). Trying next version...")
                    last_err = resp.text
                    continue
                LinkedInClient._cached_working_version = v
                if resp.status_code >= 400:
                    self._raise_linkedin_error(f"LinkedIn POST {path} failed: {resp.text}", resp.text)
                if resp.status_code == 201 and resp.headers.get("x-restli-id"):
                    return {"id": resp.headers["x-restli-id"]}
                if resp.text:
                    return resp.json()
                return {}
            raise RuntimeError(f"LinkedIn POST {path} failed (no active version): {last_err}")

    def _raise_linkedin_error(self, fallback: str, body: str) -> None:
        if "Organization permissions must be used" in body:
            raise LinkedInOrgPermissionError(member_reauth_message(
                parse_linkedin_scopes(self.settings.get("scope")),
                self._configured_org_urn(),
            ))
        raise RuntimeError(fallback)

    def _configured_org_urn(self) -> Optional[str]:
        org_urn = self.settings.get("organization_urn") or os.environ.get("LINKEDIN_ORGANIZATION_URN")
        if org_urn:
            return str(org_urn).strip()
        raw_id = self.settings.get("organization_id") or os.environ.get("LINKEDIN_ORGANIZATION_ID")
        if not raw_id:
            return None
        raw_id = str(raw_id).strip()
        if not raw_id:
            return None
        return raw_id if raw_id.startswith("urn:li:organization:") else f"urn:li:organization:{raw_id}"

    def _client_credentials(self) -> tuple:
        client_id = self.settings.get("client_id") or os.environ.get("LINKEDIN_CLIENT_ID")
        client_secret = self.settings.get("client_secret") or os.environ.get("LINKEDIN_CLIENT_SECRET")
        if not client_id or not client_secret:
            try:
                from dotenv import dotenv_values
                env_vals = dotenv_values(".env")
                client_id = client_id or env_vals.get("LINKEDIN_CLIENT_ID")
                client_secret = client_secret or env_vals.get("LINKEDIN_CLIENT_SECRET")
            except Exception:
                pass
        return client_id, client_secret

    async def ensure_granted_scopes(self) -> Optional[set[str]]:
        """Return granted scopes. None means introspection could not tell."""
        if "scope" in self.settings and isinstance(self.settings.get("scope"), str):
            return parse_linkedin_scopes(self.settings.get("scope"))

        client_id, client_secret = self._client_credentials()
        if not client_id or not client_secret:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://www.linkedin.com/oauth/v2/introspectToken",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "token": self.access_token,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except Exception as exc:
            logger.debug("LinkedIn token introspection failed: %s", exc)
            return None
        if resp.status_code >= 400:
            logger.warning("LinkedIn token introspection failed: %s", resp.status_code)
            return None
        scope = resp.json().get("scope") or ""
        self.settings["scope"] = scope
        return parse_linkedin_scopes(scope)

    async def _resolve_person_urn(self) -> Optional[str]:
        author_urn = self.settings.get("author_urn") or os.environ.get("LINKEDIN_AUTHOR_URN")
        if author_urn:
            return str(author_urn).strip()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if resp.status_code == 200:
                    sub = resp.json().get("sub")
                    if sub:
                        person = f"urn:li:person:{sub}"
                        self.settings["author_urn"] = person
                        return person
        except Exception as exc:
            logger.debug("LinkedIn userinfo lookup failed: %s", exc)

        try:
            me = await self._get_legacy_me()
            person_id = me.get("id")
            if person_id:
                person = f"urn:li:person:{person_id}"
                self.settings["author_urn"] = person
                return person
        except Exception as exc:
            logger.debug("LinkedIn legacy me lookup failed: %s", exc)
        return None

    async def resolve_author_urn(self) -> str:
        scopes = await self.ensure_granted_scopes()
        org_urn = self._configured_org_urn()
        person_urn = await self._resolve_person_urn()
        author = select_linkedin_author(scopes, org_urn=org_urn, person_urn=person_urn)
        if org_urn and author != org_urn:
            self.publish_note = (
                "Published as the connected LinkedIn member. "
                "This token does not include company page permission (w_organization_social)."
            )
        return author

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
            versions = self._get_candidate_versions()
            last_err = None
            for v in versions:
                resp = await client.post(
                    f"{LINKEDIN_API}/images?action=initializeUpload",
                    headers=self._headers(version=v),
                    json=body,
                )
                if resp.status_code == 426 and "NONEXISTENT_VERSION" in resp.text:
                    logger.warning(f"LinkedIn API version {v} not active for image upload (426). Trying next version...")
                    last_err = resp.text
                    continue
                LinkedInClient._cached_working_version = v
                if resp.status_code >= 400:
                    self._raise_linkedin_error(
                        f"LinkedIn image upload init failed: {resp.text}",
                        resp.text,
                    )
                value = resp.json().get("value", {})
                return value.get("uploadUrl"), value.get("image")
            raise RuntimeError(f"LinkedIn image upload init failed (no active version): {last_err}")

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
        try:
            return await self._create_post(
                author,
                text,
                image_url=image_url,
                image_bytes=image_bytes,
                image_content_type=image_content_type,
            )
        except LinkedInOrgPermissionError:
            person = await self._resolve_person_urn()
            if person and person != author:
                logger.warning("LinkedIn organization publish denied; retrying as member")
                self.publish_note = (
                    "Published as the connected LinkedIn member. "
                    "This token does not include company page permission (w_organization_social)."
                )
                return await self._create_post(
                    person,
                    text,
                    image_url=image_url,
                    image_bytes=image_bytes,
                    image_content_type=image_content_type,
                )
            raise

    async def _create_post(
        self,
        author: str,
        text: str,
        *,
        image_url: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_content_type: str = "image/jpeg",
    ) -> str:
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
