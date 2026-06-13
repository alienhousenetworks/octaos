import json
import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.services.llm_gateway import LLMGateway
from app.models.workflows import Workflow, WorkflowTask
from app.models.agents import ActivityLog, KnowledgeDocument
from app.services.agents.marketing import MarketingAgent
from app.services.agents.sales import SalesAgent
from app.services.agents.support import SupportAgent
from app.services.agents.finance import FinanceAgent
from app.services.agents.hr import HRAgent
from app.models.verticals import Lead

logger = logging.getLogger(__name__)

class CEOService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def generate_plan(self, objective: str, provider: str = "gemini", model: str = None) -> Workflow:
        """
        Takes a business objective and generates a structured DAG workflow with tasks assigned to departments.
        """
        system_prompt = (
            "You are the CEO AI, the top-level orchestrator of OctaOS. "
            "Your job is to analyze the user's business objective and break it down into a highly structured "
            "Directed Acyclic Graph (DAG) of tasks across departments: Marketing, Sales, Support, HR, Finance. "
            "You MUST create between 4 to 6 connected tasks that logically lead to achieving the objective. "
            "At least one task must depend on another task to show a clear sequential workflow (e.g. Sales Lead Sourcing "
            "depends on Marketing Research). The final task MUST be a 'CEO Summary & Wrap-up' task which aggregates the "
            "results and writes a final executive report.\n\n"
            "Here are the available task types you can schedule:\n"
            "- marketing_research: Research the target audience, brand rules, pain points. Returns brand context.\n"
            "- sales_leads: Source new leads matching the target audience. Payload parameters: provider ('free_search' | 'apollo'), query (str), count (int).\n"
            "- sales_outreach: Prepare outreach pitches/templates for generated leads. Payload parameters: channel ('free_outreach' | 'smtp'), subject (str), body_template (str).\n"
            "- hr_source: Source candidate profiles to help build/scale operations. Payload parameters: role (str), requirements (str), salary (str), count (int).\n"
            "- finance_budget: Update budgets and ROI forecasts. Payload parameters: amount (float).\n"
            "- ceo_summary: The final execution wrap-up task. Must depend on ALL other tasks. Payload parameters: none.\n\n"
            "Respond ONLY with a JSON object in this format (no other text, markdown wrapper is allowed but output clean JSON):\n"
            "{\n"
            "  \"analysis\": \"A concise 2-3 sentence executive summary of how this plan achieves the objective.\",\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"id\": \"unique_string_id_1\",\n"
            "      \"name\": \"Short descriptive task name (e.g. AI SaaS Competitor Analysis)\",\n"
            "      \"department\": \"Marketing | Sales | Support | HR | Finance | CEO\",\n"
            "      \"description\": \"Detailed description of what the agent will perform.\",\n"
            "      \"task_type\": \"marketing_research | sales_leads | sales_outreach | hr_source | finance_budget | ceo_summary\",\n"
            "      \"payload\": {}, \n"
            "      \"depends_on\": [] \n"
            "    },\n"
            "    {\n"
            "      \"id\": \"unique_string_id_2\",\n"
            "      \"name\": \"Lead Generation for Startups\",\n"
            "      \"department\": \"Sales\",\n"
            "      \"description\": \"Generate sales leads targeting early-stage tech founders.\",\n"
            "      \"task_type\": \"sales_leads\",\n"
            "      \"payload\": {\"provider\": \"free_search\", \"query\": \"AI startups NY\", \"count\": 5},\n"
            "      \"depends_on\": [\"unique_string_id_1\"]\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        prompt = f"Business Objective: '{objective}'"
        
        response_str = await self.llm.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            model=model
        )
        
        try:
            # Clean JSON codeblock wrappers if any
            clean_str = response_str.strip().strip("```json").strip("```").strip()
            # Robust extraction of JSON substring
            import re
            json_match = re.search(r'\{.*\}', clean_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = clean_str
                
            plan_data = json.loads(json_str)
        except Exception as e:
            logger.error(f"Error parsing CEO planning response: {e}. Raw response: {response_str}")
            # Fallback plan
            plan_data = self._get_fallback_plan(objective)

        # Create Workflow in Database
        workflow = Workflow(
            tenant_id=self.tenant_id,
            name=objective,
            vertical="CEO",
            department="CEO",
            status="active"
        )
        self.db.add(workflow)
        self.db.flush() # get workflow.id

        # Mapping generated temporary IDs to actual database IDs
        id_map = {}
        
        # 1. Create WorkflowTasks in the database
        tasks_list = plan_data.get("tasks", [])
        
        # Ensure we have a final ceo_summary task
        has_summary = any(t.get("task_type") == "ceo_summary" for t in tasks_list)
        if not has_summary:
            tasks_list.append({
                "id": "ceo_summary_final",
                "name": "CEO Executive Growth Summary",
                "department": "CEO",
                "description": "Aggregate and compile all agent execution reports into a final business summary.",
                "task_type": "ceo_summary",
                "payload": {},
                "depends_on": [t.get("id") for t in tasks_list]
            })

        # Insert tasks to get database IDs
        for t in tasks_list:
            temp_id = t.get("id")
            # Store depends_on and original temporary ID in payload
            payload = dict(t.get("payload", {}))
            payload["temp_id"] = temp_id
            payload["original_depends_on"] = t.get("depends_on", [])
            payload["department"] = t.get("department", "CEO")
            payload["description"] = t.get("description", "")
            
            task_type = t.get("task_type", "marketing_research")
            
            db_task = WorkflowTask(
                workflow_id=workflow.id,
                name=t.get("name", "Strategic Task"),
                task_type=task_type,
                status="pending",
                payload=payload,
                scheduled_at=datetime.now(timezone.utc)
            )
            self.db.add(db_task)
            self.db.flush()
            
            id_map[temp_id] = db_task.id

        # 2. Translate temp depends_on IDs to database depends_on IDs in task payloads
        db_tasks = self.db.query(WorkflowTask).filter_by(workflow_id=workflow.id).all()
        for db_task in db_tasks:
            payload = dict(db_task.payload or {})
            orig_depends = payload.get("original_depends_on", [])
            db_depends = []
            for d in orig_depends:
                if d in id_map:
                    db_depends.append(id_map[d])
            payload["depends_on"] = db_depends
            db_task.payload = payload
            
        self.db.commit()

        log = ActivityLog(
            tenant_id=self.tenant_id,
            agent_name="CEO AI",
            action="Plan Formulated",
            description=f"Strategic plan formulated: '{plan_data.get('analysis', '')}'",
            status="success"
        )
        self.db.add(log)
        self.db.commit()

        return workflow

    async def execute_workflow(self, workflow_id: str):
        """
        Orchestration loop that runs the DAG. Runs tasks whose dependencies are met,
        until all tasks are completed or one fails.
        """
        workflow = self.db.query(Workflow).filter_by(id=workflow_id, tenant_id=self.tenant_id).first()
        if not workflow:
            logger.error(f"Workflow {workflow_id} not found.")
            return

        workflow.status = "executing"
        self.db.commit()

        log = ActivityLog(
            tenant_id=self.tenant_id,
            agent_name="CEO AI",
            action="Execution Initiated",
            description=f"Initiated execution of growth plan: '{workflow.name}'",
            status="success"
        )
        self.db.add(log)
        self.db.commit()

        while True:
            # Refresh DB session tasks
            tasks = self.db.query(WorkflowTask).filter_by(workflow_id=workflow_id).all()
            
            completed_ids = [t.id for t in tasks if t.status == "completed"]
            failed_ids = [t.id for t in tasks if t.status == "failed"]
            in_progress_tasks = [t for t in tasks if t.status == "in_progress"]
            pending_tasks = [t for t in tasks if t.status == "pending"]

            if failed_ids:
                workflow.status = "failed"
                self.db.commit()
                
                log = ActivityLog(
                    tenant_id=self.tenant_id,
                    agent_name="CEO AI",
                    action="Execution Failed",
                    description=f"Growth plan execution aborted due to task failure.",
                    status="failed"
                )
                self.db.add(log)
                self.db.commit()
                break

            if not pending_tasks and not in_progress_tasks:
                # All tasks are finished
                workflow.status = "completed"
                self.db.commit()
                break

            # Find pending tasks that have all dependencies met
            ready_tasks = []
            for t in pending_tasks:
                payload = t.payload or {}
                depends_on = payload.get("depends_on", [])
                
                # Check if all depends_on IDs are in completed_ids
                if all(dep_id in completed_ids for dep_id in depends_on):
                    ready_tasks.append(t)

            if not ready_tasks and not in_progress_tasks:
                # Deadlock or cycle detection
                workflow.status = "failed"
                self.db.commit()
                
                log = ActivityLog(
                    tenant_id=self.tenant_id,
                    agent_name="CEO AI",
                    action="Execution Deadlock",
                    description="Execution stopped. Circular dependencies detected in workflow tasks.",
                    status="failed"
                )
                self.db.add(log)
                self.db.commit()
                break

            if not ready_tasks:
                # Wait a bit for currently in-progress tasks to complete
                await asyncio.sleep(2.0)
                continue

            # Run ready tasks in parallel
            tasks_to_run = []
            for t in ready_tasks:
                t.status = "in_progress"
                self.db.commit()
                tasks_to_run.append(self.execute_single_task(t))

            # Run execution tasks asynchronously
            await asyncio.gather(*tasks_to_run)

    async def execute_single_task(self, task: WorkflowTask):
        """
        Executes a single task in the DAG.
        """
        try:
            logger.info(f"Executing CEO workflow task: {task.name} ({task.task_type})")
            
            log = ActivityLog(
                tenant_id=self.tenant_id,
                agent_name="Workflow Engine",
                action="Task Started",
                description=f"Started task: '{task.name}' assigned to {task.payload.get('department', 'CEO')}.",
                status="success"
            )
            self.db.add(log)
            self.db.commit()

            result_data = {}
            
            # Execute based on task type
            if task.task_type == "marketing_research":
                result_data = await self._run_marketing_research(task)
            elif task.task_type == "sales_leads":
                result_data = await self._run_sales_leads(task)
            elif task.task_type == "sales_outreach":
                result_data = await self._run_sales_outreach(task)
            elif task.task_type == "hr_source":
                result_data = await self._run_hr_source(task)
            elif task.task_type == "finance_budget":
                result_data = await self._run_finance_budget(task)
            elif task.task_type == "ceo_summary":
                result_data = await self._run_ceo_summary(task)
            else:
                result_data = {"status": "error", "message": f"Unsupported task type: {task.task_type}"}

            task.result = result_data
            task.status = "completed"
            self.db.commit()

            log = ActivityLog(
                tenant_id=self.tenant_id,
                agent_name="Workflow Engine",
                action="Task Completed",
                description=f"Completed task: '{task.name}'. Output generated.",
                status="success"
            )
            self.db.add(log)
            self.db.commit()

        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}")
            task.status = "failed"
            task.result = {"error": str(e)}
            self.db.commit()
            
            log = ActivityLog(
                tenant_id=self.tenant_id,
                agent_name="Workflow Engine",
                action="Task Failed",
                description=f"Failed task: '{task.name}'. Error: {str(e)}",
                status="failed"
            )
            self.db.add(log)
            self.db.commit()

    async def _run_marketing_research(self, task: WorkflowTask) -> dict:
        topic = task.payload.get("topic", "AI growth strategy")
        platforms = task.payload.get("platforms", ["linkedin"])
        
        prompt = (
            f"Generate a target audience persona, brand voice rules, and key topics for: {topic}. "
            "Output must be detailed and formatted in clean markdown, containing: "
            "1. Demographics & Pain Points. "
            "2. Brand Voice guidelines. "
            "3. 3 core content angles/topics. "
            "Limit to 250 words."
        )
        
        insights = await self.llm.complete(prompt=prompt, provider="gemini", system_prompt="You are an expert Marketing Researcher.")
        
        # Save as a KnowledgeDocument in the DB!
        doc = KnowledgeDocument(
            tenant_id=self.tenant_id,
            department="Marketing",
            doc_type="Brand Guidelines",
            content=f"Strategic Audience Research:\n\n{insights}"
        )
        self.db.add(doc)
        self.db.commit()
        
        return {"report": insights, "doc_added": True}

    async def _run_sales_leads(self, task: WorkflowTask) -> dict:
        agent = SalesAgent(self.db, self.tenant_id)
        params = {
            "provider": task.payload.get("provider", "free_search"),
            "query": task.payload.get("query", "AI business prospects"),
            "count": task.payload.get("count", 5)
        }
        res = await agent.execute_task({"action": "generate_leads", "parameters": params})
        
        # Query leads generated during this run
        leads = self.db.query(Lead).filter(
            Lead.tenant_id == self.tenant_id,
            Lead.source.like(f"%{params['query']}%")
        ).order_by(Lead.created_at.desc()).limit(params["count"]).all()
        
        leads_list = [{"id": l.id, "name": l.name, "company": l.company, "email": l.email, "score": l.score} for l in leads]
        return {
            "report": f"Successfully sourced and captured {len(leads_list)} new high-intent prospects in the Sales CRM.",
            "leads": leads_list,
            "raw_agent_output": res
        }

    async def _run_sales_outreach(self, task: WorkflowTask) -> dict:
        agent = SalesAgent(self.db, self.tenant_id)
        params = {
            "channel": task.payload.get("channel", "free_outreach"),
            "subject": task.payload.get("subject", "Partnership"),
            "body_template": task.payload.get("body_template", "Hi {name}...")
        }
        res = await agent.execute_task({"action": "sales_outreach", "parameters": params})
        return {
            "report": f"Drafted and dispatched personalized sales pitches to captured leads via {params['channel']}.",
            "raw_agent_output": res
        }

    async def _run_hr_source(self, task: WorkflowTask) -> dict:
        agent = HRAgent(self.db, self.tenant_id)
        params = {
            "role": task.payload.get("role", "SDR"),
            "requirements": task.payload.get("requirements", "Sales and outreach skills"),
            "salary": task.payload.get("salary", "$50k/year"),
            "count": task.payload.get("count", 3),
            "platforms": ["linkedin"]
        }
        res = await agent.execute_task({"action": "source_candidates", "parameters": params})
        
        from app.models.verticals import Candidate
        candidates = self.db.query(Candidate).filter(
            Candidate.tenant_id == self.tenant_id,
            Candidate.role == params["role"]
        ).order_by(Candidate.created_at.desc()).limit(params["count"]).all()
        
        cand_list = [{"id": c.id, "name": c.name, "email": c.email, "score": (c.scorecard or {}).get("match_score", 85)} for c in candidates]
        return {
            "report": f"Sourced and shortlisted {len(cand_list)} candidate profiles for the role '{params['role']}'. Detailed profiles are available in the Hiring & HR pipeline.",
            "candidates": cand_list,
            "raw_agent_output": res
        }

    async def _run_finance_budget(self, task: WorkflowTask) -> dict:
        agent = FinanceAgent(self.db, self.tenant_id)
        amount = task.payload.get("amount", 2000.0)
        res = await agent.execute_task({"action": "track_roi", "parameters": {"amount": amount}})
        return {
            "report": f"Allocated growth capital budget of ${amount:.2f} for campaign spend. ROI projection logged in Finance dashboard.",
            "allocated_budget": amount,
            "raw_agent_output": res
        }

    async def _run_ceo_summary(self, task: WorkflowTask) -> dict:
        # Gather all completed task reports in this workflow
        sibling_tasks = self.db.query(WorkflowTask).filter(
            WorkflowTask.workflow_id == task.workflow_id,
            WorkflowTask.id != task.id
        ).all()
        
        reports_summary = ""
        for sibling in sibling_tasks:
            result = sibling.result or {}
            reports_summary += f"\n### Department: {sibling.payload.get('department')} — Task: {sibling.name}\n"
            reports_summary += f"Report: {result.get('report', 'No report logged.')}\n"
            
        prompt = (
            "You are the CEO AI. Review the compiled department execution reports below and write a final executive "
            "summary of the accomplishments. Synthesize what was done (audience researched, leads found, outreach drafted, "
            "candidates sourced, and financial budget registered) and deliver a highly professional, encouraging strategic outlook. "
            f"Limit your response to 300 words.\n\nCompiled Agent Reports:\n{reports_summary}"
        )
        
        summary_report = await self.llm.complete(prompt=prompt, provider="gemini", system_prompt="You are the CEO AI giving a final project review.")
        return {"report": summary_report}

    def _get_fallback_plan(self, objective: str) -> dict:
        return {
            "analysis": "Formulating a growth pipeline targeting relevant clients, sourcing supportive recruits, and establishing financial tracking.",
            "tasks": [
                {
                    "id": "task_1",
                    "name": "Target Audience Research",
                    "department": "Marketing",
                    "description": "Establish persona profiles for ideal B2B target buyers.",
                    "task_type": "marketing_research",
                    "payload": {"topic": objective, "platforms": ["linkedin"]},
                    "depends_on": []
                },
                {
                    "id": "task_2",
                    "name": "Prospect Sourcing",
                    "department": "Sales",
                    "description": "Find prospects matching targeted tech startups.",
                    "task_type": "sales_leads",
                    "payload": {"provider": "free_search", "query": "SaaS AI startups", "count": 5},
                    "depends_on": ["task_1"]
                },
                {
                    "id": "task_3",
                    "name": "Sales Outreach Sequence",
                    "department": "Sales",
                    "description": "Draft personal connection templates for target leads.",
                    "task_type": "sales_outreach",
                    "payload": {"channel": "free_outreach", "subject": "Collaboration request", "body_template": "Hello {name}, I saw {company}..."},
                    "depends_on": ["task_2"]
                },
                {
                    "id": "task_4",
                    "name": "Recruit SDR Talent",
                    "department": "HR",
                    "description": "Source Sales Representatives to execute the outreach pipeline.",
                    "task_type": "hr_source",
                    "payload": {"role": "SDR Specialist", "requirements": "Cold calling, Lead nurture", "salary": "$50,000/year", "count": 3},
                    "depends_on": []
                },
                {
                    "id": "task_5",
                    "name": "ROI Modeling & Allocation",
                    "department": "Finance",
                    "description": "Allocate budget lines for SDR hiring and email lists.",
                    "task_type": "finance_budget",
                    "payload": {"amount": 2500.0},
                    "depends_on": ["task_4"]
                }
            ]
        }
