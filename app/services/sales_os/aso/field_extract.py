"""Extract field-note facts that are written in the transcript."""
import re


def _phrase(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    value = " ".join(match.group(1).split())
    return value or None


def extract_field_note(transcript: str) -> dict:
    text = transcript or ""
    budget = None
    money = re.search(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", text)
    if money:
        budget = float(money.group(1).replace(",", ""))

    pains = []
    for pattern in (
        r"pain point is ([^.]+)",
        r"struggling with ([^.]+)",
        r"problem is ([^.]+)",
    ):
        found = _phrase(pattern, text)
        if found:
            pains.append(found)

    competitors = []
    competitor = _phrase(r"(?:competitor|using|evaluate(?:s|d)?)\s+([A-Z][A-Za-z0-9]+)", text)
    if competitor and competitor.lower() not in {"a", "the", "our"}:
        competitors.append(competitor)

    attendees = []
    person = _phrase(r"with ((?:CEO|CTO|CFO|CRO|VP|Head)[^.]{0,40})", text)
    if person:
        attendees.append(person.strip(" ,"))

    rep_commitments = []
    promised = _phrase(r"I promised to ([^.]+)", text)
    if promised:
        rep_commitments.append(promised)

    client_commitments = []
    agreed = _phrase(r"agreed to ([^.]+)", text)
    if agreed:
        client_commitments.append(agreed)

    timeline = _phrase(r"by ([^.]+)", text)
    subject = "Follow-up from our meeting" if text else ""
    if pains or rep_commitments:
        body = "Following our meeting, I noted: " + "; ".join(pains + rep_commitments) + "."
        whatsapp = body[:180]
    else:
        body = ""
        whatsapp = ""
    return {
        "attendees": attendees,
        "client_pain_points": pains,
        "competitor_mentions": competitors,
        "budget_discussed": budget,
        "timeline_stated": timeline,
        "commitments_made_by_rep": rep_commitments,
        "commitments_made_by_client": client_commitments,
        "recommended_stage": None,
        "email_subject": subject,
        "email_body": body,
        "whatsapp_body": whatsapp,
    }


def grounded_in_transcript(data: dict, transcript: str) -> dict:
    """Drop extracted strings that do not appear in the transcript."""
    source = (transcript or "").lower()
    cleaned = dict(data)

    def keep(value: str) -> bool:
        token = " ".join(value.lower().split())
        return len(token) >= 3 and token in source

    for key in (
        "attendees",
        "client_pain_points",
        "competitor_mentions",
        "commitments_made_by_rep",
        "commitments_made_by_client",
    ):
        cleaned[key] = [item for item in (data.get(key) or []) if isinstance(item, str) and keep(item)]
    budget = data.get("budget_discussed")
    if budget is not None:
        digits = str(int(float(budget))) if float(budget).is_integer() else str(budget)
        if digits not in re.sub(r"[^\d]", "", source):
            cleaned["budget_discussed"] = None
    timeline = data.get("timeline_stated")
    if isinstance(timeline, str) and not keep(timeline):
        cleaned["timeline_stated"] = None
    return cleaned
