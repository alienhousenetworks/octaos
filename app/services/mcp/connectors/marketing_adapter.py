"""Marketing, Sales Intelligence and Omnichannel Governed MCP Adapter."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.db.session import SessionLocal
from app.services.mcp.connectors.base import ConnectorAdapter, ConnectorContext, DiscoveredObjectMeta
from app.services.integrations.sendgrid_service import SendGridService
from app.services.integrations.calendly_service import CalendlyService
from app.services.integrations.zoominfo_service import ZoomInfoService
from app.services.integrations.landingi_forms_service import LandingiFormsService
from app.services.integrations.zapier_workato_service import ZapierWorkatoService
from app.services.integrations.twilio_service import TwilioService
from app.services.integrations.analytics_connectors import AnalyticsConnectorsService
from app.services.ai_employee_service import AIEmployeeService
from app.services.social.publisher import SocialPublisher
from app.services.verticals.marketing import MarketingService
from app.models.verticals import ContentPost, Lead, Ticket, TicketMessage
from app.services.media.storage import (
    ensure_public_url,
    validate_and_quarantine_media,
    _write_bytes,
)
from app.services.audit_service import AuditService
import base64

logger = logging.getLogger(__name__)


class MarketingIntegrationsAdapter(ConnectorAdapter):
    """
    Governed MCP adapter exposing marketing, sales outreach, scheduling, and iPaaS
    capabilities as dynamically discoverable objects and executable actions.
    """

    def __init__(self, db_factory=SessionLocal):
        self.db_factory = db_factory

    def _get_db(self):
        try:
            return self.db_factory()
        except Exception:
            return None

    async def discover_objects(self, ctx: ConnectorContext) -> List[DiscoveredObjectMeta]:
        return [
            DiscoveredObjectMeta(
                object_name="email_campaign",
                display_name="Email Campaign & Delivery",
                description="Transactional and marketing email broadcasts via Twilio SendGrid / SendPulse.",
                primary_key="id",
                supported_operations=["read", "create", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "to_email": {"type": "string", "format": "email"},
                        "subject": {"type": "string"},
                        "content": {"type": "string"},
                        "template_id": {"type": "string"},
                    },
                    "required": ["to_email", "subject", "content"],
                },
            ),
            DiscoveredObjectMeta(
                object_name="scheduled_meeting",
                display_name="Calendly Scheduled Meeting",
                description="Meeting bookings, SDR availability, and scheduling links via Calendly.",
                primary_key="id",
                supported_operations=["read", "query", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "event_type_uri": {"type": "string"},
                        "invitee_email": {"type": "string"},
                        "scheduling_url": {"type": "string"},
                    },
                },
            ),
            DiscoveredObjectMeta(
                object_name="firmographic_enrichment",
                display_name="ZoomInfo B2B Intelligence",
                description="Company firmographics, buyer intent signals, and executive contact discovery.",
                primary_key="domain",
                supported_operations=["read", "query", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string"},
                        "company_name": {"type": "string"},
                        "employee_count": {"type": "integer"},
                        "revenue_range": {"type": "string"},
                    },
                },
            ),
            DiscoveredObjectMeta(
                object_name="telephony_sms",
                display_name="Twilio SMS & Messaging",
                description="Direct SMS notifications, two-way outreach, and verification codes.",
                primary_key="sid",
                supported_operations=["create", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "to_phone": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["to_phone", "message"],
                },
            ),
            DiscoveredObjectMeta(
                object_name="ipaas_webhook",
                display_name="Zapier / Workato Event",
                description="Enterprise workflow trigger and event emitter for 6,000+ third-party tools.",
                primary_key="event_id",
                supported_operations=["create", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "event_name": {"type": "string"},
                        "payload": {"type": "object"},
                    },
                    "required": ["event_name"],
                },
            ),
            DiscoveredObjectMeta(
                object_name="ai_employee",
                display_name="OctaOS AI Employees Workforce",
                description="Autonomous AI Employees (marketing, sales, support, hr, ceo) ready for task delegation.",
                primary_key="id",
                supported_operations=["read", "query", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "employee": {"type": "string", "enum": ["marketing", "sales", "support", "hr", "ceo"]},
                        "task_type": {"type": "string"},
                        "parameters": {"type": "object"},
                        "instructions": {"type": "string"},
                    },
                    "required": ["employee"],
                },
            ),
            DiscoveredObjectMeta(
                object_name="social_post",
                display_name="Social Media Publishing & Marketing AI",
                description="Publish or schedule media posts to Instagram, Facebook, LinkedIn, X with auto-enhancement.",
                primary_key="id",
                supported_operations=["read", "query", "create", "invoke"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "enum": ["instagram", "facebook", "linkedin", "x"]},
                        "content": {"type": "string"},
                        "media_url": {"type": "string"},
                        "media_base64": {"type": "string"},
                        "media_type": {"type": "string", "enum": ["video", "image", "reel"]},
                        "auto_optimize_with_marketing_ai": {"type": "boolean", "default": True},
                    },
                    "required": ["platform"],
                },
            ),
            DiscoveredObjectMeta(
                object_name="media_asset",
                display_name="Secure Media & Document Asset",
                description="Quarantined storage for videos, images, and documents with permanent URLs.",
                primary_key="url",
                supported_operations=["read", "create"],
                json_schema={
                    "type": "object",
                    "properties": {
                        "file_name": {"type": "string"},
                        "media_base64": {"type": "string"},
                        "media_url": {"type": "string"},
                        "mime_type": {"type": "string"},
                    },
                },
            ),
        ]

    async def describe_object(self, ctx: ConnectorContext, object_name: str) -> Optional[DiscoveredObjectMeta]:
        objs = await self.discover_objects(ctx)
        for obj in objs:
            if obj.object_name == object_name:
                return obj
        return None

    async def query_records(
        self,
        ctx: ConnectorContext,
        object_name: str,
        query: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Query connector resources."""
        db = self._get_db()
        try:
            if object_name in ("ai_employee", "octaos_ai_workforce"):
                service = AIEmployeeService(db, ctx.tenant_id)
                emps = service.list_employees()
                records = [
                    {
                        "id": e.id,
                        "name": e.name,
                        "role_key": e.role_key,
                        "status": e.status,
                        "is_active": e.is_active,
                        "quota_daily": e.quota_daily,
                        "used_today": e.used_today,
                        "kpis": e.kpis,
                        "last_standup": e.last_standup,
                    }
                    for e in emps
                ]
                return {"records": records, "total_count": len(records), "has_more": False}
            elif object_name == "scheduled_meeting":
                service = CalendlyService(db, ctx.tenant_id)
                events = await service.list_event_types()
                return {"records": events, "total_count": len(events), "has_more": False}
            elif object_name == "firmographic_enrichment":
                domain = query.get("domain", "octaos.ai")
                service = ZoomInfoService(db, ctx.tenant_id)
                data = await service.enrich_company(domain)
                return {"records": [data], "total_count": 1, "has_more": False}
            return {"records": [], "total_count": 0, "has_more": False}
        finally:
            if db:
                db.close()

    async def get_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        try:
            if object_name == "firmographic_enrichment":
                service = ZoomInfoService(db, ctx.tenant_id)
                return await service.enrich_company(record_id)
            return None
        finally:
            if db:
                db.close()

    async def create_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        db = self._get_db()
        try:
            if object_name == "media_asset":
                raw_b64 = values.get("media_base64")
                url = values.get("media_url")
                filename = values.get("file_name", "upload")
                declared_mime = values.get("mime_type")

                if raw_b64:
                    if "," in raw_b64 and "data:" in raw_b64:
                        public_url_res = await ensure_public_url(raw_b64, prefix="asset")
                        return {"status": "success", "url": public_url_res, "source": "data_uri"}
                    else:
                        try:
                            content = base64.b64decode(raw_b64)
                            valid, detected_mime, err = validate_and_quarantine_media(content, declared_mime, filename)
                            if not valid:
                                return {"status": "error", "message": f"Quarantine rejection: {err}"}
                            public_url_res = _write_bytes(content, detected_mime, prefix="asset")
                            return {"status": "success", "url": public_url_res, "mime_type": detected_mime}
                        except Exception as e:
                            return {"status": "error", "message": f"Base64 decode failed: {str(e)}"}
                elif url:
                    public_url_res = await ensure_public_url(url, default_mime=declared_mime or "application/octet-stream", prefix="asset")
                    return {"status": "success", "url": public_url_res, "source": "remote_url"}
                return {"status": "error", "message": "Provide 'media_base64' or 'media_url'."}
            elif object_name == "email_campaign":
                service = SendGridService(db, ctx.tenant_id)
                return await service.send_email(
                    to_email=values["to_email"],
                    subject=values["subject"],
                    content=values["content"],
                )
            elif object_name == "telephony_sms":
                service = TwilioService(db, ctx.tenant_id)
                return await service.send_sms(
                    to_phone=values["to_phone"],
                    message=values["message"],
                )
            elif object_name == "ipaas_webhook":
                service = ZapierWorkatoService(db, ctx.tenant_id)
                return await service.emit_event(
                    event_name=values["event_name"],
                    payload=values.get("payload", {}),
                )
            return {"status": "unsupported_object", "object_name": object_name}
        finally:
            if db:
                db.close()

    async def update_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
        values: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {"status": "not_implemented"}

    async def delete_record(
        self,
        ctx: ConnectorContext,
        object_name: str,
        record_id: str,
    ) -> bool:
        return True

    async def invoke_action(
        self,
        ctx: ConnectorContext,
        action_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action over marketing/connector plane."""
        db = self._get_db()
        try:
            if action_name == "sendgrid_send_campaign":
                service = SendGridService(db, ctx.tenant_id)
                return await service.send_email(
                    to_email=arguments.get("to_email", ""),
                    subject=arguments.get("subject", ""),
                    content=arguments.get("content", ""),
                    template_id=arguments.get("template_id"),
                )
            elif action_name == "calendly_generate_booking_link":
                service = CalendlyService(db, ctx.tenant_id)
                event_uri = arguments.get("event_type_uri", "mock")
                return await service.create_single_use_link(event_uri)
            elif action_name == "zoominfo_enrich_lead":
                service = ZoomInfoService(db, ctx.tenant_id)
                if arguments.get("domain"):
                    return await service.enrich_company(arguments["domain"])
                elif arguments.get("email"):
                    return await service.enrich_contact(arguments["email"])
                return {"error": "Provide 'domain' or 'email' to enrich"}
            elif action_name == "twilio_send_sms":
                service = TwilioService(db, ctx.tenant_id)
                return await service.send_sms(
                    to_phone=arguments.get("to_phone", ""),
                    message=arguments.get("message", ""),
                )
            elif action_name == "zapier_emit_event":
                service = ZapierWorkatoService(db, ctx.tenant_id)
                return await service.emit_event(
                    event_name=arguments.get("event_name", "lead_trigger"),
                    payload=arguments.get("payload", {}),
                )
            elif action_name == "powerbi_push_kpis":
                service = AnalyticsConnectorsService(db, ctx.tenant_id)
                return await service.push_powerbi_rows(
                    table_name=arguments.get("table_name", "kpis"),
                    rows=arguments.get("rows", []),
                )
            elif action_name == "matomo_track_goal":
                service = AnalyticsConnectorsService(db, ctx.tenant_id)
                return await service.track_matomo_goal(
                    goal_id=int(arguments.get("goal_id", 1)),
                    revenue=float(arguments.get("revenue", 0.0)),
                )
            elif action_name in ("octaos.ai_employee.delegate", "delegate_ai_employee"):
                emp_role = (arguments.get("employee") or "marketing").lower()
                task_type = arguments.get("task_type", "execute_task")
                params = arguments.get("parameters") or {}
                instructions = arguments.get("instructions", "")

                emp_service = AIEmployeeService(db, ctx.tenant_id)
                employees = emp_service.list_employees()
                target_emp = next((e for e in employees if e.role_key == emp_role or emp_role in e.name.lower()), None)

                if target_emp:
                    target_emp.used_today = (target_emp.used_today or 0) + 1
                    target_emp.status = "working"
                    db.commit()

                execution_result: Dict[str, Any] = {}
                if emp_role == "marketing":
                    platform = (params.get("platform") or "instagram").lower()
                    caption_draft = params.get("caption_draft") or params.get("content") or instructions or "Autonomous Marketing Post"
                    enhanced_text = caption_draft
                    if params.get("auto_optimize", True):
                        try:
                            mkt_service = MarketingService(db, ctx.tenant_id)
                            enhanced_text = await mkt_service.write_post_text(caption_draft, platform=platform)
                        except Exception as e:
                            logger.warning("Marketing AI enhancement fallback: %s", e)
                            enhanced_text = caption_draft

                    if params.get("publish") or params.get("post_mode") in ("instant", "now"):
                        media_url = params.get("media_url")
                        media_b64 = params.get("media_base64")
                        if media_b64:
                            media_url = await ensure_public_url(media_b64, prefix="vid" if params.get("media_type") == "video" else "img")

                        post = ContentPost(
                            tenant_id=ctx.tenant_id,
                            platform=platform,
                            content=enhanced_text,
                            image_url=media_url if params.get("media_type") != "video" else None,
                            video_url=media_url if params.get("media_type") == "video" else None,
                            status="draft",
                        )
                        db.add(post)
                        db.commit()
                        db.refresh(post)

                        pub_res = await SocialPublisher(db, ctx.tenant_id).publish_post(post)
                        if pub_res.success:
                            post.status = "published"
                            db.commit()
                        execution_result = {
                            "published": pub_res.success,
                            "post_id": post.id,
                            "external_id": pub_res.external_id,
                            "enhanced_caption": enhanced_text,
                            "note": pub_res.note or pub_res.error,
                        }
                    else:
                        execution_result = {
                            "status": "drafted",
                            "enhanced_caption": enhanced_text,
                            "platform": platform,
                        }

                elif emp_role == "sales":
                    lead_name = params.get("name") or "Inbound Lead"
                    lead_email = params.get("email") or "lead@example.com"
                    new_lead = Lead(
                        tenant_id=ctx.tenant_id,
                        name=lead_name,
                        email=lead_email,
                        company=params.get("company"),
                        status="captured",
                        need_of_what=instructions or params.get("need_of_what"),
                    )
                    db.add(new_lead)
                    db.commit()
                    db.refresh(new_lead)
                    execution_result = {"status": "success", "lead_id": new_lead.id, "lead_name": new_lead.name}

                elif emp_role == "support":
                    ticket_id = params.get("ticket_id")
                    reply_text = params.get("content") or instructions
                    if ticket_id:
                        msg = TicketMessage(
                            ticket_id=ticket_id,
                            sender_type="agent",
                            content=reply_text,
                            message_type="reply",
                        )
                        db.add(msg)
                        db.commit()
                        execution_result = {"status": "success", "ticket_id": ticket_id, "reply_sent": True}
                    else:
                        execution_result = {"status": "acknowledged", "support_action": "no_ticket_specified"}
                else:
                    execution_result = {"status": "success", "message": f"Task delegated to {emp_role.upper()} AI Employee."}

                AuditService.log_event(
                    db=db,
                    action="ai_employee_delegation",
                    tenant_id=ctx.tenant_id,
                    user_id=target_emp.id if target_emp else "ai_workforce",
                    resource="ai_employee",
                    resource_id=target_emp.id if target_emp else emp_role,
                    details={"task_type": task_type, "employee": emp_role, "result": execution_result},
                )
                return {
                    "status": "success",
                    "employee": target_emp.name if target_emp else f"{emp_role.title()} AI",
                    "task_type": task_type,
                    "result": execution_result,
                }

            elif action_name in ("octaos.social.publish_post", "social_publish_post"):
                platform = (arguments.get("platform") or "instagram").lower()
                content = arguments.get("content", "")
                media_url = arguments.get("media_url")
                media_b64 = arguments.get("media_base64")
                media_type = arguments.get("media_type", "image")
                auto_opt = arguments.get("auto_optimize_with_marketing_ai", True)

                # 1. Resolve / Quarantine Media if Base64
                if media_b64:
                    if "," in media_b64 and "data:" in media_b64:
                        media_url = await ensure_public_url(media_b64, prefix="vid" if media_type == "video" else "img")
                    else:
                        try:
                            raw_bytes = base64.b64decode(media_b64)
                            valid, detected_mime, err = validate_and_quarantine_media(raw_bytes, None, f"media.{'mp4' if media_type == 'video' else 'jpg'}")
                            if not valid:
                                return {"success": False, "error": f"Quarantine rejection: {err}"}
                            media_url = _write_bytes(raw_bytes, detected_mime, prefix="vid" if media_type == "video" else "img")
                        except Exception as e:
                            return {"success": False, "error": f"Media decode error: {str(e)}"}
                elif media_url and not media_url.startswith("http"):
                    media_url = await ensure_public_url(media_url, prefix="vid" if media_type == "video" else "img")

                # 2. Marketing AI Caption Enhancement
                final_content = content
                if auto_opt and content:
                    try:
                        mkt_service = MarketingService(db, ctx.tenant_id)
                        final_content = await mkt_service.write_post_text(content, platform=platform)
                    except Exception as e:
                        logger.warning("Marketing AI enhancement fallback: %s", e)
                        final_content = content

                # 3. Create ContentPost Record
                is_video = media_type == "video" or (media_url and (".mp4" in media_url.lower() or ".mov" in media_url.lower()))
                post = ContentPost(
                    tenant_id=ctx.tenant_id,
                    platform=platform,
                    content=final_content,
                    image_url=media_url if not is_video else None,
                    video_url=media_url if is_video else None,
                    status="draft",
                )
                db.add(post)
                db.commit()
                db.refresh(post)

                # 4. Dispatch to SocialPublisher
                publisher = SocialPublisher(db, ctx.tenant_id)
                res = await publisher.publish_post(post)

                if res.success:
                    post.status = "published"
                    db.commit()

                AuditService.log_event(
                    db=db,
                    action=f"social_publish_{platform}",
                    tenant_id=ctx.tenant_id,
                    user_id="ai_employee_marketing",
                    resource="content_post",
                    resource_id=post.id,
                    details={"success": res.success, "platform": platform, "external_id": res.external_id, "error": res.error},
                )

                return {
                    "success": res.success,
                    "platform": platform,
                    "post_id": post.id,
                    "external_id": res.external_id,
                    "published_content": final_content,
                    "media_url": media_url,
                    "note": res.note or res.error,
                }
            return {"status": "unsupported_action", "action_name": action_name}
        finally:
            if db:
                db.close()
