"""Sales Orchestrator Agent Runtime Kernel: session lifecycle, handoffs, and governed execution."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.agent_runtime import AgentRun, AgentTask, AgentHandoff
from app.services.sales_os.runtime.tool_registry import tool_registry

logger = logging.getLogger(__name__)


class SalesOrchestrator:
    """The central orchestrator for coordinating specialized agents, durable runs, and verified handoffs."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def start_run(
        self,
        goal: str,
        agent_id: str = "sales_orchestrator",
        idempotency_key: Optional[str] = None,
        deal_room_id: Optional[str] = None,
        company_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        input_payload: Optional[Dict[str, Any]] = None,
    ) -> AgentRun:
        """Starts or retrieves a durable execution session."""
        now = datetime.now(timezone.utc)

        if idempotency_key:
            existing = (
                self.db.query(AgentRun)
                .filter_by(tenant_id=self.tenant_id, idempotency_key=idempotency_key)
                .first()
            )
            if existing:
                logger.info(f"Returning existing AgentRun {existing.id} for idempotency key '{idempotency_key}'")
                return existing

        run = AgentRun(
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            version="1.0.0",
            status="running",
            goal=goal,
            deal_room_id=deal_room_id,
            company_id=company_id,
            lead_id=lead_id,
            idempotency_key=idempotency_key,
            input_payload=input_payload or {},
            started_at=now,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        logger.info(f"Created new durable AgentRun {run.id} for goal: {goal[:60]}...")
        return run

    def create_task(
        self,
        run_id: str,
        agent_id: str,
        task_type: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> AgentTask:
        task = AgentTask(
            run_id=run_id,
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            task_type=task_type,
            status="pending",
            input_data=input_data or {},
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def execute_handoff(
        self,
        run_id: str,
        from_agent: str,
        to_agent: str,
        objective: str,
        payload: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> AgentHandoff:
        """Executes a structured, verifiable handoff between two specialist agents."""
        handoff = AgentHandoff(
            run_id=run_id,
            tenant_id=self.tenant_id,
            from_agent=from_agent,
            to_agent=to_agent,
            objective=objective,
            payload=payload or {},
            constraints=constraints or {},
            status="accepted",
        )
        self.db.add(handoff)
        self.db.commit()
        self.db.refresh(handoff)
        logger.info(f"Agent handoff recorded: [{from_agent}] -> [{to_agent}] for '{objective[:50]}'")
        return handoff

    def complete_run(
        self,
        run_id: str,
        output_payload: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> AgentRun:
        run = self.db.query(AgentRun).filter_by(id=run_id, tenant_id=self.tenant_id).first()
        if not run:
            raise ValueError(f"AgentRun {run_id} not found.")

        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        run.output_payload = output_payload or {}
        run.tokens_used += tokens_used
        run.cost_usd += cost_usd
        self.db.commit()
        self.db.refresh(run)
        return run

    def fail_run(self, run_id: str, error_summary: str) -> AgentRun:
        run = self.db.query(AgentRun).filter_by(id=run_id, tenant_id=self.tenant_id).first()
        if not run:
            raise ValueError(f"AgentRun {run_id} not found.")

        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.error_summary = error_summary
        self.db.commit()
        self.db.refresh(run)
        return run

    async def execute_tool(
        self,
        run_id: str,
        agent_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches tool execution through the governed ToolRegistry."""
        return await tool_registry.execute(
            tool_name=tool_name,
            tenant_id=self.tenant_id,
            parameters=parameters,
            db=self.db,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
        )
