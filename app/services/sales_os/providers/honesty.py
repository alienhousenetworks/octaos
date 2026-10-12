"""Reject contact fields this codebase used to invent."""
import re

FABRICATED_LOCAL_PARTS = {
    "careers", "tech-lead", "decision-maker", "outreach", "investor-relations",
    "tenders", "rfp", "sales-target", "hello",
}
FABRICATED_DOMAINS = {"hn-founder.io"}
FABRICATED_PHONES = {"18005550199", "919876543210", "911123340000"}
FABRICATED_NAMES = {
    "head of talent / vp",
    "verified contact",
    "apify discovered lead",
    "owner / gm",
    "executive leadership",
    "vp technology / engineering",
    "department head / evaluator",
    "procurement officer",
    "managing director / partner",
    "sales target contact",
    "corporate office",
    "store general manager",
    "founding team",
    "yc founder",
    "chief financial officer / founder",
    "chief technology officer / head of it",
    "vp revenue operations / product head",
    "tender committee chairperson / purchase head",
    "managing director",
    "executive decision maker",
    "head of operations",
    "general inquiries",
}


def _digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def is_fabricated_contact(record: dict) -> bool:
    email = (record.get("email") or "").strip().lower()
    if email:
        if "@" not in email:
            return False
        local, domain = email.split("@", 1)
        local = local.split("+", 1)[0]
        if local in FABRICATED_LOCAL_PARTS or domain in FABRICATED_DOMAINS:
            return True
    if _digits(record.get("phone")) in FABRICATED_PHONES:
        return True
    name = (record.get("name") or record.get("full_name") or "").strip().lower()
    if name in FABRICATED_NAMES:
        return True
    return False
