""""Synchronous helpers for Celery tasks."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from asgiref.sync import async_to_sync

from app.models.verticals import ContentPost
from app.models.base import APICredential
from app.models.teams import AgentMetric
from app.models.agents import ActivityLog
from app.services.social.publisher import publish_content_post, PublishResult


def apply_publish_result(db: Session, post: ContentPost, result, now: datetime) -> None:
    if result.success:
        log = ActivityLog(
            tenant_id=post.tenant_id,
            agent_name="Marketing AI",
            action="Publish Post",
            description=(
                f"Published to {post.platform.upper()} (Day {post.day}): "
                f"'{(post.content or '')[:60]}...' [id={result.external_id}]"
                + (f" {result.note}" if getattr(result, "note", "") else "")
            ),
            status="success",
        )
        db.add(log)

        metric = (
            db.query(AgentMetric)
            .filter(
                AgentMetric.tenant_id == post.tenant_id,
                AgentMetric.metric_name == "posts_published",
            )
            .first()
        )
        if not metric:
            metric = AgentMetric(
                tenant_id=post.tenant_id, metric_name="posts_published", value=0.0
            )
            db.add(metric)
        metric.value += 1.0

        post.approval_status = "published"
        post.published_at = now
        post.status = "published"
        if getattr(result, "external_id", None):
            post.external_post_id = result.external_id
        try:
            from app.services.marketing.analytics import MarketingAnalyticsService
            post.learning_tags = MarketingAnalyticsService.extract_content_tags(
                post.content or "", post
            )
        except Exception:
            pass
    else:
        log = ActivityLog(
            tenant_id=post.tenant_id,
            agent_name="Marketing AI",
            action="Publish Post Failed",
            description=f"Failed posting to {post.platform.upper()}: {result.error[:300]}",
            status="failed",
        )
        db.add(log)
        post.status = "failed"


def publish_post_sync(db: Session, post: ContentPost):
    now = datetime.now(timezone.utc)
    # A provider post ID means the external system accepted it; never enqueue it again.
    if post.external_post_id:
        return PublishResult(
            success=True, platform=(post.platform or "").lower(),
            external_id=post.external_post_id,
            note="Already accepted by a publishing provider; awaiting delivery reconciliation.",
        )

    buffer_credential = (
        db.query(APICredential)
        .filter(APICredential.tenant_id == post.tenant_id, APICredential.provider == "buffer")
        .first()
    )
    if buffer_credential:
        channel_map = dict((buffer_credential.settings or {}).get("channel_map", {}))
        platform_key = (post.platform or "").lower().replace("twitter", "x")
        channel_id = channel_map.get(platform_key)
        if not channel_id:
            result = PublishResult(
                success=False, platform=platform_key,
                error=f"Buffer is connected but no Buffer channel is mapped for '{platform_key}'.",
            )
            apply_publish_result(db, post, result, now)
            post.status = "needs_configuration"
            db.commit()
            return result

        try:
            from app.services.integrations.buffer_service import BufferService
            buffer = BufferService(db, post.tenant_id)
            created = async_to_sync(buffer.create_post)(
                channel_id=channel_id,
                text=post.content or "",
                image_url=post.image_url,
                video_url=post.video_url,
            )
            post.external_post_id = created["id"]
            post.status = "scheduled"
            post.fallback_reason = "Accepted by Buffer; platform delivery status is not yet reconciled."
            db.add(ActivityLog(
                tenant_id=post.tenant_id,
                agent_name="Marketing AI",
                action="Queue Post in Buffer",
                description=f"Buffer accepted approved {platform_key} post {post.id} (external id={created['id']}).",
                status="success",
            ))
            db.commit()
            return PublishResult(
                success=True, platform=platform_key, external_id=created["id"],
                note="Queued in Buffer; final social-network delivery is pending.",
            )
        except Exception as exc:
            db.rollback()
            result = PublishResult(
                success=False, platform=platform_key,
                error=f"Buffer publishing failed: {str(exc)[:240]}",
            )
            apply_publish_result(db, post, result, now)
            # A create mutation timeout can be ambiguous. Stop automatic retries until
            # the user reconciles Buffer's queue; blind retries can create duplicates.
            post.status = "publish_uncertain"
            db.commit()
            return result

    result = async_to_sync(publish_content_post)(db, post)
    apply_publish_result(db, post, result, now)
    db.commit()
    return result
