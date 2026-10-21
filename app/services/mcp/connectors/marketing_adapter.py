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
            if object_name == "scheduled_meeting":
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
            if object_name == "email_campaign":
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
        finally:
            if db:
                db.close()
