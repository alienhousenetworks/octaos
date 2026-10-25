import time
import uuid
import httpx
from typing import Dict, Any, List, Optional
from app.octa_orchestrator.orchestrator.decomposer import DAGDecomposer, ExecutionPlanDAG
from app.octa_orchestrator.orchestrator.router import ModelRouter
from app.octa_orchestrator.orchestrator.quality_gate import QualityGate
from app.core.tool_registry import ToolRegistry, ApprovalRequiredError, ToolExecutionError


class AIManagerOrchestrator:
    """
    The Executive AI Manager: Coordinates multi-agent workflows like an experienced manager,
    evaluating ROI, generating DAG task graphs, executing governed department tools,
    respecting human approval gates, and verifying results.
    """

    def __init__(self, api_key: str = None, db: Optional[Any] = None, tenant_id: Optional[str] = None, user_context: Optional[Dict[str, Any]] = None):
        self.decomposer = DAGDecomposer(api_key=api_key)
        self.router = ModelRouter()
        self.quality_gate = QualityGate()
        self.api_key = api_key
        self.db = db
        if not tenant_id or not str(tenant_id).strip():
            raise ValueError("An authenticated tenant_id is required for orchestration.")
        self.tenant_id = str(tenant_id)
        # Least-privilege default for non-route callers; never infer admin privileges.
        self.user_context = user_context or {"role": "user", "is_superuser": False}
        self.tool_registry = ToolRegistry.get_instance()

    async def execute_goal(self, user_goal: str, risk_level: str = "NORMAL") -> Dict[str, Any]:
        start_time = time.time()
        trajectory_id = str(uuid.uuid4())

        print(f"[AI Manager] Initiating goal execution: '{user_goal}' | ID: {trajectory_id}")

        # Enterprise context gathering from governed tools
        context_snippets: List[str] = []
        goal_lower = user_goal.lower()

        # 1. Check if goal matches department domain tools and fetch verified evidence
        if any(w in goal_lower for w in ("field", "visit", "showing", "salesperson", "dispatch", "route", "property")):
            try:
                from app.db.session import SessionLocal
                from app.services.sales_os.field_sales.orchestrator_bridge import FieldSalesOrchestratorBridge
                active_db = self.db or SessionLocal()
                try:
                    bridge = FieldSalesOrchestratorBridge(active_db, self.tenant_id)
                    report_data = bridge.generate_analysis_report(30)
                    context_snippets.append(f"[Live Field Sales Database Report]: {report_data}")
                finally:
                    if not self.db:
                        active_db.close()
            except Exception as e:
                print(f"[AI Manager] Field sales context query skipped: {e}")

        # Check for sales pipeline inquiries
        if any(w in goal_lower for w in ("pipeline", "deals", "opportunity", "conversion", "revenue")):
            try:
                res = await self.tool_registry.execute("sales.query_pipeline", self.tenant_id, {}, self.user_context, self.db)
                if res.get("success"):
                    context_snippets.append(f"[Live Sales Pipeline Evidence]: {res.get('data')}")
            except Exception as e:
                print(f"[AI Manager] Pipeline tool query skipped: {e}")

        # Check for campaign analytics
        if any(w in goal_lower for w in ("campaign", "ad", "marketing", "reach", "roi", "spend")):
            try:
                res = await self.tool_registry.execute("marketing.get_campaign_analytics", self.tenant_id, {}, self.user_context, self.db)
                if res.get("success"):
                    context_snippets.append(f"[Live Marketing Analytics Evidence]: {res.get('data')}")
            except Exception as e:
                print(f"[AI Manager] Marketing analytics tool query skipped: {e}")

        evidence_context = "\n".join(context_snippets)

        # 2. Generate Structured DAG Plan
        dag_plan: ExecutionPlanDAG = await self.decomposer.decompose_goal(user_goal)
        print(f"[AI Manager] Generated DAG with {len(dag_plan.tasks)} sub-tasks | Est. ROI: {dag_plan.estimated_total_roi}")

        completed_results: Dict[str, Any] = {}
        execution_logs: List[Dict[str, Any]] = []
        pending_approvals: List[Dict[str, Any]] = []

        # 3. Iterate through DAG Sub-tasks with Governed Execution
        for task in dag_plan.tasks:
            # Check route selection
            route = self.router.select_route(task.description, task.roi_priority, risk_level)
            print(f"[AI Manager] Executing {task.task_id} via route: {route['provider']} ({route['model_name']})")

            # Check if this task corresponds to a governed tool execution
            tool_executed = False
            output_text = ""

            # Check for discount approval or financial mutations
            if any(w in task.description.lower() for w in ("discount", "price concession", "commission override")):
                try:
                    tool_res = await self.tool_registry.execute(
                        "sales.approve_booking_discount",
                        self.tenant_id,
                        {"deal_id": "current_deal", "discount_pct": 2.0, "rationale": task.description},
                        self.user_context,
                        self.db,
                    )
                    output_text = f"Governed tool executed: {tool_res}"
                    tool_executed = True
                except ApprovalRequiredError as ap:
                    pending_approvals.append({
                        "task_id": task.task_id,
                        "action_key": ap.action_key,
                        "reason": ap.reason,
                        "payload": ap.payload,
                    })
                    output_text = f"[APPROVAL PENDING] {ap.reason}"
                    tool_executed = True

            if not tool_executed:
                # LLM execution via LLMGateway or HTTP fallback
                prompt = f"Goal Context: {user_goal}\nSub-task: {task.description}\nDependencies Output: {completed_results}\n{evidence_context}"
                system_prompt = f"You are a specialized worker agent: {task.assigned_agent}. Base your answers on real evidence."

                llm_success = False
                if self.db:
                    try:
                        from app.services.llm_gateway import LLMGateway
                        gateway = LLMGateway(self.db, self.tenant_id)
                        output_text = await gateway.complete(prompt, system_prompt=system_prompt)
                        llm_success = True
                    except Exception as e:
                        print(f"[AI Manager] LLMGateway call error: {e}")

                if not llm_success:
                    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                    payload = {
                        "model": route["model_name"] if route["provider"] == "frontier" else "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ]
                    }

                    try:
                        async with httpx.AsyncClient() as client:
                            res = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=40.0)
                            if res.status_code == 200:
                                output_text = res.json()["choices"][0]["message"]["content"]
                            else:
                                output_text = f"[UNAVAILABLE] Model provider returned HTTP {res.status_code}; task output was not generated."
                    except Exception as exc:
                        output_text = f"[UNAVAILABLE] Model provider request failed ({type(exc).__name__}); task output was not generated."

                # Quality Reflection Gate Check
                verification = self.quality_gate.inspect_result(task.task_id, output_text)
                if not verification["passed"]:
                    print(f"[AI Manager Quality Warning] {task.task_id} failed inspection: {verification['reason']}")

            completed_results[task.task_id] = output_text
            execution_logs.append({
                "task_id": task.task_id,
                "description": task.description,
                "route": route,
                "output": output_text
            })

        total_time_ms = int((time.time() - start_time) * 1000)

        return {
            "trajectory_id": trajectory_id,
            "user_goal": user_goal,
            "estimated_roi": dag_plan.estimated_total_roi,
            "sub_tasks_executed": len(dag_plan.tasks),
            "results": completed_results,
            "pending_approvals": pending_approvals,
            "logs": execution_logs,
            "execution_time_ms": total_time_ms
        }

