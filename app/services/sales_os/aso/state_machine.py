"""Deal Room transitions. Legacy stage names stay valid.

`discovery` in this table is a sales discovery meeting, not lead discovery.
Side effects are not performed here. Callers schedule them after commit.
"""
from typing import Any

TERMINAL = {"won", "lost"}

TRANSITIONS: dict[tuple[str, str], str] = {
    ("discovered", "qualify_pass"): "qualified",
    ("discovered", "qualify_fail"): "nurtured",
    ("discovered", "qualify_review"): "nurtured",
    ("discovered", "disqualify"): "disqualified",
    ("qualified", "qualify_pass"): "qualified",
    ("qualified", "research_start"): "researching",
    ("qualified", "research_complete"): "outreach_ready",
    ("researching", "research_complete"): "outreach_ready",
    ("researching", "needs_enrichment"): "enrichment_pending",
    ("enrichment_pending", "enrichment_complete"): "outreach_ready",
    ("outreach_ready", "submit_for_approval"): "awaiting_approval",
    ("awaiting_approval", "approve_send"): "in_cadence",
    ("awaiting_approval", "reject_send"): "outreach_ready",
    ("in_cadence", "reply_received"): "replied",
    ("replied", "nurture"): "nurtured",
    ("replied", "request_meeting"): "meeting_pending",
    ("meeting_pending", "confirm_meeting"): "meeting_booked",
    ("meeting_booked", "start_discovery_meeting"): "discovery",
    ("discovery", "request_proposal"): "proposal_pending",
    ("proposal_pending", "proposal_ready"): "proposal",
    ("proposal", "commercial_review"): "commercial_review",
    ("commercial_review", "start_closing"): "closing",
    ("closing", "win"): "won",
    ("closing", "lose"): "lost",
    ("qualified", "disqualify"): "disqualified",
    ("nurtured", "qualify_pass"): "qualified",
}

_SUPPRESS_FROM = {
    "discovered",
    "qualified",
    "researching",
    "enrichment_pending",
    "outreach_ready",
    "awaiting_approval",
    "in_cadence",
    "replied",
    "nurtured",
    "meeting_pending",
    "meeting_booked",
    "discovery",
    "proposal_pending",
    "proposal",
    "commercial_review",
    "closing",
}


def destination(current: str | None, event: str) -> str | None:
    state = current or "discovered"
    if event == "suppress" and state in _SUPPRESS_FROM:
        return "suppressed"
    if state in TERMINAL:
        return None
    return TRANSITIONS.get((state, event))


def apply_transition(
    deal_room: Any,
    event: str,
    *,
    actor: str,
    reason: str,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    current = getattr(deal_room, "stage", None) or "discovered"
    dest = destination(current, event)
    if dest is None:
        return {
            "applied": False,
            "current_state": current,
            "proposed_transition": event,
            "destination": None,
            "actor": actor,
            "reason": "transition_not_permitted",
            "evidence_refs": list(evidence_refs or []),
        }
    if dest != current:
        deal_room.stage = dest
    return {
        "applied": True,
        "current_state": current,
        "proposed_transition": event,
        "destination": dest,
        "actor": actor,
        "reason": reason,
        "evidence_refs": list(evidence_refs or []),
    }
