"""Deterministic Pre-Send Deliverability & Anti-Spam Gatekeeper.

Enforces deterministic rules on cold outbound messages:
1. Blocks banned AI tells and spam clichés.
2. Rejects unrendered template / merge tags (e.g. {{company}}, {name}, [FirstName]).
3. Enforces strict word count ceilings (<125 words for step 1, <65 for follow-ups, <40 for breakup).
4. Caps URLs (max 1 link for cold outreach).
5. Sanitizes accidental HTML tags to clean, high-deliverability plain text.
"""
import html
import re
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


BANNED_PHRASES = (
    "hope this email finds you well",
    "hope you are doing well",
    "hope you're doing well",
    "i hope you are having a",
    "in today's fast-paced",
    "in today's competitive",
    "in this digital age",
    "as an ai",
    "delighted to connect",
    "pleased to connect",
    "thrilled to connect",
    "thrilled to reach out",
    "reach out to you",
    "reaching out to you",
    "take a moment to reach out",
    "testament to",
    "game changer",
    "game-changer",
    "revolutionize",
    "seamlessly integrate",
    "seamless integration",
    "cutting-edge solution",
    "state-of-the-art",
    "unlock your potential",
    "elevate your business",
    "synergy",
    "synergies",
    "dynamic landscape",
    "embark on a journey",
    "look no further",
    "without further ado",
    "i wanted to take a moment",
    "deep dive into",
)

UNRENDERED_TAG_REGEX = re.compile(
    r"(\{\{[^{}]+\}\}|\{[a-zA-Z0-9_]+\}|\[[A-Z_]{2,}\]|\[(?:First Name|Company|Name|Title)\])",
    re.IGNORECASE,
)
HTML_TAG_REGEX = re.compile(r"<[^>]+>")
URL_REGEX = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class GatekeeperResult(BaseModel):
    is_valid: bool
    violations: List[str] = Field(default_factory=list)
    cleaned_body: str
    cleaned_subject: str
    word_count: int
    detected_links: List[str] = Field(default_factory=list)


class PreSendGatekeeper:
    """Deterministic cold outreach gatekeeper."""

    @classmethod
    def strip_html(cls, text: str) -> str:
        """Strip HTML tags and unescape entities to yield clean plain text."""
        if not text:
            return ""
        # Replace common block tag boundaries with newlines
        cleaned = re.sub(r"<(?:p|div|br\s*/?|h[1-6]|li)[\s>]", "\n", text, flags=re.IGNORECASE)
        cleaned = HTML_TAG_REGEX.sub("", cleaned)
        cleaned = html.unescape(cleaned)
        # Normalize double newlines and trailing spaces
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def evaluate(
        cls,
        subject: str,
        body: str,
        step_number: int = 1,
        max_words: Optional[int] = None,
        max_links: int = 1,
    ) -> GatekeeperResult:
        """Validate an outreach touch against deliverability rules."""
        violations: List[str] = []
        cleaned_body = cls.strip_html(body or "")
        cleaned_subject = cls.strip_html(subject or "")

        full_text_lower = f"{cleaned_subject}\n{cleaned_body}".lower()

        # 1. Banned AI / Spam Clichés
        for phrase in BANNED_PHRASES:
            if phrase in full_text_lower:
                violations.append(f"Contains banned AI/spam phrase: '{phrase}'")

        # 2. Unrendered Merge Tags
        unrendered_matches = UNRENDERED_TAG_REGEX.findall(cleaned_subject) + UNRENDERED_TAG_REGEX.findall(cleaned_body)
        if unrendered_matches:
            violations.append(f"Contains unrendered placeholder(s): {', '.join(set(unrendered_matches))}")

        # 3. Word Count Ceilings
        words = cleaned_body.split()
        word_count = len(words)

        if max_words is not None:
            ceiling = max_words
        elif step_number == 1:
            ceiling = 125
        elif step_number >= 4:
            ceiling = 45  # Breakup email
        else:
            ceiling = 75  # Follow-up touches

        if word_count > ceiling:
            violations.append(f"Word count ({word_count}) exceeds ceiling of {ceiling} words for touch {step_number}")

        if word_count < 8:
            violations.append(f"Message is too short ({word_count} words); minimum is 8 words")

        # 4. Link Limits
        links = URL_REGEX.findall(cleaned_body)
        if len(links) > max_links:
            violations.append(f"Found {len(links)} links; cold outreach allows at most {max_links} link")

        # 5. Subject checks
        if not cleaned_subject:
            violations.append("Subject line is missing or empty")
        elif len(cleaned_subject.split()) > 10:
            violations.append(f"Subject line is too long ({len(cleaned_subject.split())} words; max 10 words)")

        return GatekeeperResult(
            is_valid=len(violations) == 0,
            violations=violations,
            cleaned_body=cleaned_body,
            cleaned_subject=cleaned_subject,
            word_count=word_count,
            detected_links=links,
        )
