"""Inbound Controller Replies & Status Reporting Endpoint for OctaOS."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.api import deps
from app.models.external_agents import ActivityEvent, ControllerCommand

router = APIRouter()


class AttachmentItem(BaseModel):
    name: str = Field(..., description="Filename or label for display")
    url: str = Field(..., description="Public or presigned URL to the attachment")
    mime_type: Optional[str] = Field(None, description="MIME type of the media or document")
    size_bytes: Optional[int] = Field(None, description="Attachment size in bytes")


class ControllerReplyRequest(BaseModel):
    correlation_id: Optional[str] = Field(None, description="Correlation ID matching an issued command or task")
    kind: str = Field("status", description="status | result | error | progress | command | webhook | approval | media")
    title: str = Field(..., min_length=1, max_length=200, description="Short title for activity feed preview")
    body: str = Field(..., min_length=1, description="Detailed Markdown content or description")
    attachments: Optional[List[AttachmentItem]] = Field(default_factory=list, description="Media or document attachments")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured metadata payload")


class ControllerReplyResponse(BaseModel):
    success: bool
    event_id: str
    correlation_id: Optional[str]
    status: str


@router.post("/replies", response_model=ControllerReplyResponse, status_code=status.HTTP_201_CREATED)
def receive_controller_reply(
    request: ControllerReplyRequest,
    db: Session = Depends(deps.get_db),
    principal: deps.AuthPrincipal = Depends(deps.require_scopes(["dashboard:activity:write"])),
) -> Any:
    """
    Accept an inbound status report, execution result, error, or progress update from an external controller
    (e.g., Grok Bot, Claude Agent, ChatGPT Custom GPT, n8n webhook worker).
    Appends an activity event to the feed and updates any matching ControllerCommand status.
    """
    tenant_id = principal.tenant_id
    actor = principal.name or principal.key_name or "External Controller"

    attachments_data = [a.dict() for a in (request.attachments or [])]

    event = ActivityEvent(
        tenant_id=tenant_id,
        correlation_id=request.correlation_id,
        source="controller",
        actor=actor,
        kind=request.kind,
        title=request.title,
        body=request.body,
        attachments_json=attachments_data,
        data_json=request.data or {},
    )
    db.add(event)

    # Correlate with issued command if correlation_id provided
    if request.correlation_id:
        cmd = db.query(ControllerCommand).filter(
            ControllerCommand.tenant_id == tenant_id,
            ControllerCommand.correlation_id == request.correlation_id,
        ).first()
        if cmd:
            if request.kind == "result":
                cmd.status = "completed"
            elif request.kind == "error":
                cmd.status = "failed"
            elif request.kind in ("status", "progress"):
                cmd.status = "in_progress"
            
            summary_snippet = request.title
            if request.body:
                summary_snippet += f" - {request.body[:120]}"
            cmd.reply_summary = summary_snippet
            cmd.updated_at = func.now()

    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "event_id": event.id,
        "correlation_id": request.correlation_id,
        "status": "recorded",
    }
