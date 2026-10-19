"""Visual Creative Orchestrator (Universal Visual Creative Director Pipeline).

Coordinates the 7 modular stages:
1. visual_intent_analyzer
2. creative_director
3. visual_model_router
4. asset_generator
5. visual_critic
6. revision_controller
7. delivery_validator
"""
from typing import Dict, Any, List, Optional
import logging

from app.services.marketing.visual_creative.contracts import (
    VisualIntentInputContract,
    CreativeBrief,
    QualityReviewScorecard,
    VisualRunRecord,
    RevisionItem,
)
from app.services.marketing.visual_creative.analyzer import VisualIntentAnalyzer
from app.services.marketing.visual_creative.creative_director import DynamicCreativeDirector
from app.services.marketing.visual_creative.model_router import VisualModelRouter
from app.services.marketing.visual_creative.asset_generator import AssetGenerator
from app.services.marketing.visual_creative.critic import VisualCritic
from app.services.marketing.visual_creative.revision_controller import RevisionController
from app.services.marketing.visual_creative.validator import DeliveryValidator

logger = logging.getLogger(__name__)


class VisualCreativeOrchestrator:
    """End-to-end orchestrator for the Universal Visual Creative Director skill."""

    def __init__(self, db_session, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id
        self.generator = AssetGenerator(db_session, tenant_id)
        self.critic = VisualCritic(db_session, tenant_id)

    async def execute(
        self,
        raw_prompt: str,
        deliverable: Optional[str] = None,
        platform: Optional[str] = None,
        reference_assets: Optional[List[str]] = None,
        brand_tokens: Optional[Dict[str, Any]] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        inspect_quality: bool = True,
        max_revisions: int = 2,
    ) -> VisualRunRecord:
        """Run the complete 7-stage visual creation workflow."""
        # Stage 1 & 2: Intent & Media Analysis
        intent = VisualIntentAnalyzer.analyze(
            raw_prompt=raw_prompt,
            deliverable=deliverable,
            platform=platform,
            reference_assets=reference_assets,
            brand_tokens=brand_tokens,
        )

        # Stage 3: Dynamic Creative Director & Specialist Team Assembly
        specialists = DynamicCreativeDirector.assemble_specialists(intent)
        brief = DynamicCreativeDirector.create_brief(intent, specialists=specialists)

        # Stage 4: Model Routing & Syntax Compilation
        provider, model = VisualModelRouter.select_model(
            intent=intent,
            brief=brief,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
        )
        compiled_payload = VisualModelRouter.compile_payload(
            intent=intent,
            brief=brief,
            provider=provider,
            model=model,
        )

        # Stage 5: Generation
        gen_result = await self.generator.execute_generation(
            payload=compiled_payload,
            deliverable=intent.deliverable,
        )
        asset_url = gen_result.get("url")
        gen_error = gen_result.get("error")

        # Stage 5.5: Visual Critic & Inspection Gate
        revisions_applied: List[RevisionItem] = []
        if inspect_quality and asset_url:
            scorecard = await self.critic.inspect(
                asset_url=asset_url,
                intent=intent,
                brief=brief,
            )

            # Stage 6: Bounded Revision Controller
            current_iter = 0
            while (
                RevisionController.should_revise(scorecard, current_iter)
                and current_iter < max_revisions
            ):
                current_iter += 1
                logger.info(
                    f"[VisualCreative] Attempting bounded revision {current_iter}/{max_revisions} "
                    f"for defect: {scorecard.critical_blockers or scorecard.defects}"
                )
                fix_data = RevisionController.formulate_targeted_fix(
                    scorecard=scorecard,
                    intent=intent,
                    brief=brief,
                    compiled_payload=compiled_payload,
                    iteration=current_iter,
                )
                compiled_payload = fix_data["payload"]
                revision_item: RevisionItem = fix_data["revision_item"]

                # Re-generate with targeted correction
                retry_result = await self.generator.execute_generation(
                    payload=compiled_payload,
                    deliverable=intent.deliverable,
                )
                if retry_result.get("url"):
                    asset_url = retry_result["url"]
                    gen_error = None
                    scorecard = await self.critic.inspect(
                        asset_url=asset_url,
                        intent=intent,
                        brief=brief,
                    )
                    revision_item.new_score = scorecard.weighted_score
                    revisions_applied.append(revision_item)
                else:
                    break
        else:
            # Baseline inspection for failed or skipped inspection
            scorecard = await self.critic.inspect(
                asset_url=asset_url,
                intent=intent,
                brief=brief,
                generation_error=gen_error,
            )

        # Stage 7: Delivery Validation & Transparent Handoff
        run_record = DeliveryValidator.validate_and_package(
            intent=intent,
            brief=brief,
            asset_url=asset_url,
            scorecard=scorecard,
            adapter_info=compiled_payload,
            revisions=revisions_applied,
            generation_error=gen_error,
        )

        return run_record
