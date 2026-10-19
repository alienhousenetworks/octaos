"""One reply taxonomy for every inbound path."""
from app.services.sales_os.contracts.outputs import ReplyAssessment

CANONICAL_INTENTS = {
    "interested",
    "question",
    "objection",
    "decline",
    "unsubscribe",
    "wrong_person",
    "timing_later",
    "out_of_office",
}

_ALIASES = {
    "not_interested": "decline",
    "no_thanks": "decline",
    "stop": "unsubscribe",
    "remove_me": "unsubscribe",
    "do_not_contact": "unsubscribe",
    "ooo": "out_of_office",
    "automatic_reply": "out_of_office",
    "follow_up_later": "timing_later",
}

_ACTIONS = {
    "interested": "prepare_meeting_handoff",
    "question": "draft_answer",
    "objection": "draft_response",
    "decline": "stop_cadence",
    "unsubscribe": "suppress_and_stop",
    "wrong_person": "ask_for_referral",
    "timing_later": "nurture",
    "out_of_office": "wait",
}


def normalize_reply_intent(raw: str | None, objection: str | None = None) -> ReplyAssessment:
    token = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    intent = token if token in CANONICAL_INTENTS else _ALIASES.get(token)
    if intent is None:
        return ReplyAssessment(
            intent="needs_human_review",
            objection=None,
            opt_out=False,
            requested_action="human_review",
            confidence=0.0,
        )
    return ReplyAssessment(
        intent=intent,
        objection=objection if intent == "objection" else None,
        opt_out=intent == "unsubscribe",
        requested_action=_ACTIONS[intent],
        confidence=0.9 if token in CANONICAL_INTENTS else 0.7,
    )
