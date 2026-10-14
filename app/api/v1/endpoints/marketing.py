from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from asgiref.sync import async_to_sync

from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User
from app.schemas import verticals as schemas
from app.models import verticals as models

router = APIRouter()


class GenerateMediaRequest(BaseModel):
    media_type: str  # "image" or "video" or "remotion"
    prompt: str
    provider: Optional[str] = "together"
    sub_model: Optional[str] = None
    reference_image_url: Optional[str] = None
    aspect_ratio: Optional[str] = None


class AnimateVideoRequest(BaseModel):
    prompt: Optional[str] = None
    provider: Optional[str] = "together"
    model: Optional[str] = None
    aspect_ratio: Optional[str] = "16:9"


class ApproveOptions(BaseModel):
    publish_now: bool = False


@router.post("/generate", response_model=schemas.ContentPost)
async def generate_content(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    topic: str,
    platform: str = "linkedin",
) -> Any:
    from app.services.verticals.marketing import MarketingService

    service = MarketingService(db, tenant_id)
    post = await service.generate_post(topic, platform)
    return post


class GenerateTextRequest(BaseModel):
    topic: str
    platform: Optional[str] = "linkedin"


@router.post("/generate-text")
async def generate_text(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    req: GenerateTextRequest,
) -> Any:
    from app.services.verticals.marketing import MarketingService

    service = MarketingService(db, tenant_id)
    text = await service.write_post_text(req.topic, req.platform or "linkedin")
    return {"content": text}


@router.get("/", response_model=List[schemas.ContentPost])
def read_posts(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    posts = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.tenant_id == tenant_id)
        .order_by(models.ContentPost.day.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return posts


@router.post("/campaign")
def trigger_campaign(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    campaign_in: schemas.CampaignCreate,
) -> Any:
    from app.models.verticals import GenerationJob
    from app.worker.tasks import generate_campaign_task

    job = GenerationJob(
        tenant_id=tenant_id,
        kind="campaign",
        provider="system",
        model=campaign_in.text_model or "auto",
        request_payload={
            "topic": campaign_in.topic,
            "days": campaign_in.days,
            "platforms": campaign_in.platforms,
            "current_stage": "context",
            "current_stage_label": "Queued in Pipeline",
            "progress_pct": 5.0,
            "stages": [
                {"id": "context", "name": "Brand Context Anchor (Agents 1-5)", "status": "pending", "desc": "Ingesting Brand DNA, Product Catalog, Audience ICP, and Proof Points"},
                {"id": "strategy", "name": "Campaign Strategy & Brief (Agent 6)", "status": "pending", "desc": "Synthesizing core positioning and hook strategy"},
                {"id": "narrative", "name": "Multi-Slot Cadence Scheduling (Agent 7)", "status": "pending", "desc": "Structuring chronological daily time slots across networks"},
                {"id": "drafting", "name": "Platform Copywriting & Hooks (Agents 8-10)", "status": "pending", "desc": "Crafting native copy, viral opening hooks, and CTAs"},
                {"id": "creative", "name": "Visual Art & Video Scene Direction (Agents 11 & 12)", "status": "pending", "desc": "Compiling photographic image prompts and video shot kinetics"},
                {"id": "compliance", "name": "Dual Fact-Checking & Compliance (Agents 13 & 14)", "status": "pending", "desc": "Verifying grounded claims, brand voice, and safety rules"},
                {"id": "dispatch", "name": "Executive CMO Dispatch & Scheduling (Agent 15)", "status": "pending", "desc": "CMO final authorization and calendar publication dispatch"},
            ],
            "logs": [
                {
                    "stage": "Queue",
                    "message": f"Campaign generation requested for '{campaign_in.topic}' ({campaign_in.days} days).",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    params = campaign_in.dict()
    params["job_id"] = str(job.id)

    try:
        generate_campaign_task.delay(tenant_id, params, job_id=str(job.id))
    except Exception as exc:
        import threading
        def run_fallback():
            try:
                generate_campaign_task(tenant_id, params, job_id=str(job.id))
            except Exception:
                pass
        t = threading.Thread(target=run_fallback, daemon=True)
        t.start()

    return {
        "status": "queued",
        "job_id": job.id,
        "message": "Campaign generation has been queued in the background.",
    }


@router.get("/campaign/active-job")
def get_active_campaign_job(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Check if there is an active (queued or in_progress) or recent campaign generation job."""
    from app.models.verticals import GenerationJob
    job = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.tenant_id == tenant_id,
            GenerationJob.kind == "campaign",
        )
        .order_by(GenerationJob.created_at.desc())
        .first()
    )
    if not job:
        return {"has_active": False, "job": None}

    payload = job.request_payload or {}
    is_active = job.status in ("queued", "in_progress")
    now = datetime.now(timezone.utc)

    # Check for stale orphaned jobs (e.g., worker killed or interrupted)
    # If a job is queued or in_progress with no updates for > 90 seconds, auto-fail it
    job_updated = job.updated_at or job.created_at
    if job_updated and is_active:
        if job_updated.tzinfo is None:
            job_updated = job_updated.replace(tzinfo=timezone.utc)
        elapsed = (now - job_updated).total_seconds()
        if elapsed > 90:
            job.status = "failed"
            job.error = "Generation job timed out (worker inactive or interrupted)."
            db.commit()
            is_active = False

    recently_finished = False
    if job.updated_at and not is_active:
        job_updated = job.updated_at if job.updated_at.tzinfo else job.updated_at.replace(tzinfo=timezone.utc)
        if (now - job_updated).total_seconds() < 45:
            recently_finished = True

    return {
        "has_active": is_active,
        "recently_finished": recently_finished,
        "job": {
            "job_id": job.id,
            "status": job.status,
            "error": job.error,
            "progress_pct": payload.get("progress_pct", 100.0 if job.status == "completed" else 0.0),
            "current_stage": payload.get("current_stage_label") or payload.get("current_stage"),
            "stages": payload.get("stages", []),
            "stage_logs": payload.get("logs", []),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "topic": payload.get("topic"),
            "days": payload.get("days"),
        },
    }


@router.post("/campaign/active-job/cancel")
def cancel_active_campaign_job(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
) -> Any:
    """Cancel or dismiss any stuck active campaign generation jobs."""
    from app.models.verticals import GenerationJob
    jobs = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.tenant_id == tenant_id,
            GenerationJob.kind == "campaign",
            GenerationJob.status.in_(["queued", "in_progress"]),
        )
        .all()
    )
    for j in jobs:
        j.status = "failed"
        j.error = "Cancelled by user"
    db.commit()
    return {"status": "cancelled", "cleared": len(jobs)}


@router.post("/campaign/preview-brief")
async def preview_campaign_brief(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    topic: str = "Enterprise Automation",
    days: int = 3,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Any:
    """Preview strategy brief and narrative arc before launching background campaign generation."""
    from app.services.knowledge_os.intent_projector import CompanyContextProjectionEngine, IntentType
    from app.services.marketing.campaign_os.roles import CampaignRolesEngine
    from app.services.ai_gateway.registry import ModelRegistry

    reg = ModelRegistry.get_instance()
    strat_p, strat_m, _ = await reg.resolve_model(db, tenant_id, "text", preferred_provider=provider, preferred_model=model)

    projector = CompanyContextProjectionEngine(db, tenant_id)
    roles = CampaignRolesEngine(db, tenant_id)

    try:
        projection = await projector.get_projection(intent=IntentType.CAMPAIGN_MARKETING)
        brand_brief = await roles.execute_brand_strategist(topic=topic, campaign_projection=projection, provider=strat_p, model=strat_m)
        visual_tokens = await roles.execute_visual_director(brand_brief=brand_brief, campaign_projection=projection, provider=strat_p, model=strat_m)
        narrative_arc = await roles.execute_narrative_architect(days=days, brand_brief=brand_brief, provider=strat_p, model=strat_m)

        anchor_data = None
        try:
            brand_anchor = await roles.synthesize_brand_context_anchor(company_context=projection, topic=topic, days=days, provider=strat_p, model=strat_m)
            anchor_data = brand_anchor.model_dump()
        except Exception:
            pass

        return {
            "status": "success",
            "brand_brief": brand_brief.model_dump(),
            "visual_tokens": visual_tokens.model_dump(),
            "narrative_arc": narrative_arc.model_dump(),
            "brand_anchor": anchor_data,
            "used_model": f"{strat_p}/{strat_m}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate campaign brief: {e}")


@router.put("/posts/{post_id}", response_model=schemas.ContentPost)
def update_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.UPDATE)),
    post_id: str,
    post_in: schemas.ContentPostBase,
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.content = post_in.content
    post.platform = post_in.platform
    if post_in.image_url is not None:
        post.image_url = post_in.image_url
    if post_in.video_url is not None:
        post.video_url = post_in.video_url
    if post_in.scheduled_at is not None:
        post.scheduled_at = post_in.scheduled_at
    if post_in.media_prompt is not None:
        post.media_prompt = post_in.media_prompt
    if post_in.media_prompt_enabled is not None:
        post.media_prompt_enabled = post_in.media_prompt_enabled
    if post_in.image_prompt is not None:
        post.image_prompt = post_in.image_prompt
    if post_in.image_prompt_enabled is not None:
        post.image_prompt_enabled = post_in.image_prompt_enabled
    if post_in.video_prompt is not None:
        post.video_prompt = post_in.video_prompt
    if post_in.video_prompt_enabled is not None:
        post.video_prompt_enabled = post_in.video_prompt_enabled
    if post_in.remotion_prompt is not None:
        post.remotion_prompt = post_in.remotion_prompt
    if post_in.remotion_prompt_enabled is not None:
        post.remotion_prompt_enabled = post_in.remotion_prompt_enabled
    if hasattr(post_in, 'remotion_provider') and post_in.remotion_provider is not None:
        post.remotion_provider = post_in.remotion_provider
    if hasattr(post_in, 'remotion_model') and post_in.remotion_model is not None:
        post.remotion_model = post_in.remotion_model
    if post_in.is_manual_media is not None:
        post.is_manual_media = post_in.is_manual_media

    db.commit()
    db.refresh(post)
    return post


@router.post("/posts/create", response_model=schemas.ContentPost)
def create_manual_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    post_in: schemas.ContentPostCreate,
) -> Any:
    post = models.ContentPost(
        tenant_id=tenant_id,
        platform=post_in.platform,
        content=post_in.content,
        image_url=post_in.image_url,
        video_url=post_in.video_url,
        media_prompt=post_in.media_prompt,
        media_prompt_enabled=post_in.media_prompt_enabled,
        image_prompt=post_in.image_prompt,
        image_prompt_enabled=post_in.image_prompt_enabled,
        video_prompt=post_in.video_prompt,
        video_prompt_enabled=post_in.video_prompt_enabled,
        remotion_prompt=post_in.remotion_prompt,
        remotion_prompt_enabled=post_in.remotion_prompt_enabled,
        remotion_provider=getattr(post_in, 'remotion_provider', 'gemini'),
        remotion_model=getattr(post_in, 'remotion_model', 'gemini-2.5-flash'),
        is_manual_media=post_in.is_manual_media,
        day=post_in.day or 1,
        status="draft",
        approval_status="pending",
        scheduled_at=post_in.scheduled_at,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/posts/manual-multi", response_model=List[schemas.ContentPost])
def create_manual_multi_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    post_in: schemas.ContentPostManualMultiCreate,
) -> Any:
    platforms = post_in.platforms or ["linkedin"]
    now = datetime.now(timezone.utc)

    # Process content and tags
    content = post_in.content or ""
    tags = [t.strip().lstrip("#") for t in (post_in.tags or []) if t.strip()]

    # If tags provided and not already present in content, append formatted hashtags
    if tags:
        hashtag_tokens = [f"#{t}" for t in tags]
        missing_tokens = [tok for tok in hashtag_tokens if tok.lower() not in content.lower()]
        if missing_tokens:
            content = f"{content.rstrip()}\n\n{' '.join(missing_tokens)}"

    # Determine approval_status, status, and scheduled_at based on publish_mode
    if post_in.publish_mode == "now":
        approval_status = "approved"
        status = "scheduled"
        scheduled_at = now
    elif post_in.publish_mode == "schedule":
        approval_status = "approved"
        status = "scheduled"
        if post_in.scheduled_at:
            scheduled_at = post_in.scheduled_at
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        else:
            day = post_in.day or 1
            scheduled = (now + timedelta(days=day)).replace(hour=9, minute=0, second=0, microsecond=0)
            scheduled_at = scheduled.replace(tzinfo=timezone.utc) if scheduled.tzinfo is None else scheduled
    else:  # draft
        approval_status = "pending"
        status = "draft"
        scheduled_at = post_in.scheduled_at
        if scheduled_at and scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

    created_posts = []
    for platform in platforms:
        post = models.ContentPost(
            tenant_id=tenant_id,
            platform=platform.lower(),
            content=content,
            image_url=post_in.image_url,
            video_url=post_in.video_url,
            image_prompt=post_in.image_prompt,
            image_prompt_enabled=post_in.image_prompt_enabled,
            video_prompt=post_in.video_prompt,
            video_prompt_enabled=post_in.video_prompt_enabled,
            remotion_prompt=post_in.remotion_prompt,
            remotion_prompt_enabled=post_in.remotion_prompt_enabled,
            is_manual_media=post_in.is_manual_media,
            day=post_in.day or 1,
            status=status,
            approval_status=approval_status,
            scheduled_at=scheduled_at,
            learning_tags=tags,
        )
        db.add(post)
        created_posts.append(post)

    db.commit()
    for post in created_posts:
        db.refresh(post)

    # If publish_mode == "now", attempt direct synchronous publishing for supported platforms
    if post_in.publish_mode == "now":
        from app.services.social.publish_helpers import publish_post_sync
        for post in created_posts:
            if post.platform in ("facebook", "instagram", "linkedin"):
                try:
                    publish_post_sync(db, post)
                    db.refresh(post)
                except Exception:
                    pass

    return created_posts


@router.post("/upload-media")
async def upload_media(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    file: UploadFile = File(...),
) -> Any:
    from app.services.media.storage import _write_bytes
    content = await file.read()
    url = _write_bytes(content, file.content_type, prefix="upload")
    return {"url": url}


@router.post("/posts/{post_id}/generate-media", response_model=schemas.ContentPost)
async def generate_media_for_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    post_id: str,
    req: GenerateMediaRequest,
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    from app.services.llm_gateway import LLMGateway
    gateway = LLMGateway(db, tenant_id)

    if req.media_type == "video":
        provider = req.provider or "together"
        video_url = await gateway.generate_video(
            req.prompt,
            provider=provider,
            model=req.sub_model,
            reference_image_url=req.reference_image_url,
            aspect_ratio=req.aspect_ratio or "16:9",
        )
        if video_url.startswith("error:"):
            raise HTTPException(status_code=400, detail=video_url.replace("error:", ""))
        post.video_url = video_url
        post.image_url = None
        post.is_manual_media = False
        post.video_prompt = req.prompt
        post.video_prompt_enabled = True
        post.used_model = f"{provider}/{req.sub_model or 'default'}"
    elif req.media_type == "remotion":
        from app.services.agents.video import VideoAgent
        import httpx
        from app.services.media.storage import ensure_public_url
        import os
        from app.models.video import VideoProject
        
        agent = VideoAgent(db, tenant_id)
        project = VideoProject(
            tenant_id=tenant_id,
            title=f"Post Video {post.id}",
            prompt=req.prompt,
            duration_seconds=15,
            llm_provider=req.provider or post.remotion_provider or "gemini",
            llm_model=req.sub_model or post.remotion_model or "gemini-2.5-flash"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        res = await agent.plan_video(project.id)
        if res.get("status") == "success":
            blueprint = res.get("blueprint")
            with httpx.Client(timeout=300.0) as client:
                try:
                    resp = client.post("http://localhost:8002/render", json=blueprint)
                    if resp.status_code == 200:
                        data = resp.json()
                        local_file = data.get("file")
                        if local_file and os.path.exists(local_file):
                            with open(local_file, "rb") as f:
                                content = f.read()
                            from app.services.media.storage import _write_bytes
                            public_url = _write_bytes(content, "video/mp4", prefix="remotion")
                            post.video_url = public_url
                            post.image_url = None
                            post.is_manual_media = False
                            post.video_prompt = req.prompt
                            post.video_prompt_enabled = True
                        else:
                            raise HTTPException(status_code=500, detail="Failed to render remotion video")
                    else:
                        raise HTTPException(status_code=500, detail="Failed to communicate with renderer")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Renderer error: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail="Failed to plan video blueprint")
    else:
        provider = req.provider or "together"
        image_url = await gateway.generate_image(
            req.prompt,
            provider=provider,
            model=req.sub_model,
            reference_image_url=req.reference_image_url,
            aspect_ratio=req.aspect_ratio or "1:1",
        )
        if image_url.startswith("error:"):
            raise HTTPException(status_code=400, detail=image_url.replace("error:", ""))
        post.image_url = image_url
        post.video_url = None
        post.is_manual_media = False
        post.image_prompt = req.prompt
        post.image_prompt_enabled = True
        post.used_model = f"{provider}/{req.sub_model or 'default'}"
    db.commit()
    db.refresh(post)
    return post


@router.get("/models")
async def get_marketing_models(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
    provider: Optional[str] = None,
    modality: Optional[str] = None,
) -> Any:
    """Return curated frontier models filtered by provider/modality, plus tenant custom models."""
    from app.services.ai_gateway.registry import ModelRegistry
    from app.models.verticals import TenantModelRegistry
    reg = ModelRegistry.get_instance()
    curated = await reg.get_curated_models_with_availability(db, tenant_id, provider=provider, modality=modality)

    custom_q = db.query(TenantModelRegistry).filter(TenantModelRegistry.tenant_id == tenant_id)
    if provider and provider != "auto":
        custom_q = custom_q.filter(TenantModelRegistry.provider == provider.lower())
    if modality:
        custom_q = custom_q.filter(TenantModelRegistry.modality == modality.lower())
    custom_models = custom_q.all()
    custom_list = [
        {
            "provider": c.provider,
            "slug": c.slug,
            "display_name": f"{c.slug} (Custom)",
            "specialty": "Custom BYOM",
            "badge": "Custom",
            "modality": c.modality,
            "source": "custom",
            "id": c.id,
            "status": c.status,
            "has_api_key": True,
        }
        for c in custom_models
    ]
    return {"curated": curated, "custom": custom_list}


@router.post("/models/validate", response_model=schemas.ModelValidateResponse)
async def validate_marketing_model(
    req: schemas.ModelValidateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Live validation probe for vendor model slugs (returns available, incompatible, not_found, no_key)."""
    from app.services.ai_gateway.registry import ModelRegistry
    reg = ModelRegistry.get_instance()
    return await reg.validate_model(
        db=db,
        tenant_id=tenant_id,
        provider=req.provider,
        modality=req.modality,
        model_slug=req.model,
        mode=req.mode,
    )


@router.post("/models/custom")
async def add_custom_model(
    req: schemas.CustomModelCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
) -> Any:
    """Save a validated Bring-Your-Own-Model for this tenant."""
    from app.models.verticals import TenantModelRegistry
    from app.services.ai_gateway.registry import ModelRegistry
    reg = ModelRegistry.get_instance()
    val = await reg.validate_model(db, tenant_id, req.provider, req.modality, req.slug, mode=req.mode)
    if val.get("status") not in ("available", "unverified"):
        raise HTTPException(status_code=400, detail=val.get("message"))

    rec = db.query(TenantModelRegistry).filter(
        TenantModelRegistry.tenant_id == tenant_id,
        TenantModelRegistry.provider == req.provider.lower(),
        TenantModelRegistry.slug == req.slug,
    ).first()
    if not rec:
        rec = TenantModelRegistry(
            tenant_id=tenant_id,
            provider=req.provider.lower(),
            slug=req.slug,
            modality=req.modality.lower(),
            mode=req.mode or "text_to_text",
            status=val.get("status"),
            capabilities=val.get("capabilities", {}),
            pricing=val.get("pricing", {}),
            source="custom",
        )
        db.add(rec)
    else:
        rec.status = val.get("status")
        rec.capabilities = val.get("capabilities", {})
        rec.pricing = val.get("pricing", {})
    db.commit()
    db.refresh(rec)
    return {"message": "Custom model saved successfully", "id": rec.id, "slug": rec.slug}


@router.delete("/models/custom/{model_id}")
def delete_custom_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.DELETE)),
) -> Any:
    """Delete a custom Bring-Your-Own-Model from this tenant."""
    from app.models.verticals import TenantModelRegistry
    rec = db.query(TenantModelRegistry).filter(
        TenantModelRegistry.id == model_id,
        TenantModelRegistry.tenant_id == tenant_id,
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Custom model not found")
    db.delete(rec)
    db.commit()
    return {"status": "success", "message": "Custom model deleted"}


@router.post("/posts/{post_id}/animate-video", status_code=202)
def animate_post_to_video(
    post_id: str,
    req: AnimateVideoRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
) -> Any:
    """Animate a post's still image into a dynamic video loop (asynchronous job)."""
    post = db.query(models.ContentPost).filter(
        models.ContentPost.id == post_id,
        models.ContentPost.tenant_id == tenant_id,
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.image_url:
        raise HTTPException(status_code=400, detail="Post does not have an image to animate.")

    prompt_text = req.prompt or post.video_prompt or f"Cinematic slow camera push-in on scene illustrating {post.content[:80]}"
    from app.models.verticals import GenerationJob
    from app.worker.tasks import execute_media_generation_job_task

    job = GenerationJob(
        tenant_id=tenant_id,
        post_id=post.id,
        kind="video",
        provider=(req.provider or "together").lower(),
        model=req.model or "Wan-AI/Wan2.1-I2V-14B",
        request_payload={
            "prompt": prompt_text,
            "reference_image_url": post.image_url,
            "aspect_ratio": req.aspect_ratio or "16:9",
            "duration_seconds": 5,
        },
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    execute_media_generation_job_task.delay(job.id)
    return {
        "status": "queued",
        "job_id": job.id,
        "message": "Image-to-video animation job has been scheduled in the background.",
    }


@router.get("/jobs/{job_id}", response_model=schemas.JobStatusResponse)
def get_generation_job_status(
    job_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Get the current progress status and result of an async generation job."""
    from app.models.verticals import GenerationJob
    job = db.query(GenerationJob).filter(
        GenerationJob.id == job_id,
        GenerationJob.tenant_id == tenant_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    payload = job.request_payload or {}
    progress = payload.get("progress_pct")
    if progress is None:
        progress = 100.0 if job.status == "completed" else (10.0 if job.status == "in_progress" else 0.0)

    return schemas.JobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.result_url,
        error=job.error,
        progress_pct=float(progress),
        cost_usd=job.cost_actual or 0.0,
        current_stage=payload.get("current_stage_label") or payload.get("current_stage"),
        stages=payload.get("stages"),
        stage_logs=payload.get("logs"),
        kind=job.kind,
        topic=payload.get("topic"),
        days=payload.get("days"),
    )


class SuggestPromptRequest(BaseModel):
    content: str
    media_type: str  # "image" or "video"


@router.post("/suggest-prompt")
async def suggest_prompt(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    req: SuggestPromptRequest,
) -> Any:
    from app.services.llm_gateway import LLMGateway
    gateway = LLMGateway(db, tenant_id)

    if req.media_type == "video":
        prompt = (
            f"Based on the following social media post text, write a detailed, highly descriptive prompt to generate a 5-second video loop/cinemagraph (e.g. for Pika, Runway, or Sora). "
            f"The video should match the tone and subject of the post. Keep the prompt descriptive, focused on visual actions, movement, lighting, and style. Do not write any introduction or explanation, only output the final prompt text itself.\n\n"
            f"Post Text:\n{req.content}"
        )
    else:
        prompt = (
            f"Based on the following social media post text, write a detailed, highly descriptive prompt to generate a high-quality illustration/photo/graphic (e.g. for Midjourney or DALL-E). "
            f"The image should visually represent the theme of the post. Describe the subject, composition, background, color palette, lighting, and style (e.g., modern photography, warm corporate style, minimalist illustration). Do not write any introduction or explanation, only output the final prompt text itself.\n\n"
            f"Post Text:\n{req.content}"
        )

    suggestion = await gateway.complete(
        prompt=prompt,
        provider="gemini",
        system_prompt="You are an expert AI prompt engineer specializing in generating highly effective prompts for Text-to-Image (DALL-E, Midjourney) and Text-to-Video (Pika, Runway, Sora) models based on social media content. Respond with only the prompt itself, clean of markdown formatting, quotes, intro, or wrap-up."
    )
    clean_suggestion = suggestion.strip().strip('"\'')
    return {"prompt": clean_suggestion}


def _schedule_post(post: models.ContentPost, publish_now: bool = False) -> None:
    now = datetime.now(timezone.utc)
    post.approval_status = "approved"
    if publish_now:
        post.scheduled_at = now
        post.status = "scheduled"
    else:
        if post.scheduled_at is None:
            day = post.day or 1
            scheduled = (now + timedelta(days=day)).replace(hour=9, minute=0, second=0, microsecond=0)
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=timezone.utc)
            post.scheduled_at = scheduled
        post.status = "approved"


@router.post("/posts/{post_id}/approve", response_model=schemas.ContentPost)
def approve_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    post_id: str,
    options: ApproveOptions = ApproveOptions(),
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    _schedule_post(post, publish_now=options.publish_now)
    db.commit()
    db.refresh(post)

    if options.publish_now:
        from app.worker.tasks import publish_post_by_id

        publish_post_by_id.delay(post.id)

    return post


@router.post("/posts/{post_id}/publish-now")
def publish_post_now(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    post_id: str,
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.approval_status = "approved"
    post.scheduled_at = datetime.now(timezone.utc)
    db.commit()

    from app.services.social.publish_helpers import publish_post_sync

    success = publish_post_sync(db, post)
    if not success:
        raise HTTPException(status_code=502, detail="Publishing failed. Check activity logs for details.")
    db.refresh(post)
    return {"status": "published", "post": schemas.ContentPost.model_validate(post)}


@router.post("/posts/{post_id}/reject", response_model=schemas.ContentPost)
def reject_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    post_id: str,
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post_data = schemas.ContentPost.model_validate(post)
    db.delete(post)
    db.commit()
    return post_data


@router.post("/posts/{post_id}/regenerate", response_model=schemas.ContentPost)
async def regenerate_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.UPDATE)),
    post_id: str,
) -> Any:
    """Regenerate a post using real AI models and update the database record in-place."""
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    from app.services.knowledge_os.intent_projector import CompanyContextProjectionEngine, IntentType
    from app.services.marketing.campaign_os.roles import CampaignRolesEngine
    from app.services.marketing.campaign_os.contracts import CampaignDayOutline, BrandStrategyBrief
    from app.services.marketing.compiler.prompt_compiler import MediaPromptCompiler
    from app.services.ai_gateway.registry import ModelRegistry

    reg = ModelRegistry.get_instance()
    strat_p, strat_m, _ = await reg.resolve_model(db, tenant_id, "text")
    img_p, img_m, _ = await reg.resolve_model(db, tenant_id, "image")

    projector = CompanyContextProjectionEngine(db, tenant_id)
    projection = await projector.get_projection(intent=IntentType.CAMPAIGN_MARKETING)
    roles = CampaignRolesEngine(db, tenant_id)

    day_num = post.day or 1
    outline = CampaignDayOutline(
        day=day_num,
        theme=f"Day {day_num} Narrative Focus",
        narrative_focus="Value Agitation & Solution",
        suggested_hook_angle=f"Addressing core operational challenges in {projection.get('industry', 'enterprise operations')}",
        target_cta_intent="engagement",
    )
    brief = BrandStrategyBrief(
        core_narrative=f"Empowering {projection.get('company_name', 'enterprises')} through verified innovation.",
        tone_keywords=["Authoritative", "Pragmatic", "Insightful"],
        target_persona="Executive Leadership & Practitioners",
        key_differentiators=[p.get("usp", "Enterprise Quality") for p in projection.get("product_highlights", [])] or ["Efficiency"],
        approved_evidence_ids=[c.get("evidence_id") for c in projection.get("approved_claims", []) if c.get("evidence_id")],
        prohibited_topics=[],
    )

    try:
        draft = await roles.execute_platform_adapter(
            day_outline=outline,
            brand_brief=brief,
            platform=post.platform,
            provider=strat_p,
            model=strat_m,
        )

        visual_tokens = await roles.execute_visual_director(
            brand_brief=brief,
            campaign_projection=projection,
            provider=strat_p,
            model=strat_m,
        )

        image_intent = await roles.execute_image_concept_director(
            draft=draft,
            visual_tokens=visual_tokens,
            provider=strat_p,
            model=strat_m,
        )

        idempotency_key = f"{tenant_id}:{post.id}:{day_num}:{post.platform}"
        image_res = MediaPromptCompiler.compile_for_target(
            target_provider=img_p,
            intent=image_intent,
            visual_style=visual_tokens.model_dump(),
            seed_key=idempotency_key,
            platform=post.platform,
            model_slug=img_m,
            headline_text=draft.hook,
        )

        post.content = draft.formatted_full_post
        post.image_prompt = image_res.get("prompt")
        post.media_prompt = image_res.get("prompt")
        post.status = "draft"
        post.approval_status = "pending"
        post.fallback_reason = None
        post.used_model = f"{strat_p}/{strat_m}"
        db.commit()
        db.refresh(post)
        return post

    except Exception as e:
        post.status = "failed"
        post.approval_status = "failed"
        post.fallback_reason = f"AI generation failed: {e}"
        db.commit()
        db.refresh(post)
        raise HTTPException(status_code=500, detail=f"Post regeneration failed: {e}")


@router.post("/posts/approve-all")
def approve_all_posts(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    options: ApproveOptions = ApproveOptions(),
) -> Any:
    posts = (
        db.query(models.ContentPost)
        .filter(
            models.ContentPost.tenant_id == tenant_id,
            models.ContentPost.approval_status == "pending",
        )
        .all()
    )

    for post in posts:
        _schedule_post(post, publish_now=options.publish_now)

    db.commit()

    if options.publish_now:
        from app.worker.tasks import publish_scheduled_posts

        publish_scheduled_posts.delay()

    return {"message": f"Successfully approved and scheduled {len(posts)} posts."}


class BulkScheduleRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    posting_time: str


@router.post("/posts/bulk-schedule")
def bulk_schedule_posts(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    req: BulkScheduleRequest,
) -> Any:
    if req.end_date < req.start_date:
        raise HTTPException(status_code=400, detail="End date must be on or after start date")

    # Get all posts that are not published
    posts = (
        db.query(models.ContentPost)
        .filter(
            models.ContentPost.tenant_id == tenant_id,
            models.ContentPost.approval_status != "published",
            models.ContentPost.status != "published",
        )
        .order_by(models.ContentPost.day.asc(), models.ContentPost.created_at.asc())
        .all()
    )

    if not posts:
        return {"message": "No pending or draft posts found to schedule."}

    try:
        hour, minute = map(int, req.posting_time.split(":"))
    except Exception:
        hour, minute = 9, 0

    n = len(posts)
    if n == 1:
        scheduled_time = req.start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
        posts[0].scheduled_at = scheduled_time
        posts[0].approval_status = "approved"
        posts[0].status = "approved"
    else:
        duration = req.end_date - req.start_date
        total_seconds = duration.total_seconds()
        step_seconds = total_seconds / (n - 1)
        for i, post in enumerate(posts):
            current_dt = req.start_date + timedelta(seconds=i * step_seconds)
            scheduled_time = current_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled_time.tzinfo is None:
                scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
            post.scheduled_at = scheduled_time
            post.approval_status = "approved"
            post.status = "approved"

    db.commit()
    return {"message": f"Successfully bulk scheduled {n} posts."}


# ── Analytics + learning loop ────────────────────────────────────────────────

@router.get("/analytics/dashboard")
def marketing_analytics_dashboard(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    from app.services.marketing.analytics import MarketingAnalyticsService
    return MarketingAnalyticsService(db, tenant_id).analytics_dashboard()


@router.post("/analytics/sync")
async def sync_marketing_analytics(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
    limit: int = 50,
    background: bool = True,
) -> Any:
    """Pull impressions/engagement from Meta & LinkedIn and update learning patterns."""
    if background:
        from app.worker.tasks import sync_marketing_insights_task
        sync_marketing_insights_task.delay(tenant_id, limit)
        return {"status": "queued", "message": "Analytics sync started in background"}
    from app.services.marketing.analytics import MarketingAnalyticsService
    return await MarketingAnalyticsService(db, tenant_id).sync_all(limit=limit)


@router.post("/analytics/sync/{post_id}")
async def sync_single_post_analytics(
    post_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(404, "Post not found")
    from app.services.marketing.analytics import MarketingAnalyticsService
    return await MarketingAnalyticsService(db, tenant_id).sync_post(post)


@router.post("/analytics/rebuild-learning")
def rebuild_marketing_learning(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.EXECUTE)),
) -> Any:
    from app.services.marketing.analytics import MarketingAnalyticsService
    n = MarketingAnalyticsService(db, tenant_id).rebuild_learning_patterns()
    return {"status": "ok", "patterns_updated": n}


@router.get("/analytics/learning-prompt")
def get_learning_prompt(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
    platform: Optional[str] = None,
) -> Any:
    from app.services.marketing.analytics import MarketingAnalyticsService
    block = MarketingAnalyticsService(db, tenant_id).learning_prompt_block(platform)
    return {"platform": platform, "learning_prompt": block}


@router.get("/posts/{post_id}/insights")
def get_post_insights(
    post_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    post = (
        db.query(models.ContentPost)
        .filter(models.ContentPost.id == post_id, models.ContentPost.tenant_id == tenant_id)
        .first()
    )
    if not post:
        raise HTTPException(404, "Post not found")
    from app.models.verticals import MarketingInsightSnapshot
    snaps = (
        db.query(MarketingInsightSnapshot)
        .filter(
            MarketingInsightSnapshot.post_id == post_id,
            MarketingInsightSnapshot.tenant_id == tenant_id,
        )
        .order_by(MarketingInsightSnapshot.captured_at.desc())
        .limit(30)
        .all()
    )
    return {
        "post_id": post.id,
        "platform": post.platform,
        "external_post_id": post.external_post_id,
        "current": {
            "impressions": post.impressions,
            "reach": post.reach,
            "engagement": post.engagement,
            "likes": post.likes,
            "comments": post.comments,
            "shares": post.shares,
            "clicks": post.clicks,
            "ctr": post.ctr,
            "engagement_rate": post.engagement_rate,
            "performance_score": post.performance_score,
            "learning_tags": post.learning_tags,
            "synced_at": post.insights_synced_at,
        },
        "history": [
            {
                "impressions": s.impressions,
                "engagement": s.engagement,
                "ctr": s.ctr,
                "engagement_rate": s.engagement_rate,
                "captured_at": s.captured_at,
            }
            for s in snaps
        ],
    }


@router.get("/radar")
async def get_marketing_context_radar(
    days_ahead: int = 365,
    news_limit: int = 5,
    refresh_regional: bool = False,
    country: Optional[str] = None,
    state: Optional[str] = None,
    scope: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Returns real-world marketing context: upcoming calendar events, industry news, brand snapshot."""
    from app.services.agents.marketing import MarketingAgent
    agent = MarketingAgent(db, tenant_id)
    return await agent.scan_context_radar({
        "days_ahead": days_ahead,
        "news_limit": news_limit,
        "refresh_regional": refresh_regional,
        "country": country,
        "state": state,
        "scope": scope,
    })


@router.post("/radar/discover-regional")
async def discover_regional_moments(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
) -> Any:
    """Run on-demand agentic live search for upcoming regional moments in target region."""
    from app.services.marketing.context_radar.calendar_engine import CalendarEngine
    from app.services.knowledge_os.brand_synthesizer import BrandKnowledgeService
    payload = payload or {}
    region = payload.get("region")
    days_ahead = int(payload.get("days_ahead", 30))
    brand_ctx = BrandKnowledgeService(db, tenant_id).synthesize()
    engine = CalendarEngine(db, tenant_id)
    events = await engine.discover_agentic_regional_events(
        target_region=region,
        days_ahead=days_ahead,
        force_refresh=True,
        brand_context=brand_ctx,
    )
    return {
        "status": "ok",
        "target_region": region or (engine.get_target_regions()[0] if engine.get_target_regions() else "india"),
        "events_discovered": len(events),
        "events": events,
    }


@router.post("/autonomous-pulse")
async def trigger_autonomous_marketing_pulse(
    payload: Optional[Dict[str, Any]] = None,
    background: bool = True,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
) -> Any:
    """Trigger the autonomous marketing pulse (auto-mode marketing routine)."""
    payload = payload or {}
    if background:
        from app.worker.tasks import autonomous_marketing_pulse_task
        task = autonomous_marketing_pulse_task.delay(tenant_id, payload)
        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Autonomous marketing pulse queued in background.",
        }
    else:
        from app.services.agents.marketing import MarketingAgent
        agent = MarketingAgent(db, tenant_id)
        result = await agent.autonomous_marketing_pulse(payload)
        return result

