"""
boardroom_state.py — Single source of truth for boardroom phase transitions,
risk-tier classification, and Redis pub/sub event publishing.

All state changes in boardroom.py must go through `transition()` and `emit_event()`.
This eliminates the scattered `meeting.transcript.append()` / `db.commit()` pattern
and gives the SSE endpoint a consistent event stream to replay.
"""
from __future__ import annotations

import json
import logging
import uuid
import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase ordering (12-stage enterprise council with Type 2 fast-path support)
# ---------------------------------------------------------------------------

PHASES = [
    "assembly",     # Legacy / Step 0: Convening board
    "intake",       # Stage 1: Type 1 vs Type 2 classification
    "charter",      # Stage 2: Locked criteria weights, owner, cost of delay
    "evidence",     # Stage 3: Contradiction detection & gap analysis
    "analysis",     # Legacy phase
    "positions",    # Stage 4: Blind first positions (zero anchoring)
    "options",      # Stage 5: Generation of min 3 options (Do Nothing / Pilot / Full)
    "modeling",     # Stage 6: Base/bull/bear EV, payback, downside
    "redteam",      # Stage 7: Pre-mortem & failure modes
    "critique",     # Legacy phase
    "debate",       # Stage 8: Multi-round structured rebuttals & convergence
    "gavel",        # Stage 9: Chairman interventions & directives
    "synthesis",    # Legacy phase
    "decision",     # Stage 10: Multi-attribute scoring, vetoes, dissent register
    "approval",     # Governance approval gate
    "execution",    # Stage 11: Governed staged action dispatch & tripwires
    "completed",    # Stage 12: Scheduled 30/90/180d review & Brier calibration
]

# Legacy phase name compatibility mapping
LEGACY_PHASE_MAP: dict[str, str] = {
    "assembly": "intake",
    "evidence": "evidence",
    "analysis": "positions",
    "critique": "debate",
    "synthesis": "decision",
    "approval": "gavel",
    "execution": "execution",
    "completed": "completed",
}

TERMINAL_PHASES = {"completed", "failed", "cancelled"}

TYPE_2_FAST_PATH_SKIPPED_PHASES = {"modeling", "redteam", "debate"}

# ---------------------------------------------------------------------------
# Risk tier classification
# ---------------------------------------------------------------------------

ACTION_TYPE_MAP: dict[str, tuple[str, str]] = {
    # description keywords → (action_type, risk_tier)
    # Checked in order; first match wins.
    "create_internal_note":    ("create_internal_note", "low"),
    "create internal note":    ("create_internal_note", "low"),
    "internal note":           ("create_internal_note", "low"),
    "tag_lead":                ("tag_lead", "low"),
    "tag lead":                ("tag_lead", "low"),
    "update_tag":              ("tag_lead", "low"),
    "create lead":             ("create_lead", "medium"),
    "create_lead":             ("create_lead", "medium"),
    "capture lead":            ("create_lead", "medium"),
    "update ticket status":    ("update_ticket_status", "medium"),
    "update_ticket_status":    ("update_ticket_status", "medium"),
    "update the ticket":       ("update_ticket_status", "medium"),
    "send customer":           ("send_customer_reply", "high"),
    "reply to customer":       ("send_customer_reply", "high"),
    "notify customer":         ("send_customer_reply", "high"),
    "send a customer":         ("send_customer_reply", "high"),
    "promote candidate":       ("promote_candidate", "high"),
    "promote_candidate":       ("promote_candidate", "high"),
    "update candidate":        ("promote_candidate", "high"),
    "send email":              ("send_customer_reply", "high"),
    "send whatsapp":           ("send_customer_reply", "high"),
}

# Confidence threshold above which "medium" tier auto-approves
AUTO_APPROVE_CONFIDENCE_THRESHOLD = 0.75


def classify_action(
    description: str,
    action_type: Optional[str] = None,
    db: Optional[Session] = None,
) -> tuple[str, str]:
    """
    Return (action_type, risk_tier) for a given action description.
    Checks formal CapabilityRegistry side_effect_class (R1–R4) if db is provided,
    otherwise falls back to keyword heuristic.
    """
    lower = description.lower()
    inferred_type = action_type or "unknown"

    # 1. First check keyword map to get inferred action_type
    for keyword, (atype, tier) in ACTION_TYPE_MAP.items():
        if keyword in lower:
            inferred_type = atype
            break

    # 2. Check formal CapabilityRegistry if database session is passed
    if db:
        try:
            from app.models.executive import CapabilityRegistry
            cap = db.query(CapabilityRegistry).filter(
                (CapabilityRegistry.id == inferred_type) | (CapabilityRegistry.id == action_type)
            ).first()
            if cap and cap.side_effect_class:
                tier_lookup = {
                    "R1_INTERNAL_REVERSIBLE": "low",
                    "R2_INTERNAL_IRREVERSIBLE": "medium",
                    "R3_EXTERNAL_IRREVERSIBLE": "high",
                    "R4_FINANCIAL_CRITICAL": "high",
                }
                return cap.id, tier_lookup.get(cap.side_effect_class, "high")
        except Exception as e:
            logger.debug("CapabilityRegistry check skipped: %s", e)

    # 3. Fallback to keyword map or safe default
    for keyword, (atype, tier) in ACTION_TYPE_MAP.items():
        if keyword in lower:
            return atype, tier
    return "unknown", "high"


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------

def _next_seq(db: Session, meeting_id: str) -> int:
    """Return the next monotonic sequence number for a meeting."""
    from app.models.boardroom_events import MeetingEvent
    count = db.query(func.count(MeetingEvent.id)).filter(
        MeetingEvent.meeting_id == meeting_id
    ).scalar()
    return (count or 0) + 1


def _publish_to_redis(meeting_id: str, payload: dict) -> None:
    """Publish a boardroom event to the per-meeting Redis channel. Fails silently."""
    import os
    if os.environ.get("TESTING") == "1":
        return
    try:
        import redis as redis_lib
        from app.core.config import settings
        r = redis_lib.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                            socket_connect_timeout=1)
        r.publish(f"boardroom:{meeting_id}", json.dumps(payload, default=str))
        r.close()
    except Exception as exc:
        logger.debug("Redis publish skipped (non-fatal): %s", exc)


def emit_event(
    db: Session,
    meeting_id: str,
    event_type: str,
    actor: str = "system",
    phase: Optional[str] = None,
    payload: Optional[dict] = None,
    publish: bool = True,
) -> Any:
    """
    Append a MeetingEvent row and optionally publish to Redis for SSE fan-out.
    This is the single write point for all boardroom events.
    """
    from app.models.boardroom_events import MeetingEvent

    seq = _next_seq(db, meeting_id)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    event = MeetingEvent(
        meeting_id=meeting_id,
        seq=seq,
        event_type=event_type,
        phase=phase,
        actor=actor,
        payload=payload or {},
    )
    db.add(event)
    db.commit()

    if publish:
        _publish_to_redis(meeting_id, {
            "id": seq,
            "event": event_type,
            "phase": phase,
            "actor": actor,
            "payload": payload or {},
            "ts": ts,
        })

    return event


def transition(
    db: Session,
    meeting,  # AgentMeeting ORM instance
    to_phase: str,
    publish: bool = True,
) -> None:
    """
    Move a meeting to a new phase. Writes a `phase.changed` event and commits.
    Refuses to go backward (except to terminal states).
    """
    from_phase = meeting.current_phase
    norm_from = LEGACY_PHASE_MAP.get(from_phase, from_phase)
    norm_to = LEGACY_PHASE_MAP.get(to_phase, to_phase)

    if to_phase not in TERMINAL_PHASES and norm_to not in TERMINAL_PHASES:
        from_idx = PHASES.index(norm_from) if norm_from in PHASES else -1
        to_idx = PHASES.index(norm_to) if norm_to in PHASES else -1
        if to_idx >= 0 and from_idx >= 0 and to_idx < from_idx:
            logger.warning(
                "Refusing backward phase transition %s → %s for meeting %s",
                from_phase, to_phase, meeting.id,
            )
            return

    meeting.current_phase = to_phase
    db.add(meeting)
    db.commit()

    emit_event(
        db=db,
        meeting_id=meeting.id,
        event_type="phase.changed",
        actor="system",
        phase=to_phase,
        payload={"from_phase": from_phase, "to_phase": to_phase},
        publish=publish,
    )
