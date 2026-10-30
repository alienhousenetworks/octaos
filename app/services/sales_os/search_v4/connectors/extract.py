"""Copy only contact fields that are printed in the retrieved text."""
import re

from app.services.sales_os.providers.honesty import is_fabricated_contact
from app.services.sales_os.search_v4.urls import host_of

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,20} [A-Z][a-z]{1,20})\b")
_NAME_STOP = {"contact us", "read more", "learn more", "privacy policy", "about us", "click here"}


def page_text(raw_html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html or "")
    cleaned = re.sub(r'(?i)href="mailto:([^"?]+)[^"]*"', r" \1 ", cleaned)
    text = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    return re.sub(r"\s+", " ", text).strip()


def title_of(raw_html: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_html or "")
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()[:180]


def contact_from_text(text: str, page_url: str) -> tuple[str, str]:
    """Return a name and email found in the retrieved text."""
    host = host_of(page_url)
    best_name = ""
    best_email = ""

    # Platforms and directories where contact emails naturally differ from page domain
    platform_hosts = (
        "linkedin.com", "twitter.com", "x.com", "reddit.com", "github.com",
        "producthunt.com", "clutch.co", "ycombinator.com", "medium.com", "substack.com",
    )
    is_platform = any(host.endswith(ph) for ph in platform_hosts)

    for match in EMAIL_RE.finditer(text or ""):
        email = match.group(0).lower().strip(".,;:\"'<>(){}[]")
        if "@" not in email or is_fabricated_contact({"email": email, "name": ""}):
            continue
        domain = email.split("@", 1)[1]
        if host and not is_platform and domain != host and not domain.endswith("." + host) and not host.endswith("." + domain):
            continue

        window_before = (text or "")[max(0, match.start() - 100):match.start()]
        window_after = (text or "")[match.end():min(len(text or ""), match.end() + 80)]
        name = ""
        found = list(_NAME_RE.finditer(window_before))
        if found:
            candidate = found[-1].group(1).strip()
            if candidate.lower() not in _NAME_STOP:
                name = candidate
        if not name:
            found_after = list(_NAME_RE.finditer(window_after))
            if found_after:
                candidate = found_after[0].group(1).strip()
                if candidate.lower() not in _NAME_STOP:
                    name = candidate

        if name and email and email in (text or "").lower():
            return name, email
        if email and not best_email:
            best_email = email
            best_name = name

    if not best_name:
        # Fallback to general name regex match in lead paragraph if no email was adjacent
        found_names = list(_NAME_RE.finditer((text or "")[:500]))
        for fn in found_names:
            c = fn.group(1).strip()
            if c.lower() not in _NAME_STOP:
                best_name = c
                break

    return best_name, best_email
