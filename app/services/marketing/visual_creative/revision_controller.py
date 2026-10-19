"""Revision Controller (Stage 6 of Universal Visual Creation).

Plans and executes bounded, targeted corrections on diagnosed defects
instead of blind regeneration.
"""
from typing import Dict, Any, List, Optional
from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
    QualityReviewScorecard,
    RevisionItem,
)


class RevisionController:
    """Manages targeted defect remediation with strictly bounded iteration limits."""

    MAX_REVISIONS = 2

    @classmethod
    def should_revise(cls, scorecard: QualityReviewScorecard, current_iteration: int) -> bool:
        """Determine if a revision should be attempted."""
        if current_iteration >= cls.MAX_REVISIONS:
            return False
        # Revise if critical blocker exists or weighted score is below threshold
        return (not scorecard.passed) or (len(scorecard.critical_blockers) > 0)

    @classmethod
    def formulate_targeted_fix(
        cls,
        scorecard: QualityReviewScorecard,
        intent: VisualIntentInputContract,
        brief: CreativeBrief,
        compiled_payload: Dict[str, Any],
        iteration: int,
    ) -> Dict[str, Any]:
        """Formulate a targeted correction specifically targeting diagnosed defects."""
        updated_payload = dict(compiled_payload)
        prompt = updated_payload.get("prompt", "")

        diagnosed = "General fidelity adjustment"
        fix_description = "Refined prompt constraints"

        # Check for critical blockers first
        if scorecard.critical_blockers:
            blocker = scorecard.critical_blockers[0]
            diagnosed = blocker
            if "anatomy" in blocker.lower() or "limb" in blocker.lower() or "hand" in blocker.lower():
                prompt += ", anatomically flawless posture, pristine five-finger hands, zero anatomical distortions"
                fix_description = "Injected strict anatomical fidelity constraint"
            elif "text" in blocker.lower() or "typography" in blocker.lower():
                prompt += f', pristine typography text reading "{intent.subject[:30]}", crisp vector kerning'
                fix_description = "Strengthened in-image typographic definition"
            elif "lighting" in blocker.lower() or "reflection" in blocker.lower():
                prompt += ", accurate physical specular highlights, true reflections, natural raytraced illumination"
                fix_description = "Adjusted lighting and physical reflection parameters"
            else:
                prompt += ", hyper-focused hero composition, crystal clear subject silhouette"
                fix_description = "Sharpened focal subject definition"

        elif scorecard.defects:
            top_defect = scorecard.defects[0].get("defect", "")
            diagnosed = top_defect
            prompt += f", zero {top_defect}, perfectly rendered {intent.subject}"
            fix_description = f"Targeted suppression of '{top_defect}'"

        updated_payload["prompt"] = prompt
        return {
            "payload": updated_payload,
            "revision_item": RevisionItem(
                iteration=iteration,
                diagnosed_defect=diagnosed,
                targeted_fix=fix_description,
                previous_score=scorecard.weighted_score,
                new_score=0.0,  # Will be populated after reinspection
            )
        }
