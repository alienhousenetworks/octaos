"""Durable Campaign OS DAG Orchestrator.

Workstream E:
- 3-Stage DAG: Strategy Root -> Idempotent Post Fan-Out -> Critic & Dispatch
- Integrates Prompt Compiler, Compliance Rules Engine, and Claim Verifier
- Graceful degradation (circuit breakers, text-only fallback)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import uuid
from sqlalchemy.orm import Session

from app.models.verticals import ContentPost
from app.models.agents import ActivityLog
from app.models.enterprise import ApprovalRequest
from app.services.knowledge_os.intent_projector import CompanyContextProjectionEngine, IntentType
from app.services.marketing.campaign_os.roles import CampaignRolesEngine
from app.services.marketing.compiler.prompt_compiler import MediaPromptCompiler
from app.services.marketing.autonomy.execution_ledger import MarketingExecutionLedger

logger = logging.getLogger(__name__)


class CampaignOSOrchestrator:
    def __init__(self, db: Session, tenant_id: str, job_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.job_id = job_id
        self.roles = CampaignRolesEngine(db, tenant_id)
        self.projector = CompanyContextProjectionEngine(db, tenant_id)
        self.execution_id: Optional[str] = None
        self._ledger = MarketingExecutionLedger(db, tenant_id)
        self._active_ledger_stage: Optional[str] = None

    def update_stage(
        self,
        stage_id: str,
        stage_name: str,
        progress_pct: float,
        message: Optional[str] = None,
        is_complete: bool = False,
        is_failed: bool = False,
        error: Optional[str] = None,
    ):
        # Persist stage transitions independently of the UI GenerationJob row.
        if self.execution_id:
            try:
                if self._active_ledger_stage and self._active_ledger_stage != stage_id:
                    self._ledger.finish_step(
                        self.execution_id, self._active_ledger_stage,
                        output_payload={"message": message or "Stage advanced"},
                    )
                if is_failed:
                    self._ledger.finish_step(
                        self.execution_id, stage_id, error=error or "Stage failed"
                    )
                    self._active_ledger_stage = None
                elif is_complete:
                    if self._active_ledger_stage == stage_id:
                        self._ledger.finish_step(
                            self.execution_id, stage_id,
                            output_payload={"message": message or "Stage completed"},
                        )
                    self._active_ledger_stage = None
                elif self._active_ledger_stage != stage_id:
                    self._ledger.begin_step(
                        self.execution_id, stage_id,
                        input_payload={"stage_name": stage_name, "progress_pct": progress_pct},
                    )
                    self._active_ledger_stage = stage_id
            except Exception as ledger_err:
                logger.warning("[CampaignOS] Execution ledger update failed: %s", ledger_err)
        if not self.job_id:
            return
        try:
            from app.models.verticals import GenerationJob
            job = self.db.query(GenerationJob).filter(GenerationJob.id == self.job_id).first()
            if not job:
                return
            payload = dict(job.request_payload or {})
            payload["current_stage"] = stage_id
            payload["current_stage_label"] = stage_name
            payload["progress_pct"] = progress_pct

            stages = list(payload.get("stages", []))
            stage_order = [s["id"] for s in stages]
            if stage_id in stage_order:
                cur_idx = stage_order.index(stage_id)
                for idx, s in enumerate(stages):
                    if idx < cur_idx:
                        s["status"] = "completed"
                    elif idx == cur_idx:
                        s["status"] = "completed" if is_complete else "in_progress"
                    elif not is_complete:
                        s["status"] = "pending"
            if is_complete:
                for s in stages:
                    s["status"] = "completed"

            payload["stages"] = stages

            logs = list(payload.get("logs", []))
            if message:
                logs.append({
                    "stage": stage_name,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            payload["logs"] = logs
            job.request_payload = payload
            if is_failed:
                job.status = "failed"
                job.error = error
            elif is_complete:
                job.status = "completed"
            else:
                job.status = "in_progress"
            self.db.commit()
        except Exception as e:
            logger.debug(f"[CampaignOS] Failed to update job stage: {e}")

    async def execute_campaign_dag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the durable multi-stage campaign generation DAG using the 15-Agent Council."""
        topic = params.get("topic", "Enterprise Automation")
        idempotency_key = str(
            params.get("idempotency_key") or self.job_id or uuid.uuid4()
        )
        execution = self._ledger.start_or_resume(
            "campaign_os",
            idempotency_key,
            params,
        )
        self.execution_id = execution.id
        if execution.status == "completed" and execution.result_payload:
            return execution.result_payload
        days = int(params.get("days", 3))
        platforms = params.get("platforms", ["linkedin", "instagram"])
        posts_per_day = int(params.get("posts_per_day", 1))
        target_time_slots = params.get("target_time_slots")
        content_format = params.get("content_format", "social_posts")
        reference_image_url = params.get("reference_image_url")
        generate_images = bool(params.get("generate_images", True))
        generate_videos = bool(params.get("generate_videos", False))

        # Dynamic Model Resolution
        from app.services.ai_gateway.registry import ModelRegistry
        reg = ModelRegistry.get_instance()

        text_sel = params.get("text", {}) if isinstance(params.get("text"), dict) else {}
        image_sel = params.get("image", {}) if isinstance(params.get("image"), dict) else {}
        video_sel = params.get("video", {}) if isinstance(params.get("video"), dict) else {}

        pref_text_p = text_sel.get("provider") or params.get("text_provider") or "auto"
        pref_text_m = text_sel.get("model") or params.get("text_model") or "meta-llama/llama-3.3-70b-instruct"

        pref_img_p = image_sel.get("provider") or params.get("image_provider") or "together"
        pref_img_m = image_sel.get("model") or params.get("image_model")

        pref_vid_p = video_sel.get("provider") or params.get("video_provider") or "together"
        pref_vid_m = video_sel.get("model") or params.get("video_model")

        strat_p, strat_m, strat_fallback = await reg.resolve_model(self.db, self.tenant_id, "text", pref_text_p, pref_text_m)
        img_p, img_m, img_fallback = await reg.resolve_model(self.db, self.tenant_id, "image", pref_img_p, pref_img_m)
        vid_p, vid_m, vid_fallback = await reg.resolve_model(self.db, self.tenant_id, "video", pref_vid_p, pref_vid_m)

        fallback_notes = [f for f in [strat_fallback, img_fallback, vid_fallback] if f]
        primary_fallback_reason = "; ".join(fallback_notes) if fallback_notes else None

        # ── Stage 0: Brand & Market Context Anchor (Agents 1-5) ────────────
        self.update_stage(
            "context",
            "Brand & Market Context Anchor (Agents 1-5)",
            15.0,
            f"[Agents 1-5] Ingesting Brand DNA, Product Catalog, Audience ICP, Proof Points, and Context Radar for '{topic}'.",
        )
        campaign_projection = await self.projector.get_projection(
            intent=IntentType.CAMPAIGN_MARKETING
        )
        approved_evidence = campaign_projection.get("approved_claims", [])

        # Synthesize immutable Brand Context Anchor (Agents 1 through 5)
        try:
            brand_anchor = await self.roles.synthesize_brand_context_anchor(
                company_context=campaign_projection,
                topic=topic,
                days=days,
                provider=strat_p,
                model=strat_m,
            )
        except Exception as anchor_err:
            logger.warning(f"[CampaignOS] Anchor synthesis fell back to direct projection: {anchor_err}")
            brand_anchor = None

        # ── Stage 1: Campaign Strategy & Narrative Architecture (Agents 1, 2, 6)
        self.update_stage(
            "strategy",
            "Campaign Strategy & Narrative Architecture (Agents 1, 2, 6)",
            30.0,
            f"Formulating strategic narrative, tone architecture, and visual tokens with {strat_p}/{strat_m}.",
        )
        self.log_activity(
            "Campaign Strategy",
            f"Formulating strategic narrative and visual tokens for {days}-day campaign on: {topic} (Engine: {strat_p}/{strat_m})",
            status="pending",
        )

        try:
            brand_brief = await self.roles.execute_brand_strategist(
                topic=topic,
                campaign_projection=campaign_projection,
                provider=strat_p,
                model=strat_m,
            )

            visual_tokens = await self.roles.execute_visual_director(
                brand_brief=brand_brief,
                campaign_projection=campaign_projection,
                provider=strat_p,
                model=strat_m,
            )

            narrative_arc = await self.roles.execute_narrative_architect(
                days=days,
                brand_brief=brand_brief,
                provider=strat_p,
                model=strat_m,
            )
        except Exception as strat_err:
            logger.error(f"[CampaignOS] Strategic blueprint generation failed: {strat_err}")
            err_msg = str(strat_err)
            self.log_activity(
                "Campaign Strategy Failed",
                f"Failed to generate campaign blueprint for '{topic}': {err_msg}",
                status="failed",
            )
            return {
                "status": "failed",
                "error": err_msg,
                "campaign_title": topic,
                "total_posts_generated": 0,
                "approved_count": 0,
                "needs_review_count": 0,
                "failed_count": days * len(platforms) * posts_per_day,
                "posts": [],
            }

        # ── Stage 2: Chronological Time-Slot Cadence Scheduler (Agent 7) ────
        schedule_plan = await self.roles.execute_cadence_scheduler(
            narrative_arc=narrative_arc,
            platforms=platforms,
            posts_per_day=posts_per_day,
            target_time_slots=target_time_slots,
            provider=strat_p,
            model=strat_m,
        )

        self.update_stage(
            "narrative",
            "Multi-Day Narrative & Cadence Scheduling (Agents 6 & 7)",
            45.0,
            f"[Agent 7] Scheduled {len(schedule_plan.slots)} publication slots across {days} days ({posts_per_day} slot(s)/day) for {len(platforms)} platforms.",
        )
        self.log_activity(
            "Campaign Blueprint",
            f"Narrative arc completed: '{narrative_arc.campaign_title}'. Scheduled {len(schedule_plan.slots)} slots ({posts_per_day}/day x {days} days x {len(platforms)} platforms).",
            status="success",
        )

        # ── Stage 3: Multi-Slot Creative Fan-Out per Slot x Platform (Agents 8-12)
        generated_posts = []
        approved_count = 0
        needs_review_count = 0
        all_scorecards = []
        total_target = max(1, len(schedule_plan.slots))
        processed_count = 0

        for slot in schedule_plan.slots:
            day_outline = next((d for d in narrative_arc.days_outline if d.day == slot.day), narrative_arc.days_outline[0])
            platform = slot.platform
            idempotency_key = f"{self.tenant_id}:{narrative_arc.campaign_title[:20]}:{slot.day}:{slot.slot_index}:{platform}"

            try:
                # Role 4 / Agent 8: Platform-Native Copywriter
                draft = await self.roles.execute_platform_adapter(
                    day_outline=day_outline,
                    brand_brief=brand_brief,
                    platform=platform,
                    provider=strat_p,
                    model=strat_m,
                    content_format=content_format,
                )
                processed_count += 1
                draft_pct = 45.0 + min(25.0, (processed_count / total_target) * 25.0)
                self.update_stage(
                    "drafting",
                    "Platform Copywriting & Multi-Slot Adaptation (Agents 8 & 9)",
                    round(draft_pct, 1),
                    f"[Agent 8] Drafted {slot.slot_label} post: '{draft.hook[:45]}...'",
                )

                # Agent 9: Viral Hook & Headline Engineer
                if brand_anchor:
                    try:
                        hook_variant = await self.roles.execute_hook_engineer(
                            slot=slot,
                            brand_anchor=brand_anchor,
                            post_draft=draft,
                            provider=strat_p,
                            model=strat_m,
                        )
                        if hook_variant and hook_variant.winning_hook and hook_variant.winning_hook != draft.hook:
                            draft.hook = hook_variant.winning_hook
                    except Exception as hook_err:
                        logger.debug(f"[Agent 9: HookEngineer] Bypassed ({hook_err})")

                # Role 5 / Agent 10: Conversion CRO & Offer Architect
                cta_spec = await self.roles.execute_offer_cta_engineer(
                    draft=draft,
                    brand_brief=brand_brief,
                    provider=strat_p,
                    model=strat_m,
                )

                # Media Compilation (Agents 11 & 12)
                compiled_image_prompt = None
                compiled_video_prompt = None

                if generate_images:
                    # Role 6 / Agent 11: Visual Art Director & Image Prompt Engineer
                    image_intent = await self.roles.execute_image_concept_director(
                        draft=draft,
                        visual_tokens=visual_tokens,
                        provider=strat_p,
                        model=strat_m,
                        reference_image_url=reference_image_url,
                    )
                    image_res = MediaPromptCompiler.compile_for_target(
                        target_provider=img_p,
                        intent=image_intent,
                        visual_style=visual_tokens.model_dump(),
                        seed_key=idempotency_key,
                        platform=platform,
                        reference_image_url=reference_image_url,
                        model_slug=img_m,
                        headline_text=draft.hook,
                    )
                    compiled_image_prompt = image_res.get("prompt")

                if generate_videos:
                    # Role 7 / Agent 12: Cinematic Video Director & Motion Scriptwriter
                    video_plan = await self.roles.execute_video_shot_planner(
                        draft=draft,
                        visual_tokens=visual_tokens,
                        platform=platform,
                        provider=strat_p,
                        model=strat_m,
                        reference_image_url=reference_image_url,
                        target_provider=vid_p,
                        brand_dna=brand_anchor.brand_dna if brand_anchor else None,
                    )
                    video_res = MediaPromptCompiler.compile_video_shot_list(
                        shot_plan=video_plan,
                        seed_key=idempotency_key,
                    )
                    compiled_video_prompt = video_res.get("prompt")

                if compiled_image_prompt or compiled_video_prompt:
                    self.update_stage(
                        "creative",
                        "Visual Art & Video Scene Direction (Agents 11 & 12)",
                        round(min(80.0, draft_pct + 4.0), 1),
                        f"[Agents 11 & 12] Compiled visual prompt & scene kinetics for {slot.slot_label}.",
                    )

                # Role 9 / Agents 13 & 14: Dual Fact-Checking & Compliance Gates with Self-Repair
                score_card = await self.roles.execute_critic_judge(
                    post_draft=draft,
                    approved_evidence=approved_evidence,
                    brand_brief=brand_brief,
                    pack_id=campaign_projection.get("industry_pack_id"),
                    provider=strat_p,
                    model=strat_m,
                )
                all_scorecards.append(score_card)

                self.update_stage(
                    "compliance",
                    "Dual Fact-Checking & Compliance Review (Agents 13 & 14)",
                    round(min(88.0, draft_pct + 7.0), 1),
                    f"[Agents 13 & 14] Evaluated {slot.slot_label}: confidence {int(score_card.overall_confidence * 100)}% ({'Approved' if score_card.is_approved else 'Needs Review'}).",
                )

                # Parse scheduled time for this distinct slot
                from datetime import timedelta
                try:
                    scheduled_dt = datetime.fromisoformat(slot.scheduled_time_utc)
                except Exception:
                    scheduled_dt = datetime.now(timezone.utc) + timedelta(days=slot.day - 1, hours=slot.slot_index * 4)

                # Persist Post Record with Slot Timestamp & Model Tracking
                post = ContentPost(
                    tenant_id=self.tenant_id,
                    platform=platform,
                    content=draft.formatted_full_post,
                    image_prompt=compiled_image_prompt,
                    video_prompt=compiled_video_prompt,
                    media_prompt=compiled_image_prompt or compiled_video_prompt,
                    day=slot.day,
                    status="draft",
                    approval_status="approved" if score_card.is_approved else "pending",
                    scheduled_at=scheduled_dt,
                    performance_score=score_card.overall_confidence * 100.0,
                    learning_tags=[day_outline.narrative_focus, cta_spec.action_type, f"slot:{slot.slot_label}"],
                    used_model=f"{strat_p}/{strat_m}",
                    fallback_reason=primary_fallback_reason,
                    cost_usd=0.0,
                )
                self.db.add(post)
                self.db.commit()
                self.db.refresh(post)

                # Escalation if Confidence < 0.85
                if not score_card.is_approved:
                    needs_review_count += 1
                    approval_req = ApprovalRequest(
                        tenant_id=self.tenant_id,
                        action_type="public_post",
                        channel=platform,
                        agent_name="Campaign OS",
                        resource_type="post",
                        resource_id=post.id,
                        title=f"Review {slot.slot_label}: {draft.hook[:40]}",
                        payload={
                            "content": draft.formatted_full_post,
                            "image_prompt": compiled_image_prompt,
                            "confidence": score_card.overall_confidence,
                            "unsupported_claims": score_card.unsupported_claims,
                            "compliance_issues": score_card.compliance_issues,
                        },
                        confidence=score_card.overall_confidence,
                        status="pending",
                        policy_reason="; ".join(score_card.unsupported_claims + score_card.compliance_issues) or "Confidence below threshold",
                    )
                    self.db.add(approval_req)
                    self.db.commit()
                else:
                    approved_count += 1

                generated_posts.append({
                    "post_id": post.id,
                    "day": slot.day,
                    "slot_label": slot.slot_label,
                    "scheduled_at": scheduled_dt.isoformat(),
                    "platform": platform,
                    "approved": score_card.is_approved,
                    "confidence": score_card.overall_confidence,
                    "image_prompt": compiled_image_prompt[:120] if compiled_image_prompt else None,
                })

            except Exception as post_err:
                logger.error(f"[CampaignOS] Error generating post for {slot.slot_label}: {post_err}")
                self.db.rollback()
                failed_reason = str(post_err)
                try:
                    failed_post = ContentPost(
                        tenant_id=self.tenant_id,
                        platform=platform,
                        content="",
                        day=slot.day,
                        status="failed",
                        approval_status="failed",
                        fallback_reason=f"AI generation failed: {failed_reason[:200]}",
                        used_model=f"{strat_p}/{strat_m}",
                    )
                    self.db.add(failed_post)
                    self.db.commit()
                    self.db.refresh(failed_post)
                    f_id = failed_post.id
                except Exception:
                    self.db.rollback()
                    f_id = None
                generated_posts.append({
                    "post_id": f_id,
                    "day": slot.day,
                    "slot_label": slot.slot_label,
                    "platform": platform,
                    "failed": True,
                    "error": failed_reason,
                })

        # ── Stage 4: Chief Marketing Officer (CMO) Council Review (Agent 15) ─
        cmo_verdict = None
        if brand_anchor:
            try:
                cmo_verdict = await self.roles.execute_cmo_orchestrator(
                    campaign_title=narrative_arc.campaign_title,
                    total_slots=len(schedule_plan.slots),
                    scorecards=all_scorecards,
                    brand_anchor=brand_anchor,
                    provider=strat_p,
                    model=strat_m,
                )
            except Exception as cmo_err:
                logger.debug(f"[Agent 15: CMO] Review bypassed: {cmo_err}")

        failed_count = sum(1 for p in generated_posts if p.get("failed"))
        success_count = len(generated_posts) - failed_count

        if failed_count > 0 and success_count == 0:
            self.log_activity(
                "Campaign Generation Failed",
                f"All {failed_count} posts failed AI generation: {generated_posts[0].get('error') if generated_posts else 'Unknown error'}",
                status="failed",
            )
        elif failed_count > 0:
            self.log_activity(
                "Campaign Generation Completed with Errors",
                f"Generated {success_count} posts successfully; {failed_count} posts failed AI generation.",
                status="warning",
            )
        else:
            cmo_msg = cmo_verdict.executive_summary if cmo_verdict else ""
            self.log_activity(
                "Campaign Generation Completed",
                f"Successfully generated {len(generated_posts)} posts across {days} days ({approved_count} auto-approved, {needs_review_count} flagged for review). {cmo_msg}",
                status="success",
            )

        self.update_stage(
            "dispatch",
            "Executive CMO Dispatch & Scheduling (Agent 15)",
            95.0,
            f"[Agent 15: CMO] Confirmed {len(generated_posts)} posts scheduled in drafts ({approved_count} auto-approved, {needs_review_count} flagged for review).",
        )

        result = {
            "status": "success" if failed_count == 0 else ("partial" if success_count > 0 else "failed"),
            "campaign_title": narrative_arc.campaign_title,
            "total_posts_generated": len(generated_posts),
            "approved_count": approved_count,
            "needs_review_count": needs_review_count,
            "failed_count": failed_count,
            "posts_per_day": schedule_plan.posts_per_day,
            "cmo_verdict": cmo_verdict.model_dump() if cmo_verdict else None,
            "posts": generated_posts,
            "execution_id": self.execution_id,
        }
        if self.execution_id:
            try:
                if self._active_ledger_stage:
                    self._ledger.finish_step(
                        self.execution_id, self._active_ledger_stage,
                        output_payload={"status": result["status"], "posts": len(generated_posts)},
                    )
                    self._active_ledger_stage = None
                self._ledger.complete(self.execution_id, result)
            except Exception as ledger_err:
                logger.warning("[CampaignOS] Failed to finalize execution ledger: %s", ledger_err)
        return result

    def log_activity(self, action: str, description: str, status: str = "success"):
        try:
            log = ActivityLog(
                tenant_id=self.tenant_id,
                agent_name="Campaign OS",
                action=action,
                description=description,
                status=status,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.debug(f"[CampaignOS] Failed to log activity: {e}")
