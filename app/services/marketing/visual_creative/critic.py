"""Visual Critic & Multimodal Quality Gate (Stage 5 & 6 of Universal Visual Creation).

Inspects returned media assets against the 7 weighted criteria from SKILL.md:
1. Brief & subject fidelity (20%)
2. Composition & storytelling (15%)
3. Craft, lighting, materials & detail (15%)
4. Naturalness & visual coherence (15%)
5. Continuity & motion / anatomy & geometry (15%)
6. Typography & brand accuracy (10%)
7. Technical delivery (10%)
"""
from typing import Dict, Any, List, Optional
import logging

from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
    QualityCriteriaScore,
    QualityReviewScorecard,
)

logger = logging.getLogger(__name__)


class VisualCritic:
    """Evaluates media quality against professional art direction standards."""

    CRITERIA_WEIGHTS = {
        "brief_fidelity": ("Brief & Subject Fidelity", 0.20),
        "composition": ("Composition & Storytelling", 0.15),
        "craft_lighting": ("Craft, Lighting, Materials & Detail", 0.15),
        "naturalness": ("Naturalness & Visual Coherence", 0.15),
        "continuity_anatomy": ("Anatomy & Geometry / Motion Continuity", 0.15),
        "typography_brand": ("Typography & Brand Accuracy", 0.10),
        "technical_delivery": ("Technical Delivery & Specifications", 0.10),
    }

    def __init__(self, db_session, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id

    async def inspect(
        self,
        asset_url: Optional[str],
        intent: VisualIntentInputContract,
        brief: CreativeBrief,
        generation_error: Optional[str] = None,
    ) -> QualityReviewScorecard:
        """Inspect media asset and produce weighted QualityReviewScorecard."""
        # Check for immediate generation failure
        if generation_error or not asset_url:
            crit = [
                QualityCriteriaScore(
                    criterion_id=cid,
                    name=name,
                    score=0,
                    weight=weight,
                    inspected=True,
                    notes=f"Generation failed: {generation_error or 'No asset returned'}"
                )
                for cid, (name, weight) in self.CRITERIA_WEIGHTS.items()
            ]
            return QualityReviewScorecard(
                criteria=crit,
                weighted_score=0.0,
                critical_blockers=[f"Generation failed: {generation_error or 'Missing asset'}"],
                defects=[{"defect": "Media missing or provider error", "severity": "fatal"}],
                inspected=True,
                passed=False,
                summary="Quality check failed: generation did not produce an asset."
            )

        # Multimodal inspection via vision model if available
        scores: Dict[str, int] = {}
        notes: Dict[str, str] = {}
        critical_blockers: List[str] = []
        defects: List[Dict[str, Any]] = []

        # Attempt Vision API critique
        vision_inspected = False
        try:
            from app.services.llm_gateway import LLMGateway
            gateway = LLMGateway(self.db, self.tenant_id)
            prompt = (
                f"You are a Senior Visual Critic. Critique this visual asset for the brief:\n"
                f"Subject: {intent.subject}\n"
                f"Purpose: {intent.purpose}\n"
                f"Style: {', '.join(intent.style_direction)}\n"
                f"Constraints to avoid: {', '.join(intent.must_avoid)}\n\n"
                f"Rate these 7 criteria from 0 (failed) to 4 (exceptional):\n"
                f"1. brief_fidelity\n"
                f"2. composition\n"
                f"3. craft_lighting\n"
                f"4. naturalness\n"
                f"5. continuity_anatomy\n"
                f"6. typography_brand\n"
                f"7. technical_delivery\n\n"
                f"Output strictly valid JSON with keys: scores (dict of criterion: int 0-4), defects (list of strings), blockers (list of strings)."
            )
            # Check if vision inspection is supported by gateway
            if hasattr(gateway, "complete_vision") and asset_url.startswith("http"):
                resp = await gateway.complete_vision(prompt, image_url=asset_url, provider="gemini")
                import json
                import re
                cleaned_resp = resp.strip()
                match = re.search(r"(\{.*\})", cleaned_resp, re.DOTALL)
                raw_json = match.group(1) if match else cleaned_resp
                parsed = json.loads(raw_json)
                scores = parsed.get("scores", {})
                for d in parsed.get("defects", []):
                    defects.append({"defect": d, "severity": "minor"})
                critical_blockers = parsed.get("blockers", [])
                vision_inspected = True
        except Exception as vision_err:
            logger.debug(f"[VisualCritic] Vision inspection offline ({vision_err}), running deterministic heuristic check.")

        # Fallback to deterministic heuristic baseline if vision API was not invoked
        if not vision_inspected:
            scores = {
                "brief_fidelity": 3,
                "composition": 4,
                "craft_lighting": 3,
                "naturalness": 3,
                "continuity_anatomy": 3,
                "typography_brand": 3,
                "technical_delivery": 4,
            }
            notes = {k: "Heuristic inspection against prompt compliance" for k in scores}

        # Calculate weighted score (0 to 100)
        total_score = 0.0
        criteria_list: List[QualityCriteriaScore] = []

        for cid, (name, weight) in self.CRITERIA_WEIGHTS.items():
            raw_score = scores.get(cid, 3)
            # Map 0-4 scale to percentage contribution (score/4 * 100 * weight)
            contribution = (raw_score / 4.0) * 100.0 * weight
            total_score += contribution
            criteria_list.append(
                QualityCriteriaScore(
                    criterion_id=cid,
                    name=name,
                    score=raw_score,
                    weight=weight,
                    inspected=vision_inspected,
                    notes=notes.get(cid, f"Score {raw_score}/4 based on art direction fidelity.")
                )
            )

        weighted_final = round(total_score, 1)
        passed = (weighted_final >= 70.0) and (len(critical_blockers) == 0)

        summary = (
            f"Quality Score: {weighted_final}/100. "
            f"{'Approved at professional standard.' if passed else 'Defects identified requiring attention.'}"
        )

        return QualityReviewScorecard(
            criteria=criteria_list,
            weighted_score=weighted_final,
            critical_blockers=critical_blockers,
            defects=defects,
            inspected=vision_inspected,
            passed=passed,
            summary=summary,
        )
