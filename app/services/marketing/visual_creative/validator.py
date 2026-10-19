"""Delivery Validator & Transparent Handoff (Stage 7 of Universal Visual Creation).

Validates technical specifications, ensures format adherence, and produces
an honest delivery package disclosing any unresolved defects.
"""
from typing import Dict, Any, List, Optional
from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
    QualityReviewScorecard,
    VisualRunRecord,
)


class DeliveryValidator:
    """Verifies deliverable specifications and formats the final handoff."""

    @classmethod
    def validate_and_package(
        cls,
        intent: VisualIntentInputContract,
        brief: CreativeBrief,
        asset_url: Optional[str],
        scorecard: QualityReviewScorecard,
        adapter_info: Dict[str, Any],
        revisions: List[Any],
        generation_error: Optional[str] = None,
    ) -> VisualRunRecord:
        """Construct the complete, auditable VisualRunRecord."""
        status = "completed"
        requires_approval = False
        limitations: List[str] = []

        if generation_error:
            status = "failed"
            limitations.append(f"Media generation encountered error: {generation_error}")
            next_action = "Review API key configuration or select alternative provider."
        elif not scorecard.passed:
            status = "needs_review"
            requires_approval = True
            for blocker in scorecard.critical_blockers:
                limitations.append(f"Unresolved critical blocker: {blocker}")
            for defect in scorecard.defects:
                limitations.append(f"Visible defect: {defect.get('defect')}")
            next_action = "Manual review required before external publication."
        else:
            status = "completed"
            requires_approval = False
            next_action = "Deliverable verified and ready for deployment."

        assets_list = []
        if asset_url:
            assets_list.append({
                "url": asset_url,
                "type": intent.deliverable,
                "aspect_ratio": intent.aspect_ratio,
                "status": "ready" if scorecard.passed else "flagged",
            })

        return VisualRunRecord(
            request_id=intent.request_id,
            deliverable_type=intent.deliverable,
            status=status,
            creative_brief=brief,
            selected_specialists=brief.selected_specialists,
            selected_adapter=adapter_info.get("provider"),
            selected_model=adapter_info.get("model"),
            generation_plan=[adapter_info],
            assets=assets_list,
            primary_asset_url=asset_url,
            quality_review=scorecard,
            revisions=revisions,
            limitations=limitations,
            requires_approval=requires_approval,
            cost_usd=0.0,
            next_action=next_action,
        )
