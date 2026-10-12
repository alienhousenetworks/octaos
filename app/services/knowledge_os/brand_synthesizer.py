"""Brand & Product Knowledge Synthesizer.

Inspects all KnowledgeDocument records (pricing, docs, case studies, product pages,
brand guidelines) and builds a rich, structured brand+product catalog for the
Auto-Mode Marketing Agent.

Gracefully degrades to BusinessProfile fallbacks when KB documents are sparse.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agents import KnowledgeDocument
from app.models.verticals import BusinessProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------- #
# Typed output schema (plain dicts — no extra Pydantic deps)
# ---------------------------------------------------------------------------- #

def _safe_list(v: Any) -> List[str]:
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str) and v.strip():
        return [i.strip() for i in v.replace(",", "\n").split("\n") if i.strip()]
    return []


class BrandKnowledgeService:
    """
    Synthesizes a rich brand + product/service knowledge snapshot per tenant.

    Call ``synthesize()`` to get the full snapshot dict.  The result is a pure
    dictionary so it can be safely serialised to JSON or passed into LLM prompts.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def synthesize(self) -> Dict[str, Any]:
        """Return a structured brand/product knowledge snapshot for this tenant."""
        profile = (
            self.db.query(BusinessProfile)
            .filter(BusinessProfile.tenant_id == self.tenant_id)
            .first()
        )
        docs = (
            self.db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.tenant_id == self.tenant_id,
                KnowledgeDocument.is_active == True,  # noqa: E712
            )
            .all()
        )

        # ---------- brand identity ----------
        brand_identity = self._extract_brand_identity(profile, docs)

        # ---------- product / service catalog ----------
        products_catalog = self._extract_products_catalog(profile, docs)

        # ---------- target audiences ----------
        target_audiences = self._extract_target_audiences(profile, docs)

        # ---------- approved proof points (case studies, metrics) ----------
        proof_points = self._extract_proof_points(docs)

        # ---------- motion design tokens ----------
        motion_tokens = self._build_motion_tokens(profile, docs, brand_identity)

        # ---------- compliance rules ----------
        compliance_rules = self._extract_compliance_rules(docs)

        return {
            "company_name": profile.company_name if profile else "Brand",
            "website": profile.website if profile else "",
            "industry": profile.industry if profile else "Technology",
            "brand_identity": brand_identity,
            "brand_voice": brand_identity,
            "products_catalog": products_catalog,
            "target_audiences": target_audiences,
            "proof_points": proof_points,
            "motion_tokens": motion_tokens,
            "motion_design_tokens": motion_tokens,
            "compliance_rules": compliance_rules,
            "doc_count": len(docs),
        }

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _extract_brand_identity(
        self, profile: Optional[BusinessProfile], docs: List[KnowledgeDocument]
    ) -> Dict[str, Any]:
        # Look for dedicated Brand Guidelines or Prompt Directives docs
        brand_docs = [
            d for d in docs
            if d.doc_type in ("Brand Guidelines", "Prompt Directives", "Tone of Voice", "Brand Voice")
        ]

        tone = "Professional, authoritative, innovative"
        vocabulary: List[str] = ["Autonomous", "Enterprise", "Scalable", "Reliable"]
        banned_words: List[str] = ["Guaranteed returns", "Revolutionary", "Game-changer", "Miracle", "10x overnight"]
        brand_archetype = "Sage / Expert"
        tagline = ""

        for doc in brand_docs:
            content = doc.content or ""
            lower = content.lower()
            if "tone" in lower or "voice" in lower:
                # Extract first meaningful sentence as tone descriptor
                lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
                for ln in lines[:8]:
                    if len(ln) > 20 and not ln.startswith("#"):
                        tone = ln[:200]
                        break
            if "archetype" in lower:
                lines = [ln.strip() for ln in content.split("\n") if "archetype" in ln.lower()]
                if lines:
                    brand_archetype = lines[0][:100]
            if "tagline" in lower or "slogan" in lower:
                lines = [ln.strip() for ln in content.split("\n") if "tagline" in ln.lower() or "slogan" in ln.lower()]
                if lines:
                    tagline = lines[0][:120]
            # Banned words section
            if "avoid" in lower or "never" in lower or "do not" in lower or "banned" in lower:
                for ln in content.split("\n"):
                    if any(kw in ln.lower() for kw in ["avoid", "never say", "do not say", "banned", "prohibited"]):
                        extracted = ln.replace("Avoid:", "").replace("Never:", "").replace("Do not say:", "").strip()
                        if extracted and len(extracted) < 80:
                            banned_words.append(extracted)

        return {
            "tone": tone,
            "vocabulary": vocabulary,
            "banned_words": list(set(banned_words)),
            "brand_archetype": brand_archetype,
            "tagline": tagline,
            "usp": profile.usp[:300] if profile and profile.usp else "",
        }

    def _extract_products_catalog(
        self, profile: Optional[BusinessProfile], docs: List[KnowledgeDocument]
    ) -> List[Dict[str, Any]]:
        catalog: List[Dict[str, Any]] = []

        # Dedicated product/service docs
        product_docs = [
            d for d in docs
            if d.doc_type in ("Product", "Service", "Pricing", "Offer", "Features", "Packages", "Plans")
        ]

        for doc in product_docs:
            content = doc.content or ""
            lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
            name = doc.doc_type
            description = content[:300]
            usp = ""
            price_hint = ""

            for ln in lines[:20]:
                ln_lower = ln.lower()
                if any(kw in ln_lower for kw in ["price", "₹", "$", "usd", "inr", "month", "annual", "/mo", "/yr"]):
                    price_hint = ln[:120]
                if any(kw in ln_lower for kw in ["usp", "unique", "differentiator", "advantage"]):
                    usp = ln[:200]

            catalog.append({
                "name": name,
                "description": description,
                "usp": usp or (profile.usp[:150] if profile and profile.usp else ""),
                "price_hint": price_hint,
                "doc_id": doc.id,
            })

        # Fallback from BusinessProfile if no product docs
        if not catalog and profile:
            catalog.append({
                "name": profile.company_name or "Core Solution",
                "description": profile.service_description or "",
                "usp": profile.usp or "",
                "price_hint": profile.target_budget_range or "",
                "offer": profile.offer_details or "",
                "doc_id": None,
            })

        return catalog[:10]  # Cap at 10 products for prompt token efficiency

    def _extract_target_audiences(
        self, profile: Optional[BusinessProfile], docs: List[KnowledgeDocument]
    ) -> List[Dict[str, Any]]:
        audiences: List[Dict[str, Any]] = []

        icp_docs = [
            d for d in docs
            if d.doc_type in ("ICP", "Buyer Persona", "Target Audience", "Ideal Customer", "Customer Profile")
        ]

        for doc in icp_docs:
            content = doc.content or ""
            audiences.append({
                "source": doc.doc_type,
                "description": content[:400],
            })

        # Always include BusinessProfile-level audience data
        if profile:
            audiences.append({
                "source": "Business Profile",
                "decision_makers": profile.target_decision_makers or "VP / Director / C-Suite",
                "industries": profile.target_industries or [],
                "company_size": profile.target_company_size or "Mid-Market to Enterprise",
                "countries": profile.target_countries or [],
                "budget_range": profile.target_budget_range or "",
            })

        return audiences[:5]

    def _extract_proof_points(self, docs: List[KnowledgeDocument]) -> List[Dict[str, Any]]:
        proof_docs = [
            d for d in docs
            if d.doc_type in ("Case Study", "Testimonial", "Review", "Stats", "Metric", "Proof Point", "Social Proof")
        ]
        return [
            {"type": d.doc_type, "excerpt": (d.content or "")[:300], "doc_id": d.id}
            for d in proof_docs[:8]
        ]

    def _build_motion_tokens(
        self,
        profile: Optional[BusinessProfile],
        docs: List[KnowledgeDocument],
        brand_identity: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Derive motion/visual design tokens from brand docs and profile."""
        primary_color = "#059669"
        accent_color = "#38BDF8"
        secondary_color = "#0F172A"
        font_style = "Inter, sans-serif"
        animation_pace = "smooth"  # smooth | dynamic | calm | energetic
        video_aesthetic = "cinematic minimal"

        brand_docs = [
            d for d in docs
            if d.doc_type in ("Brand Guidelines", "Visual Identity", "Design System", "Color Palette")
        ]
        for doc in brand_docs:
            content = doc.content or ""
            for ln in content.split("\n"):
                ln = ln.strip()
                if "#" in ln and len(ln) < 50:
                    import re
                    colors = re.findall(r"#[0-9A-Fa-f]{6}", ln)
                    if colors and primary_color == "#059669":
                        primary_color = colors[0]
                    if len(colors) > 1:
                        accent_color = colors[1]
                if "font" in ln.lower() and len(ln) < 80:
                    font_style = ln.replace("Font:", "").strip()[:50]

        # Map industry to aesthetic
        industry_aesthetic_map = {
            "fintech": ("dynamic", "premium dark financial dashboard"),
            "health": ("calm", "clean minimal wellness"),
            "saas": ("smooth", "modern product ui showcase"),
            "technology": ("smooth", "cinematic tech minimal"),
            "retail": ("energetic", "vibrant product spotlight"),
            "education": ("calm", "warm editorial instructional"),
            "real estate": ("smooth", "luxury architectural walkthrough"),
        }
        industry = (profile.industry or "technology").lower() if profile else "technology"
        for key, (pace, aesthetic) in industry_aesthetic_map.items():
            if key in industry:
                animation_pace = pace
                video_aesthetic = aesthetic
                break

        return {
            "primary_color": primary_color,
            "accent_color": accent_color,
            "secondary_color": secondary_color,
            "font_style": font_style,
            "animation_pace": animation_pace,
            "video_aesthetic": video_aesthetic,
            "aspect_ratios": {
                "linkedin": "16:9",
                "reels": "9:16",
                "instagram": "9:16",
                "facebook": "1:1",
                "twitter": "16:9",
            },
        }

    def _extract_compliance_rules(self, docs: List[KnowledgeDocument]) -> List[str]:
        rules: List[str] = [
            "Never guarantee specific financial ROI without disclaimers.",
            "Do not cite competitor pricing without a verifiable timestamp.",
            "All statistics must be sourced from verified evidence records.",
            "Avoid superlatives (best, #1) without supporting data.",
        ]

        compliance_docs = [
            d for d in docs
            if d.doc_type in ("Compliance", "Legal Guidelines", "Compliance Rules", "Regulatory", "Policy")
        ]
        for doc in compliance_docs:
            for ln in (doc.content or "").split("\n"):
                ln = ln.strip()
                if ln and len(ln) > 20 and len(ln) < 200:
                    rules.append(ln)

        return list(dict.fromkeys(rules))[:15]  # deduplicate and cap
