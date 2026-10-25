"""Deterministic Compliance & Brand Guardrails Rules Engine.

Deterministic Service 4:
- Scans for prohibited financial/health guarantees
- Detects deceptive claims and regulatory red flags
- Enforces platform-specific limits (hashtags, character count)
"""
import re
from typing import List, Tuple
from pydantic import BaseModel, Field


PROHIBITED_GUARANTEES = [
    r"(?i)\bguarantee(d)?\b.*?\b(100%|roi|financial|wealth|success|returns)",
    r"(?i)\brisk-free\s+(investment|profits|returns)",
    r"(?i)\bget\s+rich\s+quick\b",
    r"(?i)\b10x\s+overnight\b",
    r"(?i)\bdouble\s+your\s+money\b",
    r"(?i)\bzero\s+risk\s+guarantee\b",
]

TABOO_WORDS = [
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


class ComplianceResult(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_disclosures: List[str] = Field(default_factory=list)
    status: str = "PASS"  # PASS, FAIL, REVIEW_REQUIRED
    cleaned_content: str


class ComplianceRulesEngine:
    """Zero-LLM deterministic rules engine for marketing copy safety."""

    @classmethod
    def audit_post(
        cls,
        content: str,
        platform: str = "linkedin",
        pack_id: str | None = None,
        enforce_blocking_disclosures: bool = True,
    ) -> ComplianceResult:
        violations = []
        warnings = []
        missing_disclosures = []
        cleaned = content

        # 1. Prohibited Guarantee Patterns
        for pat in PROHIBITED_GUARANTEES:
            if re.search(pat, content):
                violations.append(f"Prohibited absolute guarantee detected: pattern '{pat}'")

        # 2. Taboo Hyperbole Words
        lower_content = content.lower()
        for word in TABOO_WORDS:
            if word in lower_content:
                warnings.append(f"Hyperbolic word '{word}' discouraged by brand guidelines")

        # 3. Platform Constraint Auditing
        p = platform.lower()
        limits = PLATFORM_LIMITS.get(p, {"max_chars": 3000, "max_hashtags": 10, "min_hashtags": 0})

        # Length check
        if len(content) > limits["max_chars"]:
            violations.append(
                f"Post length ({len(content)} chars) exceeds {platform} limit ({limits['max_chars']} chars)"
            )

        # Hashtag check
        hashtags = re.findall(r"#\w+", content)
        if len(hashtags) > limits["max_hashtags"]:
            warnings.append(
                f"Hashtag count ({len(hashtags)}) exceeds recommended {platform} limit ({limits['max_hashtags']})"
            )

        # 4. Industry Vertical Specific Checks
        if pack_id:
            from app.services.marketing.verticals.compliance import IndustryComplianceEngine

            ind_res = IndustryComplianceEngine.audit_post(content, platform, pack_id)
            for v in ind_res.violations:
                if v not in violations:
                    violations.append(v)
            for w in ind_res.warnings:
                if w not in warnings:
                    warnings.append(w)
                if "disclosure" in w.lower() or "rera" in w.lower():
                    missing_disclosures.append(w)

            # P0.5: Enforce blocking disclosures during release evaluation
            if enforce_blocking_disclosures and missing_disclosures:
                for disc in missing_disclosures:
                    v_msg = f"Blocking regulatory disclosure missing: {disc}"
                    if v_msg not in violations:
                        violations.append(v_msg)

        passed = len(violations) == 0
        return ComplianceResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            missing_disclosures=missing_disclosures,
            status="PASS" if passed else "FAIL",
            cleaned_content=cleaned,
        )
