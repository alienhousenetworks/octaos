"""Tenant-scoped one-click Buffer connection and approved-post publishing."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.models.verticals import ContentPost
from app.services.integrations.buffer_service import (
    BUFFER_TOKEN_URL, BufferAPIError, BufferService, disconnect_buffer, save_buffer_tokens,
)

router = APIRouter()
BUFFER_AUTH_URL = "https://auth.buffer.com/auth"
BUFFER_SCOPES = "posts:read posts:write account:read offline_access"


def _state_cipher() -> Fernet:
    # Derive a stable Fernet key from the server-only signing secret; no extra secret is exposed.
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encode_state(payload: dict) -> str:
    return _state_cipher().encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def _decode_state(value: str) -> dict:
    try:
        payload = json.loads(_state_cipher().decrypt(value.encode(), ttl=600))
        issued_at = int(payload["issued_at"])
        if int(time.time()) - issued_at > 600 or int(time.time()) < issued_at:
            raise ValueError("expired state")
    except (InvalidToken, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Buffer connection state is invalid or expired.") from exc
    return payload


def _frontend_url(result: str) -> str:
    base = (settings.FRONTEND_BASE_URL or "http://localhost:3000").rstrip("/")
    return f"{base}/settings/integrations?buffer={result}"


class BufferAPIKeyRequest(BaseModel):
    api_key: str = Field(min_length=12, max_length=2048)


class BufferChannelMapRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=80)
    channel_id: str = Field(min_length=1, max_length=256)


class PublishPostRequest(BaseModel):
    channel_id: str = Field(min_length=1, max_length=256)
    scheduled_at: Optional[datetime] = None


@router.get("/connect")
def connect_buffer(
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.INTEGRATIONS, Action.UPDATE)),
):
    """Start Buffer OAuth 2.0 Authorization Code + PKCE flow."""
    if not settings.BUFFER_CLIENT_ID or not settings.BUFFER_CLIENT_SECRET or not settings.BUFFER_REDIRECT_URI:
        raise HTTPException(
            status_code=503,
            detail="Buffer one-click connection is not configured. Set BUFFER_CLIENT_ID and BUFFER_REDIRECT_URI.",
        )
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = _encode_state({
        "tenant_id": tenant_id, "user_id": user.id, "verifier": verifier,
        "issued_at": int(time.time()), "nonce": secrets.token_urlsafe(24),
    })
    params = {
        "client_id": settings.BUFFER_CLIENT_ID,
        "redirect_uri": settings.BUFFER_REDIRECT_URI,
        "response_type": "code",
        "scope": BUFFER_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "consent",
    }
    return {"url": f"{BUFFER_AUTH_URL}?{urlencode(params)}"}


@router.get("/callback")
async def buffer_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(deps.get_db),
):
    """OAuth callback uses encrypted short-lived state; no tenant comes from query parameters."""
    if not state:
        return RedirectResponse(_frontend_url("error"))
    try:
        payload = _decode_state(state)
        issued_at = int(payload["issued_at"])
        if int(time.time()) - issued_at > 600 or int(time.time()) < issued_at:
            raise ValueError("expired state")
        tenant_id, user_id, verifier = payload["tenant_id"], payload["user_id"], payload["verifier"]
    except (KeyError, ValueError, TypeError, HTTPException):
        return RedirectResponse(_frontend_url("error"))
    if error or not code:
        return RedirectResponse(_frontend_url("cancelled"))
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True)).first()
    if not user:
        return RedirectResponse(_frontend_url("error"))
    if not settings.BUFFER_CLIENT_ID or not settings.BUFFER_CLIENT_SECRET or not settings.BUFFER_REDIRECT_URI:
        return RedirectResponse(_frontend_url("not-configured"))
    form = {
        "client_id": settings.BUFFER_CLIENT_ID,
        "client_secret": settings.BUFFER_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.BUFFER_REDIRECT_URI,
        "code_verifier": verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(BUFFER_TOKEN_URL, data=form)
        if response.status_code >= 400:
            return RedirectResponse(_frontend_url("error"))
        tokens = response.json()
        save_buffer_tokens(db, tenant_id, tokens, auth_type="oauth")
    except (httpx.HTTPError, ValueError, BufferAPIError):
        db.rollback()
        return RedirectResponse(_frontend_url("error"))
    return RedirectResponse(_frontend_url("connected"))


@router.get("/status")
def buffer_status(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    from app.models.base import APICredential
    row = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id, APICredential.provider == "buffer"
    ).first()
    if not row:
        return {"connected": False, "provider": "buffer", "connection_method": None}
    return {
        "connected": True,
        "provider": "buffer",
        "connection_method": (row.settings or {}).get("auth_type", "api_key"),
        "connected_at": (row.settings or {}).get("updated_at"),
        "scopes": (row.settings or {}).get("scope", ""),
    }


@router.post("/api-key")
async def connect_buffer_api_key(
    body: BufferAPIKeyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.INTEGRATIONS, Action.UPDATE)),
):
    """BYOK fallback; key is submitted only to the backend and encrypted at rest."""
    # Validate the submitted key before replacing an existing working connection.
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.buffer.com",
                headers={"Authorization": "Bearer " + body.api_key, "Content-Type": "application/json"},
                json={"query": "query OctaOSValidateBufferKey { account { id email organizations { id name } } }"},
            )
        if response.status_code >= 400:
            raise BufferAPIError("Buffer rejected the API key.")
        payload = response.json()
        if payload.get("errors") or not (payload.get("data") or {}).get("account"):
            raise BufferAPIError("Buffer did not return an authorized account.")
    except (httpx.HTTPError, ValueError, BufferAPIError) as exc:
        raise HTTPException(status_code=400, detail="Buffer API key validation failed. Check the key and try again.") from exc
    save_buffer_tokens(db, tenant_id, {"access_token": body.api_key, "scope": "api-key"}, auth_type="api_key")
    return {"connected": True, "provider": "buffer", "connection_method": "api_key"}


@router.get("/channels")
async def buffer_channels(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
):
    try:
        account = await BufferService(db, tenant_id).account_and_channels()
    except BufferAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    from app.models.base import APICredential
    credential = db.query(APICredential).filter(APICredential.tenant_id == tenant_id, APICredential.provider == "buffer").first()
    channel_map = (credential.settings or {}).get("channel_map", {}) if credential else {}
    return {
        "channel_map": channel_map,
        "account": {"id": account.get("id"), "email": account.get("email")},
        "organizations": [
            {"id": org.get("id"), "name": org.get("name"),
             "channels": [
                 {"id": ch.get("id"), "name": ch.get("name"), "service": ch.get("service")}
                 for ch in org.get("channels", [])
             ]}
            for org in account.get("organizations", [])
        ],
    }


@router.post("/channels/map")
async def map_buffer_channel(
    body: BufferChannelMapRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.INTEGRATIONS, Action.UPDATE)),
):
    """Map a platform to a verified Buffer channel for scheduled campaign delivery."""
    platform = body.platform.strip().lower().replace("twitter", "x")
    try:
        account = await BufferService(db, tenant_id).account_and_channels()
    except BufferAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    channels = [
        channel
        for organization in account.get("organizations", [])
        for channel in organization.get("channels", [])
    ]
    selected = next((channel for channel in channels if channel.get("id") == body.channel_id), None)
    if not selected:
        raise HTTPException(status_code=400, detail="Channel is not part of this Buffer account.")
    actual = (selected.get("service") or "").lower().replace("twitter", "x")
    if platform not in actual and actual not in platform:
        raise HTTPException(status_code=409, detail="Channel platform does not match the requested platform.")
    from app.models.base import APICredential
    credential = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id, APICredential.provider == "buffer"
    ).first()
    if not credential:
        raise HTTPException(status_code=409, detail="Connect Buffer before mapping channels.")
    settings_json = dict(credential.settings or {})
    channel_map = dict(settings_json.get("channel_map", {}))
    channel_map[platform] = body.channel_id
    settings_json["channel_map"] = channel_map
    credential.settings = settings_json
    db.add(credential)
    db.commit()
    return {"platform": platform, "channel_id": body.channel_id, "mapped": True}


@router.post("/publish/{post_id}")
async def publish_approved_post(
    post_id: str,
    body: PublishPostRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
):
    """Queue only approved tenant-owned content; persist provider confirmation."""
    post = db.query(ContentPost).filter(
        ContentPost.id == post_id, ContentPost.tenant_id == tenant_id
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    if post.approval_status != "approved":
        raise HTTPException(status_code=409, detail="Post must be approved before publishing.")
    if post.status == "published" or post.external_post_id:
        raise HTTPException(status_code=409, detail="This post already has a Buffer post ID; reconcile before retrying.")
    try:
        buffer = BufferService(db, tenant_id)
        account = await buffer.account_and_channels()
        channels = [
            channel
            for organization in account.get("organizations", [])
            for channel in organization.get("channels", [])
        ]
        selected = next((channel for channel in channels if channel.get("id") == body.channel_id), None)
        if not selected:
            raise HTTPException(status_code=400, detail="Selected channel is not connected to this workspace's Buffer account.")
        expected = (post.platform or "").lower().replace("twitter", "x")
        actual = (selected.get("service") or "").lower().replace("twitter", "x")
        if expected and expected not in actual and actual not in expected:
            raise HTTPException(status_code=409, detail="Selected Buffer channel does not match this post's target platform.")
        result = await buffer.create_post(
            channel_id=body.channel_id, text=post.content or "", scheduled_at=body.scheduled_at,
            image_url=post.image_url, video_url=post.video_url,
        )
    except HTTPException:
        raise
    except BufferAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    post.external_post_id = result["id"]
    post.status = "scheduled"
    if result.get("dueAt"):
        try:
            post.scheduled_at = datetime.fromisoformat(result["dueAt"].replace("Z", "+00:00"))
        except (TypeError, ValueError):
            pass
    db.add(post)
    db.commit()
    return {
        "status": "scheduled",
        "provider": "buffer",
        "external_post_id": result["id"],
        "scheduled_at": result.get("dueAt"),
        "channel_id": result.get("channelId") or body.channel_id,
    }


@router.delete("/disconnect")
def disconnect_buffer_account(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.INTEGRATIONS, Action.UPDATE)),
):
    disconnected = disconnect_buffer(db, tenant_id)
    return {"connected": False, "disconnected": disconnected}
