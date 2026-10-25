"""Autonomous Marketing Agent.

Equipped with:
  1. Brand & Product Knowledge Synthesizer (deep comprehension of brand offerings)
  2. Context Radar (upcoming cultural/business calendar events & live industry news/innovations)
  3. Trend Synthesizer (connects brand USPs with current events/news like a human marketer)
  4. External AI Video & Visual Generation (Wan2.1, Kling, MiniMax, FLUX via AI Gateway)
  5. Autonomous Scheduling & Multi-Channel Distribution with Safety Gate.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from app.services.agents.base import BaseAgent
from app.models.verticals import ContentPost
from app.models.enterprise import ApprovalRequest
from app.services.knowledge_os.brand_synthesizer import BrandKnowledgeService
from app.services.marketing.context_radar.calendar_engine import CalendarEngine
from app.services.marketing.context_radar.news_radar import NewsRadar
from app.services.marketing.context_radar.trend_synthesizer import TrendSynthesizer
from app.services.media.storage import ensure_public_url
from app.services.marketing.autonomy.decision_engine import compute_schedule_time

logger = logging.getLogger(__name__)


def _prompt_text(value: Any) -> Optional[str]:
    """Prompt columns are Text; LLM briefs may return structured dicts."""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _compute_optimal_schedule_time(
    platform: str,
    offset_days: int = 0,
    timezone_name: str = "UTC",
    preferred_hours: Optional[Dict[str, int]] = None,
) -> datetime:
    """Return a UTC timestamp for a local-time posting slot.

    Platform hours are fallback heuristics, not a claim about this account's
    audience. Supply measured account-specific hours through preferred_hours.
    """
    return compute_schedule_time(
        platform,
        offset_days=offset_days,
        timezone_name=timezone_name,
        preferred_hours=preferred_hours,
    )


class MarketingAgent(BaseAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "Marketing AI")

    # ------------------------------------------------------------------ #
    # Task Router
    # ------------------------------------------------------------------ #

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})

        if action == "autonomous_marketing_pulse":
            return await self.autonomous_marketing_pulse(params)
        elif action == "scan_context_radar":
            return await self.scan_context_radar(params)
        elif action == "create_posts":
            return await self._create_posts(params)
        elif action == "generate_campaign":
            return await self._generate_campaign(params)
        elif action == "sync_analytics":
            return await self._sync_analytics(params)
        elif action == "learning_report":
            return await self._learning_report(params)
        return {"status": "Unknown action", "action": action}

    # ------------------------------------------------------------------ #
    # Context Radar Inspection API
    # ------------------------------------------------------------------ #

    async def scan_context_radar(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scan calendar events, industry news signals, and brand summary.
        Useful for UI dashboards and human marketer inspection before firing campaigns.
        """
        params = params or {}
        days_ahead = int(params.get("days_ahead", 365))
        news_limit = int(params.get("news_limit", 5))
        refresh_regional = bool(params.get("refresh_regional", False))

        brand_service = BrandKnowledgeService(self.db, self.tenant_id)
        brand_knowledge = brand_service.synthesize()

        cal_engine = CalendarEngine(self.db, self.tenant_id)
        param_country = params.get("country")
        param_state = params.get("state")
        param_scope = params.get("scope")

        target_regions = [param_country] if param_country else cal_engine.get_target_regions()
        target_states = [param_state] if param_state else cal_engine.get_target_states()

        # Autonomous Agentic Live Context Search:
        # Trigger discovery if on-demand refresh requested or if target regions exist without fresh 30-day cache
        if refresh_regional or (target_regions and not cal_engine.has_recent_agentic_events(max_age_days=30)):
            try:
                await cal_engine.discover_agentic_regional_events(
                    target_region=target_regions[0] if target_regions else None,
                    target_state=target_states[0] if target_states else None,
                    days_ahead=max(30, days_ahead),
                    force_refresh=refresh_regional,
                    brand_context=brand_knowledge,
                )
            except Exception as disc_err:
                logger.debug(f"[MarketingAgent] Agentic regional context discovery skipped: {disc_err}")

        upcoming_events = cal_engine.get_upcoming_events(
            days_ahead=days_ahead,
            industry=brand_knowledge.get("industry"),
            target_regions=target_regions,
            target_states=target_states,
            scope=param_scope,
        )

        news_engine = NewsRadar(self.db, self.tenant_id)
        news_signals = news_engine.get_top_signals(
            limit=news_limit,
            brand_context=brand_knowledge.get("industry") or "technology",
        )

        return {
            "tenant_id": self.tenant_id,
            "company_name": brand_knowledge.get("company_name"),
            "industry": brand_knowledge.get("industry"),
            "target_regions": target_regions,
            "target_states": target_states,
            "products_count": len(brand_knowledge.get("products_catalog", [])),
            "upcoming_events": upcoming_events,
            "news_signals": news_signals,
            "brand_voice": brand_knowledge.get("brand_voice"),
            "motion_design_tokens": brand_knowledge.get("motion_design_tokens"),
        }

    # ------------------------------------------------------------------ #
    # Autonomous Marketing Pulse (Auto Mode)
    # ------------------------------------------------------------------ #

    async def autonomous_marketing_pulse(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an autonomous marketing pulse:
          1. Synthesize brand & product knowledge from the KB.
          2. Scan real-world calendar & industry news radar.
          3. Synthesize human marketer angles connecting brand to context.
          4. Generate platform-tailored copy and external AI video / image assets.
          5. Autonomously schedule posts and evaluate critic safety gates.
        """
        params = params or {}
        platforms = params.get("platforms") or ["linkedin", "instagram"]
        if isinstance(platforms, str):
            platforms = [platforms]

        generate_media = params.get("generate_media", True)
        preferred_media_type = params.get("media_type", "auto")  # "video" | "image" | "auto"
        confidence_threshold = float(params.get("confidence_threshold", 0.85))
        auto_schedule = params.get("auto_schedule", True)

        self.log_activity(
            "Autonomous Pulse Initiated",
            f"Scanning Context Radar for {len(platforms)} platforms ({', '.join(platforms)}).",
            status="pending",
        )

        # 1. Synthesize Brand & Product Catalog
        brand_service = BrandKnowledgeService(self.db, self.tenant_id)
        brand_knowledge = brand_service.synthesize()

        # 2. Context Radar Scans
        cal_engine = CalendarEngine(self.db, self.tenant_id)
        upcoming_events = cal_engine.get_upcoming_events(days_ahead=7)

        news_engine = NewsRadar(self.db, self.tenant_id)
        news_signals = news_engine.get_top_signals(
            limit=5,
            brand_context=brand_knowledge.get("industry") or "technology",
        )

        # 3. Trend Synthesizer
        trend_engine = TrendSynthesizer(self.db, self.tenant_id, self.llm)

        created_posts: List[Dict[str, Any]] = []
        angles_used: List[Dict[str, Any]] = []

        for idx, platform in enumerate(platforms):
            try:
                # 3a. Synthesize Strategic Creative Brief
                brief = await trend_engine.synthesize_angle(
                    brand_knowledge=brand_knowledge,
                    calendar_events=upcoming_events,
                    news_signals=news_signals,
                    platform=platform,
                )
                angles_used.append({
                    "platform": platform,
                    "topic": brief.topic,
                    "hook": brief.hook,
                    "media_type": brief.media_type,
                })

                # Determine media mode: force video or image if requested
                active_media_type = brief.media_type
                if preferred_media_type in ("video", "image"):
                    active_media_type = preferred_media_type

                # 3b. Generate Platform Post Copy
                post_copy = await self._generate_platform_copy(
                    brief=brief,
                    brand_knowledge=brand_knowledge,
                    platform=platform,
                )

                # 3c. Generate External AI Video or Image Asset
                image_url: Optional[str] = None
                video_url: Optional[str] = None
                used_model: Optional[str] = None

                if generate_media:
                    if active_media_type == "video":
                        vid_prompt = brief.video_prompt or brief.hook
                        vid_provider = params.get("video_provider") or brief.video_provider
                        vid_model = params.get("video_model") or brief.video_model
                        try:
                            v_raw = await self.llm.generate_video(
                                prompt=vid_prompt,
                                provider=vid_provider,
                                model=vid_model,
                            )
                            if v_raw and not str(v_raw).startswith("error:"):
                                video_url = await ensure_public_url(
                                    v_raw, prefix="vid", default_mime="video/mp4"
                                )
                                used_model = f"{vid_provider}/{vid_model or 'default'}"
                        except Exception as vid_err:
                            logger.warning(
                                f"[AutoPulse] Video generation failed gracefully for {platform}: {vid_err}"
                            )
                    else:
                        img_prompt = brief.image_prompt or brief.hook
                        img_provider = params.get("image_provider") or brief.image_provider
                        img_model = params.get("image_model") or brief.image_model
                        try:
                            raw = await self.llm.generate_image(
                                prompt=img_prompt,
                                provider=img_provider,
                                model=img_model,
                            )
                            if raw and not str(raw).startswith("error:"):
                                image_url = await ensure_public_url(raw, prefix="img")
                                used_model = f"{img_provider}/{img_model or 'default'}"
                        except Exception as img_err:
                            logger.warning(
                                f"[AutoPulse] Image generation failed gracefully for {platform}: {img_err}"
                            )

                # 3d. Autonomous Scheduling
                scheduled_time = (
                    _compute_optimal_schedule_time(
                        platform,
                        offset_days=idx,
                        timezone_name=params.get("timezone") or params.get("account_timezone") or "UTC",
                        preferred_hours=params.get("preferred_posting_hours"),
                    )
                    if auto_schedule
                    else None
                )

                # 3e. Critic & Confidence Evaluation
                confidence_score = self._evaluate_post_confidence(brief, brand_knowledge)
                # LLM failure/fallback output must never self-approve for scheduling.
                is_approved = (
                    confidence_score >= confidence_threshold
                    and getattr(brief, "generation_status", "generated") == "generated"
                )

                # 3f. Persist ContentPost
                post = ContentPost(
                    tenant_id=self.tenant_id,
                    platform=platform,
                    content=post_copy,
                    image_url=image_url,
                    video_url=video_url,
                    image_prompt=_prompt_text(brief.image_prompt),
                    image_prompt_enabled=bool(image_url),
                    video_prompt=_prompt_text(brief.video_prompt),
                    video_prompt_enabled=bool(video_url),
                    media_prompt=_prompt_text(
                        brief.video_prompt if active_media_type == "video" else brief.image_prompt
                    ),
                    status="scheduled" if (auto_schedule and is_approved) else "draft",
                    approval_status="approved" if is_approved else "pending",
                    scheduled_at=scheduled_time,
                    performance_score=confidence_score * 100.0,
                    learning_tags=[brief.topic[:30], f"angle:{active_media_type}"],
                    used_model=used_model,
                )
                self.db.add(post)
                self.db.commit()
                self.db.refresh(post)

                # Human review queue escalation if confidence < threshold
                if not is_approved:
                    approval_req = ApprovalRequest(
                        tenant_id=self.tenant_id,
                        action_type="public_post",
                        channel=platform,
                        agent_name="Marketing AI",
                        resource_type="post",
                        resource_id=post.id,
                        title=f"Auto-Mode Review: {brief.hook[:40]} ({platform.title()})",
                        payload={
                            "content": post_copy,
                            "topic": brief.topic,
                            "media_type": active_media_type,
                            "image_url": image_url,
                            "video_url": video_url,
                            "confidence": confidence_score,
                        },
                        confidence=confidence_score,
                        status="pending",
                        policy_reason=f"Confidence {confidence_score:.2f} below threshold {confidence_threshold:.2f}",
                    )
                    self.db.add(approval_req)
                    self.db.commit()

                created_posts.append({
                    "id": post.id,
                    "platform": platform,
                    "topic": brief.topic,
                    "hook": brief.hook,
                    "media_type": active_media_type,
                    "image_url": image_url,
                    "video_url": video_url,
                    "status": post.status,
                    "approval_status": post.approval_status,
                    "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
                    "confidence": confidence_score,
                })

            except Exception as platform_err:
                self.db.rollback()
                logger.error(
                    f"[AutoPulse] Failed generating post for {platform}: {platform_err}",
                    exc_info=True,
                )

        summary_msg = (
            f"Autonomous pulse created {len(created_posts)} posts across "
            f"[{', '.join(p['platform'] for p in created_posts)}]."
        )
        self.log_activity("Autonomous Pulse Complete", summary_msg, status="success")

        return {
            "status": "success",
            "message": summary_msg,
            "posts_created": len(created_posts),
            "posts": created_posts,
            "angles_used": angles_used,
            "radar_context": {
                "events_detected": len(upcoming_events),
                "news_signals_detected": len(news_signals),
                "brand_name": brand_knowledge.get("company_name"),
            },
        }

    # ------------------------------------------------------------------ #
    # Platform Copy Generation
    # ------------------------------------------------------------------ #

    async def _generate_platform_copy(
        self,
        brief: Any,
        brand_knowledge: Dict[str, Any],
        platform: str,
    ) -> str:
        """Generate high-converting platform-tailored copy using LLMGateway."""
        company = brand_knowledge.get("company_name", "Our Company")
        voice = brand_knowledge.get("brand_voice", {})
        tone = voice.get("tone", "Authoritative, insightful, visionary")

        platform_guidelines = {
            "linkedin": (
                "Write in a thoughtful, B2B editorial voice. 3-4 paragraphs with white space. "
                "Include a bold opening line, 2-3 bulleted insights, and an engaging question at the end."
            ),
            "instagram": (
                "Write a concise, visually compelling caption. Keep it relatable and human. "
                "Add 3-5 relevant hashtags at the bottom."
            ),
            "facebook": (
                "Warm, community-driven conversational tone. Foster discussion and connection."
            ),
            "twitter": (
                "Punchy, high-signal, under 260 characters. A bold claim or provocative observation."
            ),
        }.get(platform.lower(), "Authentic, engaging, value-first.")

        prompt = f"""You are a world-class social media copywriter writing for {company}.

Brand Tone: {tone}
Platform: {platform.title()}
Guidelines: {platform_guidelines}

Topic: {brief.topic}
Opening Hook: {brief.hook}
Narrative Angle: {brief.narrative_angle}
Call to Action: {brief.call_to_action}

Write the complete post caption now. Do not include meta commentary or introductory labels."""

        try:
            resp = await self.llm.complete(
                prompt,
                system_prompt="You are an expert social media copywriter. Output only the final post text.",
            )
            if resp and resp.strip():
                return resp.strip()
        except Exception as e:
            logger.warning(f"Copy generation LLM call failed ({e}); using brief template.")

        # High-quality fallback template
        return f"{brief.hook}\n\n{brief.narrative_angle}\n\n{brief.call_to_action}\n\n#Innovation #{company.replace(' ', '')}"

    def _evaluate_post_confidence(
        self, brief: Any, brand_knowledge: Dict[str, Any]
    ) -> float:
        """Heuristic confidence evaluation for auto-scheduling safety gate."""
        score = 0.88  # base confident score for synthesized brief

        # Higher confidence if verified products exist
        if brand_knowledge.get("products_catalog"):
            score += 0.04

        # Higher confidence if approved claims exist
        if brand_knowledge.get("approved_claims"):
            score += 0.03

        # Slightly lower if hook is very short
        if len(getattr(brief, "hook", "")) < 20:
            score -= 0.08

        return min(0.98, max(0.60, score))

    # ------------------------------------------------------------------ #
    # Existing Campaigns, Analytics & Routine API (Maintained for Compat)
    # ------------------------------------------------------------------ #

    async def _generate_campaign(self, params: dict):
        from app.worker.tasks import generate_campaign_task

        payload = {
            "topic": params.get("topic", "our company"),
            "days": int(params.get("days", 7)),
            "platforms": params.get("platforms", ["linkedin", "instagram", "facebook"]),
            "text_provider": params.get("text_provider") or params.get("provider") or "gemini",
            "text_model": params.get("text_model") or params.get("model"),
            "image_provider": params.get("image_provider", "together"),
            "video_provider": params.get("video_provider", "together"),
            "generate_images": params.get("generate_images", True),
            "generate_videos": params.get("generate_videos", False),
            "generate_remotion": False,
        }
        generate_campaign_task.delay(self.tenant_id, payload)
        days = payload["days"]
        self.log_activity(
            "Campaign Generation",
            f"Queued {days}-day multi-platform campaign with media generation.",
            status="pending",
        )
        return {
            "status": "queued",
            "message": f"{days}-day marketing campaign queued (text + images; learning-aware).",
            "params": payload,
        }

    async def _create_posts(self, params: dict):
        """Learning-aware short batch."""
        days = int(params.get("days", 3))
        topic = params.get("topic", "our business")
        platforms = params.get("platforms", ["linkedin"])
        return await self._generate_campaign({
            "topic": topic,
            "days": days,
            "platforms": platforms,
            "generate_images": params.get("generate_images", True),
            "generate_videos": params.get("generate_videos", False),
            "text_provider": params.get("provider"),
            "text_model": params.get("model"),
            "image_provider": params.get("image_provider", "together"),
        })

    async def _sync_analytics(self, params: dict):
        from app.services.marketing.analytics import MarketingAnalyticsService
        from asgiref.sync import async_to_sync

        svc = MarketingAnalyticsService(self.db, self.tenant_id)
        result = async_to_sync(svc.sync_all)(limit=int(params.get("limit", 50)))
        self.log_activity(
            "Analytics Sync",
            f"Synced insights: {result.get('synced')} ok, {result.get('errors')} errors, "
            f"{result.get('patterns_updated')} patterns.",
            status="success",
        )
        return result

    async def _learning_report(self, params: dict):
        from app.services.marketing.analytics import MarketingAnalyticsService

        dash = MarketingAnalyticsService(self.db, self.tenant_id).analytics_dashboard()
        self.log_activity(
            "Learning Report",
            "Generated marketing performance learning dashboard.",
            status="success",
        )
        return dash

    async def daily_routine(self):
        """Daily autonomous routine: syncs analytics, then fires context-aware pulse."""
        self.log_activity("Daily Routine", "Initiating autonomous daily marketing cycle.", status="pending")
        try:
            await self._sync_analytics({"limit": 40})
        except Exception as e:
            logger.warning(f"Daily Analytics sync failed gracefully: {e}")
            self.log_activity("Daily Analytics Warning", str(e)[:200], status="warning")

        # Execute the Autonomous Marketing Pulse with Context Radar
        try:
            pulse_result = await self.autonomous_marketing_pulse({
                "platforms": ["linkedin", "instagram"],
                "generate_media": True,
                "auto_schedule": True,
            })
            self.log_activity(
                "Daily Marketing Pulse Completed",
                f"Autonomous pulse created {pulse_result.get('posts_created', 0)} posts.",
                status="success",
            )
            return pulse_result
        except Exception as e:
            logger.error(f"Autonomous marketing pulse failed: {e}", exc_info=True)
            self.log_activity("Daily Marketing Pulse Failed", str(e)[:200], status="failed")
            # Safe fallback to standard light post generation
            return await self._create_posts({
                "days": 1,
                "topic": "daily brand awareness",
                "platforms": ["linkedin"],
                "generate_images": True,
            })
