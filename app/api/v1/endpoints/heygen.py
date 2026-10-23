"""Dedicated FastAPI Router for HeyGen Video AI Integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.verticals import GenerationJob, ContentPost
from app.services.credentials import save_credential, get_decrypted_credential
from app.services.integrations.heygen import (
    HeyGenClient,
    HeyGenError,
    get_heygen_client,
)
from app.core.rbac import require_permission, Resource, Action

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateVideoRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=10000, description="Video generation brief or script")
    post_id: Optional[str] = Field(None, description="Optional associated ContentPost ID")
    mode: str = Field("generate", description="Generation mode: generate|preview")


class CreateVideoResponse(BaseModel):
    session_id: Optional[str] = None
    video_id: Optional[str] = None
    status: Optional[str] = None
    job_id: Optional[str] = None
    provider_response: Dict[str, Any] = Field(default_factory=dict)


class SaveHeyGenKeyRequest(BaseModel):
    api_key: str = Field(min_length=10, description="HeyGen API Key")


@router.get("/health")
async def check_heygen_health(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Validate tenant HeyGen API credentials and return connectivity status."""
    try:
        client = get_heygen_client(db, tenant_id)
        validation = await client.validate_key()
        return {
            "provider": "heygen",
            "connected": True,
            "user": validation.get("user", {}),
        }
    except HeyGenError as exc:
        return {
            "provider": "heygen",
            "connected": False,
            "status_code": exc.status_code,
            "error": exc.message,
        }
    except Exception as exc:
        logger.error(f"[HeyGen Endpoint] Health check error: {exc}")
        return {
            "provider": "heygen",
            "connected": False,
            "error": str(exc),
        }


@router.post("/credentials")
async def save_heygen_credentials(
    req: SaveHeyGenKeyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.UPDATE)),
) -> Any:
    """Encrypt and store HeyGen API key for the authenticated tenant."""
    test_client = HeyGenClient(api_key=req.api_key)
    try:
        validation = await test_client.validate_key()
    except HeyGenError as exc:
        raise HTTPException(
            status_code=exc.status_code if exc.status_code != 502 else 400,
            detail=f"HeyGen rejected the provided API key: {exc.message}",
        )

    cred = save_credential(db, tenant_id, "heygen", req.api_key)
    return {
        "status": "success",
        "message": "HeyGen API key verified and stored securely.",
        "provider": "heygen",
        "id": cred.id,
    }


@router.post("/videos", response_model=CreateVideoResponse)
async def create_heygen_video(
    req: CreateVideoRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
) -> Any:
    """Initiate an AI video agent generation task with HeyGen."""
    client = get_heygen_client(db, tenant_id)

    # Validate post if provided
    post = None
    if req.post_id:
        post = (
            db.query(ContentPost)
            .filter(ContentPost.id == req.post_id, ContentPost.tenant_id == tenant_id)
            .first()
        )

    try:
        raw_res = await client.create_video_agent(prompt=req.prompt, mode=req.mode)
    except HeyGenError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.error(f"[HeyGen Endpoint] Video creation error: {exc}")
        raise HTTPException(status_code=502, detail="Failed to initiate video generation with HeyGen.")

    session_id = raw_res.get("session_id") or raw_res.get("id")
    video_id = raw_res.get("video_id")
    current_status = raw_res.get("status", "submitted")

    # Record GenerationJob for asynchronous status tracking
    job = GenerationJob(
        tenant_id=tenant_id,
        post_id=post.id if post else None,
        kind="video",
        provider="heygen",
        model="heygen/v3-video-agent",
        request_payload={"prompt": req.prompt, "mode": req.mode},
        provider_job_id=session_id or video_id,
        status="in_progress",
    )
    db.add(job)

    if post:
        post.video_prompt = req.prompt
        post.video_prompt_enabled = True
        post.used_model = "heygen/v3-video-agent"

    db.commit()
    db.refresh(job)

    return CreateVideoResponse(
        session_id=session_id,
        video_id=video_id,
        status=current_status,
        job_id=job.id,
        provider_response=raw_res,
    )


@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Inspect the status of a HeyGen video agent session."""
    client = get_heygen_client(db, tenant_id)
    try:
        session_data = await client.get_video_agent_session(session_id)
        return session_data
    except HeyGenError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.error(f"[HeyGen Endpoint] Error checking session {session_id}: {exc}")
        raise HTTPException(status_code=502, detail="Failed to retrieve session from HeyGen.")


@router.get("/videos/{video_id}")
async def get_video_status(
    video_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Retrieve video render details and final playable URL."""
    client = get_heygen_client(db, tenant_id)
    try:
        video_data = await client.get_video(video_id)
        return video_data
    except HeyGenError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.error(f"[HeyGen Endpoint] Error checking video {video_id}: {exc}")
        raise HTTPException(status_code=502, detail="Failed to retrieve video details from HeyGen.")
