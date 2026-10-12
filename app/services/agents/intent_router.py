"""
Intent Router for the Hybrid Orchestration Layer.
Employs a high-speed rule-based fast-path (<5ms) with an LLM fallback for low-confidence queries.
Branches into: 'execution' | 'analytics' | 'hybrid'.
"""
from __future__ import annotations

import re
from typing import Dict, Any, Literal, Optional, Tuple


class IntentRouter:
    """Classifies user prompts into execution, analytics, or hybrid intent."""

    EXECUTION_PATTERNS = [
        r"\b(create|draft|generate|launch|write)\b.*?\b(posts?|campaigns?|listings?|articles?|blogs?|content|outlines?)\b",
        r"\b(source|find|gather|scrape|enrich)\b.*?\b(leads?|candidates?|developers?|engineers?|accounts?|ctos?|ceos?)\b",
        r"\b(send|dispatch|blast)\b.*?\b(emails?|pitches?|proposals?|messages?|outreach)\b",
        r"\b(schedule|book|set\s+up)\b.*?\b(meetings?|interviews?|calls?|outreach|cadence)\b",
        r"\b(post|publish)\b.*?\b(daily|specials?|social|facebook|instagram|linkedin|twitter)\b",
        r"\b(hire|recruit)\b.*?\b(developers?|engineers?|roles?|staff)\b",
    ]

    ANALYTIC_PATTERNS = [
        r"\b(report|briefing|overview|status|audit|diagnosis|health|breakdown|review)\b",
        r"\b(how\s+(are|is|did)|what\s+(is|are)\s+our)\b",
        r"\b(conversion(\s+rate)?|funnel|sla|pipeline|revenue|churn|roi|kpis?|metrics?|impressions?)\b",
        r"\b(weakness(es)?|bottlenecks?|vulnerabilit(y|ies)|leak(age)?|stalled)\b",
        r"\b(charts?|graphs?|visual(s|ization)?|plotly|matplotlib)\b",
        r"\b(ceo\s+report|executive\s+summary|operational\s+review)\b",
    ]

    REMEDY_PATTERNS = [
        r"\b(fix|resolve|remedy|solve|address|improve|automate)\b",
    ]

    @classmethod
    def classify(cls, prompt: str) -> Tuple[Literal["execution", "analytics", "hybrid"], float]:
        """
        Fast-path classifier returning (mode, confidence).
        Rules fast-path completes in sub-millisecond time.
        """
        p = prompt.strip().lower()

        has_remedy = any(re.search(pat, p) for pat in cls.REMEDY_PATTERNS)
        exec_matches = sum(1 for pat in cls.EXECUTION_PATTERNS if re.search(pat, p))
        analytic_matches = sum(1 for pat in cls.ANALYTIC_PATTERNS if re.search(pat, p))

        # Check hybrid conditions:
        if analytic_matches > 0 and (has_remedy or exec_matches > 0):
            return "hybrid", 0.95

        # Pure Analytics
        if analytic_matches > 0 and exec_matches == 0:
            conf = min(0.75 + (analytic_matches * 0.10), 0.99)
            return "analytics", conf

        # Pure Execution
        if exec_matches > 0 and analytic_matches == 0:
            conf = min(0.75 + (exec_matches * 0.10), 0.99)
            return "execution", conf

        # Word-level fallback checks
        analytics_keywords = ["report", "metrics", "analytics", "kpis", "kpi", "performance", "weakness", "breakdown", "audit", "diagnose", "review"]
        execution_keywords = ["create", "send", "post", "source", "hire", "generate", "schedule", "draft", "write"]

        has_ak = any(re.search(rf"\b{w}\b", p) for w in analytics_keywords)
        has_ek = any(re.search(rf"\b{w}\b", p) for w in execution_keywords)

        if has_ak and (has_remedy or has_ek):
            return "hybrid", 0.90
        if has_ak:
            return "analytics", 0.85
        if has_ek:
            return "execution", 0.85

        # Default fallback
        return "execution", 0.70
