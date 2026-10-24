"""Merge parallel search evidence onto leads the existing connectors already found."""
from app.services.sales_os.search_v4.contracts import QualifiedCandidate, SearchBatch
from app.services.sales_os.search_v4.urls import host_of


def _domains(row: dict) -> set[str]:
    found = set()
    website = row.get("website") or ""
    host = host_of(website if "://" in website else f"https://{website}") if website else ""
    if host:
        found.add(host)
    email = (row.get("email") or "").strip().lower()
    if "@" in email:
        found.add(email.split("@", 1)[1])
    return found


def _attach(row: dict, candidate: QualifiedCandidate) -> None:
    record = candidate.record
    item = {
        "title": record.title,
        "snippet": record.snippet,
        "url": record.original_url,
        "source": f"{record.method}/{record.provider}",
        "intent": candidate.assessment.intent.value,
        "verification_state": candidate.evidence.verification_state,
    }
    if record.method == "jobs":
        row.setdefault("jobs", []).append({"title": record.title, "snippet": record.snippet, "url": record.original_url})
    else:
        row.setdefault("news", []).append(item)
    row.setdefault("parallel_evidence", []).append(item)
    if not row.get("evidence_url"):
        row["evidence_url"] = record.original_url


_GENERIC_MATCH_COMPANIES = {
    "target corp", "target accounts", "website development", "web design",
    "unknown", "local business", "startup", "target", "organizations",
}


def _matches(row: dict, candidate: QualifiedCandidate) -> bool:
    record = candidate.record
    domains = _domains(row)
    if record.company_domain and record.company_domain.lower() in domains:
        return True
    company = (row.get("company") or "").strip().lower()
    if not company or company in _GENERIC_MATCH_COMPANIES or len(company) < 4:
        return False
    title = f"{record.title} {record.snippet}".lower()
    return company in title


def _lead_from_candidate(candidate: QualifiedCandidate) -> dict | None:
    record = candidate.record
    email = (record.contact_email or "").strip().lower()
    name = (record.contact_name or "").strip()
    if not email or "@" not in email or not name:
        return None
    return {
        "name": name,
        "email": email,
        "company": record.company_name or record.company_domain or "",
        "website": record.company_domain or "",
        "title": "",
        "phone": "",
        "source": f"search_v4:{record.method}/{record.provider}",
        "evidence_url": record.original_url,
        "freshness": {
            "signal_snippet": record.snippet[:180],
            "freshness_label": candidate.evidence.verification_state,
            "event_date": record.published_at.isoformat() if record.published_at else None,
        },
        "intent": candidate.assessment.intent.value,
        "qualification_reason": candidate.assessment.rationale,
    }


def merge_connector_leads(existing: list[dict] | None, batch: SearchBatch | None) -> tuple[list[dict], str]:
    """Keep every connector lead. Attach evidence, and add a row only when the page printed a name and email."""
    rows = [dict(row) for row in (existing or [])]
    if batch is None:
        return rows, "Parallel search did not return a batch."
    seen_emails = {(row.get("email") or "").strip().lower() for row in rows if row.get("email")}
    for candidate in batch.candidates:
        if candidate.assessment.decision == "reject":
            continue
        matched = False
        for row in rows:
            if _matches(row, candidate):
                _attach(row, candidate)
                matched = True
        if matched:
            continue
        lead = _lead_from_candidate(candidate)
        if lead is None or lead["email"] in seen_emails:
            continue
        if candidate.assessment.decision != "accept":
            continue
        rows.append(lead)
        seen_emails.add(lead["email"])
    return rows, batch.report
