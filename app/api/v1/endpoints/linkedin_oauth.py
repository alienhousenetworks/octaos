"""LinkedIn OAuth flow."""
import os
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.services.credentials import save_credential

router = APIRouter()

MEMBER_SCOPE_PARTS = ("openid", "profile", "w_member_social")


def normalize_linkedin_scopes(scope: Optional[str] = None) -> str:
    """Always request member identity plus posting. Keep any extra scopes the caller asked for."""
    raw = scope or os.environ.get("LINKEDIN_SCOPES") or "openid profile w_member_social w_organization_social"
    parts = []
    seen = set()
    for part in str(raw).replace(",", " ").split():
        if part and part not in seen:
            seen.add(part)
            parts.append(part)
    for required in MEMBER_SCOPE_PARTS:
        if required not in seen:
            parts.append(required)
            seen.add(required)
    return " ".join(parts)


def _linkedin_app_config(tenant_id: Optional[str] = None, db: Optional[Session] = None):
    client_id = None
    client_secret = None
    if tenant_id and db:
        try:
            from app.models.tenant import APICredential
            cred = db.query(APICredential).filter(
                APICredential.tenant_id == tenant_id,
                APICredential.provider == "linkedin"
            ).first()
            if cred and cred.settings:
                client_id = cred.settings.get("client_id")
                client_secret = cred.settings.get("client_secret")
        except Exception:
            pass

    if not client_id or not client_secret:
        client_id = client_id or settings.LINKEDIN_CLIENT_ID or os.environ.get("LINKEDIN_CLIENT_ID")
        client_secret = client_secret or settings.LINKEDIN_CLIENT_SECRET or os.environ.get("LINKEDIN_CLIENT_SECRET")

    if not client_id or not client_secret:
        try:
            from dotenv import dotenv_values
            env_vals = dotenv_values(".env")
            client_id = client_id or env_vals.get("LINKEDIN_CLIENT_ID")
            client_secret = client_secret or env_vals.get("LINKEDIN_CLIENT_SECRET")
        except Exception:
            pass

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be configured")
    return client_id, client_secret


@router.get("/auth")
def linkedin_auth(
    request: Request,
    tenant_id: Optional[str] = None,
    scope: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from app.models.base import Tenant

    resolved_tenant = None
    if tenant_id:
        resolved_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not resolved_tenant:
        resolved_tenant = db.query(Tenant).order_by(Tenant.created_at.asc()).first()
    
    final_tenant_id = resolved_tenant.id if resolved_tenant else (tenant_id or "tenant-default")

    client_id, _ = _linkedin_app_config(final_tenant_id, db)
    host = str(request.base_url).rstrip("/")
    redirect_uri = f"{host}/api/v1/linkedin/callback"
    scope_str = normalize_linkedin_scopes(scope)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope_str,
        "state": final_tenant_id,
    }
    return RedirectResponse(f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}")


@router.get("/callback")
async def linkedin_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    if error:
        if not request.headers.get("accept", "").startswith("application/json"):
            query = urlencode({
                "linkedin_error": error,
                "linkedin_error_description": error_description or "",
            })
            return RedirectResponse(f"{frontend_url}/app/settings/integrations?{query}")
        raise HTTPException(
            status_code=400,
            detail=f"LinkedIn authorization rejected: {error} - {error_description}",
        )
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from LinkedIn.")

    from app.models.base import Tenant

    tenant_id = state or "tenant-default"
    resolved_tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not resolved_tenant:
        resolved_tenant = db.query(Tenant).order_by(Tenant.created_at.asc()).first()
        if resolved_tenant:
            tenant_id = resolved_tenant.id
        else:
            raise HTTPException(status_code=400, detail="No tenant found in the database.")

    client_id, client_secret = _linkedin_app_config(tenant_id, db)
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

        token_payload = token_resp.json()
        access_token = token_payload.get("access_token")
        expires_in = token_payload.get("expires_in")
        granted_scope = token_payload.get("scope") or ""

        org_settings = {"expires_in": expires_in, "scope": granted_scope}
        if token_payload.get("refresh_token"):
            org_settings["refresh_token"] = token_payload["refresh_token"]

        info_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code == 200:
            sub = info_resp.json().get("sub")
            if sub:
                org_settings["author_urn"] = f"urn:li:person:{sub}"

        org_resp = await client.get(
            "https://api.linkedin.com/v2/organizationAcls",
            params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if org_resp.status_code == 200:
            elements = org_resp.json().get("elements", [])
            if elements:
                org_urn = elements[0].get("organization")
                if org_urn:
                    org_settings["organization_urn"] = org_urn

    save_credential(db, tenant_id, "linkedin", access_token, settings=org_settings)
    if not request.headers.get("accept", "").startswith("application/json"):
        return RedirectResponse(f"{frontend_url}/app/settings/integrations?linkedin=connected")
    return {
        "status": "success",
        "message": "LinkedIn connected successfully.",
        "tenant_id": tenant_id,
        "organization_urn": org_settings.get("organization_urn"),
    }
