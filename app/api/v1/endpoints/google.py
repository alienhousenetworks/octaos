import os
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.base import APICredential
from app.api.deps import get_db

router = APIRouter()

# Scopes needed for Gmail send and Google Calendar management
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

def get_google_client_config():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google Client ID and Secret not configured")
    
    return {
        "web": {
            "client_id": client_id,
            "project_id": os.environ.get("GOOGLE_PROJECT_ID", "octaos-project"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret
        }
    }

@router.get("/auth")
def google_auth(tenant_id: str, request: Request):
    try:
        from google_auth_oauthlib.flow import Flow
        client_config = get_google_client_config()
        
        # Use HTTP referer or host to build redirect URI
        # Assuming frontend or backend URL. If it's API, the callback is usually on the backend
        host_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{host_url}/api/v1/google/callback"
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        # We need offline access to get a refresh token
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # We encode tenant_id into state so we can recover it in the callback
        # In a real system, you'd store this mapping securely (e.g. in Redis or a DB)
        # For simplicity we'll just append it to state separated by a special character
        state_with_tenant = f"{state}::{tenant_id}"
        
        authorization_url = authorization_url.replace(state, state_with_tenant)
        
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback")
def google_callback(request: Request, state: str, code: str, db: Session = Depends(get_db)):
    try:
        from google_auth_oauthlib.flow import Flow
        client_config = get_google_client_config()
        
        host_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{host_url}/api/v1/google/callback"
        
        # Extract original state and tenant_id
        if "::" not in state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        original_state, tenant_id = state.split("::", 1)
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=original_state,
            redirect_uri=redirect_uri
        )
        
        # Get full URL to fetch token
        authorization_response = str(request.url)
        # Replace the modified state with the original state in the URL for validation
        authorization_response = authorization_response.replace(state, original_state)
        
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        
        if not credentials.refresh_token:
            # If no refresh token, they might have authorized before without prompt='consent'
            # But we passed prompt='consent' so it should be there.
            pass
            
        # Store refresh token in APICredential for gmail and google_calendar
        creds_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        creds_json = json.dumps(creds_dict)
        
        # Store for both 'gmail' and 'google_calendar'
        for provider in ["gmail", "google_calendar"]:
            existing = db.query(APICredential).filter_by(tenant_id=tenant_id, provider=provider).first()
            if existing:
                existing.encrypted_key = creds_json
            else:
                new_cred = APICredential(
                    tenant_id=tenant_id,
                    provider=provider,
                    encrypted_key=creds_json
                )
                db.add(new_cred)
                
        db.commit()
        
        return {"status": "success", "message": "Google Workspace connected successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
