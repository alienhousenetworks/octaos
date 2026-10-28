from typing import Optional, Dict, Any, List
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.verticals.sales import SalesService
from app.services.media.storage import ensure_public_url
from asgiref.sync import async_to_sync

@celery_app.task(name="score_lead_task")
def score_lead_task(tenant_id: str, lead_id: str):
    db = SessionLocal()
    try:
        service = SalesService(db, tenant_id)
        async_to_sync(service.score_lead)(lead_id)
    finally:
        db.close()

@celery_app.task(name="enrich_lead_task")
def enrich_lead_task(tenant_id: str, lead_id: str):
    from app.models.verticals import Lead
    from app.models.base import APICredential
    from app.services.llm_gateway import LLMGateway
    from app.core.security import decrypt_api_key
    import httpx

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        if not lead:
            return

        enrichment = {}

        # Apollo enrichment when configured
        apollo_cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="apollo").first()
        if apollo_cred and apollo_cred.encrypted_key:
            api_key = decrypt_api_key(apollo_cred.encrypted_key)
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        "https://api.apollo.io/v1/people/match",
                        json={"api_key": api_key, "email": lead.email, "reveal_personal_emails": False},
                    )
                    if resp.status_code == 200:
                        person = resp.json().get("person") or {}
                        enrichment["apollo"] = {
                            "title": person.get("title"),
                            "linkedin_url": person.get("linkedin_url"),
                            "seniority": person.get("seniority"),
                            "department": person.get("departments"),
                        }
                        if person.get("organization", {}).get("name"):
                            lead.company = person["organization"]["name"]
                            
                    # Deep Context Enrichment (News & Jobs)
                    domain = ""
                    if lead.email and "@" in lead.email:
                        domain = lead.email.split("@")[-1]
                        
                    if domain:
                        from app.services.agents.sales import SalesAgent
                        agent = SalesAgent(db, tenant_id)
                        org_id = async_to_sync(agent._fetch_apollo_org_data)(api_key, domain)
                        if org_id:
                            news = async_to_sync(agent._fetch_apollo_news)(api_key, org_id)
                            jobs = async_to_sync(agent._fetch_apollo_jobs)(api_key, org_id)
                            if news:
                                enrichment["apollo"]["news"] = news
                            if jobs:
                                enrichment["apollo"]["jobs"] = jobs
            except Exception:
                pass

        # LLM enrichment fallback / supplement
        llm = LLMGateway(db, tenant_id)
        
        news_context = ""
        jobs_context = ""
        if enrichment.get("apollo", {}).get("news"):
            news_context = "Recent News: " + ", ".join([n["title"] for n in enrichment["apollo"]["news"]]) + "\n"
        if enrichment.get("apollo", {}).get("jobs"):
            jobs_context = "Recent Job Openings: " + ", ".join([j["title"] for j in enrichment["apollo"]["jobs"]]) + "\n"
            
        prompt = (
            f"Enrich this B2B lead with professional details as JSON only.\n"
            f"Name: {lead.name}\nEmail: {lead.email}\nCompany: {lead.company}\n"
            f"{news_context}{jobs_context}"
            f"Output keys: title, industry, company_size, pain_points (array), outreach_angle, "
            f"personal_email, company_email, mobile_no, company_contact_no, need_of_what, how_much, why, target_context, priority (one of: low, medium, high)."
        )
        response = async_to_sync(llm.complete)(prompt=prompt, provider="gemini")
        try:
            import json
            cleaned = response.strip().strip("```json").strip("```").strip()
            res_dict = json.loads(cleaned)
            enrichment["llm"] = res_dict
            
            # Directly update empty fields on lead
            if not lead.personal_email:
                lead.personal_email = res_dict.get("personal_email")
            if not lead.company_email:
                lead.company_email = res_dict.get("company_email") or lead.email
            if not lead.mobile_no:
                lead.mobile_no = res_dict.get("mobile_no") or lead.phone
            if not lead.company_contact_no:
                lead.company_contact_no = res_dict.get("company_contact_no")
            if not lead.need_of_what:
                lead.need_of_what = res_dict.get("need_of_what")
            if not lead.how_much:
                lead.how_much = res_dict.get("how_much")
            if not lead.why:
                lead.why = res_dict.get("why")
            if not lead.target_context:
                lead.target_context = res_dict.get("target_context")
            if not lead.priority or lead.priority == "medium":
                lead.priority = res_dict.get("priority", "medium")
        except Exception:
            enrichment["llm"] = {"raw": response[:500]}

        lead.data = {**(lead.data or {}), "enrichment": enrichment}
        if lead.status == "captured":
            lead.status = "enriched"
        db.commit()
    finally:
        db.close()


@celery_app.task(name="handle_lead_with_ai_task")
def handle_lead_with_ai_task(tenant_id: str, lead_id: str):
    from app.services.verticals.sales import SalesService
    from app.models.verticals import Lead
    from datetime import datetime

    # 1. Run enrichment
    enrich_lead_task(tenant_id, lead_id)

    # 2. Run scoring & outreach generation
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        if lead:
            service = SalesService(db, tenant_id)
            async_to_sync(service.score_lead)(lead_id)
            
            message = async_to_sync(service.generate_outreach)(lead_id)
            if message:
                from app.services.sales.outbox_service import SalesOutboxService
                recipient_email = lead.email or lead.company_email or lead.personal_email
                if recipient_email:
                    outbox = SalesOutboxService(db, tenant_id)
                    outbox.stage_touch(
                        lead_id=lead.id,
                        recipient_email=recipient_email,
                        subject=f"Partnership Opportunity - {lead.company}",
                        body=message,
                        step_number=1,
                        channel="email",
                        scheduled_for=datetime.utcnow(),
                        recipient_name=lead.name,
                    )
                    # Drain immediately with safety checks
                    outbox.drain_due_items(limit=1, max_jitter_sec=0)
    finally:
        db.close()


@celery_app.task(name="generate_campaign_task")
def generate_campaign_task(tenant_id: str, params: dict, job_id: str = None, *args, **kwargs):
    from app.services.llm_gateway import LLMGateway
    from app.models.verticals import ContentPost, GenerationJob
    from app.models.agents import ActivityLog
    from app.services.marketing.campaign_os.orchestrator import CampaignOSOrchestrator
    from asgiref.sync import async_to_sync
    from datetime import datetime, timezone
    import logging
    
    task_logger = logging.getLogger("generate_campaign_task")
    if not job_id and isinstance(params, dict):
        job_id = params.get("job_id") or kwargs.get("job_id")
    elif not job_id and kwargs.get("job_id"):
        job_id = kwargs.get("job_id")

    db = SessionLocal()
    try:
        topic = params.get("topic", "our company")
        days = int(params.get("days", 30))
        platforms = params.get("platforms", ["linkedin", "instagram", "facebook"])
        img_sel = params.get("image", {}) if isinstance(params.get("image"), dict) else {}
        vid_sel = params.get("video", {}) if isinstance(params.get("video"), dict) else {}
        import os
        image_provider = img_sel.get("provider") or params.get("image_provider") or os.getenv("DEFAULT_IMAGE_PROVIDER") or os.getenv("IMAGE_PROVIDER") or "together"
        image_model = img_sel.get("model") or params.get("image_model") or os.getenv("DEFAULT_IMAGE_MODEL") or os.getenv("IMAGE_MODEL") or "black-forest-labs/FLUX.1-schnell"
        video_provider = vid_sel.get("provider") or params.get("video_provider") or os.getenv("DEFAULT_VIDEO_PROVIDER") or os.getenv("VIDEO_PROVIDER") or "together"
        video_model = vid_sel.get("model") or params.get("video_model") or os.getenv("DEFAULT_VIDEO_MODEL") or os.getenv("VIDEO_MODEL") or "minimax/video-01"
        reference_image_url = params.get("reference_image_url")
        generate_images = bool(params.get("generate_images", True))
        generate_videos = bool(params.get("generate_videos", False))

        # Log start activity
        log = ActivityLog(
            tenant_id=tenant_id,
            agent_name="Campaign OS",
            action="Campaign DAG Started",
            description=f"Initiating 3-stage Campaign OS DAG for a {days}-day multi-platform campaign on: {topic}.",
            status="pending"
        )
        db.add(log)
        db.commit()

        # Execute the 3-stage Campaign OS Orchestrator
        orchestrator = CampaignOSOrchestrator(db, tenant_id, job_id=job_id)
        result = async_to_sync(orchestrator.execute_campaign_dag)(params)

        if result.get("status") == "failed":
            task_logger.error(f"[generate_campaign_task] DAG failed: {result.get('error')}")
            if job_id:
                try:
                    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                    if job:
                        job.status = "failed"
                        job.error = result.get("error")
                        db.commit()
                except Exception:
                    pass
            return result

        # Dispatch Media Rendering with Circuit Breakers (if requested and prompt exists)
        llm = LLMGateway(db, tenant_id)
        target_post_ids = [
            p.get("post_id")
            for p in result.get("posts", [])
            if p.get("post_id") and not p.get("failed")
        ]
        created_posts = (
            db.query(ContentPost)
            .filter(
                ContentPost.tenant_id == tenant_id,
                ContentPost.id.in_(target_post_ids),
                ContentPost.status != "failed",
                ContentPost.approval_status != "failed",
                ContentPost.image_url == None,  # noqa: E711
            )
            .all()
            if target_post_ids
            else []
        )

        from app.services.marketing.visual_creative.critic import VisualCritic
        from app.services.marketing.visual_creative.analyzer import VisualIntentAnalyzer
        from app.services.marketing.visual_creative.creative_director import DynamicCreativeDirector
        critic = VisualCritic(db, tenant_id)

        for post in created_posts:
            # Image Rendering Dispatch
            if generate_images and post.image_prompt and not post.image_url:
                try:
                    raw = async_to_sync(llm.generate_image)(
                        post.image_prompt,
                        provider=image_provider,
                        model=image_model,
                        reference_image_url=reference_image_url,
                    )
                    if raw and not raw.startswith("error:"):
                        post.image_url = async_to_sync(ensure_public_url)(raw, prefix="img")
                        post.used_model = f"{image_provider}/{image_model or 'default'}"
                        # Visual Quality Gate Inspection
                        try:
                            intent = VisualIntentAnalyzer.analyze(post.content or post.image_prompt, deliverable="image", platform=post.platform)
                            brief = DynamicCreativeDirector.create_brief(intent)
                            scorecard = async_to_sync(critic.inspect)(post.image_url, intent, brief)
                            insights = dict(post.insights_raw or {})
                            insights["quality_scorecard"] = scorecard.model_dump()
                            post.insights_raw = insights
                        except Exception as q_err:
                            task_logger.debug(f"Critic check bypassed for post {post.id}: {q_err}")
                    elif raw and raw.startswith("error:"):
                        post.image_url = raw  # Keep error sentinel for UI warning
                except Exception as img_err:
                    task_logger.warning(f"Image generation failed gracefully for post {post.id}: {img_err}")
                    # Circuit breaker: graceful degradation to text-only

            # Video Rendering Dispatch (supports image-to-video if post has image_url)
            if generate_videos and post.video_prompt and not post.video_url:
                try:
                    v_ref = post.image_url if (post.image_url and not post.image_url.startswith("error:")) else reference_image_url
                    v_raw = async_to_sync(llm.generate_video)(
                        post.video_prompt,
                        provider=video_provider,
                        model=video_model,
                        reference_image_url=v_ref,
                    )
                    if v_raw and not str(v_raw).startswith("error:"):
                        post.video_url = async_to_sync(ensure_public_url)(v_raw, prefix="vid", default_mime="video/mp4")
                        post.used_model = f"{video_provider}/{video_model or 'default'}"
                        # Visual Quality Gate Inspection
                        try:
                            intent = VisualIntentAnalyzer.analyze(post.content or post.video_prompt, deliverable="video", platform=post.platform)
                            brief = DynamicCreativeDirector.create_brief(intent)
                            scorecard = async_to_sync(critic.inspect)(post.video_url, intent, brief)
                            insights = dict(post.insights_raw or {})
                            insights["quality_scorecard"] = scorecard.model_dump()
                            post.insights_raw = insights
                        except Exception as q_err:
                            task_logger.debug(f"Critic check bypassed for video post {post.id}: {q_err}")
                except Exception as vid_err:
                    task_logger.warning(f"Video generation failed gracefully for post {post.id}: {vid_err}")

        db.commit()

        if job_id:
            try:
                job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                if job:
                    payload = dict(job.request_payload or {})
                    payload["current_stage"] = "dispatch"
                    payload["current_stage_label"] = "Campaign Generation Ready"
                    payload["progress_pct"] = 100.0
                    for s in payload.get("stages", []):
                        s["status"] = "completed"
                    logs = list(payload.get("logs", []))
                    logs.append({
                        "stage": "Complete",
                        "message": f"Campaign generated successfully! {result.get('total_posts_generated', 0)} posts ready ({result.get('approved_count', 0)} approved).",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    payload["logs"] = logs
                    job.request_payload = payload
                    job.status = "completed"
                    db.commit()
            except Exception as j_err:
                task_logger.debug(f"Failed to finalize job: {j_err}")

        final_log = ActivityLog(
            tenant_id=tenant_id,
            agent_name="Campaign OS",
            action="Campaign DAG Completed",
            description=f"Generated {result.get('total_posts_generated', 0)} posts. Auto-approved: {result.get('approved_count', 0)}, Review needed: {result.get('needs_review_count', 0)}.",
            status="success"
        )
        db.add(final_log)
        db.commit()

        return result

    except Exception as e:
        task_logger.error(f"Error in Campaign OS DAG task: {e}", exc_info=True)
        if job_id:
            try:
                job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                if job:
                    payload = dict(job.request_payload or {})
                    payload["progress_pct"] = 0.0
                    logs = list(payload.get("logs", []))
                    logs.append({
                        "stage": "Error",
                        "message": f"Campaign generation halted: {str(e)[:150]}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    payload["logs"] = logs
                    job.request_payload = payload
                    job.status = "failed"
                    job.error = str(e)
                    db.commit()
            except Exception:
                pass
        error_log = ActivityLog(
            tenant_id=tenant_id,
            agent_name="Campaign OS",
            action="Campaign DAG Failed",
            description=f"Error in Campaign OS DAG: {str(e)[:300]}",
            status="failed"
        )
        db.add(error_log)
        db.commit()
        raise e
    finally:
        db.close()


@celery_app.task(name="publish_post_by_id")
def publish_post_by_id(post_id: str):
    from app.models.verticals import ContentPost
    from app.services.social.publish_helpers import publish_post_sync

    db = SessionLocal()
    try:
        post = db.query(ContentPost).filter(ContentPost.id == post_id).first()
        if post:
            publish_post_sync(db, post)
    finally:
        db.close()


@celery_app.task(name="publish_scheduled_posts")
def publish_scheduled_posts():
    from app.models.verticals import ContentPost
    from datetime import datetime, timezone
    from app.services.social.publish_helpers import publish_post_sync

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        posts = (
            db.query(ContentPost)
            .filter(
                ContentPost.approval_status == "approved",
                ContentPost.scheduled_at <= now,
                ContentPost.status.notin_(["published", "needs_configuration", "publish_uncertain", "buffer_scheduling"]),
                ContentPost.external_post_id.is_(None),
            )
            .with_for_update(skip_locked=True)
            .all()
        )

        for post in posts:
            publish_post_sync(db, post)
    finally:
        db.close()

@celery_app.task(name="run_daily_operations")
def run_daily_operations():
    from app.models.base import Tenant
    from app.services.agents.orchestrator import OrchestratorAgent
    db = SessionLocal()
    try:
        # First, run daily ops routines
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        for t in tenants:
            agent = OrchestratorAgent(db, t.id)
            async_to_sync(agent.run_daily_ops)()
            
        # Also run scheduled post publishing
        publish_scheduled_posts()
    finally:
        db.close()

@celery_app.task(name="autonomous_marketing_pulse_task")
def autonomous_marketing_pulse_task(tenant_id: str, params: Optional[dict] = None):
    from app.services.agents.marketing import MarketingAgent
    from asgiref.sync import async_to_sync
    import logging
    task_logger = logging.getLogger("autonomous_marketing_pulse_task")
    db = SessionLocal()
    try:
        agent = MarketingAgent(db, tenant_id)
        result = async_to_sync(agent.autonomous_marketing_pulse)(params or {})
        task_logger.info(f"Autonomous pulse completed for tenant {tenant_id}: {result.get('message')}")
        return result
    except Exception as e:
        task_logger.error(f"Error in autonomous_marketing_pulse_task for tenant {tenant_id}: {e}", exc_info=True)
        raise e
    finally:
        db.close()

@celery_app.task(name="auto_reply_task")
def auto_reply_task(tenant_id: str, ticket_id: str, trigger_msg_id: str, channel: str):
    from app.services.agents.support import SupportAgent
    db = SessionLocal()
    try:
        agent = SupportAgent(db, tenant_id)
        async_to_sync(agent.process_auto_reply)(ticket_id, trigger_msg_id, channel)
    except Exception as e:
        print(f"Error in auto_reply_task: {e}")
        raise e
    finally:
        db.close()

@celery_app.task(name="check_human_handoff_timeout_task")
def check_human_handoff_timeout_task(tenant_id: str, ticket_id: str, expected_generation: int = 0):
    from app.services.agents.support import SupportAgent
    db = SessionLocal()
    try:
        agent = SupportAgent(db, tenant_id)
        async_to_sync(agent.process_handoff_timeout)(ticket_id, expected_generation)
    except Exception as e:
        print(f"Error in check_human_handoff_timeout_task: {e}")
        raise e
    finally:
        db.close()

@celery_app.task(name="run_boardroom_meeting_task")
def run_boardroom_meeting_task(
    tenant_id: str,
    meeting_id: str,
    provider: Optional[str] = None,
    model: Optional[str] = None
):
    from app.services.agents.boardroom import BoardroomService
    db = SessionLocal()
    try:
        service = BoardroomService(db, tenant_id, provider=provider, model=model)
        async_to_sync(service.run_meeting)(meeting_id)
    except Exception as e:
        print(f"Error in run_boardroom_meeting_task: {e}")
        raise e
    finally:
        db.close()

@celery_app.task(name="check_ticket_coordination_task")
def check_ticket_coordination_task(tenant_id: str, ticket_id: str):
    from app.services.agents.boardroom import BoardroomService
    db = SessionLocal()
    try:
        service = BoardroomService(db, tenant_id)
        classification = async_to_sync(service.classify_ticket_inquiry)(ticket_id)
        if classification.get("needs_meeting"):
            async_to_sync(service.create_meeting_from_ticket)(ticket_id, classification)
    except Exception as e:
        print(f"Error in check_ticket_coordination_task: {e}")
        raise e
    finally:
        db.close()

@celery_app.task(name="execute_local_batch_task")
def execute_local_batch_task(batch_id: str):
    from app.models.base import AIBatchJob
    from app.services.ai_gateway import ai_gateway
    from datetime import datetime, timezone
    
    db = SessionLocal()
    try:
        job = db.query(AIBatchJob).filter(AIBatchJob.id == batch_id).first()
        if not job:
            print(f"Batch job {batch_id} not found.")
            return

        tasks = job.results.get("tasks", [])
        completed_results = []
        completed_count = 0
        failed_count = 0
        
        for index, t in enumerate(tasks):
            custom_id = f"task-{index}"
            try:
                content = async_to_sync(ai_gateway.executeRequest)(
                    db=db,
                    tenant_id=job.tenant_id,
                    prompt=t.get("prompt"),
                    model=job.model,
                    provider=job.provider,
                    system_prompt=t.get("system_prompt"),
                    task_type="bulk_batch",
                    bulk=True,
                    **(t.get("kwargs") or {})
                )
                completed_results.append({
                    "custom_id": custom_id,
                    "content": content,
                    "status": "success",
                    "input_tokens": len(t.get("prompt", "").split()) + len(t.get("system_prompt", "").split() if t.get("system_prompt") else []),
                    "output_tokens": len(content.split())
                })
                completed_count += 1
            except Exception as e:
                print(f"Error executing batch task {custom_id}: {e}")
                completed_results.append({
                    "custom_id": custom_id,
                    "content": "",
                    "status": "failed",
                    "error": str(e),
                    "input_tokens": 0,
                    "output_tokens": 0
                })
                failed_count += 1
            
            # Save progress incrementally
            job.completed_tasks = completed_count
            job.failed_tasks = failed_count
            job.results = {"completed": completed_results, "tasks": tasks}
            db.commit()

        job.status = "completed" if completed_count > 0 else "failed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as ex:
        print(f"Failed executing batch {batch_id}: {ex}")
        job = db.query(AIBatchJob).filter(AIBatchJob.id == batch_id).first()
        if job:
            job.status = "failed"
            db.commit()
    finally:
        db.close()

@celery_app.task(name="poll_native_batches_task")
def poll_native_batches_task():
    from app.models.base import AIBatchJob
    from app.services.ai_gateway import ai_gateway
    from app.services.ai_gateway.batching import BatchExecutionEngine
    
    db = SessionLocal()
    try:
        active_native_jobs = db.query(AIBatchJob).filter(
            AIBatchJob.status == "processing",
            AIBatchJob.provider_batch_id != None
        ).all()
        
        for job in active_native_jobs:
            api_key = ai_gateway._get_api_key(db, job.tenant_id, job.provider)
            adapter = ai_gateway._get_adapter(job.provider, api_key)
            async_to_sync(BatchExecutionEngine.monitorBatch)(db, job.id, adapter)
    except Exception as e:
        print(f"Error polling native batches: {e}")
    finally:
        db.close()

@celery_app.task(name="process_sales_inbound_task")
def process_sales_inbound_task(
    tenant_id: str,
    lead_id: str,
    channel: str,
    content: str,
    subject: str = None,
    external_id: str = None,
):
    from app.services.sales.reply_handler import SalesReplyHandler

    db = SessionLocal()
    try:
        handler = SalesReplyHandler(db, tenant_id)
        async_to_sync(handler.process_inbound)(
            lead_id, channel, content, subject=subject, external_id=external_id
        )
    except Exception as e:
        print(f"process_sales_inbound_task error: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="sales_auto_reply_task")
def sales_auto_reply_task(
    tenant_id: str,
    lead_id: str,
    channel: str,
    reply_content: str,
    trigger_external_id: str,
):
    from app.models.verticals import Lead
    from app.services.sales.reply_handler import SalesReplyHandler

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        if not lead:
            return
        data = lead.data or {}
        if trigger_external_id and data.get("pending_auto_reply_for") != trigger_external_id:
            return

        handler = SalesReplyHandler(db, tenant_id)
        async_to_sync(handler.send_sales_reply)(lead, channel, reply_content)
    except Exception as e:
        print(f"sales_auto_reply_task error: {e}")
    finally:
        db.close()


@celery_app.task(name="poll_gmail_sales_inbox")
def poll_gmail_sales_inbox():
    from app.models.base import Tenant
    from app.services.sales.gmail_poll import poll_gmail_inbox_for_sales

    db = SessionLocal()
    try:
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
        for tenant in tenants:
            try:
                poll_gmail_inbox_for_sales(db, tenant.id)
            except Exception as e:
                print(f"Gmail poll error for {tenant.id}: {e}")
    finally:
        db.close()


@celery_app.task(name="send_sales_meeting_reminders")
def send_sales_meeting_reminders():
    """Telegram: 24h-before meeting, 1h-before call, 24h follow-up on contacted leads."""
    from datetime import datetime, timedelta, timezone
    from app.models.base import Tenant
    from app.models.verticals import Lead
    from app.services.notifications.sales_alerts import (
        format_followup_reminder,
        format_meeting_reminder_1h,
        format_meeting_reminder_tomorrow,
        meeting_start_from_lead,
        send_sales_telegram,
    )

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        tenants = db.query(Tenant).filter(Tenant.is_active == True).all()

        for tenant in tenants:
            # Meeting reminders
            scheduled = (
                db.query(Lead)
                .filter(
                    Lead.tenant_id == tenant.id,
                    Lead.status == "meeting_scheduled",
                )
                .all()
            )
            for lead in scheduled:
                data = dict(lead.data or {})
                starts_at = meeting_start_from_lead(lead)
                if not starts_at:
                    continue

                delta = starts_at - now
                meeting_time = data.get("meeting_time", starts_at.isoformat())
                meet_url = data.get("meeting_link", "")

                # ~24 hours before
                if (
                    timedelta(hours=23, minutes=30) <= delta <= timedelta(hours=24, minutes=30)
                    and not data.get("reminder_24h_sent")
                ):
                    msg = format_meeting_reminder_tomorrow(lead, meeting_time, meet_url)
                    if send_sales_telegram(db, tenant.id, msg):
                        data["reminder_24h_sent"] = True
                        lead.data = data
                        db.commit()

                # ~1 hour before
                if (
                    timedelta(minutes=50) <= delta <= timedelta(hours=1, minutes=10)
                    and not data.get("reminder_1h_sent")
                ):
                    msg = format_meeting_reminder_1h(lead, meeting_time, meet_url)
                    if send_sales_telegram(db, tenant.id, msg):
                        data["reminder_1h_sent"] = True
                        lead.data = data
                        db.commit()

            # Follow-up: contacted 24h+ ago, no meeting
            contacted = (
                db.query(Lead)
                .filter(
                    Lead.tenant_id == tenant.id,
                    Lead.status == "contacted",
                )
                .all()
            )
            for lead in contacted:
                data = dict(lead.data or {})
                if data.get("followup_reminder_sent"):
                    continue
                raw_sent = data.get("outreach_sent_at")
                if not raw_sent:
                    continue
                try:
                    sent_at = datetime.fromisoformat(str(raw_sent).replace("Z", "+00:00"))
                    if sent_at.tzinfo is None:
                        sent_at = sent_at.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue

                if now - sent_at >= timedelta(hours=24):
                    msg = format_followup_reminder(lead)
                    if send_sales_telegram(db, tenant.id, msg):
                        data["followup_reminder_sent"] = True
                        lead.data = data
                        db.commit()
    except Exception as e:
        print(f"Error in send_sales_meeting_reminders: {e}")
    finally:
        db.close()


@celery_app.task(name="poll_and_execute_workflows")
def poll_and_execute_workflows():
    from app.models.workflows import WorkflowTask
    from app.services.agents.workflow_engine import WorkflowEngine
    from datetime import datetime, timezone
    
    db = SessionLocal()
    try:
        from sqlalchemy import or_
        from app.models.workflows import Workflow
        now = datetime.now(timezone.utc)
        tasks_to_run = db.query(WorkflowTask).join(Workflow, Workflow.id == WorkflowTask.workflow_id).filter(
            WorkflowTask.status == "pending",
            WorkflowTask.scheduled_at <= now,
            or_(Workflow.vertical.is_(None), Workflow.vertical != "hr"),
            or_(WorkflowTask.task_type.is_(None), ~WorkflowTask.task_type.like("hr.%")),
        ).all()
        
        if tasks_to_run:
            engine = WorkflowEngine(db)
            for task in tasks_to_run:
                async_to_sync(engine.execute_task)(task)
                
    except Exception as e:
        print(f"Error polling workflows: {e}")
    finally:
        db.close()


@celery_app.task(name="drain_hr_outbox")
def drain_hr_outbox():
    import asyncio
    import app.services.hr.capabilities  # noqa: F401 — registers hr.* capabilities
    from app.workers.outbox_worker import OutboxWorker

    db = SessionLocal()
    try:
        worker = OutboxWorker(db, "hr-drain")
        asyncio.run(worker.process_batch(capability_prefix="hr."))
    except Exception as e:
        print(f"Error draining HR outbox: {e}")
    finally:
        db.close()


@celery_app.task(name="expire_hr_approvals")
def expire_hr_approvals():
    from datetime import datetime, timezone
    from app.models.executive import ExecutiveApprovalRequest
    from app.core.governance import DeterministicGovernanceKernel

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        rows = db.query(ExecutiveApprovalRequest).filter(
            ExecutiveApprovalRequest.status == "PENDING",
            ExecutiveApprovalRequest.capability_id.like("hr.%"),
            ExecutiveApprovalRequest.expires_at < now,
        ).all()
        for row in rows:
            row.status = "EXPIRED"
            if row.idempotency_key:
                DeterministicGovernanceKernel(db, row.tenant_id).release_hr_hold(row.idempotency_key)
        db.commit()
    except Exception as e:
        print(f"Error expiring HR approvals: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="poll_scheduled_triggers")
def poll_scheduled_triggers():
    from app.models.schedules import ScheduledTrigger
    from app.models.verticals import BusinessProfile
    from app.models.agents import ActivityLog
    from datetime import datetime, timezone
    import logging
    from app.services.runtime_governance.triggers import lease_scheduled_trigger, complete_scheduled_trigger

    task_logger = logging.getLogger("poll_scheduled_triggers")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_triggers = (
            db.query(ScheduledTrigger)
            .filter(
                ScheduledTrigger.is_active == True,
                ScheduledTrigger.next_run_at <= now,
            )
            .with_for_update(skip_locked=True)
            .all()
        )

        for trigger in due_triggers:
            task_logger.info(f"Executing scheduled trigger {trigger.id} for {trigger.target_type} (tenant: {trigger.tenant_id})")
            # Lease the trigger while dispatch is in flight so another beat worker
            # does not pick up the same occurrence concurrently.
            lease_scheduled_trigger(trigger, now=now, lease_seconds=300)
            db.commit()

            try:
                if trigger.target_type in ("lead_generation", "prompt_sales_agent"):
                    config = trigger.config or {}
                    provider = config.get("provider", "auto")
                    model = config.get("model")
                    count = int(config.get("count") or config.get("lead_count") or 50)
                    freshness = config.get("freshness") or "30_days"
                    prompt_text = trigger.instructions or "Find high-intent B2B target accounts fitting current market opportunities."

                    run_sales_v3_task.delay(
                        trigger.tenant_id,
                        provider=provider,
                        model=model,
                        count=count,
                        freshness=freshness,
                        mode="prompt_agent",
                        prompt_instructions=prompt_text
                    )
                    
                    log = ActivityLog(
                        tenant_id=trigger.tenant_id,
                        agent_name="Prompt Sales Agent",
                        action="Scheduled Prompt Agent Triggered",
                        description=f"Autonomous prompt lead discovery triggered on schedule ({trigger.frequency} at {trigger.time_of_day}).",
                        status="success"
                    )
                    db.add(log)
                    db.commit()

                elif trigger.target_type == "configured_sales_engine":
                    config = trigger.config or {}
                    provider = config.get("provider", "auto")
                    model = config.get("model")
                    count = int(config.get("count") or config.get("lead_count") or 50)
                    freshness = config.get("freshness") or "30_days"

                    run_sales_v3_task.delay(
                        trigger.tenant_id,
                        provider=provider,
                        model=model,
                        count=count,
                        freshness=freshness,
                        mode="configured_engine"
                    )

                    log = ActivityLog(
                        tenant_id=trigger.tenant_id,
                        agent_name="Configured Sales Engine",
                        action="Scheduled Configured Engine Triggered",
                        description=f"Autonomous configured sales engine triggered on schedule ({trigger.frequency} at {trigger.time_of_day}).",
                        status="success"
                    )
                    db.add(log)
                    db.commit()

                elif trigger.target_type == "campaign_planner":
                    config = trigger.config or {}
                    topic = config.get("topic") or (trigger.instructions[:80] if trigger.instructions else "Scheduled Campaign")
                    days = int(config.get("days", 30))
                    platforms = config.get("platforms", ["linkedin", "instagram", "facebook"])
                    
                    params = {
                        "topic": topic,
                        "days": days,
                        "platforms": platforms,
                        "generate_images": config.get("generate_images", True),
                        "instructions": trigger.instructions
                    }
                    generate_campaign_task.delay(trigger.tenant_id, params)

                    log = ActivityLog(
                        tenant_id=trigger.tenant_id,
                        agent_name="Campaign OS",
                        action="Scheduled Campaign Triggered",
                        description=f"Autonomous {days}-day campaign generation triggered on schedule ({trigger.frequency} at {trigger.time_of_day}).",
                        status="success"
                    )
                    db.add(log)
                    db.commit()

                complete_scheduled_trigger(
                    trigger, now=datetime.now(timezone.utc), succeeded=True
                )
                db.commit()
            except Exception as trig_err:
                task_logger.error(f"Error executing trigger {trigger.id}: {trig_err}")
                # Retry quickly rather than silently losing a missed run.
                complete_scheduled_trigger(
                    trigger, now=datetime.now(timezone.utc), succeeded=False, error=str(trig_err)
                )
                db.commit()

    except Exception as e:
        task_logger.error(f"Error in poll_scheduled_triggers: {e}")
    finally:
        db.close()


@celery_app.task(name="run_ceo_workflow_task")
def run_ceo_workflow_task(tenant_id: str, workflow_id: str):
    from app.services.agents.ceo import CEOService
    db = SessionLocal()
    try:
        service = CEOService(db, tenant_id)
        async_to_sync(service.execute_workflow)(workflow_id)
    except Exception as e:
        print(f"Error in run_ceo_workflow_task: {e}")
        raise e
    finally:
        db.close()

@celery_app.task(name="run_sales_v3_task")
def run_sales_v3_task(
    tenant_id: str,
    provider: str = None,
    model: str = None,
    count: int = 50,
    freshness: str = None,
    mode: str = "configured_engine",
    prompt_instructions: str = None,
    *args,
    **kwargs
):
    from app.services.agents.sales import SalesAgent
    from app.models.verticals import BusinessProfile
    from datetime import datetime
    db = SessionLocal()
    try:
        agent = SalesAgent(db, tenant_id)
        async_to_sync(agent.run_sales_ai_v3_workflow)(
            provider=provider,
            model=model,
            count=count,
            freshness=freshness,
            mode=mode,
            prompt_instructions=prompt_instructions
        )
    except Exception as e:
        print(f"Error in run_sales_v3_task: {e}")
        try:
            p = db.query(BusinessProfile).filter_by(tenant_id=tenant_id).first()
            if p and p.v3_workflow_status:
                st = dict(p.v3_workflow_status)
                st["status"] = "failed"
                logs_list = list(st.get("logs", []))
                logs_list.append(f"[{datetime.now().strftime('%H:%M:%S')}] Workflow execution error: {str(e)}")
                st["logs"] = logs_list
                p.v3_workflow_status = st
                db.commit()
        except Exception:
            pass
        raise e
    finally:
        db.close()


@celery_app.task(name="sync_marketing_insights_task")
def sync_marketing_insights_task(tenant_id: str = None, limit: int = 50):
    """Pull FB/IG/LinkedIn insights and rebuild learning patterns."""
    from app.models.base import Tenant
    from app.services.marketing.analytics import MarketingAnalyticsService

    db = SessionLocal()
    try:
        if tenant_id:
            tenant_ids = [tenant_id]
        else:
            tenant_ids = [t.id for t in db.query(Tenant).filter(Tenant.is_active == True).all()]  # noqa: E712

        summary = []
        for tid in tenant_ids:
            try:
                result = async_to_sync(MarketingAnalyticsService(db, tid).sync_all)(limit=limit)
                summary.append({"tenant_id": tid, **{k: result.get(k) for k in ("synced", "errors", "patterns_updated")}})
            except Exception as e:
                summary.append({"tenant_id": tid, "error": str(e)[:200]})
        return {"status": "ok", "tenants": summary}
    finally:
        db.close()


@celery_app.task(name="rebuild_marketing_learning_task")
def rebuild_marketing_learning_task(tenant_id: str):
    from app.services.marketing.analytics import MarketingAnalyticsService
    db = SessionLocal()
    try:
        n = MarketingAnalyticsService(db, tenant_id).rebuild_learning_patterns()
        return {"status": "ok", "patterns_updated": n}
    finally:
        db.close()


@celery_app.task(name="scan_regional_context_radar_task")
def scan_regional_context_radar_task(tenant_id: str = None, days_ahead: int = 30):
    """Monthly background scanner for cultural, seasonal, and commercial moments in target regions."""
    from app.models.base import Tenant
    from app.services.marketing.context_radar.calendar_engine import CalendarEngine
    from app.services.knowledge_os.brand_synthesizer import BrandKnowledgeService
    import logging

    task_logger = logging.getLogger("scan_regional_context_radar_task")
    db = SessionLocal()
    try:
        if tenant_id:
            tenant_ids = [tenant_id]
        else:
            tenant_ids = [t.id for t in db.query(Tenant).filter(Tenant.is_active == True).all()]  # noqa: E712

        summary = []
        for tid in tenant_ids:
            try:
                brand_knowledge = BrandKnowledgeService(db, tid).synthesize()
                cal_engine = CalendarEngine(db, tid)
                events = async_to_sync(cal_engine.discover_agentic_regional_events)(
                    days_ahead=days_ahead,
                    force_refresh=True,
                    brand_context=brand_knowledge,
                )
                summary.append({"tenant_id": tid, "events_discovered": len(events)})
                task_logger.info(f"Discovered {len(events)} regional events for tenant {tid}")
            except Exception as e:
                task_logger.warning(f"Error scanning regional radar for tenant {tid}: {e}")
                summary.append({"tenant_id": tid, "error": str(e)[:200]})
        return {"status": "ok", "tenants": summary}
    finally:
        db.close()


@celery_app.task(name="dead_letter_handler")
def dead_letter_handler(task_name: str, task_id: str, exception: str, args: str, kwargs: str):
    import logging
    import ast
    from app.db.session import SessionLocal
    from app.services.durable_workflows import DeadLetterService

    logger = logging.getLogger(__name__)
    logger.error(
        f"[DLQ EVENT] Celery task '{task_name}' (ID: {task_id}) failed. "
        f"Exception: {exception}. Args: {args}, Kwargs: {kwargs}"
    )
    db = SessionLocal()
    try:
        parsed_args = []
        parsed_kwargs = {}
        try:
            parsed_args = list(ast.literal_eval(args)) if args else []
        except Exception:
            parsed_args = [args]
        try:
            parsed_kwargs = dict(ast.literal_eval(kwargs)) if kwargs else {}
        except Exception:
            parsed_kwargs = {"raw": kwargs}
        tenant_id = None
        if parsed_args and isinstance(parsed_args[0], str):
            tenant_id = parsed_args[0]
        elif isinstance(parsed_kwargs, dict):
            tenant_id = parsed_kwargs.get("tenant_id")
        DeadLetterService(db).record(
            task_name=task_name,
            task_id=task_id,
            args=parsed_args,
            kwargs=parsed_kwargs,
            error=exception,
            tenant_id=tenant_id,
        )

        # Mark associated GenerationJob as failed so it does not stay orphaned in 'queued'
        failed_job_id = None
        if isinstance(parsed_kwargs, dict) and parsed_kwargs.get("job_id"):
            failed_job_id = parsed_kwargs.get("job_id")
        elif len(parsed_args) > 1 and isinstance(parsed_args[1], dict) and parsed_args[1].get("job_id"):
            failed_job_id = parsed_args[1].get("job_id")

        if failed_job_id:
            try:
                from app.models.verticals import GenerationJob
                gen_job = db.query(GenerationJob).filter(GenerationJob.id == failed_job_id).first()
                if gen_job and gen_job.status in ("queued", "in_progress"):
                    gen_job.status = "failed"
                    gen_job.error = f"Celery task failure: {exception[:250]}"
                    payload = dict(gen_job.request_payload or {})
                    logs = list(payload.get("logs", []))
                    logs.append({
                        "stage": "Error",
                        "message": f"Worker task failed: {exception[:150]}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    payload["logs"] = logs
                    gen_job.request_payload = payload
                    db.commit()
            except Exception as j_err:
                logger.debug(f"Failed to update generation job from DLQ: {j_err}")

        return {"status": "DLQ_RECORDED", "task_id": task_id, "persisted": True}
    except Exception as e:
        logger.error(f"Failed to persist DLQ job: {e}")
        return {"status": "DLQ_RECORDED", "task_id": task_id, "persisted": False}
    finally:
        db.close()



@celery_app.task(name="plan_video_task")
def plan_video_task(tenant_id: str, project_id: str):
    from app.services.agents.video import VideoAgent
    from app.db.session import SessionLocal
    from asgiref.sync import async_to_sync
    
    db = SessionLocal()
    try:
        agent = VideoAgent(db, tenant_id)
        async_to_sync(agent.plan_video)(project_id)
    except Exception as e:
        import logging
        logging.error(f"Error in plan_video_task: {e}")
        raise e
    finally:
        db.close()

@celery_app.task(name="render_video_task")
def render_video_task(tenant_id: str, project_id: str):
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        import httpx
        import logging
        from app.models.video import VideoProject, VideoRender
        from app.services.media.storage import upload_file_to_storage
        import os
        from datetime import datetime, timezone
        from asgiref.sync import async_to_sync

        project = db.query(VideoProject).filter(
            VideoProject.id == project_id, 
            VideoProject.tenant_id == tenant_id
        ).first()

        if not project or not project.blueprint:
            logging.error(f"Cannot render video: Project {project_id} not found or has no blueprint.")
            return

        project.status = "rendering"
        render_job = VideoRender(project_id=project.id, status="processing")
        db.add(render_job)
        db.commit()

        # Call local Node.js renderer service
        with httpx.Client(timeout=1200.0) as client:
            resp = client.post(
                "http://localhost:8002/render",
                json=project.blueprint
            )
            
            if resp.status_code == 200:
                data = resp.json()
                local_file = data.get("file")
                
                if local_file and os.path.exists(local_file):
                    # Upload local mp4 file to public storage
                    with open(local_file, "rb") as f:
                        file_bytes = f.read()
                    
                    filename = f"render_{project_id}_{int(datetime.now(timezone.utc).timestamp())}.mp4"
                    public_url = async_to_sync(upload_file_to_storage)(file_bytes, filename, "video/mp4")
                    
                    project.final_video_url = public_url
                    project.status = "completed"
                    render_job.status = "success"
                    render_job.render_url = public_url
                    render_job.progress = 100.0
                    render_job.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    # Cleanup local file
                    try:
                        os.remove(local_file)
                    except:
                        pass
                else:
                    raise Exception("Renderer returned success but file not found on disk.")
            else:
                raise Exception(f"Renderer API failed with status {resp.status_code}: {resp.text}")

    except Exception as e:
        logging.error(f"Video rendering failed for project {project_id}: {e}")
        try:
            if 'render_job' in locals():
                render_job.status = "error"
                render_job.error_logs = str(e)
            if 'project' in locals():
                project.status = "failed"
            db.commit()
        except Exception as inner_e:
            logging.error(f"Failed to update error status in DB: {inner_e}")
            db.rollback()
    finally:
        db.close()


@celery_app.task(name="recrawl_due_knowledge_sources_task")
def recrawl_due_knowledge_sources_task():
    """Periodically check and re-crawl scheduled knowledge sources."""
    from datetime import datetime, timezone, timedelta
    from app.models.agents import KnowledgeSource
    from app.services.web_ingestion.website_sync import WebsiteSyncService

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        sources = db.query(KnowledgeSource).filter(
            KnowledgeSource.schedule.in_(["daily", "weekly"]),
            KnowledgeSource.last_status != "running",
        ).all()

        for s in sources:
            should_crawl = False
            if not s.last_crawled_at:
                should_crawl = True
            elif s.schedule == "daily" and (now - s.last_crawled_at) > timedelta(days=1):
                should_crawl = True
            elif s.schedule == "weekly" and (now - s.last_crawled_at) > timedelta(days=7):
                should_crawl = True

            if should_crawl:
                try:
                    sync_service = WebsiteSyncService(db, s.tenant_id)
                    async_to_sync(sync_service.sync_knowledge_source)(s.id)
                except Exception as e:
                    logging.error(f"Periodic crawl failed for source {s.id}: {e}")
    finally:
        db.close()


@celery_app.task(name="execute_media_generation_job_task")
def execute_media_generation_job_task(job_id: str):
    """Execute asynchronous image/video generation job and persist result to durable storage."""
    from app.db.session import SessionLocal
    from app.models.verticals import GenerationJob, ContentPost
    from app.services.ai_gateway.registry import ModelRegistry
    from app.services.ai_gateway.providers.base import VideoReq, ImageReq, JobHandle
    from app.services.media.storage import ensure_public_url
    from asgiref.sync import async_to_sync
    import asyncio
    import logging

    logger = logging.getLogger("execute_media_generation_job_task")
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            logger.error(f"GenerationJob {job_id} not found.")
            return

        job.status = "in_progress"
        job.attempts = (job.attempts or 0) + 1
        db.commit()

        registry = ModelRegistry.get_instance()
        provider_name = (job.provider or "together").lower()
        adapter = registry.get_adapter(provider_name)
        if not adapter:
            job.status = "failed"
            job.error = f"Unsupported provider '{job.provider}'"
            db.commit()
            return

        from app.services.ai_gateway import ai_gateway
        api_key = ai_gateway._get_api_key(db, job.tenant_id, provider_name)
        if not api_key:
            job.status = "failed"
            job.error = f"API key for {provider_name.title()} is missing."
            db.commit()
            return

        payload = job.request_payload or {}
        prompt = payload.get("prompt", "")
        ref_image = payload.get("reference_image_url")
        ar = payload.get("aspect_ratio", "16:9" if job.kind == "video" else "1:1")

        if job.kind == "video":
            req = VideoReq(
                model=job.model,
                prompt=prompt,
                reference_image_url=ref_image,
                aspect_ratio=ar,
                duration_seconds=int(payload.get("duration_seconds", 5)),
            )

            # Submit or use existing provider job ID
            if not job.provider_job_id:
                handle = async_to_sync(adapter.submit_video)(req, api_key=api_key)
                job.provider_job_id = handle.job_id
                db.commit()
            else:
                handle = JobHandle(job_id=job.provider_job_id, provider=provider_name, model=job.model)

            # Poll for completion (up to 60 iterations * 5s = 5 minutes)
            final_url = None
            for _ in range(60):
                status = async_to_sync(adapter.poll_video)(handle, api_key=api_key)
                if status.status == "completed" and status.result_url:
                    final_url = status.result_url
                    break
                elif status.status == "failed":
                    raise Exception(status.error or "Video generation provider reported failure.")
                async_to_sync(asyncio.sleep)(5)

            if not final_url:
                raise Exception("Video generation timed out after 5 minutes.")

            # Persist to permanent storage
            permanent_url = async_to_sync(ensure_public_url)(final_url, prefix="vid", default_mime="video/mp4") or final_url
            job.status = "completed"
            job.result_url = permanent_url
            db.commit()

            if job.post_id:
                post = db.query(ContentPost).filter(ContentPost.id == job.post_id).first()
                if post:
                    post.video_url = permanent_url
                    post.video_prompt = prompt
                    post.used_model = f"{provider_name}/{job.model}"
                    db.commit()

        elif job.kind == "image":
            img_req = ImageReq(
                model=job.model,
                prompt=prompt,
                reference_image_url=ref_image,
                aspect_ratio=ar,
            )
            res = async_to_sync(adapter.generate_image)(img_req, api_key=api_key)
            permanent_url = async_to_sync(ensure_public_url)(res.image_url, prefix="img") or res.image_url
            job.status = "completed"
            job.result_url = permanent_url
            db.commit()

            if job.post_id:
                post = db.query(ContentPost).filter(ContentPost.id == job.post_id).first()
                if post:
                    post.image_url = permanent_url
                    post.image_prompt = prompt
                    post.used_model = f"{provider_name}/{job.model}"
                    db.commit()

    except Exception as e:
        logger.error(f"Error in execute_media_generation_job_task for job {job_id}: {e}")
        db.rollback()
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@celery_app.task(name="execute_sales_cadence_touches")
def execute_sales_cadence_touches():
    """Processes pending multi-channel cadence touches (Email, LinkedIn, WhatsApp) via DurableCadenceRunner."""
    from app.services.sales.cadence_runner import DurableCadenceRunner

    db = SessionLocal()
    try:
        return DurableCadenceRunner.run_all_tenants_cadence(db, max_touches_per_tenant=50)
    except Exception as e:
        logger.error(f"Error in execute_sales_cadence_touches: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()



# Registers the sales-os discovery task. It is not on the beat schedule.
from app.workers.sales_os.discovery import run_sales_os_discovery_task  # noqa: E402, F401


# Register the durable autonomous-work Celery task.
from app.services.autonomous_runtime import worker as _autonomous_runtime_worker  # noqa: F401


@celery_app.task(name="sync_buffer_delivery_status_task")
def sync_buffer_delivery_status_task():
    """Reconcile Buffer queue receipts with actual sent/error status without blind writes."""
    from datetime import datetime, timezone
    from asgiref.sync import async_to_sync
    from app.models.base import APICredential
    from app.models.verticals import ContentPost
    from app.models.teams import AgentMetric
    from app.models.agents import ActivityLog
    from app.services.integrations.buffer_service import BufferService, BufferAPIError
    import logging

    task_logger = logging.getLogger("sync_buffer_delivery_status_task")
    db = SessionLocal()
    try:
        credentials = db.query(APICredential).filter(APICredential.provider == "buffer").all()
        now = datetime.now(timezone.utc)
        for credential in credentials:
            tenant_id = credential.tenant_id
            try:
                buffer = BufferService(db, tenant_id)
                account = async_to_sync(buffer.account_and_channels)()
                external_posts = {}
                for organization in account.get("organizations", []):
                    # Include all account channels so manually queued posts are also reconciled.
                    org_channels = [
                        channel.get("id")
                        for channel in organization.get("channels", [])
                        if channel.get("id")
                    ]
                    if not org_channels:
                        continue
                    for external_post in async_to_sync(buffer.list_posts)(
                        organization_id=organization["id"], channel_ids=org_channels
                    ):
                        if external_post.get("id"):
                            external_posts[external_post["id"]] = external_post
                if not external_posts:
                    continue

                local_posts = (
                    db.query(ContentPost)
                    .filter(
                        ContentPost.tenant_id == tenant_id,
                        ContentPost.external_post_id.in_(list(external_posts.keys())),
                    )
                    .with_for_update(skip_locked=True)
                    .all()
                )
                for post in local_posts:
                    external = external_posts.get(post.external_post_id) or {}
                    status = (external.get("status") or "").lower()
                    if status == "sent" and post.status != "published":
                        post.status = "published"
                        post.approval_status = "published"
                        sent_at = external.get("sentAt")
                        try:
                            post.published_at = datetime.fromisoformat(sent_at.replace("Z", "+00:00")) if sent_at else now
                        except (TypeError, ValueError):
                            post.published_at = now
                        post.fallback_reason = None
                        post.external_url = external.get("externalLink") or post.external_url
                        metric = (
                            db.query(AgentMetric)
                            .filter(
                                AgentMetric.tenant_id == tenant_id,
                                AgentMetric.metric_name == "posts_published",
                            )
                            .first()
                        )
                        if not metric:
                            metric = AgentMetric(tenant_id=tenant_id, metric_name="posts_published", value=0.0)
                            db.add(metric)
                        metric.value += 1.0
                        db.add(ActivityLog(
                            tenant_id=tenant_id,
                            agent_name="Marketing AI",
                            action="Buffer Delivery Confirmed",
                            description=f"Buffer confirmed post {post.id} was sent (Buffer post {post.external_post_id}).",
                            status="success",
                        ))
                    elif status == "error" and post.status != "failed":
                        post.status = "failed"
                        post.fallback_reason = "Buffer reports a delivery error. Inspect the Buffer post before retrying."
                        db.add(ActivityLog(
                            tenant_id=tenant_id,
                            agent_name="Marketing AI",
                            action="Buffer Delivery Failed",
                            description=f"Buffer reports a delivery error for post {post.id} (Buffer post {post.external_post_id}).",
                            status="failed",
                        ))
                    elif status == "sending":
                        post.status = "publishing"
                    elif status == "scheduled":
                        post.status = "scheduled"
                    db.add(post)
                db.commit()
            except BufferAPIError as exc:
                db.rollback()
                task_logger.warning("Buffer status sync unavailable for tenant %s: %s", tenant_id, exc)
            except Exception:
                db.rollback()
                task_logger.exception("Buffer status sync failed for tenant %s", tenant_id)
    finally:
        db.close()


@celery_app.task(name="schedule_future_buffer_posts_task")
def schedule_future_buffer_posts_task():
    """Send approved future posts to Buffer early so Buffer honors OctaOS's chosen time."""
    from datetime import datetime, timedelta, timezone
    from asgiref.sync import async_to_sync
    import logging
    from app.models.base import APICredential
    from app.models.verticals import ContentPost
    from app.models.agents import ActivityLog
    from app.services.integrations.buffer_service import BufferService

    task_logger = logging.getLogger("schedule_future_buffer_posts_task")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        credentials = db.query(APICredential).filter(APICredential.provider == "buffer").all()
        for credential in credentials:
            tenant_id = credential.tenant_id
            channel_map = dict((credential.settings or {}).get("channel_map", {}))
            if not channel_map:
                continue

            # Recover stale claims conservatively; ambiguous writes must not be retried blindly.
            stale_claims = (
                db.query(ContentPost)
                .filter(
                    ContentPost.tenant_id == tenant_id,
                    ContentPost.status == "buffer_scheduling",
                    ContentPost.external_post_id.is_(None),
                )
                .with_for_update(skip_locked=True)
                .all()
            )
            for stuck in stale_claims:
                marker = "Buffer scheduling started at "
                try:
                    raw_timestamp = (stuck.fallback_reason or "").split(marker, 1)[1].rstrip(".")
                    started = datetime.fromisoformat(raw_timestamp)
                except (IndexError, ValueError):
                    started = now - timedelta(minutes=16)
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if now - started > timedelta(minutes=15):
                    stuck.status = "publish_uncertain"
                    stuck.fallback_reason = "A Buffer scheduling attempt was interrupted. Inspect the Buffer queue before retrying."
                    db.add(stuck)
            db.commit()

            candidates = (
                db.query(ContentPost)
                .filter(
                    ContentPost.tenant_id == tenant_id,
                    ContentPost.approval_status == "approved",
                    ContentPost.scheduled_at > now,
                    ContentPost.external_post_id.is_(None),
                    ContentPost.status.notin_(["published", "failed", "needs_configuration", "publish_uncertain", "buffer_scheduling"]),
                )
                .with_for_update(skip_locked=True)
                .limit(100)
                .all()
            )
            claimed_posts = []
            for post in candidates:
                platform = (post.platform or "").lower().replace("twitter", "x")
                channel_id = channel_map.get(platform)
                if not channel_id:
                    continue
                post.status = "buffer_scheduling"
                post.fallback_reason = "Buffer scheduling started at " + now.isoformat() + "."
                db.add(post)
                claimed_posts.append((post, channel_id))
            # Commit every claim before any network write so concurrent workers cannot select it.
            db.commit()

            for post, channel_id in claimed_posts:
                try:
                    scheduled_at = post.scheduled_at
                    if scheduled_at and scheduled_at.tzinfo is None:
                        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
                    created = async_to_sync(BufferService(db, tenant_id).create_post)(
                        channel_id=channel_id,
                        text=post.content or "",
                        scheduled_at=scheduled_at,
                        image_url=post.image_url,
                        video_url=post.video_url,
                    )
                    post.external_post_id = created["id"]
                    post.status = "scheduled"
                    post.fallback_reason = "Accepted by Buffer for the OctaOS scheduled time; awaiting delivery reconciliation."
                    db.add(ActivityLog(
                        tenant_id=tenant_id,
                        agent_name="Marketing AI",
                        action="Schedule Future Post in Buffer",
                        description=f"Buffer accepted post {post.id} for {scheduled_at} (external id={created['id']}).",
                        status="success",
                    ))
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    uncertain = db.query(ContentPost).filter(
                        ContentPost.id == post.id, ContentPost.tenant_id == tenant_id
                    ).first()
                    if uncertain and not uncertain.external_post_id:
                        uncertain.status = "publish_uncertain"
                        uncertain.fallback_reason = "Buffer scheduling result is uncertain. Inspect Buffer before retrying. " + str(exc)[:160]
                        db.add(uncertain)
                        db.commit()
                    task_logger.warning("Buffer scheduling needs reconciliation for post %s: %s", post.id, exc)
    finally:
        db.close()


@celery_app.task(name="execute_approved_tool", bind=True, max_retries=0)
def execute_approved_tool(self, approval_id: str, tenant_id: str):
    """Execute one approved high-risk tool action using its persisted exact binding."""
    from app.models.enterprise import ApprovalRequest
    from app.models.flow_engine import AgentVersion
    from app.services.agents.tools import tool_registry

    db = SessionLocal()
    try:
        approval = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.tenant_id == tenant_id,
        ).with_for_update().first()
        if not approval:
            return {"status": "not_found"}
        if approval.status != "approved" or not approval.action_binding:
            approval.execution_status = "failed"
            approval.execution_error = "APPROVAL_NOT_APPROVED_OR_BINDING_MISSING"
            db.commit()
            return {"status": "failed", "reason": approval.execution_error}
        if approval.execution_status in {"running", "completed"}:
            return {"status": approval.execution_status, "deduplicated": True}
        payload_record = approval.payload or {}
        version_id = payload_record.get("agent_version_id")
        version = db.query(AgentVersion).filter(AgentVersion.id == version_id).first() if version_id else None
        if not version:
            approval.execution_status = "failed"
            approval.execution_error = "AGENT_VERSION_NOT_FOUND"
            db.commit()
            return {"status": "failed", "reason": approval.execution_error}
        binding = approval.action_binding
        if str(version.agent_id) != str(binding.get("bot_id") or ""):
            approval.execution_status = "failed"
            approval.execution_error = "APPROVED_BOT_DOES_NOT_MATCH_AGENT_VERSION"
            db.commit()
            return {"status": "failed", "reason": approval.execution_error}
        tool_name = str(binding.get("tool_name") or "")
        tool_payload = binding.get("payload")
        if not tool_name or not isinstance(tool_payload, dict):
            approval.execution_status = "failed"
            approval.execution_error = "INVALID_PERSISTED_ACTION_BINDING"
            db.commit()
            return {"status": "failed", "reason": approval.execution_error}
        approval.execution_status = "running"
        approval.execution_error = None
        db.commit()
        try:
            result = async_to_sync(tool_registry.execute_tool)(
                name=tool_name,
                payload=tool_payload,
                db=db,
                tenant_id=tenant_id,
                context={
                    "approval_id": approval.id,
                    "run_id": str(binding.get("run_id") or ""),
                    "bot_id": str(binding.get("bot_id") or ""),
                    "agent_id": str(binding.get("bot_id") or ""),
                    "policy_version": str(binding.get("policy_version") or "1"),
                    "granted_tools": version.tool_grants or [],
                    "request_tenant_id": tenant_id,
                    "connection_active": True,
                },
            )
            normalized_result = result if isinstance(result, dict) else {"result": str(result)}
            side_effect_failed = (
                normalized_result.get("sent") is False
                or normalized_result.get("success") is False
                or (
                    isinstance(normalized_result.get("status_code"), int)
                    and normalized_result["status_code"] >= 400
                )
            )
            approval.execution_result = normalized_result
            if side_effect_failed:
                approval.execution_status = "failed"
                approval.execution_error = "SIDE_EFFECT_NOT_CONFIRMED"
                db.commit()
                return {"status": "failed", "reason": approval.execution_error, "approval_id": approval.id}
            approval.execution_status = "completed"
            approval.execution_error = None
            db.commit()
            return {"status": "completed", "approval_id": approval.id}
        except Exception as exc:
            db.rollback()
            failed = db.query(ApprovalRequest).filter(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.tenant_id == tenant_id,
            ).with_for_update().first()
            if failed:
                failed.execution_status = "failed"
                failed.execution_error = str(exc)[:2000]
                db.commit()
            raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.worker.tasks.run_research_search_task",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_research_search_task(
    self,
    tenant_id: str,
    job_id: str,
    query: str,
    options: Optional[Dict[str, Any]] = None,
    resume_job: bool = False,
):
    """Execute or resume a tenant-scoped Search V4 job in the existing worker queue."""
    del self
    from app.models.search_v4 import SearchV4Job
    from app.services.research import EnterpriseWebResearchService

    db = SessionLocal()
    try:
        row = (
            db.query(SearchV4Job)
            .filter(SearchV4Job.id == job_id, SearchV4Job.tenant_id == tenant_id)
            .first()
        )
        if row is None:
            return {"job_id": job_id, "status": "not_found"}
        if row.status in {"succeeded", "cancelled"}:
            return {"job_id": job_id, "status": row.status}

        payload = dict(row.payload or {})
        should_resume = bool(payload.get("tasks")) and (resume_job or row.status == "running")
        payload["status"] = "running"
        payload.pop("error_code", None)
        row.payload = payload
        row.status = "running"
        db.commit()

        service = EnterpriseWebResearchService(db=db, tenant_id=tenant_id)
        if should_resume:
            batch = async_to_sync(service.resume)(job_id)
        else:
            saved_spec = payload.get("spec") or {}
            run_options = dict(options or {})
            if resume_job:
                run_options = {
                    "freshness": saved_spec.get("freshness") or "14_days",
                    "geography": saved_spec.get("geography") or None,
                    "industries": saved_spec.get("industries") or None,
                    "buyer_roles": saved_spec.get("buyer_roles") or None,
                    "exclusions": saved_spec.get("exclusions") or None,
                    "budget_inr": float(saved_spec.get("budget_inr") or 0),
                }
            batch = async_to_sync(service.run)(
                query or saved_spec.get("query") or "",
                job_id=job_id,
                **run_options,
            )
        return {"job_id": batch.job_id, "status": batch.status}
    except Exception:
        db.rollback()
        try:
            row = (
                db.query(SearchV4Job)
                .filter(SearchV4Job.id == job_id, SearchV4Job.tenant_id == tenant_id)
                .first()
            )
            if row is not None:
                payload = dict(row.payload or {})
                payload["status"] = "failed"
                payload["error_code"] = "RESEARCH_EXECUTION_FAILED"
                row.payload = payload
                row.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="dispatch_webhook_delivery_task", bind=True, max_retries=4)
def dispatch_webhook_delivery_task(self, delivery_id: str):
    """Dispatches an outbound webhook event with exponential retry backoff."""
    from app.models.external_agents import WebhookDelivery, ExternalAgentConnection
    from app.services.webhooks.dispatcher import deliver_webhook
    from datetime import datetime, timezone, timedelta

    db = SessionLocal()
    try:
        delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
        if not delivery or delivery.status == "delivered":
            return {"status": "skipped", "delivery_id": delivery_id}

        connection = db.query(ExternalAgentConnection).filter(ExternalAgentConnection.id == delivery.connection_id).first()
        if not connection or not connection.enabled:
            delivery.status = "dead"
            delivery.last_error = "Connection missing or disabled"
            db.commit()
            return {"status": "cancelled", "delivery_id": delivery_id}

        res = async_to_sync(deliver_webhook)(connection, delivery.payload_json, db, delivery_record=delivery)
        if res.status != "delivered" and self.request.retries < self.max_retries:
            backoff_delays = [30, 120, 600, 3600]
            countdown = backoff_delays[min(self.request.retries, len(backoff_delays) - 1)]
            delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=countdown)
            db.commit()
            raise self.retry(countdown=countdown)
        elif res.status != "delivered":
            delivery.status = "dead"
            db.commit()
        return {"status": res.status, "delivery_id": delivery_id, "http_status": res.last_http_status}
    finally:
        db.close()

