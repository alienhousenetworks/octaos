from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel

from app.api import deps
from app.models.verticals import AgentMeeting, Ticket, Candidate
from app.schemas import verticals as schemas
from app.services.agents.boardroom import BoardroomService
from app.core.celery_app import celery_app

router = APIRouter()

class ManualMeetingRequest(BaseModel):
    title: str
    participants: List[str]
    topic: str
    trigger_type: str = "manual"
    trigger_id: Optional[str] = None

@router.get("/meetings", response_model=List[schemas.AgentMeeting])
def get_meetings(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meetings = db.query(AgentMeeting).filter(
        AgentMeeting.tenant_id == tenant_id
    ).order_by(AgentMeeting.created_at.desc()).all()
    return meetings

@router.get("/meetings/{meeting_id}", response_model=schemas.AgentMeeting)
def get_meeting_details(
    meeting_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting

@router.post("/meetings/create", response_model=schemas.AgentMeeting)
async def create_manual_meeting(
    payload: ManualMeetingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    # Validate participants
    if not payload.participants:
        raise HTTPException(status_code=400, detail="At least one participant is required.")
    
    parts = list(payload.participants)
    if "CEO AI" not in parts:
        parts.insert(0, "CEO AI")
    
    # Save the meeting
    meeting = AgentMeeting(
        tenant_id=tenant_id,
        title=payload.title,
        status="active",
        trigger_type=payload.trigger_type,
        trigger_id=payload.trigger_id,
        context_summary=f"Custom Topic: {payload.topic}",
        participants=parts,
        transcript=[],
        action_items=[]
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Log boardroom summoning activity
    from app.models.agents import ActivityLog
    log = ActivityLog(
        tenant_id=tenant_id,
        agent_name="CEO AI",
        action="Meeting Summoned",
        description=f"Summoned custom boardroom discussion: '{meeting.title}'.",
        status="success"
    )
    db.add(log)
    db.commit()

    # Trigger simulation asynchronously
    try:
        celery_app.send_task("run_boardroom_meeting_task", args=[tenant_id, meeting.id])
    except Exception as e:
        print(f"Failed to queue celery task. Running in FastAPI background task: {e}")
        service = BoardroomService(db, tenant_id)
        background_tasks.add_task(service.run_simulation, meeting.id)

    return meeting
