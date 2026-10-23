"""Deterministic Regulatory & Statutory Industry Compliance Engine.

Scans marketing copy against both universal advertising safety rules and
specialized vertical constraints (e.g. Fair Housing & RERA for Real Estate,
SEC/TILA for Banking & Mortgage, FDA for Pharma/Healthcare).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.marketing.verticals.registry import get_marketing_pack

# Universal Prohibited Guarantees
UNIVERSAL_PROHIBITED_GUARANTEES = [
    r"(?i)\bguarantee(d)?\b.*?\b(100%|roi|financial|wealth|success|return(s)?|profit(s)?|yield)",
    r"(?i)\brisk-free\b",
    r"(?i)\bget\s+rich\s+quick\b",
    r"(?i)\b10x\s+overnight\b",
    r"(?i)\bdouble\s+your\s+money\b",
    r"(?i)\bzero\s+risk\b",
]

UNIVERSAL_TABOO_WORDS = [
    "miracle",
    "foolproof",
    "cheat code",
    "insider secret",
    "hack the system",
]

PLATFORM_LIMITS = {
    "linkedin": {"max_chars": 3000, "max_hashtags": 5, "min_hashtags": 1},
    "instagram": {"max_chars": 2200, "max_hashtags": 25, "min_hashtags": 3},
    "facebook": {"max_chars": 5000, "max_hashtags": 10, "min_hashtags": 0},
    "twitter": {"max_chars": 280, "max_hashtags": 3, "min_hashtags": 0},
    "x": {"max_chars": 280, "max_hashtags": 3, "min_hashtags": 0},
}


class IndustryComplianceResult(BaseModel):
    passed: bool
    pack_id: Optional[str] = None
    pack_name: Optional[str] = None
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    required_disclosures: List[str] = Field(default_factory=list)
    remediation_suggestions: List[str] = Field(default_factory=list)
    cleaned_content: str


class IndustryComplianceEngine:
    """Zero-LLM deterministic compliance linter for multi-industry marketing copy."""

    @classmethod
    def audit_post(
        cls,
        content: str,
        platform: str = "linkedin",
        pack_id: Optional[str] = None,
    ) -> IndustryComplianceResult:
        violations: List[str] = []
        warnings: List[str] = []
        suggestions: List[str] = []
        cleaned = content
        pack = get_marketing_pack(pack_id) if pack_id else None
        pack_name = pack["name"] if pack else None

        # ── 1. Universal Prohibited Guarantee Patterns ────────────────────────
        for pat in UNIVERSAL_PROHIBITED_GUARANTEES:
            if re.search(pat, content):
                violations.append(f"Prohibited absolute guarantee detected: pattern '{pat}'")
                suggestions.append("Replace absolute guarantees with grounded historical data or conditional statements.")

        # ── 2. Universal Taboo Words ──────────────────────────────────────────
        for word in UNIVERSAL_TABOO_WORDS:
            pattern = rf"(?i)\b{re.escape(word)}\b"
            if re.search(pattern, content):
                warnings.append(f"Taboo hyperbole keyword detected: '{word}'")
                suggestions.append(f"Avoid '{word}' to maintain professional brand credibility.")

        # ── 3. Platform Syntax & Limits ───────────────────────────────────────
        plat_cfg = PLATFORM_LIMITS.get(platform.lower(), PLATFORM_LIMITS["linkedin"])
        if len(content) > plat_cfg["max_chars"]:
            violations.append(f"Character count ({len(content)}) exceeds {platform} limit of {plat_cfg['max_chars']}")
            suggestions.append(f"Trim copy to under {plat_cfg['max_chars']} characters.")

        hashtags = re.findall(r"#\w+", content)
        if len(hashtags) > plat_cfg["max_hashtags"]:
            warnings.append(f"Found {len(hashtags)} hashtags, exceeding recommended max of {plat_cfg['max_hashtags']} for {platform}")

        # ── 4. Industry-Specific Guardrails ───────────────────────────────────
        if pack:
            guardrails = pack.get("compliance_guardrails", {})
            ind_prohibited = guardrails.get("prohibited_guarantees", [])
            ind_taboos = guardrails.get("taboo_words", [])

            # Check industry prohibited patterns
            for pat in ind_prohibited:
                if re.search(pat, content):
                    violations.append(f"[{pack_name} Regulatory Violation] Prohibited pattern detected: '{pat}'")
                    if pack_id == "real_estate" and any(k in pat for k in ["children", "couples", "bachelor", "religious", "hindu", "muslim", "christian"]):
                        suggestions.append("Fair Housing Act violation: Remove all exclusionary wording regarding family status, religion, or community restrictions.")
                    elif pack_id in ("banking", "mortgage"):
                        suggestions.append("TILA/CFPB violation: Prohibit unverified rate or profit guarantees without statutory disclosures.")
                    elif pack_id == "pharma":
                        suggestions.append("FDA violation: Medical or cure claims must be removed unless supported by verified clinical labels.")

            # Check industry taboo words
            for word in ind_taboos:
                pattern = rf"(?i)\b{re.escape(word)}\b"
                if re.search(pattern, content):
                    violations.append(f"[{pack_name} Taboo Word] Prohibited industry expression: '{word}'")

            # Real Estate Specific: Check for RERA mention on property campaigns
            if pack_id == "real_estate":
                is_promotional = any(kw in content.lower() for kw in ["bhk", "apartment", "villa", "project", "tower", "floor plan", "amenities", "launch", "booking"])
                has_rera = bool(re.search(r"(?i)\b(rera|pr/kn/|rera\s+no|reg\.?\s*no)\b", content))
                if is_promotional and not has_rera:
                    warnings.append("[Real Estate Compliance] Promotional property copy is missing a statutory RERA Registration Number disclosure.")
                    suggestions.append("Add the project's RERA Registration Number (e.g. 'RERA No: PRM/KA/RERA/...') at the end of the post.")

        passed = len(violations) == 0
        disclosures = pack.get("compliance_guardrails", {}).get("required_disclosures", []) if pack else []

        return IndustryComplianceResult(
            passed=passed,
            pack_id=pack_id,
            pack_name=pack_name,
            violations=violations,
            warnings=warnings,
            required_disclosures=disclosures,
            remediation_suggestions=list(dict.fromkeys(suggestions)),
            cleaned_content=cleaned,
        )
