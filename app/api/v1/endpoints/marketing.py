from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from asgiref.sync import async_to_sync

from app.api import deps
from app.schemas import verticals as schemas
from app.models import verticals as models

router = APIRouter()


class ApproveOptions(BaseModel):
    publish_now: bool = False


@router.post("/generate", response_model=schemas.ContentPost)
async def generate_content(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    topic: str,
    platform: str = "linkedin",
) -> Any:
    from app.services.verticals.marketing import MarketingService

    service = MarketingService(db, tenant_id)
    post = await service.generate_post(topic, platform)
    return post


@router.get("/", response_model=List[schemas.ContentPost])
def read_posts(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
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
    campaign_in: schemas.CampaignCreate,
) -> Any:
    from app.worker.tasks import generate_campaign_task

    generate_campaign_task.delay(tenant_id, campaign_in.dict())
    return {"status": "queued", "message": "Campaign generation has been queued in the background."}


@router.put("/posts/{post_id}", response_model=schemas.ContentPost)
def update_post(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
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

    db.commit()
    db.refresh(post)
    return post


def _schedule_post(post: models.ContentPost, publish_now: bool = False) -> None:
    now = datetime.now(timezone.utc)
    post.approval_status = "approved"
    if publish_now:
        post.scheduled_at = now
        post.status = "scheduled"
    else:
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


@router.post("/posts/approve-all")
def approve_all_posts(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
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
