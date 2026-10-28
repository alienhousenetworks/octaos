"""Sales AI employee jobs: use real leads, research the web, and draft. Never send."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy.orm import Session

from app.models.verticals import BusinessProfile, Lead
from app.services.sales.contact_quality import (
    correct_sender_signature,
    is_invented_email,
    is_invented_name,
    prospect_hosts,
)

logger = logging.getLogger(__name__)

_OPEN_STATUSES = {"captured", "scored", "ready", "needs_review"}
_RESEARCH_TASKS = {"generate_leads", "research", "find_leads", "web_search", "research_and_draft"}
_RESEARCH_WORDS = (
    "research",
    "web search",
    "search the web",
    "from the internet",
    "find new",
    "generate lead",
    "new leads",
    "look up companies",
    "source leads",
)


def _real_email(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    email = value.strip()
    if is_invented_email(email):
        return None
    return email


def _text_asks_research(task_type: str, params: dict, instructions: str) -> bool:
    if (task_type or "").lower() in _RESEARCH_TASKS:
        return True
    if (params.get("query") or "").strip() or (params.get("provider") or "").strip():
        return True
    text = (instructions or "").lower()
    return any(word in text for word in _RESEARCH_WORDS)


def _lead_blob(lead: Lead) -> str:
    data = lead.data or {}
    tags = data.get("tags") if isinstance(data, dict) else None
    parts = [
        lead.name,
        lead.company,
        lead.email,
        lead.source,
        lead.need_of_what,
        lead.target_context,
        lead.why,
        " ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags or ""),
    ]
    return " ".join(part for part in parts if part).lower()


def _usable_existing(lead: Lead) -> bool:
    if not _real_email(lead.email):
        return False
    if is_invented_name(lead.name) and is_invented_name(lead.company):
        return False
    source = (lead.source or "").lower()
    if "site_inquiry" in source or "v3 workflow" in source:
        return False
    return (lead.status or "").lower() in _OPEN_STATUSES


def _sender_profile(db: Session, tenant_id: str) -> tuple[str, Optional[str]]:
    profile = db.query(BusinessProfile).filter_by(tenant_id=tenant_id).first()
    company = (profile.company_name or "").strip() if profile and profile.company_name else ""
    website = (profile.website or "").strip() if profile and profile.website else ""
    return company or "our team", website or None


def _matching_existing(leads: list[Lead], params: dict, instructions: str, limit: int) -> tuple[list[Lead], str]:
    pool = [lead for lead in leads if _usable_existing(lead)]
    email = _real_email(params.get("email"))
    company = str(params.get("company") or "").strip()
    tag = str(params.get("tag") or "").strip().lower()
    text = f"{instructions or ''} {tag}".lower()
    if "ahn icp" in text and "ahn icp" not in tag:
        tag = "ahn icp"

    if email:
        matched = [lead for lead in pool if (lead.email or "").lower() == email.lower()]
        return matched[:limit], "email"
    if company:
        matched = [lead for lead in pool if company.lower() in (lead.company or "").lower()]
        if matched:
            return matched[:limit], "company"
    if tag:
        tagged = [lead for lead in pool if tag in _lead_blob(lead)]
        if tagged:
            return tagged[:limit], "tag"
        if pool:
            return pool[:limit], "tag_missing"
    named = [
        lead for lead in pool
        if lead.company and len(lead.company) > 3 and lead.company.lower() in text
    ]
    if named:
        return named[:limit], "named_in_instructions"
    return pool[:limit], "crm"


async def _default_researcher(db: Session, tenant_id: str, params: dict) -> dict:
    from app.services.sales.discovery_service import DiscoveryService

    return await DiscoveryService(db, tenant_id).generate_leads(params)


async def _default_drafter(db: Session, tenant_id: str, lead: Lead, instructions: str) -> Optional[str]:
    from app.services.verticals.sales import SalesService

    return await SalesService(db, tenant_id).generate_outreach(lead.id, instructions=instructions)


def _store_draft(lead: Lead, subject: str, body: str) -> None:
    data = dict(lead.data or {})
    now = datetime.now(timezone.utc).isoformat()
    data["draft_subject"] = subject
    data["draft_body"] = body
    data["outreach_draft"] = {
        "channel": "email",
        "subject": subject,
        "body": body,
        "status": "draft",
        "created_at": now,
        "requires_authorization": True,
        "sent": False,
    }
    lead.data = data


async def run_sales_employee_job(
    db: Session,
    tenant_id: str,
    *,
    task_type: str = "execute_task",
    params: Optional[dict] = None,
    instructions: str = "",
    researcher: Optional[Callable[..., Awaitable[dict]]] = None,
    drafter: Optional[Callable[..., Awaitable[Optional[str]]]] = None,
) -> dict:
    """Research or reuse real leads and store unsent email drafts.

    A missing contact is never replaced with lead@example.com. Nothing is sent.
    """
    params = dict(params or {})
    # Callers sometimes forward the placeholder defaults. They are not contacts.
    if is_invented_email(params.get("email")):
        params.pop("email", None)
    if is_invented_name(params.get("name")):
        params.pop("name", None)
    if is_invented_name(params.get("company")):
        params.pop("company", None)

    try:
        limit = int(params.get("count") or 25)
    except (TypeError, ValueError):
        limit = 25
    limit = max(1, min(limit, 25))

    leads = (
        db.query(Lead)
        .filter(Lead.tenant_id == tenant_id)
        .order_by(Lead.created_at.desc())
        .limit(200)
        .all()
    )
    selected, match_reason = _matching_existing(leads, params, instructions, limit)
    research_result = None
    created_ids: list[str] = []
    explicit_target = bool(_real_email(params.get("email")) or (params.get("company") or "").strip() or params.get("lead_id"))
    should_research = _text_asks_research(task_type, params, instructions) or (not selected and not explicit_target)

    if explicit_target and not selected and not _text_asks_research(task_type, params, instructions):
        should_research = False

    if should_research and len(selected) < limit:
        query = str(params.get("query") or instructions or "").strip()
        if not query:
            company_name, _website = _sender_profile(db, tenant_id)
            profile = db.query(BusinessProfile).filter_by(tenant_id=tenant_id).first()
            offer = (profile.service_description or "").strip() if profile and profile.service_description else ""
            query = offer or f"companies that buy from {company_name}"
        research = researcher or _default_researcher
        try:
            research_result = await research(
                db,
                tenant_id,
                {
                    "provider": params.get("provider") or "web_search",
                    "query": query,
                    "count": max(1, limit - len(selected)),
                    "freshness": params.get("freshness") or "14_days",
                },
            )
        except Exception as exc:
            logger.warning("Sales research failed: %s", exc)
            research_result = {"status": "error", "message": str(exc), "lead_ids": []}
        fresh_ids = [str(lead_id) for lead_id in (research_result or {}).get("lead_ids") or []]
        if fresh_ids:
            fresh = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.id.in_(fresh_ids)).all()
            known = {lead.id for lead in selected}
            for lead in fresh:
                if lead.id in known or not _real_email(lead.email):
                    continue
                selected.append(lead)
                created_ids.append(lead.id)
                known.add(lead.id)
                if len(selected) >= limit:
                    break

    sender_company, sender_website = _sender_profile(db, tenant_id)
    draft_fn = drafter or (lambda lead, note: _default_drafter(db, tenant_id, lead, note))
    drafted = 0
    skipped = 0
    failed = 0
    lead_rows = []
    note = (
        f"Write on behalf of {sender_company}. "
        "Sign off with that company only. "
        + (f"The only website in the signature is {sender_website}. " if sender_website else "Do not invent a website. ")
        + "Never end the email with the prospect's own website. "
        + (instructions or "")
    ).strip()

    for lead in selected:
        data = dict(lead.data or {})
        if str(data.get("draft_body") or "").strip():
            skipped += 1
            lead_rows.append({
                "id": lead.id,
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "drafted": False,
                "reason": "draft_already_present",
            })
            continue
        try:
            body = await draft_fn(lead, note)
        except Exception as exc:
            logger.warning("Sales draft failed for %s: %s", lead.id, exc)
            failed += 1
            lead_rows.append({
                "id": lead.id,
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "drafted": False,
                "reason": "draft_failed",
            })
            continue
        body = correct_sender_signature(
            body if isinstance(body, str) else "",
            prospect_hosts=prospect_hosts(lead),
            sender_website=sender_website,
        )
        if not body.strip():
            failed += 1
            lead_rows.append({
                "id": lead.id,
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "drafted": False,
                "reason": "no_draft",
            })
            continue
        subject = f"{sender_company} and {lead.company or lead.name}".strip()
        _store_draft(lead, subject, body.strip())
        drafted += 1
        lead_rows.append({
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "drafted": True,
            "created": lead.id in created_ids,
        })

    if lead_rows:
        db.commit()

    if not selected:
        message = "No real contact was found. No placeholder lead was created and nothing was sent."
        if research_result and research_result.get("message"):
            message = f"{message} {research_result.get('message')}"
        status = "needs_real_contact"
    elif drafted or skipped:
        status = "drafted"
        message = (
            f"Used {len(selected)} real lead(s). Drafted {drafted} unsent email(s). "
            f"Left {skipped} existing draft(s) unchanged. Nothing was sent."
        )
    else:
        status = "needs_real_contact"
        message = "Real leads were found, but no email draft was produced. Nothing was sent."

    if match_reason == "tag_missing":
        message += " The requested tag is not stored on these leads, so the job used real captured contacts."

    return {
        "status": status,
        "sent": False,
        "created_count": len(created_ids),
        "matched_existing": len(selected) - len(created_ids),
        "drafted_count": drafted,
        "skipped_existing_drafts": skipped,
        "draft_failures": failed,
        "leads": lead_rows,
        "research": research_result,
        "message": message.strip(),
    }
