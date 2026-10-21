"""
Universal HR Copilot & Agent Orchestrator.
Understands multi-submodule requests, executes HR tasks in the live database,
retrieves authorized workforce context, and provides AI-powered, database-backed answers.
"""
import uuid
import logging
import re
import json
import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.hr_core import EmployeeProfile, Department, CompanyPolicy
from app.models.hr_workforce import LeaveRequest, LeaveType
from app.models.hr import JobRequisition, Application, HRWorkflowTask
from app.models.verticals import Candidate
from app.services.llm_gateway import LLMGateway
from app.services.agents.hr.schemas import (
    CopilotChatRequest,
    CopilotChatResponse,
    AutonomyLevel,
    RiskTier,
    AgentTaskResult,
    Finding,
    ProposedAction
)
from app.services.agents.hr.specialists.leave_impact import LeaveImpactSpecialist
from app.services.agents.hr.specialists.people_admin import PeopleAdminSpecialist
from app.services.agents.hr.risk_classifier import HRRiskClassifier

logger = logging.getLogger(__name__)


class HREnterpriseOrchestrator:
    """Master orchestrator for all 16 HR submodules, live database queries, and task executions."""

    def __init__(self, db: Session, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.leave_specialist = LeaveImpactSpecialist(db, tenant_id)
        self.people_admin_specialist = PeopleAdminSpecialist(db, tenant_id)
        self.llm = LLMGateway(db, tenant_id)

    def _safe_call(self, fn, default):
        """Run one read in a savepoint so a missing table does not abort the chat."""
        try:
            with self.db.begin_nested():
                return fn()
        except Exception as exc:
            logger.warning("HR copilot skipped a live read: %s", exc)
            return default

    def _get_workforce_data(self) -> Dict[str, Any]:
        """Gathers ground-truth enterprise workforce state from the database."""
        employees = self._safe_call(
            lambda: self.db.query(EmployeeProfile).filter_by(
                tenant_id=self.tenant_id
            ).order_by(EmployeeProfile.created_at.desc()).limit(100).all(),
            [],
        ) or []

        active_count = sum(1 for e in employees if e.status == "active")

        departments = self._safe_call(
            lambda: self.db.query(Department).filter_by(tenant_id=self.tenant_id).all(),
            [],
        ) or []

        open_reqs = self._safe_call(
            lambda: self.db.query(JobRequisition).filter(
                JobRequisition.tenant_id == self.tenant_id,
                JobRequisition.status.in_(["open", "draft"])
            ).all(),
            [],
        ) or []

        candidates = self._safe_call(
            lambda: self.db.query(Candidate).filter_by(
                tenant_id=self.tenant_id
            ).order_by(Candidate.created_at.desc()).limit(100).all(),
            [],
        ) or []

        total_candidates_count = self._safe_call(
            lambda: self.db.query(Candidate).filter_by(tenant_id=self.tenant_id).count(),
            len(candidates),
        )
        if total_candidates_count is None:
            total_candidates_count = len(candidates)

        candidates_by_status: Dict[str, int] = {}
        candidates_by_role: Dict[str, int] = {}
        for c in candidates:
            st = (c.status or "sourced").lower()
            candidates_by_status[st] = candidates_by_status.get(st, 0) + 1
            r = c.role or "Unassigned"
            candidates_by_role[r] = candidates_by_role.get(r, 0) + 1

        pending_leaves_records = self._safe_call(
            lambda: self.db.query(LeaveRequest).filter_by(
                tenant_id=self.tenant_id, status="pending"
            ).order_by(LeaveRequest.created_at.desc()).limit(20).all(),
            [],
        ) or []

        policies = self._safe_call(
            lambda: self.db.query(CompanyPolicy).filter_by(
                tenant_id=self.tenant_id, is_active=True
            ).all(),
            [],
        ) or []

        applications = self._safe_call(
            lambda: self.db.query(Application).filter_by(tenant_id=self.tenant_id).all(),
            [],
        ) or []
        applications_by_stage: Dict[str, int] = {}
        for app in applications:
            stage = (app.current_stage or "sourced").lower()
            applications_by_stage[stage] = applications_by_stage.get(stage, 0) + 1

        return {
            "employees": employees,
            "active_count": active_count,
            "total_count": len(employees),
            "departments": departments,
            "open_reqs": open_reqs,
            "candidates": candidates,
            "candidates_count": total_candidates_count,
            "candidates_by_status": candidates_by_status,
            "candidates_by_role": candidates_by_role,
            "pending_leaves": len(pending_leaves_records),
            "pending_leaves_records": pending_leaves_records,
            "policies": policies,
            "applications": applications,
            "applications_by_stage": applications_by_stage,
        }

    def _place_candidate_in_flow(self, candidate: Candidate, role: str) -> str:
        """Open or reuse a requisition and attach an application so the hire shows in the pipeline."""
        title = (role or "").strip() or "General Role"
        requisitions = self.db.query(JobRequisition).filter_by(tenant_id=self.tenant_id).all()
        requisition = None
        title_l = title.lower()
        for row in requisitions:
            existing_title = (row.title or "").lower()
            if existing_title and (existing_title in title_l or title_l in existing_title):
                requisition = row
                break
        if requisition is None:
            requisition = JobRequisition(
                tenant_id=self.tenant_id,
                title=title,
                headcount_approved=1,
                headcount_filled=0,
                status="open",
                opened_at=datetime.now(),
                opened_at_confirmed=True,
                recruiter_user_id=self.user_id,
            )
            self.db.add(requisition)
            self.db.flush()

        existing = self.db.query(Application).filter_by(
            tenant_id=self.tenant_id,
            candidate_id=candidate.id,
            requisition_id=requisition.id,
        ).first()
        if existing:
            return existing.id

        application = Application(
            tenant_id=self.tenant_id,
            candidate_id=candidate.id,
            requisition_id=requisition.id,
            current_stage="sourced",
            status="active",
            source="HR Copilot",
            consent_status="unknown_legacy",
        )
        self.db.add(application)
        self.db.flush()
        from app.services.hr.anchors import ensure_application_anchor
        ensure_application_anchor(self.db, self.tenant_id, application)
        return application.id

    def _sync_candidate_stage(self, candidate: Candidate, spoken_stage: str) -> str:
        """Move the hiring-flow application when the spoken stage is an allowed internal edge."""
        flow_stage = {
            "sourced": "sourced",
            "screened": "screened",
            "interviewed": "interviewing",
            "interviewing": "interviewing",
            "offered": "offer",
            "offer": "offer",
        }.get(spoken_stage)
        if not flow_stage:
            return "Hire and rejection stay on the approval path, so the application stage was not moved."

        applications = self.db.query(Application).filter_by(
            tenant_id=self.tenant_id, candidate_id=candidate.id
        ).all()
        if not applications:
            try:
                with self.db.begin_nested():
                    self._place_candidate_in_flow(candidate, candidate.role or "General Role")
            except Exception as exc:
                logger.warning("Could not open an application for stage move: %s", exc)
                return "No application is in the hiring flow yet, so only the candidate record changed."
            applications = self.db.query(Application).filter_by(
                tenant_id=self.tenant_id, candidate_id=candidate.id
            ).all()
        if not applications:
            return "No application is in the hiring flow yet, so only the candidate record changed."

        from app.models.base import User
        from app.services.hr.stage_service import StageService
        user = self.db.query(User).filter_by(id=self.user_id).first()
        role = user.role if user and user.role else "admin"
        service = StageService(self.db, self.tenant_id)
        notes: List[str] = []
        for application in applications:
            if application.current_stage == flow_stage:
                notes.append(f"application already at {flow_stage}")
                continue
            try:
                with self.db.begin_nested():
                    service.transition(application, flow_stage, self.user_id or "user", role)
                notes.append(f"hiring flow moved to {flow_stage}")
            except Exception as exc:
                detail = getattr(exc, "detail", None) or str(exc)
                notes.append(f"hiring flow stayed at {application.current_stage} ({detail})")
        return " ".join(notes)

    def _execute_pending_workflow_tasks(self) -> CopilotChatResponse:
        """Complete commanded, non-approval tasks on running HR workflow instances."""
        conv_id = f"hr-task-{uuid.uuid4().hex[:8]}"
        held_types = ("approval", "offer", "email", "send", "reject", "hire")
        tasks = self._safe_call(
            lambda: self.db.query(HRWorkflowTask).filter_by(
                tenant_id=self.tenant_id, status="pending"
            ).all(),
            None,
        )
        if tasks is None:
            return CopilotChatResponse(
                conversation_id=conv_id,
                reply="I could not read HR workflow tasks. The hiring flow tables are not available yet.",
                specialist_agent="Talent Acquisition Agent",
                autonomy_level=AutonomyLevel.L0_INFORMATIONAL,
            )
        if not tasks:
            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    "There are no pending tasks on an HR workflow instance.\n\n"
                    "You can still command work in the hiring flow:\n"
                    "- *\"Open a job requisition for Backend Engineer with 2 openings\"*\n"
                    "- *\"Add candidate Alice Smith for Backend Engineer\"*\n"
                    "- *\"Move candidate Alice Smith to screened\"*"
                ),
                specialist_agent="Talent Acquisition Agent",
                autonomy_level=AutonomyLevel.L0_INFORMATIONAL,
            )

        completed = []
        held = []
        for task in tasks:
            kind = (task.task_type or "").lower()
            if any(token in kind for token in held_types):
                held.append(task)
                continue
            task.status = "completed"
            task.completed_at = datetime.now()
            task.output_payload = {"completed_by": "hr_copilot", "user_id": self.user_id}
            completed.append(task)
        self.db.commit()

        lines = ["### HR workflow tasks"]
        if completed:
            lines.append(f"Completed **{len(completed)}** commanded task(s) inside the HR flow:")
            for task in completed[:12]:
                lines.append(f"- `{task.task_type}` on instance `{str(task.instance_id)[:8]}`")
        else:
            lines.append("No operational task was waiting.")
        if held:
            lines.append("")
            lines.append(f"**{len(held)}** task(s) still need a person. Approvals, offers, and sends stay gated:")
            for task in held[:8]:
                lines.append(f"- `{task.task_type}` remains `{task.status}`")
        return CopilotChatResponse(
            conversation_id=conv_id,
            reply="\n".join(lines),
            specialist_agent="Talent Acquisition Agent",
            autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
            task_result=AgentTaskResult(
                task_id=f"task-flow-{uuid.uuid4().hex[:6]}",
                agent_id="talent_agent",
                intent="execute_workflow_tasks",
                status="completed" if completed else "awaiting_approval",
                summary=f"Completed {len(completed)} HR workflow task(s); held {len(held)} for a person.",
                proposed_actions=[
                    ProposedAction(
                        action_type="workflow.task.complete",
                        title=f"Completed {len(completed)} HR workflow task(s)",
                        payload={"completed": len(completed), "held": len(held)},
                        risk_tier=RiskTier.R1_LOW_IMPACT,
                        requires_approval=bool(held) and not completed,
                        executed=bool(completed),
                    )
                ],
            ) if completed or held else None,
        )

    async def _execute_commanded_flow(self, text: str) -> Optional[CopilotChatResponse]:
        """Run an explicit HR-flow command that the directory task parser does not own."""
        lower = text.lower()
        conv_id = f"hr-task-{uuid.uuid4().hex[:8]}"
        if re.search(r"\b(run|execute|advance|complete)\b.{0,60}\b(workflow|hr flow|onboarding|pending tasks?)\b", lower):
            return self._execute_pending_workflow_tasks()

        action = None
        params: Dict[str, Any] = {}
        if re.search(r"\bsource\s+(?:\d+\s+)?candidates?\b", lower) or "source candidates" in lower:
            count_match = re.search(r"(\d+)\s+candidates?", lower)
            role_match = re.search(r"\bfor\s+(.+)$", text, re.IGNORECASE)
            action = "source_candidates"
            params = {
                "role": role_match.group(1).strip(" .") if role_match else "Software Engineer",
                "count": int(count_match.group(1)) if count_match else 5,
                "requirements": "General qualifications",
                "platforms": ["greenhouse", "lever"],
            }
        elif re.search(r"\b(send|start|run)\b.{0,40}\b(outreach|candidate emails?)\b", lower):
            action = "candidate_outreach"
            params = {"channel": "smtp"}
        elif re.search(r"\bschedule\b.{0,40}\binterview", lower):
            action = "schedule_interview"
            params = {"tool": "google_calendar"}
        if not action:
            return None

        from app.services.agents.hr.talent_agent import HRAgent
        try:
            result = await HRAgent(self.db, self.tenant_id).execute_task(
                {"action": action, "parameters": params}
            )
        except Exception as exc:
            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    f"I could not run **{action.replace('_', ' ')}** in the HR flow.\n\n"
                    f"{exc}\n\n"
                    "The candidate record was not changed."
                ),
                specialist_agent="Talent Acquisition Agent",
                autonomy_level=AutonomyLevel.L0_INFORMATIONAL,
            )
        status = result.get("status") if isinstance(result, dict) else "completed"
        return CopilotChatResponse(
            conversation_id=conv_id,
            reply=f"HR flow task **{action.replace('_', ' ')}** finished with status `{status}`.\n\n{json.dumps(result, default=str)[:1200]}",
            specialist_agent="Talent Acquisition Agent",
            autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
            task_result=AgentTaskResult(
                task_id=f"task-agent-{uuid.uuid4().hex[:6]}",
                agent_id="talent_agent",
                intent=action,
                status="completed" if status == "success" else "failed",
                summary=f"Ran {action} in the HR flow.",
                proposed_actions=[
                    ProposedAction(
                        action_type=f"hr.{action}",
                        title=action.replace("_", " ").title(),
                        payload=result if isinstance(result, dict) else {"result": str(result)},
                        risk_tier=RiskTier.R1_LOW_IMPACT,
                        requires_approval=False,
                        executed=status == "success",
                    )
                ],
            ),
        )

    def _retrieve_rag_context(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves genuine HR knowledge base documents and company policies."""
        rag_hits: List[Dict[str, Any]] = []

        # 1. CompanyPolicy from database (authoritative source)
        try:
            words = [w for w in re.findall(r"[a-zA-Z0-9]{3,}", query.lower()) if len(w) > 3]
            if words:
                pols = self.db.query(CompanyPolicy).filter(
                    CompanyPolicy.tenant_id == self.tenant_id,
                    CompanyPolicy.is_active.is_(True)
                ).all()
                for p in pols:
                    score = 0
                    p_text = f"{p.title} {p.category or ''} {p.summary or ''} {p.content or ''}".lower()
                    for w in words:
                        if w in p_text:
                            score += 2
                    if score > 0:
                        rag_hits.append({
                            "title": p.title,
                            "department": "HR Policy",
                            "content": (p.summary or p.content or "")[:800],
                            "score": score + 5,
                            "citation": f"Company Policy: '{p.title}' (v{p.version})"
                        })
        except Exception as pe:
            logger.debug(f"CompanyPolicy RAG notice: {pe}")

        # 2. KnowledgeRAGService - strictly filtered to HR department
        try:
            from app.services.kb_rag import KnowledgeRAGService
            kb_service = KnowledgeRAGService(self.db, self.tenant_id)
            hits = kb_service.retrieve(query, department="HR", top_k=4)
            if hits:
                for h in hits:
                    dept = (h.get("department") or "").upper()
                    title = (h.get("title") or "").lower()
                    citation = (h.get("citation") or "").lower()
                    # Filter out non-HR crawled web pages
                    if dept == "HR" or "policy" in title or "handbook" in title or "hr" in citation:
                        rag_hits.append(h)
        except Exception as e:
            logger.debug(f"KnowledgeRAGService retrieve notice: {e}")

        rag_hits.sort(key=lambda x: x.get("score", 0), reverse=True)
        return rag_hits[:4]

    def _format_workforce_context(self, data: Dict[str, Any], rag_hits: Optional[List[Dict[str, Any]]] = None) -> str:
        """Serializes live workforce state and RAG extracts into structured context for the LLM."""
        lines = [
            "=== LIVE WORKFORCE METRICS ===",
            f"- Active Employees: {data['active_count']} (Total Directory Records: {data['total_count']})",
            f"- Candidates in ATS: {data['candidates_count']}",
            f"- Active Job Requisitions: {len(data['open_reqs'])}",
            f"- Pending Leave Requests: {data['pending_leaves']}",
            f"- Departments Configured: {len(data['departments'])}",
        ]
        if data["departments"]:
            dept_strs = [f"{d.name} (Code: {d.code or 'N/A'})" for d in data["departments"]]
            lines.append(f"- Department List: {', '.join(dept_strs)}")

        if data["candidates"]:
            status_strs = [f"{st}: {cnt}" for st, cnt in data["candidates_by_status"].items()]
            lines.append(f"- Candidate Stages: {', '.join(status_strs)}")
            lines.append("\nCandidates Tracked in ATS (Live Database):")
            for c in data["candidates"][:25]:
                extra = ""
                if c.scorecard and isinstance(c.scorecard, dict):
                    m = c.scorecard.get("match_score")
                    if m is not None:
                        extra += f" | Match: {m}%"
                lines.append(f"  • {c.name} | Role: {c.role or 'N/A'} | Status: {c.status} | Email: {c.email}{extra}")

        if data["open_reqs"]:
            lines.append("\nOpen Job Requisitions (Live Database):")
            for r in data["open_reqs"][:10]:
                lines.append(f"  • {r.title} | Headcount: {r.headcount_filled}/{r.headcount_approved} | Status: {r.status}")

        if data["employees"]:
            lines.append("\nEmployee Directory (Live Database):")
            for e in data["employees"][:25]:
                dept_name = e.department_name or "General"
                lines.append(f"  • {e.full_name} | Role: {e.job_title} | Department: {dept_name} | Status: {e.status} | Email: {e.email}")

        if data.get("pending_leaves_records"):
            lines.append("\nPending Leave Requests:")
            emp_map = {e.id: e.full_name for e in data["employees"]}
            for l in data["pending_leaves_records"]:
                emp_name = emp_map.get(l.employee_id, f"Employee {l.employee_id[:6]}")
                start_str = l.start_date.strftime("%Y-%m-%d") if hasattr(l.start_date, "strftime") else str(l.start_date)
                end_str = l.end_date.strftime("%Y-%m-%d") if hasattr(l.end_date, "strftime") else str(l.end_date)
                lines.append(f"  • {emp_name} | {l.days_requested} days ({start_str} to {end_str}) | Reason: {l.reason or 'Not specified'}")

        if rag_hits:
            lines.append("\n=== RETRIEVED HR KNOWLEDGE & POLICIES (RAG) ===")
            for h in rag_hits:
                citation = h.get("citation", h.get("title", "Policy"))
                content = h.get("content", "").strip()
                lines.append(f"[{citation}]:\n{content}\n")

        return "\n".join(lines)

    # =========================================================================
    # TASK EXECUTION ENGINE: IMPLEMENTS PROMPTED HR TASKS IN THE DATABASE
    # =========================================================================

    def _execute_hr_task(self, text: str, data: Dict[str, Any]) -> Optional[CopilotChatResponse]:
        """Detects actionable HR requests and implements them directly in the database."""
        conv_id = f"hr-task-{uuid.uuid4().hex[:8]}"
        lower = text.lower().strip()

        # ---------------------------------------------------------------------
        # 1. TASK: ADD / CREATE EMPLOYEE
        # ---------------------------------------------------------------------
        is_add_emp = bool(re.search(
            r"\b(add|create|hire|register|onboard)\s+(?:a\s+|an\s+)?(?:new\s+)?employee\b",
            lower
        ))
        if is_add_emp:
            email_match = re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)
            email = email_match.group(0).lower() if email_match else None

            # Extract name
            name = None
            name_match = re.search(
                r"(?:add|create|hire|register|onboard)(?:\s+a|\s+an)?(?:\s+new)?\s+employee(?:\s+profile)?\s+(?:named\s+|called\s+)?([A-Za-z\.\'\-]+(?:\s+[A-Za-z\.\'\-]+)+)",
                text, re.IGNORECASE
            )
            if name_match:
                name = name_match.group(1).strip()
            elif email:
                user_part = email.split("@")[0].replace(".", " ").title()
                name = user_part
            else:
                name = "New Employee"

            # Clean name if trailing words got caught
            for stopword in [",", " job title", " role", " department", " dept", " email", " as a", " as an"]:
                if stopword in name.lower():
                    idx = name.lower().find(stopword)
                    name = name[:idx].strip()

            parts = name.split()
            first_name = parts[0] if parts else "Employee"
            last_name = " ".join(parts[1:]) if len(parts) > 1 else "Staff"

            if not email:
                email = f"{first_name.lower()}.{last_name.lower().replace(' ', '')}@internal.octaos.com"

            # Check if employee with this email already exists
            existing = self.db.query(EmployeeProfile).filter_by(
                tenant_id=self.tenant_id, email=email
            ).first()
            if existing:
                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=(
                        f"ℹ️ An employee with email **{existing.email}** is already registered in the system.\n\n"
                        f"- **Employee ID**: `{existing.employee_number}`\n"
                        f"- **Name**: **{existing.full_name}**\n"
                        f"- **Role**: {existing.job_title}\n"
                        f"- **Department**: {existing.department_name}\n"
                        f"- **Status**: `{existing.status}`"
                    ),
                    specialist_agent="People & Policy Administration Agent",
                    autonomy_level=AutonomyLevel.L0_INFORMATIONAL
                )

            # Extract job title
            title_match = re.search(
                r"(?:job\s+title|role|position|as\s+a|as\s+an|title)[:\s]+([^,\n\.]+?)(?:,|\bin\b|\bdept|\bdepartment|\bemail|\bphone|$)",
                text, re.IGNORECASE
            )
            job_title = title_match.group(1).strip() if title_match else None
            if not job_title:
                # Secondary title attempt: look between name and department
                after_name = text[name_match.end():] if name_match else ""
                clean_after = re.sub(r"^[,\s]+", "", after_name)
                first_clause = clean_after.split(",")[0].strip()
                if first_clause and not any(w in first_clause.lower() for w in ["department", "email", "phone"]):
                    job_title = first_clause
            if not job_title:
                job_title = "Team Member"

            # Extract department
            dept_match = re.search(
                r"(?:department|dept|team)[:\s]+([^,\n\.]+?)(?:,|\bemail|\bphone|\brole|\bstatus|$)",
                text, re.IGNORECASE
            )
            department_name = dept_match.group(1).strip() if dept_match else None
            if not department_name:
                in_dept = re.search(r"\bin\s+([A-Za-z\s]+?)\s+(?:department|dept|team)", text, re.IGNORECASE)
                department_name = in_dept.group(1).strip() if in_dept else "Engineering"

            # Resolve or create department
            dept = self.db.query(Department).filter_by(
                tenant_id=self.tenant_id, name=department_name
            ).first()
            if not dept:
                dept_code = "".join([w[0].upper() for w in department_name.split()[:4]]) or "GEN"
                dept = Department(tenant_id=self.tenant_id, name=department_name, code=dept_code)
                self.db.add(dept)
                self.db.commit()
                self.db.refresh(dept)

            # Generate next employee number
            total_emps = self.db.query(EmployeeProfile).filter_by(tenant_id=self.tenant_id).count()
            emp_number = f"EMP-{total_emps + 1:04d}"

            # Create EmployeeProfile
            new_emp = EmployeeProfile(
                tenant_id=self.tenant_id,
                employee_number=emp_number,
                first_name=first_name,
                last_name=last_name,
                email=email,
                job_title=job_title,
                department_id=dept.id,
                department_name=dept.name,
                status="active",
                employment_type="full_time",
                work_location="HQ",
                hire_date=datetime.now()
            )
            self.db.add(new_emp)
            self.db.commit()
            self.db.refresh(new_emp)

            action = ProposedAction(
                action_type="employee.create",
                title=f"Created Employee: {new_emp.full_name}",
                resource_id=new_emp.id,
                payload={
                    "employee_id": new_emp.id,
                    "employee_number": new_emp.employee_number,
                    "name": new_emp.full_name,
                    "job_title": new_emp.job_title,
                    "department": new_emp.department_name,
                    "email": new_emp.email
                },
                risk_tier=RiskTier.R1_LOW_IMPACT,
                requires_approval=False,
                executed=True
            )

            task_res = AgentTaskResult(
                task_id=f"task-emp-{uuid.uuid4().hex[:6]}",
                agent_id="people_admin_agent",
                intent="create_employee",
                status="completed",
                summary=f"Successfully added employee {new_emp.full_name} ({new_emp.job_title}) to {new_emp.department_name}.",
                findings=[Finding(severity="info", code="EMPLOYEE_CREATED", message=f"Employee profile {new_emp.employee_number} committed to live directory.")],
                proposed_actions=[action]
            )

            reply = (
                f"✅ **Employee Created Successfully in Live Database**\n\n"
                f"- **Employee ID**: `{new_emp.employee_number}`\n"
                f"- **Full Name**: **{new_emp.full_name}**\n"
                f"- **Job Title**: {new_emp.job_title}\n"
                f"- **Department**: {new_emp.department_name}\n"
                f"- **Email**: `{new_emp.email}`\n"
                f"- **Status**: `{new_emp.status}`\n"
                f"- **Hire Date**: {new_emp.hire_date.strftime('%Y-%m-%d')}\n\n"
                f"The People Directory and Org Chart have been updated live."
            )

            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=reply,
                specialist_agent="People & Policy Administration Agent",
                autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
                task_result=task_res
            )

        # ---------------------------------------------------------------------
        # 2. TASK: UPDATE EMPLOYEE PROFILE
        # ---------------------------------------------------------------------
        is_update_emp = bool(re.search(
            r"\b(update|change|edit|promote|set)\s+(?:the\s+)?(?:employee|job\s+title|role|department|status)\b",
            lower
        ))
        if is_update_emp:
            # Find employee in database
            target_emp = None
            for e in data["employees"]:
                if e.full_name.lower() in lower or e.email.lower() in lower or e.first_name.lower() in lower:
                    target_emp = e
                    break

            if target_emp:
                updated_fields = []
                # Check for job title update
                title_match = re.search(r"(?:title|role|position)\s+(?:to|as)\s+([^,\n\.]+)", text, re.IGNORECASE)
                if title_match:
                    new_title = title_match.group(1).strip()
                    target_emp.job_title = new_title
                    updated_fields.append(f"Job Title -> **{new_title}**")

                # Check for department update
                dept_match = re.search(r"department\s+(?:to|as)\s+([^,\n\.]+)", text, re.IGNORECASE)
                if dept_match:
                    new_dept = dept_match.group(1).strip()
                    target_emp.department_name = new_dept
                    updated_fields.append(f"Department -> **{new_dept}**")

                # Check for status update
                status_match = re.search(r"status\s+(?:to|as)\s+(active|on_leave|probation|terminated|inactive)", lower)
                if status_match:
                    new_status = status_match.group(1).strip()
                    target_emp.status = new_status
                    updated_fields.append(f"Status -> `{new_status}`")

                if updated_fields:
                    self.db.commit()
                    self.db.refresh(target_emp)

                    action = ProposedAction(
                        action_type="employee.update",
                        title=f"Updated Profile: {target_emp.full_name}",
                        resource_id=target_emp.id,
                        payload={"employee_id": target_emp.id, "updates": updated_fields},
                        risk_tier=RiskTier.R1_LOW_IMPACT,
                        requires_approval=False,
                        executed=True
                    )

                    return CopilotChatResponse(
                        conversation_id=conv_id,
                        reply=(
                            f"✅ **Employee Profile Updated Successfully**\n\n"
                            f"- **Employee**: **{target_emp.full_name}** (`{target_emp.employee_number}`)\n"
                            f"- **Applied Updates**:\n  • " + "\n  • ".join(updated_fields) + "\n\n"
                            f"Live directory changes have been persisted."
                        ),
                        specialist_agent="People & Policy Administration Agent",
                        autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
                        task_result=AgentTaskResult(
                            task_id=f"task-update-{uuid.uuid4().hex[:6]}",
                            agent_id="people_admin_agent",
                            intent="update_employee",
                            status="completed",
                            summary=f"Updated profile for {target_emp.full_name}.",
                            proposed_actions=[action]
                        )
                    )

        # ---------------------------------------------------------------------
        # 3. TASK: CREATE / OPEN JOB REQUISITION
        # ---------------------------------------------------------------------
        is_create_req = bool(re.search(
            r"\b(create|open|post|add)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:job\s+requisition|job\s+opening|requisition|position|opening|vacancy)\b",
            lower
        ))
        if is_create_req:
            # Extract title
            req_match = re.search(
                r"(?:create|open|post|add)(?:\s+a|\s+an)?(?:\s+new)?\s+(?:job\s+requisition|job\s+opening|position|requisition|vacancy|opening)\s+(?:for\s+)?([^,\n\.]+)",
                text, re.IGNORECASE
            )
            title = req_match.group(1).strip() if req_match else "Software Engineer"
            for stop in [" with ", " headcount", " openings", " status", " in "]:
                if stop in title.lower():
                    title = title[:title.lower().find(stop)].strip()

            # Extract headcount
            hc_match = re.search(r"(?:headcount|openings|positions|spots)[:\s]+(\d+)", text, re.IGNORECASE)
            if not hc_match:
                hc_match = re.search(r"(\d+)\s+(?:openings|headcount|spots|positions)", text, re.IGNORECASE)
            headcount = int(hc_match.group(1)) if hc_match else 1

            new_req = JobRequisition(
                tenant_id=self.tenant_id,
                title=title,
                headcount_approved=headcount,
                headcount_filled=0,
                status="open",
                opened_at=datetime.now(),
                opened_at_confirmed=True
            )
            self.db.add(new_req)
            self.db.commit()
            self.db.refresh(new_req)

            action = ProposedAction(
                action_type="requisition.create",
                title=f"Opened Requisition: {new_req.title}",
                resource_id=new_req.id,
                payload={"requisition_id": new_req.id, "title": new_req.title, "headcount": new_req.headcount_approved},
                risk_tier=RiskTier.R1_LOW_IMPACT,
                requires_approval=False,
                executed=True
            )

            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    f"✅ **Job Requisition Opened Successfully**\n\n"
                    f"- **Position Title**: **{new_req.title}**\n"
                    f"- **Requisition ID**: `{new_req.id[:8]}`\n"
                    f"- **Approved Headcount**: `{new_req.headcount_approved}` position(s)\n"
                    f"- **Status**: `{new_req.status.upper()}`\n"
                    f"- **Opened At**: {new_req.opened_at.strftime('%Y-%m-%d')}\n\n"
                    f"This requisition is now live in ATS and ready for candidate sourcing."
                ),
                specialist_agent="Talent Acquisition Agent",
                autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
                task_result=AgentTaskResult(
                    task_id=f"task-req-{uuid.uuid4().hex[:6]}",
                    agent_id="talent_agent",
                    intent="create_job_requisition",
                    status="completed",
                    summary=f"Opened job requisition {new_req.title} with {new_req.headcount_approved} headcounts.",
                    proposed_actions=[action]
                )
            )

        # ---------------------------------------------------------------------
        # 4. TASK: CLOSE / UPDATE JOB REQUISITION STATUS
        # ---------------------------------------------------------------------
        is_close_req = bool(re.search(
            r"\b(close|fill|cancel)\s+(?:the\s+)?(?:job\s+requisition|job\s+opening|requisition|position|opening)\b",
            lower
        ))
        if is_close_req:
            target_req = None
            for r in data["open_reqs"]:
                if r.title.lower() in lower:
                    target_req = r
                    break
            if not target_req and data["open_reqs"]:
                target_req = data["open_reqs"][0]

            if target_req:
                target_req.status = "closed"
                self.db.commit()
                self.db.refresh(target_req)

                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=(
                        f"✅ **Job Requisition Closed Successfully**\n\n"
                        f"- **Title**: **{target_req.title}** (`{target_req.id[:8]}`)\n"
                        f"- **Status**: `CLOSED`\n"
                        f"- **Final Headcount Filled**: `{target_req.headcount_filled}/{target_req.headcount_approved}`\n\n"
                        f"The position has been removed from active recruitment pipelines."
                    ),
                    specialist_agent="Talent Acquisition Agent",
                    autonomy_level=AutonomyLevel.L1_SUGGESTIVE
                )

        # ---------------------------------------------------------------------
        # 5. TASK: ADD / CREATE CANDIDATE IN ATS
        # ---------------------------------------------------------------------
        is_add_cand = bool(re.search(
            r"\b(add|create|source|register)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:candidate|applicant)\b",
            lower
        ))
        if is_add_cand:
            email_match = re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)
            email = email_match.group(0).lower() if email_match else None

            cand_match = re.search(
                r"(?:add|create|source|register)(?:\s+a|\s+an)?(?:\s+new)?\s+(?:candidate|applicant)\s+(?:named\s+|called\s+)?([A-Za-z\.\'\-]+(?:\s+[A-Za-z\.\'\-]+)+)",
                text, re.IGNORECASE
            )
            cand_name = cand_match.group(1).strip() if cand_match else "Candidate"
            for stop in [",", " for ", " role", " email"]:
                if stop in cand_name.lower():
                    cand_name = cand_name[:cand_name.lower().find(stop)].strip()

            if not email:
                email = f"{cand_name.lower().replace(' ', '.')}@candidates.internal"

            role_match = re.search(r"(?:for|role|position)[:\s]+([^,\n\.]+?)(?:,|\bemail|\bphone|$)", text, re.IGNORECASE)
            role = role_match.group(1).strip() if role_match else "General Role"

            new_cand = Candidate(
                tenant_id=self.tenant_id,
                name=cand_name,
                email=email,
                role=role,
                status="sourced",
                scorecard={"match_score": 85, "summary": "Added via HR Copilot command"}
            )
            self.db.add(new_cand)
            self.db.flush()
            flow_note = ""
            try:
                with self.db.begin_nested():
                    application_id = self._place_candidate_in_flow(new_cand, role)
                flow_note = f"\n\nThe candidate is in the hiring flow (application `{str(application_id)[:8]}`)."
            except Exception as exc:
                logger.warning("Could not open a hiring-flow application: %s", exc)
                flow_note = "\n\nThe candidate was saved. A hiring-flow application could not be opened."
            self.db.commit()
            self.db.refresh(new_cand)

            action = ProposedAction(
                action_type="candidate.create",
                title=f"Added Candidate: {new_cand.name}",
                resource_id=new_cand.id,
                payload={"candidate_id": new_cand.id, "name": new_cand.name, "role": new_cand.role, "email": new_cand.email},
                risk_tier=RiskTier.R1_LOW_IMPACT,
                requires_approval=False,
                executed=True
            )

            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    f"✅ **Candidate Added to Talent Pipeline (ATS)**\n\n"
                    f"- **Candidate Name**: **{new_cand.name}**\n"
                    f"- **Target Role**: {new_cand.role}\n"
                    f"- **Email**: `{new_cand.email}`\n"
                    f"- **Initial Stage**: `SOURCED`\n"
                    f"- **Match Score**: `85%`\n\n"
                    f"Candidate record is live in the ATS talent pipeline."
                    f"{flow_note}"
                ),
                specialist_agent="Talent Acquisition Agent",
                autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
                task_result=AgentTaskResult(
                    task_id=f"task-cand-{uuid.uuid4().hex[:6]}",
                    agent_id="talent_agent",
                    intent="create_candidate",
                    status="completed",
                    summary=f"Added candidate {new_cand.name} for role {new_cand.role}.",
                    proposed_actions=[action]
                )
            )

        # ---------------------------------------------------------------------
        # 6. TASK: UPDATE CANDIDATE STAGE (MOVE CANDIDATE)
        # ---------------------------------------------------------------------
        is_move_cand = bool(re.search(
            r"\b(move|update|advance)\s+candidate\b",
            lower
        ))
        if is_move_cand:
            target_cand = None
            for c in data["candidates"]:
                cand_name = (c.name or "").lower()
                if cand_name and (cand_name in lower or any(part in lower for part in cand_name.split() if len(part) > 2)):
                    target_cand = c
                    break

            stage = None
            for st in ["screened", "interviewed", "offered", "hired", "rejected", "sourced"]:
                if st in lower:
                    stage = st
                    break

            if target_cand and stage:
                target_cand.status = stage
                flow_note = ""
                try:
                    with self.db.begin_nested():
                        flow_note = self._sync_candidate_stage(target_cand, stage)
                except Exception as exc:
                    logger.warning("Hiring flow stage sync skipped: %s", exc)
                    flow_note = "The candidate record was updated. The hiring-flow application was left unchanged."
                self.db.commit()
                self.db.refresh(target_cand)

                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=(
                        f"✅ **Candidate Stage Updated**\n\n"
                        f"- **Candidate**: **{target_cand.name}**\n"
                        f"- **Role**: {target_cand.role}\n"
                        f"- **New Stage**: `{stage.upper()}`\n\n"
                        f"Talent ATS pipeline has been updated. {flow_note}"
                    ),
                    specialist_agent="Talent Acquisition Agent",
                    autonomy_level=AutonomyLevel.L1_SUGGESTIVE
                )

        # ---------------------------------------------------------------------
        # 7. TASK: SUBMIT / CREATE LEAVE REQUEST
        # ---------------------------------------------------------------------
        is_submit_leave = bool(re.search(
            r"\b(submit|request|apply|take|create)\s+(?:a\s+)?leave\b",
            lower
        ))
        if is_submit_leave:
            target_emp = None
            for e in data["employees"]:
                if e.full_name.lower() in lower or e.first_name.lower() in lower:
                    target_emp = e
                    break
            if not target_emp and data["employees"]:
                target_emp = data["employees"][0]

            if target_emp:
                days_match = re.search(r"(\d+(?:\.\d+)?)\s+days?", lower)
                days = float(days_match.group(1)) if days_match else 2.0

                start = datetime.now() + timedelta(days=7)
                end = start + timedelta(days=int(days) - 1)

                reason_match = re.search(r"(?:for|reason)[:\s]+([^,\n\.]+)", text, re.IGNORECASE)
                reason = reason_match.group(1).strip() if reason_match else "Annual Personal Leave"

                # Resolve LeaveType
                ltype = self.db.query(LeaveType).filter_by(tenant_id=self.tenant_id, code="ANNUAL").first()
                if not ltype:
                    ltype = LeaveType(tenant_id=self.tenant_id, name="Annual Leave", code="ANNUAL", annual_allowance_days=20.0)
                    self.db.add(ltype)
                    self.db.commit()
                    self.db.refresh(ltype)

                # Coverage Evaluation
                impact = self.leave_specialist.evaluate_leave_request(
                    employee_id=target_emp.id,
                    leave_type_code="ANNUAL",
                    start_date=start,
                    end_date=end,
                    days_requested=days
                )

                new_leave = LeaveRequest(
                    tenant_id=self.tenant_id,
                    employee_id=target_emp.id,
                    leave_type_id=ltype.id,
                    start_date=start,
                    end_date=end,
                    days_requested=days,
                    reason=reason,
                    status="pending",
                    coverage_score=impact.coverage_score,
                    conflict_count=impact.conflicting_leaves_count,
                    ai_risk_level=impact.risk_tier.value.lower(),
                    ai_coverage_notes=impact.explanation
                )
                self.db.add(new_leave)
                self.db.commit()
                self.db.refresh(new_leave)

                action = ProposedAction(
                    action_type="leave.submit",
                    title=f"Submitted Leave for {target_emp.full_name}",
                    resource_id=new_leave.id,
                    payload={"leave_id": new_leave.id, "employee": target_emp.full_name, "days": days},
                    risk_tier=RiskTier.R1_LOW_IMPACT,
                    requires_approval=True,
                    executed=True
                )

                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=(
                        f"✅ **Leave Request Submitted for Review**\n\n"
                        f"- **Employee**: **{target_emp.full_name}**\n"
                        f"- **Duration**: `{days} day(s)` ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')})\n"
                        f"- **Reason**: {reason}\n"
                        f"- **Team Coverage Score**: `{int(impact.coverage_score * 100)}%`\n"
                        f"- **Status**: `PENDING APPROVAL`\n\n"
                        f"The request is now pending in the manager approval queue."
                    ),
                    specialist_agent="Leave & Workforce Impact Agent",
                    autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
                    task_result=AgentTaskResult(
                        task_id=f"task-leave-{uuid.uuid4().hex[:6]}",
                        agent_id="leave_impact_agent",
                        intent="submit_leave",
                        status="completed",
                        summary=f"Submitted {days} days leave for {target_emp.full_name}.",
                        proposed_actions=[action]
                    )
                )

        # ---------------------------------------------------------------------
        # 8. TASK: APPROVE / REJECT LEAVE REQUEST
        # ---------------------------------------------------------------------
        is_leave_decision = bool(re.search(
            r"\b(approve|accept|grant|reject|deny)\s+(?:pending\s+)?leave\b",
            lower
        ))
        if is_leave_decision:
            is_approve = "reject" not in lower and "deny" not in lower
            status_target = "approved" if is_approve else "rejected"

            target_req = None
            pending_leaves = data.get("pending_leaves_records", [])
            for pl in pending_leaves:
                emp_name = next((e.full_name.lower() for e in data["employees"] if e.id == pl.employee_id), "")
                if emp_name and (emp_name in lower or pl.id in lower):
                    target_req = pl
                    break
            if not target_req and pending_leaves:
                target_req = pending_leaves[0]

            if target_req:
                target_req.status = status_target
                target_req.approver_user_id = self.user_id
                target_req.approved_at = datetime.now()
                if not is_approve:
                    target_req.rejection_reason = "Rejected from Ask HR"
                self.db.commit()
                self.db.refresh(target_req)

                emp_name = next((e.full_name for e in data["employees"] if e.id == target_req.employee_id), "Employee")

                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=(
                        f"✅ **Leave Request {status_target.capitalize()}**\n\n"
                        f"- **Employee**: **{emp_name}**\n"
                        f"- **Days**: `{target_req.days_requested} day(s)`\n"
                        f"- **Status**: `{status_target.upper()}`\n\n"
                        f"Leave ledger and workforce availability have been updated live."
                    ),
                    specialist_agent="Leave & Workforce Impact Agent",
                    autonomy_level=AutonomyLevel.L1_SUGGESTIVE
                )

        # ---------------------------------------------------------------------
        # 9. TASK: CREATE DEPARTMENT
        # ---------------------------------------------------------------------
        is_create_dept = bool(re.search(
            r"\b(create|add|new)\s+(?:department|team)\b",
            lower
        ))
        if is_create_dept:
            dept_match = re.search(r"(?:create|add|new)\s+(?:department|team)\s+([A-Za-z\s]+)", text, re.IGNORECASE)
            dept_name = dept_match.group(1).strip() if dept_match else "Operations"
            for stop in [" with ", " code"]:
                if stop in dept_name.lower():
                    dept_name = dept_name[:dept_name.lower().find(stop)].strip()

            code_match = re.search(r"(?:code)[:\s]+([A-Za-z0-9]+)", text, re.IGNORECASE)
            dept_code = code_match.group(1).upper() if code_match else "".join([w[0].upper() for w in dept_name.split()[:4]]) or "DEPT"

            existing_dept = self.db.query(Department).filter_by(tenant_id=self.tenant_id, name=dept_name).first()
            if existing_dept:
                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=f"ℹ️ Department **{dept_name}** (Code: `{existing_dept.code}`) already exists.",
                    specialist_agent="People & Policy Administration Agent",
                    autonomy_level=AutonomyLevel.L0_INFORMATIONAL
                )

            new_dept = Department(tenant_id=self.tenant_id, name=dept_name, code=dept_code)
            self.db.add(new_dept)
            self.db.commit()
            self.db.refresh(new_dept)

            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    f"✅ **Department Created Successfully**\n\n"
                    f"- **Department Name**: **{new_dept.name}**\n"
                    f"- **Code**: `{new_dept.code}`\n\n"
                    f"Department is now available for employee placements and org charting."
                ),
                specialist_agent="People & Policy Administration Agent",
                autonomy_level=AutonomyLevel.L1_SUGGESTIVE
            )

        # ---------------------------------------------------------------------
        # 10. TASK: CREATE / ADD COMPANY POLICY
        # ---------------------------------------------------------------------
        is_create_policy = bool(re.search(
            r"\b(create|add|publish|draft)\s+(?:company\s+)?policy\b",
            lower
        ))
        if is_create_policy:
            pol_match = re.search(r"(?:create|add|publish|draft)\s+(?:company\s+)?policy\s+(?:on\s+|for\s+|named\s+)?([^:\n]+)(?::\s*(.+))?", text, re.IGNORECASE)
            title = pol_match.group(1).strip() if pol_match else "Company Policy"
            content = pol_match.group(2).strip() if pol_match and pol_match.group(2) else "Standard workplace guidelines and principles."

            new_pol = CompanyPolicy(
                tenant_id=self.tenant_id,
                title=title,
                category="general",
                summary=content[:200],
                content=content,
                version=1,
                is_active=True
            )
            self.db.add(new_pol)
            self.db.commit()
            self.db.refresh(new_pol)

            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    f"✅ **Company Policy Published to Live Knowledge Base**\n\n"
                    f"- **Policy Title**: **{new_pol.title}** (v{new_pol.version})\n"
                    f"- **Category**: `{new_pol.category}`\n"
                    f"- **Summary**: {new_pol.summary}\n\n"
                    f"This policy is now indexed and available for employee inquiries across the company."
                ),
                specialist_agent="People & Policy Administration Agent",
                autonomy_level=AutonomyLevel.L1_SUGGESTIVE
            )

        return None

    # =========================================================================
    # DETERMINISTIC DATABASE-GROUNDED RESPONSES (FOR QUESTIONS & INQUIRIES)
    # =========================================================================

    def _format_analytics(self, lower: str, data: Dict[str, Any]) -> Optional[str]:
        """Answer hiring-analytics questions from stored rows. Missing inputs stay insufficient."""
        hints = (
            "analytics", "time to fill", "time-to-fill", "source quality",
            "cost per hire", "cost-per-hire", "plan vs actual", "workload",
            "completion rate", "hiring metric", "recruiting metric",
            "pipeline health", "funnel",
        )
        if not any(hint in lower for hint in hints):
            return None

        from app.services.hr.analytics import RecruitmentAnalytics
        catalogue = [
            ("time_to_fill", ("time to fill", "time-to-fill")),
            ("source_quality", ("source quality",)),
            ("workload", ("workload",)),
            ("plan_vs_actual", ("plan vs actual", "headcount plan")),
            ("workflow_completion_rate", ("completion rate", "workflow")),
            ("cost_per_hire", ("cost per hire", "cost-per-hire")),
        ]
        selected = [name for name, keys in catalogue if any(key in lower for key in keys)]
        if not selected or "analytics" in lower or "funnel" in lower or "pipeline health" in lower:
            selected = [name for name, _keys in catalogue]

        analytics = RecruitmentAnalytics(self.db, self.tenant_id)
        lines = [
            "### Hiring analytics",
            "",
            "These figures come from stored recruitment records. Missing inputs stay insufficient. They are not estimated.",
            "",
        ]
        for name in selected:
            try:
                with self.db.begin_nested():
                    row = analytics.metric(name)
            except Exception as exc:
                logger.warning("Analytics metric %s failed: %s", name, exc)
                row = {"status": "insufficient_data", "value": None, "unit": "", "sample_size": 0, "missing": ["metric_read"]}
            label = name.replace("_", " ")
            if row.get("status") != "ok":
                missing = ", ".join(row.get("missing") or []) or "stored inputs"
                lines.append(f"- **{label}**: insufficient data (needs {missing})")
            else:
                lines.append(
                    f"- **{label}**: `{row.get('value')}` {row.get('unit') or ''} "
                    f"(sample {row.get('sample_size', 0)})"
                )

        stage_counts = data.get("applications_by_stage") or {}
        if stage_counts:
            stage_bits = ", ".join(f"{stage}: {count}" for stage, count in stage_counts.items())
            lines.append(f"- **applications by stage**: {stage_bits}")
        lines.append("")
        lines.append(
            f"Live snapshot: **{data['active_count']} active employee(s)**, "
            f"**{data['candidates_count']} candidates**, "
            f"**{len(data['open_reqs'])} open requisitions**, "
            f"**{data['pending_leaves']} pending leave requests**."
        )
        return "\n".join(lines)

    def _generate_fallback_response(
        self,
        text: str,
        data: Dict[str, Any],
        rag_hits: Optional[List[Dict[str, Any]]] = None,
        specific_only: bool = False,
    ) -> Optional[str]:
        """Deterministic response powered by real database records and authorized RAG retrieval."""
        lower = text.lower()
        analytics_reply = self._format_analytics(lower, data)
        if analytics_reply:
            return analytics_reply
        active = data["active_count"]
        total = data["total_count"]
        depts = data["departments"]
        cands = data["candidates"]
        cand_count = data["candidates_count"]
        open_reqs = data["open_reqs"]
        pending_leaves = data["pending_leaves"]
        pending_leaves_records = data.get("pending_leaves_records", [])

        # 1. Candidate & Talent Pipeline Queries
        is_candidate_query = (
            any(w in lower for w in [
                "candidate", "candidates", "cancdiate", "cancdiates", "candidat",
                "applicant", "applicants", "who applied", "talent pipeline"
            ])
            or ("pipeline" in lower and any(w in lower for w in ["talent", "recruitment", "hiring", "ats", "job"]))
            or (any(w in lower for w in ["how many", "count", "number of", "list", "show"]) and any(w in lower for w in ["interviewed", "screened", "sourced", "hired"]))
        )
        if is_candidate_query:
            if cand_count == 0:
                return (
                    "### 🎯 Talent Pipeline & Candidates\n\n"
                    "There are currently **0 candidates** tracked in your ATS pipeline.\n\n"
                    f"- **Active Job Requisitions**: `{len(open_reqs)}` open positions\n\n"
                    "**Next Steps**:\n"
                    "- Ask me: *\"Add candidate John Doe for Software Engineer, email john@example.com\"*\n"
                    "- Go to the **Hiring (ATS)** tab to upload resumes or source talent."
                )

            resp = (
                f"### 🎯 Talent Pipeline & Candidates\n\n"
                f"There are currently **{cand_count} candidate(s)** tracked in your organization's ATS pipeline.\n\n"
            )
            if data["candidates_by_status"]:
                stage_parts = [f"**{st.capitalize()}**: `{cnt}`" for st, cnt in data["candidates_by_status"].items()]
                resp += f"**Stage Breakdown**: {' · '.join(stage_parts)}\n\n"

            if data["candidates_by_role"]:
                role_parts = [f"• {r}: {cnt}" for r, cnt in list(data["candidates_by_role"].items())[:5]]
                resp += "**By Target Role**:\n" + "\n".join(role_parts) + "\n\n"

            resp += "**Tracked Candidates**:\n"
            for c in cands[:8]:
                score_tag = ""
                if c.scorecard and isinstance(c.scorecard, dict):
                    m = c.scorecard.get("match_score")
                    if m is not None:
                        score_tag = f" — Match: `{m}%`"
                role_str = f" for **{c.role}**" if c.role else ""
                resp += f"- **{c.name}**{role_str} (Status: `{c.status}`{score_tag})\n  _Email_: {c.email}\n"

            if len(cands) > 8:
                resp += f"\n_...and {cand_count - 8} more candidates tracked in the Hiring tab._"
            return resp

        # 2. Specific Employee Lookup Query ("who is John", "lookup employee", etc.)
        if any(lower.startswith(prefix) or f" {prefix}" in lower for prefix in ["who is ", "lookup ", "find employee ", "search employee ", "details for "]):
            search_term = re.sub(r"^(who is|lookup|find employee|search employee|details for)\s+", "", lower).strip().strip("?")
            if search_term and data["employees"]:
                matches = [
                    e for e in data["employees"]
                    if search_term in e.full_name.lower() or search_term in e.email.lower() or search_term in (e.job_title or "").lower()
                ]
                if matches:
                    e = matches[0]
                    dept = e.department_name or "General"
                    return (
                        f"### 👤 Employee Profile: **{e.full_name}**\n\n"
                        f"- **Employee ID**: `{e.employee_number}`\n"
                        f"- **Job Title**: {e.job_title}\n"
                        f"- **Department**: {dept}\n"
                        f"- **Status**: `{e.status}`\n"
                        f"- **Email**: {e.email}\n"
                        f"- **Location**: {e.work_location or 'HQ'}\n"
                        f"- **Employment Type**: `{e.employment_type}`\n"
                        f"- **Hire Date**: {e.hire_date.strftime('%Y-%m-%d') if e.hire_date else 'N/A'}"
                    )

        # 3. Employee Headcount & Directory Queries
        is_employee_query = (
            any(w in lower for w in ["how many", "count", "headcount", "number of", "list", "directory", "who works", "team member", "employees", "people", "staff"])
            and any(w in lower for w in ["employee", "employees", "people", "staff", "worker", "workers", "emplyee", "team", "who works"])
        )
        if is_employee_query:
            resp = (
                f"### 👥 Workforce Headcount\n\n"
                f"There are currently **{active} active employees** ({total} total directory profiles) in your organization.\n\n"
            )
            if depts:
                resp += f"- **Configured Departments**: `{len(depts)}`\n"
            if data["employees"]:
                resp += "\n**Current Team Directory**:\n"
                for e in data["employees"][:10]:
                    dept = e.department_name or "General"
                    resp += f"- **{e.full_name}** (`{e.employee_number}`) — {e.job_title} ({dept}, `{e.status}`)\n  _Email_: {e.email}\n"
            return resp

        # 4. Open Job Requisitions / Roles Queries
        is_requisition_query = any(phrase in lower for phrase in [
            "open position", "open positions", "active requisitions", "recruitment status",
            "open roles", "open job", "open jobs", "job openings", "hiring for", "requisitions"
        ])
        if is_requisition_query:
            if not open_reqs:
                return (
                    "### 💼 Job Requisitions\n\n"
                    "No active job requisitions currently open.\n\n"
                    "**Next Steps**:\n"
                    "- Ask me: *\"Create job requisition for Senior Backend Engineer with 2 openings\"*\n"
                    "- Or create requisitions in **Hiring -> Recruitment**."
                )
            resp = (
                f"### 💼 Open Job Requisitions\n\n"
                f"Your organization has **{len(open_reqs)} open position(s)** in the database:\n\n"
            )
            for r in open_reqs[:8]:
                resp += f"- **{r.title}** (`{r.id[:8]}`) — Headcount: `{r.headcount_filled}/{r.headcount_approved}` filled, Status: `{r.status}`\n"
            return resp

        # 5. Leave & Time Off Queries
        is_leave_query = any(w in lower for w in ["leave", "leaves", "time off", "vacation", "pto", "holiday", "absent", "absence"])
        if is_leave_query:
            if pending_leaves == 0:
                return (
                    "### 🏖️ Leave & Attendance Status\n\n"
                    "There are currently **0 pending leave requests** requiring approval.\n\n"
                    "All employee leave balances are up to date.\n"
                    "To submit a leave, ask me: *\"Submit leave for [Employee] for [N] days for [Reason]\"*."
                )
            resp = (
                f"### 🏖️ Pending Leave Requests\n\n"
                f"There are **{pending_leaves} pending leave request(s)** in the database:\n\n"
            )
            emp_map = {e.id: e.full_name for e in data["employees"]}
            for l in pending_leaves_records[:6]:
                emp_name = emp_map.get(l.employee_id, f"Employee {l.employee_id[:6]}")
                start_str = l.start_date.strftime("%Y-%m-%d") if hasattr(l.start_date, "strftime") else str(l.start_date)
                end_str = l.end_date.strftime("%Y-%m-%d") if hasattr(l.end_date, "strftime") else str(l.end_date)
                resp += f"- **{emp_name}**: `{l.days_requested} days` ({start_str} to {end_str}) — _Reason_: {l.reason or 'Personal'}\n"
            return resp

        # 6. Department queries
        if any(w in lower for w in ["department", "departments", "teams"]):
            if depts:
                dept_list = "\n".join([f"- **{d.name}** (Code: `{d.code or 'N/A'}`)" for d in depts])
                return f"### 🏢 Departments\n\nYour organization has **{len(depts)} department(s)** configured in the database:\n\n{dept_list}"
            return "No dedicated departments configured yet. You can ask me: *\"Create department Marketing with code MKT\"*."

        # 7. Policy Queries (ONLY if explicitly asked about policy or handbook)
        if any(w in lower for w in ["policy", "handbook", "guideline", "rule", "benefits", "remote work", "wfh", "overtime", "probation"]):
            if rag_hits:
                resp = "### 📖 Grounded Company Policy\n\n"
                for h in rag_hits[:3]:
                    cit = h.get("citation", h.get("title", "Policy"))
                    cont = h.get("content", "").strip()
                    resp += f"**{cit}**:\n{cont}\n\n"
                return resp
            return (
                "### 📖 Company Policy\n\n"
                "No official company policy document currently matches your inquiry.\n\n"
                "To add a policy to the company knowledge base, ask me:\n"
                "- *\"Add company policy on Remote Work: Employees can work remotely up to 3 days per week.\"*"
            )

        # 8. Greetings. Match whole words so "hiring" and "this" are not greetings.
        if re.search(r"\b(hi|hello|hey|hwq|greetings)\b", lower) or "good morning" in lower or "good afternoon" in lower:
            return (
                f"Hello! I am your **Universal HR Copilot**.\n\n"
                f"I am connected to your live workforce database with **{active} active employee(s)**, "
                f"**{cand_count} candidates in ATS**, and **{len(open_reqs)} open job requisitions**.\n\n"
                f"You can ask me questions about your workforce or prompt me to perform tasks:\n"
                f"- *\"Add employee Jane Smith, Product Manager, email jane@example.com\"*\n"
                f"- *\"Open job requisition for Senior Frontend Engineer, 2 openings\"*\n"
                f"- *\"Add candidate David Clark for Backend Engineer\"*\n"
                f"- *\"Submit leave for Jane Smith for 3 days\"*\n"
                f"- *\"How many employees are there?\"*"
            )

        if specific_only:
            return None

        # 9. Dynamic Live Overview
        return (
            f"### 🤖 Universal HR Copilot (Live Workforce AI)\n\n"
            f"- **Active Employees**: `{active}` ({total} in directory)\n"
            f"- **Candidates in ATS**: `{cand_count}`\n"
            f"- **Open Job Requisitions**: `{len(open_reqs)}`\n"
            f"- **Pending Leaves**: `{pending_leaves}`\n"
            f"- **Departments**: `{len(depts)}`\n\n"
            f"**Try asking me to perform any task or query**:\n"
            f"- *\"Add an employee named Jane Smith, Product Manager, email jane@example.com\"*\n"
            f"- *\"Open position for Senior DevOps Engineer\"*\n"
            f"- *\"How many candidates are in the pipeline?\"*\n"
            f"- *\"Show me all pending leave requests\"*\n"
            f"- *\"Who works in Engineering?\"*"
        )

    # =========================================================================
    # PRIMARY MESSAGE ENTRYPOINT
    # =========================================================================

    async def handle_message(self, request: CopilotChatRequest) -> CopilotChatResponse:
        try:
            return await self._handle_message(request)
        except Exception as exc:
            logger.exception("Ask HR failed: %s", exc)
            try:
                self.db.rollback()
            except Exception:
                logger.warning("Ask HR rollback failed", exc_info=True)
            return CopilotChatResponse(
                conversation_id=f"hr-conv-{uuid.uuid4().hex[:8]}",
                reply=(
                    "Ask HR could not finish that request. "
                    "Ask for hiring analytics, headcount, or the talent pipeline, "
                    "or command a task such as adding an employee, opening a requisition, "
                    "moving a candidate, or running the pending HR workflow tasks."
                ),
                specialist_agent="Universal HR Copilot",
                autonomy_level=AutonomyLevel.L0_INFORMATIONAL,
            )

    async def _handle_message(self, request: CopilotChatRequest) -> CopilotChatResponse:
        text = (request.message or "").strip()
        lower = text.lower()
        conv_id = f"hr-conv-{uuid.uuid4().hex[:8]}"

        # 1. HARD GUARDRAIL: Intercept unauthorized execution attempts
        blocked_actions = [
            "fire them", "terminate immediately", "cut their salary", "dismiss employee",
            "fire everyone", "terminate all", "delete all employees", "drop table", "truncate employees"
        ]
        if any(w in lower for w in blocked_actions):
            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=(
                    "⚠️ **Action Restricted**: Consequential employment decisions (termination, disciplinary dismissal, salary alterations) "
                    "cannot be executed via chat commands. They must follow formal procedural safeguards with mandatory human review."
                ),
                specialist_agent="Fair Conduct & Compliance Sentinel",
                autonomy_level=AutonomyLevel.L4_RESTRICTED
            )

        # Gather ground-truth workforce data first
        workforce_data = self._get_workforce_data()

        # 2. TASK EXECUTION (Execute prompted HR work in live database)
        task_response = self._execute_hr_task(text, workforce_data)
        if task_response:
            return task_response

        commanded = await self._execute_commanded_flow(text)
        if commanded:
            return commanded

        # 3. SPECIALIZED LEAVE COVERAGE SIMULATION / GAP EVALUATION
        is_leave_eval = (
            "staffing gap" in lower
            or ("approving" in lower and "leave" in lower)
            or ("coverage" in lower and any(k in lower for k in ["gap", "score", "assessment", "adequate", "check"]))
            or ("simulate" in lower and "leave" in lower)
            or ("evaluate" in lower and "leave" in lower)
        )
        if is_leave_eval:
            emp = None
            if request.resource_id:
                emp = self.db.query(EmployeeProfile).filter_by(
                    id=request.resource_id, tenant_id=self.tenant_id
                ).first()
            if not emp:
                emp = self.db.query(EmployeeProfile).filter_by(
                    tenant_id=self.tenant_id
                ).first()

            if emp:
                start = datetime.now() + timedelta(days=7)
                end = start + timedelta(days=4)
                eval_result = self.leave_specialist.evaluate_leave_request(
                    employee_id=emp.id,
                    leave_type_code="ANNUAL",
                    start_date=start,
                    end_date=end,
                    days_requested=5.0
                )

                proposed_action = ProposedAction(
                    action_type="leave.approve",
                    title=f"Approve 5 days leave for {emp.full_name}",
                    resource_id=emp.id,
                    payload={
                        "employee_id": emp.id,
                        "days": 5.0,
                        "start_date": eval_result.start_date,
                        "end_date": eval_result.end_date,
                        "coverage_score": eval_result.coverage_score
                    },
                    risk_tier=eval_result.risk_tier,
                    requires_approval=eval_result.requires_approval
                )

                task_result = AgentTaskResult(
                    task_id=f"task-leave-{uuid.uuid4().hex[:6]}",
                    agent_id="leave_impact_agent",
                    intent="evaluate_leave_coverage",
                    status="completed",
                    summary=eval_result.explanation,
                    findings=[Finding(
                        severity="info" if eval_result.is_staffing_adequate else "warning",
                        code="COVERAGE_ANALYSIS",
                        message=f"Team coverage score: {int(eval_result.coverage_score*100)}% ({eval_result.active_in_office_count}/{eval_result.department_team_size} active)."
                    )],
                    proposed_actions=[proposed_action],
                    risk_assessment={
                        "risk_tier": eval_result.risk_tier.value,
                        "requires_approval": eval_result.requires_approval
                    }
                )

                reply_text = (
                    f"### 🏖️ Leave Coverage Assessment for **{emp.full_name}**\n\n"
                    f"- **Current Balance**: `{eval_result.current_balance} days`\n"
                    f"- **Projected Balance**: `{eval_result.projected_balance} days`\n"
                    f"- **Team Coverage Score**: `{int(eval_result.coverage_score*100)}%`\n"
                    f"- **Department Status**: `{eval_result.active_in_office_count}` of `{eval_result.department_team_size}` team members available.\n\n"
                    f"**Analysis**: {eval_result.explanation}"
                )

                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=reply_text,
                    specialist_agent="Leave & Workforce Impact Agent",
                    autonomy_level=AutonomyLevel.L1_SUGGESTIVE,
                    task_result=task_result
                )

        # 4. Live database answers, including hiring analytics, before any model call.
        is_candidate_query = (
            any(w in lower for w in [
                "candidate", "candidates", "cancdiate", "cancdiates", "candidat",
                "applicant", "applicants", "who applied", "talent pipeline"
            ])
            or ("pipeline" in lower and any(w in lower for w in ["talent", "recruitment", "hiring", "ats", "job"]))
            or (any(w in lower for w in ["how many", "count", "number of", "list", "show"]) and any(w in lower for w in ["interviewed", "screened", "sourced", "hired"]))
        )
        is_policy_query = any(w in lower for w in ["policy", "handbook", "guideline", "rule", "remote work", "overtime", "wfh"])
        rag_hits = self._retrieve_rag_context(text)
        specific_reply = self._generate_fallback_response(text, workforce_data, rag_hits, specific_only=True)
        if specific_reply:
            is_analytics = "hiring analytics" in specific_reply.lower()
            return CopilotChatResponse(
                conversation_id=conv_id,
                reply=specific_reply,
                specialist_agent=(
                    "Talent Acquisition Agent" if is_candidate_query or is_analytics
                    else "People & Policy Administration Agent" if is_policy_query
                    else "Universal HR Copilot"
                ),
                autonomy_level=AutonomyLevel.L0_INFORMATIONAL,
            )

        # 5. Open questions go to the model, then back to the live snapshot.
        workforce_context = self._format_workforce_context(workforce_data, rag_hits)

        # Multi-turn history
        conversation_context = ""
        if request.messages:
            history_lines = []
            for m in request.messages:
                role = (m.get("role") or "").lower()
                content = (m.get("content") or "").strip()
                if not content or "Universal HR Copilot" in content:
                    continue
                if role == "user":
                    history_lines.append(f"User: {content}")
                elif role in ("assistant", "system"):
                    history_lines.append(f"HR Copilot: {content}")
            if history_lines:
                conversation_context = "Recent Conversation History:\n" + "\n".join(history_lines)

        system_prompt = (
            "You are the OctaOS Universal HR Copilot, an enterprise-grade AI assistant with direct access to live workforce data and company knowledge.\n"
            "Your role is to assist HR managers, administrators, and employees across all 16 HR submodules:\n"
            "- People Management (Directory, headcount, profiles, departments, onboarding)\n"
            "- Talent Management (ATS, recruitment, requisitions, candidates, sourcing)\n"
            "- Compensation & Workforce (Leave management, balances, attendance, shifts)\n"
            "- Culture & Compliance (Policies, reviews, training)\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Always give direct, authoritative, and helpful answers grounded in the provided LIVE ENTERPRISE WORKFORCE DATA.\n"
            "2. If asked about candidate count or candidates in the pipeline, report the exact numbers and candidate names/details from the LIVE ATS DATA.\n"
            "3. If asked about employees, headcount, or open roles, report the exact live numbers and records.\n"
            "4. If asked about company policies, ground your answer in the RETRIEVED HR KNOWLEDGE & POLICIES (RAG) section. If no policy is found, say so.\n"
            "5. Format your answers cleanly with markdown (bold headers, bullet points, code tags).\n"
            "6. Be friendly, professional, and concise. Never repeat generic canned intros or greetings unless directly greeted.\n\n"
            f"LIVE ENTERPRISE WORKFORCE DATA:\n{workforce_context}"
        )

        user_prompt = f"{conversation_context}\n\nCurrent User Query: {text}" if conversation_context else text

        try:
            ai_reply = await asyncio.wait_for(
                self.llm.complete(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    task_type="hr",
                ),
                timeout=12,
            )
            if ai_reply and ai_reply.strip():
                agent_name = (
                    "Talent Acquisition Agent" if is_candidate_query
                    else "People & Policy Administration Agent" if is_policy_query
                    else "Universal HR Copilot AI"
                )
                return CopilotChatResponse(
                    conversation_id=conv_id,
                    reply=ai_reply.strip(),
                    specialist_agent=agent_name,
                    autonomy_level=AutonomyLevel.L0_INFORMATIONAL
                )
        except Exception as e:
            logger.warning(f"HR Copilot AI completion error, falling back to deterministic answer: {e}")

        # Deterministic fallback response with live database records
        fallback_reply = self._generate_fallback_response(text, workforce_data, rag_hits) or (
            "I could not match that to a live HR record. Ask for hiring analytics, headcount, or the pipeline, "
            "or command a task such as opening a requisition or moving a candidate."
        )
        fallback_agent = (
            "Talent Acquisition Agent" if is_candidate_query
            else "People & Policy Administration Agent" if is_policy_query
            else "Universal HR Copilot"
        )
        return CopilotChatResponse(
            conversation_id=conv_id,
            reply=fallback_reply,
            specialist_agent=fallback_agent,
            autonomy_level=AutonomyLevel.L0_INFORMATIONAL
        )
