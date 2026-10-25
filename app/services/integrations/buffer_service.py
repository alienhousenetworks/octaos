"""Buffer GraphQL API adapter with tenant-scoped OAuth token storage.

Tokens are stored as one encrypted JSON document in APICredential.encrypted_key.
OAuth refresh tokens rotate on every refresh and must be persisted immediately.
"""
from __future__ import annotations

import json
import logging
import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_api_key, encrypt_api_key
from app.models.base import APICredential

logger = logging.getLogger(__name__)
BUFFER_API_URL = "https://api.buffer.com"
BUFFER_TOKEN_URL = "https://auth.buffer.com/token"


class BufferAPIError(RuntimeError):
    """Safe, user-displayable Buffer API failure."""


def _load_credential(db: Session, tenant_id: str) -> Optional[APICredential]:
    return (
        db.query(APICredential)
        .filter(APICredential.tenant_id == tenant_id, APICredential.provider == "buffer")
        .first()
    )


def save_buffer_tokens(
    db: Session, tenant_id: str, token_data: Dict[str, Any], auth_type: str = "oauth"
) -> APICredential:
    """Encrypt access/refresh tokens at rest; never put secrets in settings JSON."""
    now = datetime.now(timezone.utc)
    payload = {
        "auth_type": auth_type,
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_at": (
            (now + timedelta(seconds=max(0, int(token_data.get("expires_in", 0)))))
            .isoformat()
            if token_data.get("expires_in") is not None else None
        ),
        "scope": token_data.get("scope", ""),
        "token_type": token_data.get("token_type", "Bearer"),
    }
    if not payload["access_token"]:
        raise BufferAPIError("Buffer did not return an access token.")
    row = _load_credential(db, tenant_id)
    encrypted = encrypt_api_key(json.dumps(payload))
    if row:
        row.encrypted_key = encrypted
        row.settings = {
            **(row.settings or {}),
            "connected": True,
            "auth_type": auth_type,
            "scope": payload["scope"],
            "updated_at": now.isoformat(),
        }
    else:
        row = APICredential(
            tenant_id=tenant_id,
            provider="buffer",
            encrypted_key=encrypted,
            settings={
                "connected": True,
                "auth_type": auth_type,
                "scope": payload["scope"],
                "updated_at": now.isoformat(),
            },
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def disconnect_buffer(db: Session, tenant_id: str) -> bool:
    row = _load_credential(db, tenant_id)
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


class BufferService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def _credential_and_tokens(self) -> tuple[APICredential, Dict[str, Any]]:
        row = _load_credential(self.db, self.tenant_id)
        if not row:
            raise BufferAPIError("Buffer is not connected for this workspace.")
        try:
            token_data = json.loads(decrypt_api_key(row.encrypted_key))
        except Exception as exc:
            raise BufferAPIError("Stored Buffer credentials could not be decrypted.") from exc
        return row, token_data

    async def _access_token(self) -> str:
        row, token_data = self._credential_and_tokens()
        expires_at = token_data.get("expires_at")
        if token_data.get("auth_type") == "oauth" and expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at)
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
            except ValueError:
                expiry = datetime.min.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc) + timedelta(seconds=90):
                refresh_token = token_data.get("refresh_token")
                if not refresh_token:
                    raise BufferAPIError("Buffer authorization expired. Reconnect Buffer.")
                if not settings.BUFFER_CLIENT_ID or not settings.BUFFER_CLIENT_SECRET:
                    raise BufferAPIError("Buffer OAuth client is not configured on this server.")
                form = {
                    "client_id": settings.BUFFER_CLIENT_ID,
                    "client_secret": settings.BUFFER_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
                try:
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        response = await client.post(BUFFER_TOKEN_URL, data=form)
                except httpx.HTTPError as exc:
                    raise BufferAPIError("Could not refresh Buffer authorization. Reconnect Buffer and retry.") from exc
                if response.status_code >= 400:
                    logger.warning("Buffer refresh failed with HTTP %s", response.status_code)
                    raise BufferAPIError("Buffer authorization expired. Reconnect Buffer.")
                refreshed = response.json()
                # Buffer refresh tokens are single-use; persist the replacement immediately.
                save_buffer_tokens(self.db, self.tenant_id, refreshed, auth_type="oauth")
                _, token_data = self._credential_and_tokens()
        token = token_data.get("access_token")
        if not token:
            raise BufferAPIError("Buffer access token is missing. Reconnect Buffer.")
        return token

    async def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token = await self._access_token()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    BUFFER_API_URL,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={"query": query, "variables": variables or {}},
                )
        except httpx.HTTPError as exc:
            raise BufferAPIError("Could not reach Buffer. Check connectivity and reconcile before retrying writes.") from exc
        if response.status_code == 401:
            raise BufferAPIError("Buffer rejected the authorization. Reconnect Buffer.")
        if response.status_code >= 400:
            logger.warning("Buffer API returned HTTP %s", response.status_code)
            raise BufferAPIError(f"Buffer API request failed (HTTP {response.status_code}).")
        body = response.json()
        if body.get("errors"):
            # Do not return provider response payloads that might contain sensitive context.
            messages = [str(item.get("message", "GraphQL error"))[:180] for item in body["errors"]]
            raise BufferAPIError("Buffer API: " + "; ".join(messages))
        return body.get("data") or {}

    async def account_and_channels(self) -> Dict[str, Any]:
        data = await self.graphql(
            """query OctaOSBufferAccount {
              account { id email organizations { id name } }
            }"""
        )
        account = data.get("account")
        if not account:
            raise BufferAPIError("Buffer returned no account. Check the granted account:read scope.")
        organizations = account.get("organizations") or []
        for organization in organizations:
            org_id = organization.get("id")
            if not org_id:
                organization["channels"] = []
                continue
            channel_data = await self.graphql(
                """query OctaOSBufferChannels($input: ChannelsInput!) {
                  channels(input: $input) { id name service }
                }""",
                {"input": {"organizationId": org_id}},
            )
            organization["channels"] = channel_data.get("channels") or []
        return account

    async def list_posts(
        self, *, organization_id: str, channel_ids: list[str], max_pages: int = 5
    ) -> list[Dict[str, Any]]:
        """Read recent Buffer queue/delivery states for reconciliation (no write retries)."""
        if not organization_id or not channel_ids:
            return []
        posts: list[Dict[str, Any]] = []
        cursor = None
        query = """query OctaOSBufferPosts($first: Int!, $after: String, $input: PostsInput!) {
          posts(first: $first, after: $after, input: $input) {
            edges { node { id status dueAt sentAt createdAt channelId externalLink } }
            pageInfo { hasNextPage endCursor }
          }
        }"""
        for _ in range(max(1, min(max_pages, 5))):
            variables = {
                "first": 100,
                "after": cursor,
                "input": {
                    "organizationId": organization_id,
                    "filter": {
                        "status": ["scheduled", "sending", "sent", "error"],
                        "channelIds": channel_ids,
                    },
                },
            }
            data = await self.graphql(query, variables)
            result = data.get("posts") or {}
            posts.extend(
                edge.get("node", {})
                for edge in (result.get("edges") or [])
                if edge.get("node")
            )
            page_info = result.get("pageInfo") or {}
            if not page_info.get("hasNextPage") or not page_info.get("endCursor"):
                break
            cursor = page_info["endCursor"]
        return posts

    async def create_post(
        self, *, channel_id: str, text: str, scheduled_at: Optional[datetime] = None,
        image_url: Optional[str] = None, video_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not channel_id or not text.strip():
            raise BufferAPIError("A Buffer channel and non-empty post text are required.")
        if image_url and video_url:
            raise BufferAPIError("Buffer publishing currently accepts one image or one video per post.")
        assets = []
        for kind, url in (("image", image_url), ("video", video_url)):
            if url:
                parsed = urlparse(url)
                if parsed.scheme != "https" or not parsed.hostname:
                    raise BufferAPIError("Buffer media must use a publicly accessible HTTPS URL.")
                hostname = parsed.hostname.lower().rstrip(".")
                if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
                    raise BufferAPIError("Buffer media URL must not point to a local host.")
                try:
                    address = ipaddress.ip_address(hostname)
                    if not address.is_global:
                        raise BufferAPIError("Buffer media URL must not point to a private or reserved IP address.")
                except ValueError:
                    pass
                assets.append({kind: {"url": url}})
        if scheduled_at:
            if scheduled_at.tzinfo is None:
                raise BufferAPIError("scheduled_at must include a timezone.")
            if scheduled_at <= datetime.now(timezone.utc):
                raise BufferAPIError("scheduled_at must be in the future; omit it to add the post to the Buffer queue.")
            mode = "customScheduled"
            due_at = scheduled_at.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            query = """mutation OctaOSCreatePost($input: CreatePostInput!) {
              createPost(input: $input) {
                ... on PostActionSuccess { post { id text dueAt channelId } }
                ... on MutationError { message }
              }
            }"""
            input_data = {
                "text": text, "channelId": channel_id, "schedulingType": "automatic",
                "mode": mode, "dueAt": due_at, "aiAssisted": True,
            }
            if assets:
                input_data["assets"] = assets
            variables = {"input": input_data}
        else:
            query = """mutation OctaOSCreatePost($input: CreatePostInput!) {
              createPost(input: $input) {
                ... on PostActionSuccess { post { id text dueAt channelId } }
                ... on MutationError { message }
              }
            }"""
            input_data = {
                "text": text, "channelId": channel_id, "schedulingType": "automatic",
                "mode": "addToQueue", "aiAssisted": True,
            }
            if assets:
                input_data["assets"] = assets
            variables = {"input": input_data}
        data = await self.graphql(query, variables)
        result = data.get("createPost") or {}
        if result.get("message"):
            raise BufferAPIError(str(result["message"])[:240])
        post = result.get("post")
        if not post or not post.get("id"):
            raise BufferAPIError("Buffer did not confirm that the post was created.")
        return post
