"""Shared utilities for Sales OS agents and services."""
import json
import re
from typing import Any, Dict


def extract_json(text: str):
    """Extract and parse a JSON array or object from model text output."""
    if not text:
        raise ValueError("JSON extraction failed. Input text is empty or None.")
    text = str(text).strip()
    if text.startswith("```") and text.endswith("```") and "\n" not in text:
        text = text[3:-3].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    elif text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        array_match = re.search(r"\[.*\]", text, re.DOTALL)
        obj_match = re.search(r"\{.*\}", text, re.DOTALL)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except Exception:
                pass
        if obj_match:
            try:
                return json.loads(obj_match.group(0))
            except Exception:
                pass
        raise ValueError(f"JSON extraction failed. Raw output: {text}")


def _build_lead_data(c: dict) -> dict:
    """Structured, real-only dossier data derived from a discovered company dict."""
    contact = c.get("contact") or {}
    data = {
        "contact": {
            "name": contact.get("name") or "",
            "title": contact.get("title") or "",
            "linkedin_url": contact.get("linkedin_url") or "",
        },
        "company": {
            "name": c.get("company_name") or "",
            "website": c.get("website") or "",
            "industry": c.get("industry") or "",
        },
        "freshness": c.get("freshness") or {},
        "evidence_url": c.get("evidence_url") or "",
        "why_now": c.get("why_now") or "",
        "purchasing_capacity": c.get("purchasing_capacity") or "",
        "qualification_reason": c.get("qualification_reason") or "",
        "retrieval_provider": c.get("retrieval_provider") or "",
        "publisher": c.get("publisher") or "",
        "buying_signal": c.get("buying_signal") or "",
        "evidence_quote": c.get("evidence_quote") or "",
        "contact_status": c.get("contact_status") or "READY",
        "contact_confidence": c.get("contact_confidence") or "UNKNOWN",
        "platform_contact": c.get("platform_contact") or "",
        "evidence_tier": c.get("evidence_tier") or "VERIFIED",
        "qualification_score": c.get("qualification_score") or (
            c.get("scoring", {}).get("total") if isinstance(c.get("scoring"), dict) else 0.0
        ),
        "rejection_reason": c.get("rejection_reason"),
    }
    if c.get("pain_points"):
        data["pain_points"] = c["pain_points"]
    if c.get("scoring"):
        data["scoring_breakdown"] = c["scoring"]
    return data
