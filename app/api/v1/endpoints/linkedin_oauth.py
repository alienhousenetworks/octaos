"""LinkedIn OAuth flow."""
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

LINKEDIN_SCOPES = [
    "openid",
    "profile",
    "w_member_social",
    "email",
]


def _linkedin_app_config():
    client_id = settings.LINKEDIN_CLIENT_ID or os.environ.get("LINKEDIN_CLIENT_ID")
    client_secret = settings.LINKEDIN_CLIENT_SECRET or os.environ.get("LINKEDIN_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be configured")
    return client_id, client_secret


@router.get("/auth")
def linkedin_auth(tenant_id: str, request: Request):
    client_id, _ = _linkedin_app_config()
    host = str(request.base_url).rstrip("/")
    redirect_uri = f"{host}/api/v1/linkedin/callback"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(LINKEDIN_SCOPES),
        "state": tenant_id,
    }
    return RedirectResponse(f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}")


@router.get("/callback")
async def linkedin_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = state
    client_id, client_secret = _linkedin_app_config()
    host = str(request.base_url).rstrip("/")
    redirect_uri = f"{host}/api/v1/linkedin/callback"

    async with httpx.AsyncClient(timeout=60.0) as client:
        token_resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"LinkedIn token exchange failed: {token_resp.text}")

        access_token = token_resp.json().get("access_token")
        expires_in = token_resp.json().get("expires_in")

        org_resp = await client.get(
            "https://api.linkedin.com/v2/organizationAcls",
            params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        org_settings = {"expires_in": expires_in}
        if org_resp.status_code == 200:
            elements = org_resp.json().get("elements", [])
            if elements:
                org_urn = elements[0].get("organization")
                if org_urn:
                    org_settings["organization_urn"] = org_urn

    save_credential(db, tenant_id, "linkedin", access_token, settings=org_settings)
    return {
        "status": "success",
        "message": "LinkedIn connected successfully.",
        "organization_urn": org_settings.get("organization_urn"),
    }
