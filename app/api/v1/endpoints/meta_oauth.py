"""Meta (Facebook / Instagram) OAuth flow."""
import os
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services.credentials import save_credential

router = APIRouter()

META_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "instagram_basic",
    "instagram_content_publish",
    "business_management",
]


def _meta_app_config():
    app_id = settings.META_APP_ID or os.environ.get("META_APP_ID")
    app_secret = settings.META_APP_SECRET or os.environ.get("META_APP_SECRET")
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="META_APP_ID and META_APP_SECRET must be configured")
    return app_id, app_secret


@router.get("/auth")
def meta_auth(tenant_id: str, request: Request):
    app_id, _ = _meta_app_config()
    host = str(request.base_url).rstrip("/")
    redirect_uri = f"{host}/api/v1/meta/callback"
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join(META_SCOPES),
        "response_type": "code",
        "state": tenant_id,
    }
    return RedirectResponse(f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}")


@router.get("/callback")
async def meta_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = state
    app_id, app_secret = _meta_app_config()
    host = str(request.base_url).rstrip("/")
    redirect_uri = f"{host}/api/v1/meta/callback"

    async with httpx.AsyncClient(timeout=60.0) as client:
        token_resp = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Meta token exchange failed: {token_resp.text}")
        short_token = token_resp.json().get("access_token")

        long_resp = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
        )
        access_token = long_resp.json().get("access_token", short_token)

        pages_resp = await client.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={
                "access_token": access_token,
                "fields": "id,name,access_token,instagram_business_account",
            },
        )
        pages = pages_resp.json().get("data", [])
        meta_settings = {"app_id": app_id}
        if pages:
            page = pages[0]
            meta_settings.update(
                {
                    "page_id": page.get("id"),
                    "page_name": page.get("name"),
                    "page_access_token": page.get("access_token"),
                }
            )
            ig = page.get("instagram_business_account") or {}
            if ig.get("id"):
                meta_settings["instagram_account_id"] = ig["id"]

    save_credential(db, tenant_id, "meta", access_token, settings=meta_settings)
    return {
        "status": "success",
        "message": "Meta (Facebook & Instagram) connected successfully.",
        "page": meta_settings.get("page_name"),
    }


@router.post("/refresh-token")
async def refresh_meta_token(tenant_id: str, db: Session = Depends(get_db)):
    from app.services.credentials import get_decrypted_credential
    from app.services.social.meta_client import MetaGraphClient

    token, cred_settings = get_decrypted_credential(db, tenant_id, "meta")
    if not token:
        raise HTTPException(status_code=404, detail="Meta credential not found")

    app_id = cred_settings.get("app_id") or settings.META_APP_ID or os.environ.get("META_APP_ID")
    app_secret = settings.META_APP_SECRET or os.environ.get("META_APP_SECRET")
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="Meta app credentials not configured")

    client = MetaGraphClient(token, cred_settings)
    new_token = await client.refresh_long_lived_token(app_id, app_secret)
    save_credential(db, tenant_id, "meta", new_token, settings=cred_settings)
    return {"status": "success", "message": "Meta access token refreshed."}
