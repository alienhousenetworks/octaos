"""
OctaOS Automation Event Bridge.
Connects internal business domain events (leads, deals, tickets, approvals)
with active automation workflows using durable, idempotent delivery (Principles #12 & #13).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.models.automations import AutomationWorkflow, AutomationExecution
from app.services.automation.base import FailureClassification
from app.services.automation.factory import get_automation_engine

logger = logging.getLogger(__name__)


class AutomationEventBridge:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def dispatch_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries all active workflows subscribed to this event_type for the tenant,
        and triggers execution through the configured engine adapter.
        """
        workflows = (
            self.db.query(AutomationWorkflow)
            .filter_by(tenant_id=self.tenant_id, status="active", trigger_type="octaos_event")
            .filter(AutomationWorkflow.trigger_event == event_type)
            .all()
        )

        if not workflows:
            logger.debug(f"No active automation workflows subscribed to event '{event_type}' for tenant {self.tenant_id}")
            return []

        logger.info(f"Dispatching event '{event_type}' to {len(workflows)} active automation workflows")
        results = []
        adapter = get_automation_engine(self.tenant_id, self.db)

        for wf in workflows:
            # Persisted dedupe handles sequential provider retries. A unique receipt table
            # is still required to close the concurrent first-delivery race.
            if idempotency_key:
                prior = (
                    self.db.query(AutomationExecution)
                    .filter_by(tenant_id=self.tenant_id, workflow_id=wf.id)
                    .order_by(AutomationExecution.created_at.desc())
                    .all()
                )
                duplicate = next((item for item in prior
                    if (item.trigger_context or {}).get("idempotency_key") == idempotency_key), None)
                if duplicate:
                    results.append({"workflow_id": wf.id, "workflow_name": wf.name,
                        "execution_id": duplicate.id, "status": duplicate.status,
                        "deduplicated": True})
                    continue

            start_time = time.time()
            execution = AutomationExecution(
                tenant_id=self.tenant_id,
                workflow_id=wf.id,
                trigger_type="octaos_event",
                trigger_event=event_type,
                status="running",
                trigger_context={**payload, **({"idempotency_key": idempotency_key} if idempotency_key else {})},
                inputs=payload,
                attempt=1,
                max_attempts=3,
            )
            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            try:
                # Trigger engine execution
                engine_res = await adapter.trigger_workflow_manually(
                    tenant_id=self.tenant_id,
                    external_id=wf.external_flow_id or wf.id,
                    payload={"event": event_type, "data": payload},
                )
                duration_ms = int((time.time() - start_time) * 1000)

                execution.status = "succeeded"
                execution.external_execution_id = engine_res.get("execution_id")
                execution.outputs = engine_res.get("outputs", {})
                execution.duration_ms = duration_ms
                execution.finished_at = datetime.now(timezone.utc)
                self.db.commit()

                results.append({
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "execution_id": execution.id,
                    "status": "succeeded",
                    "duration_ms": duration_ms,
                })
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                error_str = str(e)

                # Classify failure (Principle #36)
                classification = FailureClassification.PLATFORM_RUNTIME.value
                if "rate limit" in error_str.lower() or "503" in error_str.lower():
                    classification = FailureClassification.EXTERNAL_SERVICE.value
                elif "auth" in error_str.lower() or "token" in error_str.lower() or "expired" in error_str.lower():
                    classification = FailureClassification.USER_CONFIGURATION.value

                execution.status = "failed"
                execution.failure_classification = classification
                execution.failure_reason = error_str
                execution.duration_ms = duration_ms
                execution.finished_at = datetime.now(timezone.utc)
                self.db.commit()

                results.append({
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "execution_id": execution.id,
                    "status": "failed",
                    "failure_classification": classification,
                    "error": error_str,
                })

        return results
