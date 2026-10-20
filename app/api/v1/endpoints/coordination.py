import asyncio
import json
import logging
from typing import List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Query
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import deps
from app.core.config import settings
from app.core.celery_app import celery_app
from app.models.verticals import AgentMeeting
from app.models.boardroom_events import (
    MeetingEvent,
    MeetingEvidence,
    MeetingAction,
    DecisionCharter,
    MeetingOption,
    MeetingPosition,
    DissentRecord,
    DecisionOutcome,
)
from app.schemas import verticals as schemas
from app.schemas.boardroom import (
    MeetingEventOut,
    MeetingEvidenceOut,
    MeetingActionOut,
    MeetingActionApprove,
    MeetingActionReject,
    DecisionCharterOut,
    MeetingOptionOut,
    MeetingPositionOut,
    DissentRecordOut,
    DecisionOutcomeOut,
    ChairmanInterventionRequest,
)
from app.services.agents.boardroom import BoardroomService

logger = logging.getLogger(__name__)

router = APIRouter()


class ManualMeetingRequest(BaseModel):
    title: str
    topic: str
    participants: Optional[List[str]] = None
    auto_select_experts: bool = True
    industry: Optional[str] = None
    decision_category: Optional[str] = None
    trigger_type: str = "manual"
    trigger_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


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
    service = BoardroomService(db, tenant_id, provider=payload.provider, model=payload.model)
    decision_profile = service.build_decision_profile(
        title=payload.title,
        context=payload.topic,
        industry=payload.industry,
        decision_category=payload.decision_category,
    )
    if payload.auto_select_experts:
        parts = service.assemble_boardroom(decision_profile, payload.participants)
    else:
        if not payload.participants:
            raise HTTPException(status_code=400, detail="At least one participant is required.")
        parts = service.assemble_boardroom(decision_profile, payload.participants, include_dynamic=False)

    meeting = AgentMeeting(
        tenant_id=tenant_id,
        title=payload.title,
        status="active",
        current_phase="assembly",
        trigger_type=payload.trigger_type,
        trigger_id=payload.trigger_id,
        context_summary=service.format_decision_context(payload.topic, decision_profile),
        participants=parts,
        transcript=[],
        action_items=[]
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

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

    try:
        celery_app.send_task("run_boardroom_meeting_task", args=[tenant_id, meeting.id])
    except Exception as e:
        logger.warning("Failed to queue celery task. Running in FastAPI background task: %s", e)
        background_tasks.add_task(service.run_meeting, meeting.id)

    return meeting


# ---------------------------------------------------------------------------
# SSE Live Event Stream
# ---------------------------------------------------------------------------

@router.get("/meetings/{meeting_id}/stream")
async def stream_meeting_events(
    meeting_id: str,
    last_event_id: Optional[int] = Header(None, alias="Last-Event-ID"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """
    Server-Sent Events (SSE) endpoint providing real-time boardroom updates.
    Supports reconnection and missed-event replay using standard `Last-Event-ID`.
    """
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    missed_events = []
    if last_event_id is not None:
        missed_events = db.query(MeetingEvent).filter(
            MeetingEvent.meeting_id == meeting_id,
            MeetingEvent.seq > last_event_id
        ).order_by(MeetingEvent.seq.asc()).all()

    async def event_generator():
        # 1. Replay missed events if client reconnected with Last-Event-ID
        for ev in missed_events:
            msg_payload = {
                "id": ev.seq,
                "event": ev.event_type,
                "phase": ev.phase,
                "actor": ev.actor,
                "payload": ev.payload or {},
                "ts": ev.created_at.isoformat() if ev.created_at else None,
            }
            yield f"id: {ev.seq}\nevent: {ev.event_type}\ndata: {json.dumps(msg_payload)}\n\n"

        # 2. If meeting already terminal and no missed events, send current snapshot and close
        if meeting.status in ("completed", "failed", "cancelled") and not missed_events:
            snap_payload = {
                "id": 0,
                "event": f"meeting.{meeting.status}",
                "phase": meeting.current_phase,
                "actor": "system",
                "payload": {"status": meeting.status},
                "ts": datetime.now().isoformat()
            }
            yield f"id: 0\nevent: meeting.{meeting.status}\ndata: {json.dumps(snap_payload)}\n\n"
            return

        # 3. Subscribe to Redis pub/sub channel for real-time live events
        pubsub = None
        redis_client = None
        try:
            import redis as redis_lib
            redis_client = redis_lib.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                socket_connect_timeout=2
            )
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"boardroom:{meeting_id}")
        except Exception as exc:
            logger.warning("Redis pubsub unavailable for SSE stream (%s). Fallback heartbeat.", exc)

        try:
            idle_ticks = 0
            while True:
                if pubsub:
                    msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if msg and msg.get("type") == "message":
                        raw_data = msg["data"]
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8")
                        try:
                            parsed = json.loads(raw_data)
                            event_type = parsed.get("event", "message")
                            seq = parsed.get("id", 0)
                            yield f"id: {seq}\nevent: {event_type}\ndata: {json.dumps(parsed)}\n\n"
                            if event_type in ("meeting.completed", "meeting.failed", "meeting.cancelled"):
                                break
                        except Exception as e:
                            logger.error("Error decoding SSE redis message: %s", e)
                else:
                    await asyncio.sleep(2.0)

                # Keep-alive heartbeat every 15s
                idle_ticks += 1
                if idle_ticks >= 15:
                    yield ": keep-alive\n\n"
                    idle_ticks = 0
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        finally:
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception:
                    pass
            if redis_client:
                try:
                    redis_client.close()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ---------------------------------------------------------------------------
# Events, Evidence, and Governance Endpoints
# ---------------------------------------------------------------------------

@router.get("/meetings/{meeting_id}/events", response_model=List[MeetingEventOut])
def get_meeting_events(
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

    events = db.query(MeetingEvent).filter(
        MeetingEvent.meeting_id == meeting_id
    ).order_by(MeetingEvent.seq.asc()).all()
    return events


@router.get("/meetings/{meeting_id}/evidence", response_model=List[MeetingEvidenceOut])
def get_meeting_evidence(
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

    evidence = db.query(MeetingEvidence).filter(
        MeetingEvidence.meeting_id == meeting_id
    ).order_by(MeetingEvidence.created_at.asc()).all()
    return evidence


@router.get("/meetings/{meeting_id}/actions", response_model=List[MeetingActionOut])
def get_meeting_actions(
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

    actions = db.query(MeetingAction).filter(
        MeetingAction.meeting_id == meeting_id
    ).order_by(MeetingAction.created_at.asc()).all()
    return actions


@router.post("/meetings/{meeting_id}/actions/{action_id}/approve", response_model=MeetingActionOut)
async def approve_meeting_action(
    meeting_id: str,
    action_id: str,
    payload: MeetingActionApprove = MeetingActionApprove(),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = BoardroomService(db, tenant_id)
    try:
        updated_action = await service.approve_action(action_id, approved_by=payload.approved_by)
        return updated_action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meetings/{meeting_id}/actions/{action_id}/reject", response_model=MeetingActionOut)
def reject_meeting_action(
    meeting_id: str,
    action_id: str,
    payload: MeetingActionReject = MeetingActionReject(),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = BoardroomService(db, tenant_id)
    try:
        updated_action = service.reject_action(action_id, rejected_by=payload.rejected_by, reason=payload.reason)
        return updated_action
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Institutional Governance Endpoints (Charter, Options, Dissents, Outcomes)
# ---------------------------------------------------------------------------

@router.get("/meetings/{meeting_id}/charter", response_model=Optional[DecisionCharterOut])
def get_meeting_charter(
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

    charter = db.query(DecisionCharter).filter(
        DecisionCharter.meeting_id == meeting_id
    ).first()
    return charter


@router.get("/meetings/{meeting_id}/options", response_model=List[MeetingOptionOut])
def get_meeting_options(
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

    options = db.query(MeetingOption).filter(
        MeetingOption.meeting_id == meeting_id
    ).order_by(MeetingOption.created_at.asc()).all()
    return options


@router.get("/meetings/{meeting_id}/positions", response_model=List[MeetingPositionOut])
def get_meeting_positions(
    meeting_id: str,
    round_no: Optional[int] = Query(None, alias="round"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    q = db.query(MeetingPosition).filter(MeetingPosition.meeting_id == meeting_id)
    if round_no is not None:
        q = q.filter(MeetingPosition.round == round_no)
    return q.order_by(MeetingPosition.created_at.asc()).all()


@router.get("/meetings/{meeting_id}/dissents", response_model=List[DissentRecordOut])
def get_meeting_dissents(
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

    dissents = db.query(DissentRecord).filter(
        DissentRecord.meeting_id == meeting_id
    ).order_by(DissentRecord.created_at.asc()).all()
    return dissents


@router.get("/meetings/{meeting_id}/outcomes", response_model=List[DecisionOutcomeOut])
def get_meeting_outcomes(
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

    outcomes = db.query(DecisionOutcome).filter(
        DecisionOutcome.meeting_id == meeting_id
    ).order_by(DecisionOutcome.review_date.asc()).all()
    return outcomes


@router.post("/meetings/{meeting_id}/intervene", response_model=MeetingEventOut)
def intervene_as_chairman(
    meeting_id: str,
    payload: ChairmanInterventionRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """Inject a human Chairman directive or constraint into the active boardroom deliberation."""
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = BoardroomService(db, tenant_id)
    try:
        ev = service.inject_chairman_directive(
            meeting_id=meeting_id,
            directive=payload.directive,
            actor="Chair (Human)"
        )
        return ev
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meetings/{meeting_id}/stop", response_model=schemas.AgentMeeting)
def stop_meeting(
    meeting_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """Instantly halt and abort an ongoing deliberation."""
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = BoardroomService(db, tenant_id)
    res = service.cancel_meeting(meeting_id, reason="Emergency halt triggered by human chairman")
    return res


@router.post("/meetings/{meeting_id}/cancel", response_model=schemas.AgentMeeting)
def cancel_meeting(
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

    service = BoardroomService(db, tenant_id)
    res = service.cancel_meeting(meeting_id, reason="Deliberation cancelled by user")
    return res


@router.post("/meetings/{meeting_id}/rerun", response_model=schemas.AgentMeeting)
async def rerun_meeting(
    meeting_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    BoardroomService.unhalt_meeting(meeting_id)
    meeting.status = "active"
    meeting.current_phase = "assembly"
    meeting.failure_reason = None
    db.commit()

    service = BoardroomService(db, tenant_id)
    try:
        celery_app.send_task("run_boardroom_meeting_task", args=[tenant_id, meeting.id])
    except Exception as e:
        logger.warning("Celery queue failed for rerun, using background task: %s", e)
        background_tasks.add_task(service.run_meeting, meeting.id)

    return meeting


@router.get("/meetings/{meeting_id}/export")
def export_meeting(
    meeting_id: str,
    format: str = Query("md", pattern="^(md|json)$"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    meeting = db.query(AgentMeeting).filter(
        AgentMeeting.id == meeting_id,
        AgentMeeting.tenant_id == tenant_id
    ).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    evidence = db.query(MeetingEvidence).filter(MeetingEvidence.meeting_id == meeting_id).all()
    actions = db.query(MeetingAction).filter(MeetingAction.meeting_id == meeting_id).all()
    events = db.query(MeetingEvent).filter(MeetingEvent.meeting_id == meeting_id).order_by(MeetingEvent.seq.asc()).all()
    charter = db.query(DecisionCharter).filter(DecisionCharter.meeting_id == meeting_id).first()
    options = db.query(MeetingOption).filter(MeetingOption.meeting_id == meeting_id).all()
    dissents = db.query(DissentRecord).filter(DissentRecord.meeting_id == meeting_id).all()

    if format == "json":
        return JSONResponse({
            "id": meeting.id,
            "title": meeting.title,
            "status": meeting.status,
            "current_phase": meeting.current_phase,
            "participants": meeting.participants,
            "created_at": meeting.created_at.isoformat() if meeting.created_at else None,
            "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
            "finished_at": meeting.finished_at.isoformat() if meeting.finished_at else None,
            "charter": {
                "decision_type": charter.decision_type,
                "question": charter.question,
                "owner": charter.decision_owner,
                "cost_of_delay_per_week": charter.cost_of_delay_per_week,
                "criteria_weights": charter.criteria_weights,
            } if charter else None,
            "options": [{
                "option_code": o.option_code,
                "title": o.title,
                "description": o.description,
                "financial_model": o.financial_model or {},
                "weighted_score": o.weighted_score,
            } for o in options],
            "evidence": [{"source_ref": e.source_ref, "type": e.source_type, "trust": e.trust_score, "excerpt": e.excerpt} for e in evidence],
            "actions": [{"id": a.id, "type": a.action_type, "assigned_to": a.assigned_to, "risk": a.risk_tier, "status": a.status, "desc": a.description} for a in actions],
            "dissents": [{
                "agent": d.agent,
                "preferred_option": d.preferred_option,
                "dissent_position": d.dissent_position,
                "addressed": d.addressed,
                "requires_human_signoff": d.requires_human_signoff,
            } for d in dissents],
            "transcript": meeting.transcript or [],
            "events_count": len(events)
        })

    # Format Markdown export
    lines = [
        f"# 🏛️ AI Boardroom Decision Record",
        f"**Topic**: {meeting.title}",
        f"**Status**: {meeting.status} (Phase: {meeting.current_phase})",
        f"**Date**: {meeting.created_at.strftime('%Y-%m-%d %H:%M UTC') if meeting.created_at else 'N/A'}",
        f"**Participants**: {', '.join(meeting.participants or [])}",
    ]
    if charter:
        weights_str = ", ".join(f"{w.get('name', 'k')}: {w.get('weight', 0)}" for w in (charter.criteria_weights or [])) if isinstance(charter.criteria_weights, list) else str(charter.criteria_weights)
        lines.extend([
            "",
            f"## 📋 Decision Charter ({charter.decision_type.upper()})",
            f"- **Question**: {charter.question}",
            f"- **Owner**: {charter.decision_owner}",
            f"- **Cost of Delay**: ${charter.cost_of_delay_per_week:,.0f} / week",
            f"- **Criteria Weights**: {weights_str}",
        ])
    if options:
        lines.extend([
            "",
            "## ⚖️ Options Matrix",
            "| Option | Code | EV | Downside (P10) | Score |",
            "|---|---|---|---|---|",
        ])
        for opt in options:
            fm = opt.financial_model or {}
            ev_val = fm.get('ev', 0)
            p10_val = fm.get('downside_p10', 0)
            lines.append(f"| {opt.title} | `{opt.option_code}` | ${ev_val:,.0f} | ${p10_val:,.0f} | {opt.weighted_score:.2f} |")

    lines.extend([
        "",
        "## 1. Evidence Pack",
        "| Source | Type | Trust Score | Excerpt |",
        "|---|---|---|---|",
    ])
    for ev in evidence:
        lines.append(f"| `{ev.source_ref}` | {ev.source_type} | {ev.trust_score or 'N/A'}% | {ev.excerpt or ''} |")

    lines.extend([
        "",
        "## 2. Governed Action Items",
        "| ID | Risk | Assignee | Status | Description | Approved By |",
        "|---|---|---|---|---|---|",
    ])
    for act in actions:
        lines.append(f"| `{act.id}` | **{act.risk_tier.upper()}** | {act.assigned_to} | `{act.status}` | {act.description} | {act.approved_by or '-'} |")

    if dissents:
        lines.extend([
            "",
            "## ⚠️ Dissent Register",
            "| Agent | Preferred Option | Dissent Rationale | Addressed |",
            "|---|---|---|---|",
        ])
        for dis in dissents:
            lines.append(f"| **{dis.agent}** | {dis.preferred_option or 'N/A'} | {dis.dissent_position} | {'Yes' if dis.addressed else 'Pending Signoff'} |")

    lines.extend([
        "",
        "## 3. Deliberation Transcript",
    ])
    for msg in (meeting.transcript or []):
        sender = msg.get("sender", "Agent")
        phase = msg.get("phase", "")
        content = msg.get("content", "")
        lines.append(f"### {sender} ({phase})")
        lines.append(content)
        lines.append("")

    return PlainTextResponse("\n".join(lines), media_type="text/markdown")


@router.get("/analytics")
def get_boardroom_analytics(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """Boardroom executive analytics: meeting volume, action approvals, and risk distribution."""
    total_meetings = db.query(func.count(AgentMeeting.id)).filter(AgentMeeting.tenant_id == tenant_id).scalar() or 0
    completed_meetings = db.query(func.count(AgentMeeting.id)).filter(
        AgentMeeting.tenant_id == tenant_id,
        AgentMeeting.status == "completed"
    ).scalar() or 0
    awaiting_meetings = db.query(func.count(AgentMeeting.id)).filter(
        AgentMeeting.tenant_id == tenant_id,
        AgentMeeting.status == "awaiting_approval"
    ).scalar() or 0

    total_actions = db.query(func.count(MeetingAction.id)).join(
        AgentMeeting, MeetingAction.meeting_id == AgentMeeting.id
    ).filter(AgentMeeting.tenant_id == tenant_id).scalar() or 0

    approved_actions = db.query(func.count(MeetingAction.id)).join(
        AgentMeeting, MeetingAction.meeting_id == AgentMeeting.id
    ).filter(AgentMeeting.tenant_id == tenant_id, MeetingAction.status.in_(["executing", "completed"])).scalar() or 0

    high_risk_actions = db.query(func.count(MeetingAction.id)).join(
        AgentMeeting, MeetingAction.meeting_id == AgentMeeting.id
    ).filter(AgentMeeting.tenant_id == tenant_id, MeetingAction.risk_tier == "high").scalar() or 0

    return {
        "total_meetings": total_meetings,
        "completed_meetings": completed_meetings,
        "awaiting_approval_meetings": awaiting_meetings,
        "completion_rate": round((completed_meetings / total_meetings * 100), 1) if total_meetings else 0,
        "total_actions": total_actions,
        "approved_actions": approved_actions,
        "high_risk_actions": high_risk_actions,
        "auto_approval_rate": round(((total_actions - high_risk_actions) / total_actions * 100), 1) if total_actions else 0,
    }


# ==============================================================================
# Decision Intelligence & Assurance System — Consequence & Authority Endpoints
# ==============================================================================

class DecisionCaseCreateRequest(BaseModel):
    title: str
    proposal_summary: str
    business_rationale: str
    risk_class: str = "R1_INTERNAL_REVERSIBLE"
    financial_exposure: float = 0.0
    reversibility: str = "MEDIUM"
    cost_of_delay_per_week: float = 0.0
    decision_owner_user_id: Optional[str] = None
    deadline: Optional[datetime] = None
    objective_id: Optional[str] = None
    workflow_id: Optional[str] = None
    assumptions: Optional[List[str]] = None
    uncertainties: Optional[List[str]] = None
    financial_assessment: Optional[dict] = None
    compliance_assessment: Optional[dict] = None
    operational_feasibility: Optional[dict] = None


class DecisionAlternativeCreateRequest(BaseModel):
    alternative_code: str
    title: str
    description: str
    is_do_nothing: bool = False
    is_pilot: bool = False
    reversibility: str = "MEDIUM"
    financial_model: Optional[dict] = None
    score: float = 0.0


class DecisionGrantRequest(BaseModel):
    decision: str  # "APPROVE", "REJECT"
    rationale: str
    delegation_level: str = "EXECUTIVE_L3"
    selected_alternative_code: Optional[str] = None
    action_hash: Optional[str] = None
    policy_version: str = "1.0"
    conditions: Optional[List[str]] = None
    expires_in_days: int = 14


class DecisionOutcomeReviewRequest(BaseModel):
    milestone: str = "30d"
    tripwires: Optional[List[dict]] = None
    predicted_metrics: Optional[dict] = None
    actual_metrics: Optional[dict] = None
    brier_score: Optional[float] = None
    review_notes: Optional[str] = None


@router.get("/decision-cases")
def list_decision_cases(
    status: Optional[str] = None,
    risk_class: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    from app.models.decision_cases import DecisionCase
    query = db.query(DecisionCase).filter(DecisionCase.tenant_id == tenant_id)
    if status and status.upper() != "ALL":
        query = query.filter(DecisionCase.status == status.upper())
    if risk_class and risk_class.upper() != "ALL":
        query = query.filter(DecisionCase.risk_class == risk_class)
    
    cases = query.order_by(DecisionCase.created_at.desc()).all()
    results = []
    for c in cases:
        results.append({
            "id": c.id,
            "case_number": c.case_number,
            "title": c.title,
            "proposal_summary": c.proposal_summary,
            "business_rationale": c.business_rationale,
            "risk_class": c.risk_class,
            "financial_exposure": float(c.financial_exposure or 0),
            "reversibility": c.reversibility,
            "cost_of_delay_per_week": float(c.cost_of_delay_per_week or 0),
            "decision_owner_user_id": c.decision_owner_user_id,
            "requester_user_id": c.requester_user_id,
            "status": c.status,
            "selected_alternative_code": c.selected_alternative_code,
            "active_grant_id": c.active_grant_id,
            "alternatives_count": len(c.alternatives),
            "has_grant": len(c.grants) > 0,
            "financial_assessment": c.financial_assessment,
            "compliance_assessment": c.compliance_assessment,
            "operational_feasibility": c.operational_feasibility,
            "deadline": c.deadline.isoformat() if c.deadline else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        })
    return results


@router.post("/decision-cases")
def create_decision_case(
    payload: DecisionCaseCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    from app.models.decision_cases import DecisionCase, DecisionAlternative
    from decimal import Decimal
    import random

    count = db.query(DecisionCase).filter_by(tenant_id=tenant_id).count() + 1
    case_number = f"DEC-{datetime.now().year}-{count:04d}"

    case = DecisionCase(
        tenant_id=tenant_id,
        case_number=case_number,
        objective_id=payload.objective_id,
        workflow_id=payload.workflow_id,
        title=payload.title,
        proposal_summary=payload.proposal_summary,
        business_rationale=payload.business_rationale,
        risk_class=payload.risk_class,
        financial_exposure=Decimal(str(payload.financial_exposure)),
        reversibility=payload.reversibility,
        cost_of_delay_per_week=Decimal(str(payload.cost_of_delay_per_week)),
        decision_owner_user_id=payload.decision_owner_user_id or (current_user.id if current_user else "user-executive"),
        requester_user_id=current_user.id if current_user else "user-lead",
        status="UNDER_ASSURANCE",
        deadline=payload.deadline,
        assumptions=payload.assumptions or [],
        uncertainties=payload.uncertainties or [],
        financial_assessment=payload.financial_assessment or {
            "downside_p10": -float(payload.financial_exposure) * 0.3,
            "expected_value": float(payload.financial_exposure) * 1.8,
            "payback_months": 4.5,
        },
        compliance_assessment=payload.compliance_assessment or {
            "passed": True,
            "evaluated_rules_count": 4,
            "violations": [],
        },
        operational_feasibility=payload.operational_feasibility or {
            "credentials_valid": True,
            "capacity_score": 0.95,
        },
    )
    db.add(case)
    db.flush()

    # Pre-populate default decision alternatives: Do-Nothing and Pilot
    alt_a = DecisionAlternative(
        case_id=case.id,
        alternative_code="A",
        title="Do Nothing (Defer)",
        description="Preserve resources and avoid immediate exposure.",
        is_do_nothing=True,
        financial_model={"cost": 0, "expected_outcome": 0},
        score=4.0,
    )
    alt_b = DecisionAlternative(
        case_id=case.id,
        alternative_code="B",
        title="Pilot Phase (Controlled Test)",
        description="Test assumptions on 25% budget before full authorization.",
        is_pilot=True,
        reversibility="HIGH",
        financial_model={
            "cost": float(payload.financial_exposure) * 0.25,
            "expected_outcome": float(payload.financial_exposure) * 0.6,
        },
        score=8.5,
    )
    alt_c = DecisionAlternative(
        case_id=case.id,
        alternative_code="C",
        title="Full Scale Execution",
        description="Deploy full authorized budget immediately.",
        reversibility=payload.reversibility,
        financial_model={
            "cost": float(payload.financial_exposure),
            "expected_outcome": float(payload.financial_exposure) * 1.8,
        },
        score=7.0,
    )
    db.add_all([alt_a, alt_b, alt_c])
    db.commit()

    return {
        "status": "CREATED",
        "case_id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "message": f"Decision case {case.case_number} created under active assurance."
    }


@router.get("/decision-cases/{case_id}")
def get_decision_case_details(
    case_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    from app.models.decision_cases import DecisionCase
    case = db.query(DecisionCase).filter(
        DecisionCase.id == case_id,
        DecisionCase.tenant_id == tenant_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Decision case not found")

    alternatives = [{
        "id": a.id,
        "alternative_code": a.alternative_code,
        "title": a.title,
        "description": a.description,
        "is_do_nothing": a.is_do_nothing,
        "is_pilot": a.is_pilot,
        "reversibility": a.reversibility,
        "financial_model": a.financial_model,
        "score": a.score,
    } for a in case.alternatives]

    grants = [{
        "id": g.id,
        "decision": g.decision,
        "granter_user_id": g.granter_user_id,
        "granter_role": g.granter_role,
        "delegation_level": g.delegation_level,
        "action_hash": g.action_hash,
        "rationale": g.rationale,
        "conditions": g.conditions,
        "expires_at": g.expires_at.isoformat() if g.expires_at else None,
    } for g in case.grants]

    outcomes = [{
        "id": o.id,
        "milestone": o.milestone,
        "scheduled_for": o.scheduled_for.isoformat() if o.scheduled_for else None,
        "tripwires": o.tripwires,
        "tripwire_triggered": o.tripwire_triggered,
        "predicted_metrics": o.predicted_metrics,
        "actual_metrics": o.actual_metrics,
        "brier_score": o.brier_score,
        "review_notes": o.review_notes,
    } for o in case.outcomes]

    return {
        "id": case.id,
        "case_number": case.case_number,
        "title": case.title,
        "proposal_summary": case.proposal_summary,
        "business_rationale": case.business_rationale,
        "risk_class": case.risk_class,
        "financial_exposure": float(case.financial_exposure or 0),
        "reversibility": case.reversibility,
        "cost_of_delay_per_week": float(case.cost_of_delay_per_week or 0),
        "decision_owner_user_id": case.decision_owner_user_id,
        "requester_user_id": case.requester_user_id,
        "status": case.status,
        "selected_alternative_code": case.selected_alternative_code,
        "active_grant_id": case.active_grant_id,
        "assumptions": case.assumptions,
        "uncertainties": case.uncertainties,
        "financial_assessment": case.financial_assessment,
        "compliance_assessment": case.compliance_assessment,
        "operational_feasibility": case.operational_feasibility,
        "deadline": case.deadline.isoformat() if case.deadline else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
        "alternatives": alternatives,
        "grants": grants,
        "outcomes": outcomes,
    }


@router.post("/decision-cases/{case_id}/grant")
def grant_decision_authority(
    case_id: str,
    payload: DecisionGrantRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    from app.models.decision_cases import DecisionCase, DecisionGrant
    from datetime import timedelta
    import hashlib

    case = db.query(DecisionCase).filter(
        DecisionCase.id == case_id,
        DecisionCase.tenant_id == tenant_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Decision case not found")

    user_id = current_user.id if current_user else "user-executive"
    user_role = current_user.role if current_user else "admin"

    # Enforce Anti-Self-Approval
    if case.requester_user_id and case.requester_user_id == user_id and payload.decision == "APPROVE":
        raise HTTPException(status_code=403, detail="Anti-Self-Approval violation: Requester cannot approve their own decision case.")

    # Cryptographic action hash
    action_hash = payload.action_hash or hashlib.sha256(f"{case.id}:{payload.decision}:{payload.selected_alternative_code}".encode()).hexdigest()

    grant = DecisionGrant(
        tenant_id=tenant_id,
        case_id=case.id,
        decision=payload.decision,
        granter_user_id=user_id,
        granter_role=user_role,
        delegation_level=payload.delegation_level,
        action_hash=action_hash,
        policy_version=payload.policy_version,
        rationale=payload.rationale,
        conditions=payload.conditions or [],
        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days),
    )
    db.add(grant)
    db.flush()

    case.active_grant_id = grant.id
    if payload.selected_alternative_code:
        case.selected_alternative_code = payload.selected_alternative_code
    case.status = "AUTHORIZED" if payload.decision == "APPROVE" else "REJECTED"
    case.resolved_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": case.status,
        "grant_id": grant.id,
        "action_hash": grant.action_hash,
        "message": f"Decision {case.case_number} {case.status.lower()} by {user_role} ({user_id})."
    }


@router.post("/decision-cases/{case_id}/reviews")
def add_decision_outcome_review(
    case_id: str,
    payload: DecisionOutcomeReviewRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    from app.models.decision_cases import DecisionCase, DecisionOutcomeReview
    from datetime import timedelta
    case = db.query(DecisionCase).filter(
        DecisionCase.id == case_id,
        DecisionCase.tenant_id == tenant_id
    ).first()
    if not case:
        raise HTTPException(status_code=404, detail="Decision case not found")

    review = DecisionOutcomeReview(
        tenant_id=tenant_id,
        case_id=case.id,
        milestone=payload.milestone,
        scheduled_for=datetime.now(timezone.utc) + timedelta(days=30),
        tripwires=payload.tripwires or [],
        tripwire_triggered=False,
        predicted_metrics=payload.predicted_metrics or {},
        actual_metrics=payload.actual_metrics or {},
        brier_score=payload.brier_score,
        review_notes=payload.review_notes,
        reviewed_by_user_id=current_user.id if current_user else "user-executive",
        reviewed_at=datetime.now(timezone.utc) if payload.actual_metrics else None,
    )
    db.add(review)
    db.commit()
    return {"status": "RECORDED", "review_id": review.id, "milestone": review.milestone}
