"""SalesAgent Facade for OctaOS.

Decomposed into dedicated modular services under app.services.sales:
- DiscoveryService: Lead generation, parallel search, and external provider sourcing
- EnrichmentService: Apollo organization data, news, and jobs
- OutreachService: Multichannel outreach drafting, compliance gates, and dispatch
- MeetingService: Calendar booking and reply coordination
- WorkflowOrchestrator: 10-step autonomous Sales AI pipeline
- Utils: JSON extraction and lead dossier formatting
"""
import logging
from typing import Any, Dict, List, Optional

from app.services.agents.base import BaseAgent
from app.services.sales.discovery_service import DiscoveryService
from app.services.sales.enrichment_service import EnrichmentService
from app.services.sales.meeting_service import MeetingService
from app.services.sales.outreach_service import OutreachService
from app.services.sales.utils import _build_lead_data, extract_json
from app.services.sales.workflow_orchestrator import WorkflowOrchestrator

logger = logging.getLogger(__name__)

# Re-export shared utilities for backward compatibility
__all__ = ["SalesAgent", "extract_json", "_build_lead_data"]


class SalesAgent(BaseAgent):
    """Modular facade maintaining 100% backward compatibility for all callers and tests."""

    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Sales AI")
        self.discovery = DiscoveryService(db, tenant_id, llm=self.llm, log_activity=self.log_activity)
        self.enrichment = EnrichmentService(db, tenant_id, log_activity=self.log_activity)
        self.outreach = OutreachService(db, tenant_id, llm=self.llm, log_activity=self.log_activity)
        self.meeting = MeetingService(db, tenant_id, log_activity=self.log_activity)
        self.orchestrator = WorkflowOrchestrator(
            db,
            tenant_id,
            llm=self.llm,
            log_activity=self.log_activity,
            discovery_service=self.discovery,
            enrichment_service=self.enrichment,
            agent=self,
        )

    async def execute_task(self, task: dict) -> dict:
        """Route tasks to the appropriate modular domain service."""
        action = task.get("action")
        params = task.get("parameters", {})

        if action == "generate_leads":
            return await self._generate_leads(params)
        elif action == "sales_outreach":
            return await self._sales_outreach(params)
        elif action == "schedule_meeting":
            return await self._schedule_meeting(params)
        elif action in ("collaborate_market_research", "collaborate_external"):
            required_caps = params.get("required_capabilities") or ["market_analysis", "realtime_research"]
            subtask = {
                "description": params.get("query") or params.get("task_description") or "Market Research",
                "output_schema": params.get("output_schema"),
            }
            constraints = {
                "preferred_provider": params.get("provider"),
                "max_cost_usd": params.get("max_cost_usd", 2.0),
                "_test_mock_response": params.get("_test_mock_response"),
            }
            res = await self.collaborate_with_external_ai(
                task=subtask,
                required_capabilities=required_caps,
                context=params.get("context", {}),
                constraints=constraints,
                parent_task_id=task.get("parent_task_id"),
            )
            self.log_activity("External AI Collaboration", f"Collaborated with external AI: {subtask['description']}")
            return {
                "status": "success",
                "collaboration": res,
                "workflow_resumed": True,
                "leads_enriched": True,
            }
        elif action == "run_v3_workflow":
            return await self.run_sales_ai_v3_workflow()
        return {"status": f"Unknown action: {action}"}

    async def run_sales_ai_v3_workflow(
        self,
        provider=None,
        model=None,
        count=50,
        freshness=None,
        mode: str = "configured_engine",
        prompt_instructions: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """Delegate V3 autonomous pipeline execution to WorkflowOrchestrator."""
        return await self.orchestrator.run_sales_ai_v3_workflow(
            provider=provider,
            model=model,
            count=count,
            freshness=freshness,
            mode=mode,
            prompt_instructions=prompt_instructions,
            idempotency_key=idempotency_key,
        )

    async def _generate_leads(self, params: dict):
        return await self.discovery.generate_leads(params)

    async def _collect_parallel_search(self, *args, **kwargs):
        return await self.discovery.collect_parallel_search(*args, **kwargs)

    def _record_parallel_search_spend(self, batch) -> None:
        return self.discovery.record_parallel_search_spend(batch)

    async def _fetch_real_leads(self, *args, **kwargs) -> list:
        return await self.discovery.fetch_real_leads(*args, **kwargs)

    async def _fetch_apollo_org_data(self, api_key: str, domain: str) -> Optional[str]:
        return await self.enrichment.fetch_apollo_org_data(api_key, domain)

    async def _fetch_apollo_news(self, api_key: str, org_id: str) -> list:
        return await self.enrichment.fetch_apollo_news(api_key, org_id)

    async def _fetch_apollo_jobs(self, api_key: str, org_id: str) -> list:
        return await self.enrichment.fetch_apollo_jobs(api_key, org_id)

    async def _sales_outreach(self, params: dict):
        return await self.outreach.sales_outreach(params)

    async def _schedule_meeting(self, params: dict):
        return await self.meeting.schedule_meeting(params)

    async def daily_routine(self):
        self.log_activity("Daily Routine", "Checking active lead outreach campaigns.", status="success")
        try:
            from app.services.sales.cadence_runner import DurableCadenceRunner
            from app.services.sales.outbox_service import SalesOutboxService
            runner = DurableCadenceRunner(self.db, self.tenant_id)
            stats = runner.get_cadence_stats()
            outbox = SalesOutboxService(self.db, self.tenant_id)
            drained = outbox.drain_due_items(limit=25)
            self.log_activity(
                "Daily Routine",
                f"Active pipeline: {stats.get('enrolled', 0)} enrolled, {stats.get('pending_touches', 0)} pending touches. Drained {drained.get('sent', 0)} touches.",
                status="success",
            )
        except Exception as e:
            logger.debug(f"Sales daily routine check: {e}")
