import asyncio
import ipaddress
import logging
import socket
import urllib.parse
from typing import Dict, Any, List, Optional, Callable
import httpx
from sqlalchemy.orm import Session
from app.services.runtime_governance.tool_policy import action_fingerprint, authorize_tool_call

logger = logging.getLogger(__name__)

SECTION_TOOL_PREFIXES: Dict[str, str] = {
    "lead.": "sales",
    "ticket.": "support",
    "post.": "marketing",
    "campaign.": "marketing",
    "applicant.": "hr",
}


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        required_scopes: List[str],
        risk_level: str = "LOW",  # LOW, MEDIUM, HIGH
        side_effect: str = "READ",  # READ, WRITE
        approval_required: bool = False,
        rate_limit_per_minute: int = 60,
        timeout_seconds: int = 30,
        handler: Optional[Callable] = None,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.required_scopes = required_scopes
        self.risk_level = risk_level
        self.side_effect = side_effect
        self.approval_required = approval_required
        self.rate_limit_per_minute = rate_limit_per_minute
        self.timeout_seconds = timeout_seconds
        self.handler = handler


class SSRFProtectionError(Exception):
    pass


def _is_private_or_local_address(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Handle DNS64/NAT64 answers without weakening private-network checks.

    Some CI and dual-stack networks return public IPv4 destinations as a
    ``64:ff9b::/96`` IPv6 synthesis address. Python correctly marks that
    well-known translation prefix as reserved, but the embedded IPv4 address
    is the address that determines whether the destination is safe.
    """

    if isinstance(ip_obj, ipaddress.IPv6Address):
        if ip_obj.ipv4_mapped is not None:
            ip_obj = ip_obj.ipv4_mapped
        elif ip_obj in ipaddress.IPv6Network("64:ff9b::/96"):
            ip_obj = ipaddress.IPv4Address(ip_obj.packed[-4:])

    return (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
    )


def validate_outbound_url(url_str: str) -> str:
    """Blocks loopback, link-local, RFC 1918 private ranges, and non-http(s) schemes."""
    parsed = urllib.parse.urlparse(url_str.strip())
    if parsed.scheme not in ("http", "https"):
        raise SSRFProtectionError(f"Prohibited scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFProtectionError("Missing hostname in target URL")

    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if _is_private_or_local_address(ip_obj):
                raise SSRFProtectionError(f"Access to private/local network address {ip_str} is forbidden.")
    except socket.gaierror:
        # DNS resolution failure
        pass

    return url_str


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_default_tools()

    def register(self, tool: ToolDefinition, handler: Optional[Callable] = None):
        self._tools[tool.name] = tool
        assigned_handler = handler or tool.handler
        if assigned_handler:
            self._handlers[tool.name] = assigned_handler

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
                "output_schema": t.output_schema,
                "risk_level": t.risk_level,
                "side_effect": t.side_effect,
                "approval_required": t.approval_required,
                "required_scopes": t.required_scopes,
            }
            for t in self._tools.values()
        ]

    async def execute_tool(
        self,
        name: str,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' is not registered.")
        # Every dispatch requires server-created authorization context. Frontend visibility
        # and the model's requested tool name are not authorization controls.
        policy_context = context or {}
        if tool.approval_required and not policy_context.get("approval_id"):
            raise PermissionError("APPROVAL_REQUIRED")
        granted_tools = policy_context.get("granted_tools")
        request_tenant_id = policy_context.get("request_tenant_id")
        if not isinstance(granted_tools, (list, tuple, set)) or not request_tenant_id:
            raise PermissionError("TOOL_POLICY_CONTEXT_REQUIRED")
        approval_status = policy_context.get("approval_status")
        action_binding = None
        approved_action_binding = None
        if name and any(
            name == prefix or name.startswith(prefix)
            for prefix in (
                "email.send", "email.delete", "crm.delete", "payment.", "billing.",
                "post.publish", "contract.sign", "user.delete", "browser.submit", "webhook_post",
            )
        ):
            # Fingerprint the exact proposed side effect on the server. The approval
            # fingerprint must come from a persisted, server-validated approval record;
            # never accept a client-supplied boolean as authorization.
            target = str(
                payload.get("target")
                or payload.get("recipient")
                or payload.get("recipient_email")
                or payload.get("email")
                or payload.get("url")
                or payload.get("account_id")
                or ""
            )
            action_binding = action_fingerprint(
                tenant_id=tenant_id,
                run_id=str(policy_context.get("run_id") or ""),
                bot_id=str(policy_context.get("bot_id") or policy_context.get("agent_id") or ""),
                tool_name=name,
                target=target,
                payload=payload,
                policy_version=str(policy_context.get("policy_version") or "1"),
            )
            # Resolve the approval from the database. Never trust an approval status or
            # fingerprint supplied by a caller/UI context.
            approval_id = policy_context.get("approval_id")
            approved_action_binding = None
            persisted_status = None
            if approval_id:
                from app.models.enterprise import ApprovalRequest
                approval = db.query(ApprovalRequest).filter(
                    ApprovalRequest.id == str(approval_id),
                    ApprovalRequest.tenant_id == tenant_id,
                ).with_for_update().first()
                if approval:
                    persisted_status = approval.status
                    stored = approval.action_binding or {}
                    # An approval is valid only for the same run, bot, tool, target,
                    # payload and policy version. Legacy approvals without bindings fail closed.
                    same_action = (
                        approval.status == "approved"
                        and approval.action_fingerprint
                        and stored.get("run_id") == str(policy_context.get("run_id") or "")
                        and stored.get("bot_id") == str(policy_context.get("bot_id") or policy_context.get("agent_id") or "")
                        and stored.get("tool_name") == name
                        and stored.get("target") == target
                        and stored.get("payload") == payload
                        and stored.get("policy_version") == str(policy_context.get("policy_version") or "1")
                    )
                    if same_action:
                        approved_action_binding = approval.action_fingerprint
            approval_status = persisted_status

        decision = authorize_tool_call(
            tenant_id=tenant_id,
            request_tenant_id=str(request_tenant_id),
            tool_name=name,
            granted_tools=granted_tools,
            connection_active=bool(policy_context.get("connection_active", True)),
            approval_status=approval_status,
            action_binding=action_binding,
            approved_action_binding=(
                str(approved_action_binding) if approved_action_binding else None
            ),
        )
        if not decision.allowed:
            raise PermissionError(decision.reason)

        # Direct handler dispatch if registered on tool or registry
        handler = tool.handler or self._handlers.get(name)
        if handler:
            return await handler(payload=payload, db=db, tenant_id=tenant_id, context=context)

        # Dynamic section tool dispatch (e.g. lead.*, ticket.*, post.*, campaign.*, applicant.*)
        for prefix, section in SECTION_TOOL_PREFIXES.items():
            if name.startswith(prefix):
                from app.services.agents.section_registry import section_registry
                return await section_registry.execute_action(section, name, tenant_id, payload, db)

        # Dynamic browser kernel tool dispatch
        if name == "restart_browser" or (name or "").startswith("agent_browser_"):
            from app.services.agents.kernel.browser_session import run_browser_tool
            return await run_browser_tool(name, payload, tenant_id, context)

        raise NotImplementedError(f"Tool '{name}' execution handler not implemented.")

    async def _exec_web_search(
        self,
        payload: Dict[str, Any],
        db: Session = None,
        tenant_id: str = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        query = payload.get("query", "").strip()
        if not query:
            return {"results": [], "query": query, "message": "Empty query."}
        from app.services.research import EnterpriseWebResearchService

        count = max(1, min(int(payload.get("count", 10) or 10), 100))
        try:
            batch = await asyncio.wait_for(
                EnterpriseWebResearchService(db, tenant_id).run(
                    query,
                    count=count,
                    freshness=payload.get("freshness") or payload.get("freshness_window") or "14_days",
                    geography=payload.get("geography"),
                    industries=payload.get("industries"),
                    buyer_roles=payload.get("buyer_roles"),
                    exclusions=payload.get("exclusions"),
                    seed_urls=payload.get("seed_urls"),
                ),
                # The loop stops a tool at 70s. Leave room for that outer wait.
                timeout=55.0,
            )
            summary = EnterpriseWebResearchService.summarize(batch, count=count)
            return {
                "query": query,
                "provider": "enterprise_web_research",
                "results": summary["contacts"],
                "extras": summary["extras"],
                "methods": summary["methods"],
                "report": summary["report"],
                "status": batch.status,
            }
        except Exception as search_err:
            logger.warning("Live web search timed out or failed (%s). No leads were invented.", search_err)
            return {
                "success": False,
                "query": query,
                "provider": "enterprise_web_research",
                "results": [],
                "extras": [],
                "methods": [],
                "status": "failed",
                "error": str(search_err),
                "message": "The live search did not return companies. No leads were invented.",
            }

    async def _exec_agent_consult(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        target_agent = str(payload.get("target_agent") or "").strip().lower()
        task = str(payload.get("task") or payload.get("query") or "").strip()
        if not target_agent or not task:
            raise ValueError("Missing 'target_agent' or 'task' in agent.consult payload.")

        ctx = context or {}
        caller_slug = str(ctx.get("agent_slug") or ctx.get("agent_id") or "").lower()
        target_slug = target_agent.replace(" ", "_")

        # Cycle & self-consultation check
        if caller_slug and (caller_slug == target_slug or caller_slug.replace("_ai", "") == target_slug.replace("_ai", "")):
            raise ValueError(f"Agent '{caller_slug}' cannot consult itself.")

        current_depth = int(ctx.get("depth", 0))
        if current_depth >= 2:
            raise ValueError(f"Maximum inter-agent consultation depth (2) reached. Cannot chain further to '{target_agent}'.")

        from app.services.agents.runtime import agent_runtime
        res = await agent_runtime.execute(
            agent_id=target_slug,
            input_context={
                "prompt": task,
                "depth": current_depth + 1,
                "caller_agent": caller_slug,
                "assignment_mode": "consult",
                **({"connector_tools": ctx["connector_tools"]} if ctx.get("connector_tools") is not None else {}),
                **({"connector_scopes": ctx["connector_scopes"]} if ctx.get("connector_scopes") is not None else {}),
                **({"task_id": ctx["task_id"]} if ctx.get("task_id") else {}),
            },
            db=db,
            tenant_id=tenant_id,
            dry_run=False,
        )
        child_status = res.get("status")
        return {
            "target_agent": target_slug,
            "mode": "consult",
            "status": "completed" if child_status == "succeeded" else (child_status or "failed"),
            "outcome": "done" if child_status == "succeeded" else "provider_error",
            "response": res.get("output", ""),
            "tool_calls": len(res.get("tool_calls") or []),
        }

    async def _exec_agent_notify(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a notice. Notify does not run tools or treat the model text as done."""
        message = str(payload.get("message") or payload.get("task") or "").strip()
        if not message:
            raise ValueError("Missing 'message' in agent.notify payload.")
        ctx = context or {}
        task_id = ctx.get("task_id")
        recorded = False
        if task_id:
            from app.models.autonomous_work import AutonomousTask, AutonomousTaskEvent
            from app.services.agents.kernel.assignment import stamp_assignment
            import uuid
            task = db.query(AutonomousTask).filter_by(id=task_id, tenant_id=tenant_id).first()
            if task is not None:
                stamp_assignment(task, mode="notify", status="completed", outcome="done", depth=int(ctx.get("depth") or 0))
                db.add(AutonomousTaskEvent(
                    id=str(uuid.uuid4()),
                    task_id=task.id,
                    tenant_id=tenant_id,
                    actor_type="agent",
                    actor_id=str(ctx.get("agent_slug") or ctx.get("agent_id") or ""),
                    event_type="notify",
                    message=message,
                    payload={"mode": "notify", "outcome": "done"},
                ))
                db.commit()
                recorded = True
        return {
            "mode": "notify",
            "status": "completed",
            "outcome": "done",
            "recorded": recorded,
            "message": message,
        }

    async def _exec_agent_delegate(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import uuid
        from app.models.autonomous_work import AutonomousTask
        from app.services.agents.kernel.assignment import MAX_DELEGATION_DEPTH, stamp_assignment
        from app.services.agents.work_graph.engine import WorkGraphEngine
        target_agent = str(payload.get("target_agent") or "").strip().lower()
        title = str(payload.get("title") or "Delegated Task").strip()
        task_desc = str(payload.get("task") or payload.get("goal") or "").strip()
        department = str(payload.get("department") or "operations").strip().lower()
        acceptance_criteria = payload.get("acceptance_criteria") or []

        if not target_agent or not task_desc:
            raise ValueError("Missing 'target_agent' or 'task' in agent.delegate payload.")

        ctx = context or {}
        parent_task_id = ctx.get("task_id")
        created_by_id = ctx.get("user_id") or "system"
        current_depth = int(ctx.get("depth") or 0)
        if current_depth >= MAX_DELEGATION_DEPTH:
            raise ValueError(f"Maximum delegation depth ({MAX_DELEGATION_DEPTH}) reached.")

        # Create child autonomous task
        child_task = AutonomousTask(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            parent_task_id=parent_task_id,
            title=title,
            goal=task_desc,
            department=department,
            assigned_agent_slug=target_agent,
            status="planned",
            acceptance_criteria=acceptance_criteria,
            dependencies=[],
            context=dict(ctx),
        )
        stamp_assignment(
            child_task,
            mode="work",
            status="queued",
            depth=current_depth + 1,
            parent_id=parent_task_id,
        )
        db.add(child_task)
        db.commit()

        # Execute subtask with verification
        res = await WorkGraphEngine.execute_subtask(db, tenant_id, child_task.id)
        return {
            "task_id": child_task.id,
            "target_agent": target_agent,
            "status": res.get("status"),
            "verification_status": res.get("verification_status"),
            "output": res.get("output"),
            "score": res.get("score"),
            "success": res.get("success", False),
        }

    async def _exec_work_graph_create(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.services.agents.work_graph.engine import WorkGraphEngine
        title = str(payload.get("title") or "Company Project").strip()
        goal = str(payload.get("goal") or title).strip()
        subtasks = payload.get("subtasks") or []
        department = str(payload.get("department") or "executive").strip().lower()
        agent_slug = str(payload.get("assigned_agent") or "chief-of-staff").strip().lower()

        ctx = context or {}
        created_by_id = ctx.get("user_id") or "system"

        root_task = WorkGraphEngine.create_graph(
            db=db,
            tenant_id=tenant_id,
            created_by_id=created_by_id,
            title=title,
            goal=goal,
            department=department,
            assigned_agent_slug=agent_slug,
            subtasks=subtasks,
            context=ctx,
        )

        return {
            "root_task_id": root_task.id,
            "title": root_task.title,
            "department": root_task.department,
            "subtask_count": len(subtasks),
            "status": root_task.status,
            "message": f"Durable work graph '{title}' created with {len(subtasks)} planned subtasks.",
        }

    async def _exec_email_send(
        self,
        payload: Dict[str, Any],
        db: Session = None,
        tenant_id: str = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.services.email.sender import send_email

        to_email = payload.get("to") or payload.get("email")
        subject = payload.get("subject", "OctaOS Autonomous Agent Notification")
        body = payload.get("body") or payload.get("content", "")

        if not to_email or not body:
            raise ValueError("Missing 'to' or 'body' in email.send payload.")

        delivery = send_email(db, tenant_id, to_email, subject, body)
        sent = bool(delivery.get("sent")) if isinstance(delivery, dict) else bool(delivery)
        return {
            "sent": sent,
            "delivery": delivery if isinstance(delivery, dict) else {"result": str(delivery)},
            "to": to_email,
            "subject": subject,
            "preview": body[:120],
            "message": "Email provider confirmed delivery request." if sent else "Email was not sent; provider configuration or delivery failed.",
        }

    async def _exec_webhook_post(
        self,
        payload: Dict[str, Any],
        db: Session = None,
        tenant_id: str = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = payload.get("url")
        data = payload.get("data", {})
        if not url:
            raise ValueError("Missing 'url' in webhook_post payload.")

        safe_url = validate_outbound_url(url)
        headers = payload.get("headers", {"Content-Type": "application/json"})

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(safe_url, json=data, headers=headers)
            return {
                "status_code": resp.status_code,
                "response_body": resp.text[:500],
                "success": resp.status_code < 400,
            }

    async def _exec_external_agent_send_command(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.models.external_agents import ControllerCommand
        from app.services.webhooks.dispatcher import enqueue_webhook_event
        import uuid

        command_text = payload.get("command")
        if not command_text:
            raise ValueError("Missing 'command' in external_agent.send_command payload.")

        connection_id = payload.get("connection_id")
        correlation_id = payload.get("correlation_id") or f"cmd_{uuid.uuid4().hex[:12]}"
        ctx = payload.get("context") or {}
        actor = (context or {}).get("agent_name") or "OctaOS Agent"

        cmd = ControllerCommand(
            tenant_id=tenant_id,
            connection_id=connection_id,
            correlation_id=correlation_id,
            command=command_text,
            context_json=ctx,
            status="sent",
            issued_by=actor,
        )
        db.add(cmd)
        db.commit()
        db.refresh(cmd)

        enqueue_webhook_event(
            db=db,
            tenant_id=tenant_id,
            event_type="command.issued",
            payload={
                "command_id": cmd.id,
                "correlation_id": correlation_id,
                "command": cmd.command,
                "context": cmd.context_json,
                "issued_by": actor,
                "reply_endpoint": "/api/v1/controller/replies",
            },
            correlation_id=correlation_id,
        )

        return {
            "success": True,
            "command_id": cmd.id,
            "correlation_id": correlation_id,
            "status": cmd.status,
        }

    async def _exec_knowledge_search(
        self,
        payload: Dict[str, Any],
        db: Session = None,
        tenant_id: str = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.models.agents import KnowledgeDocument

        query_text = payload.get("query", "").lower()
        dept = payload.get("department")

        q = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.is_active == True,
        )
        if dept:
            q = q.filter(KnowledgeDocument.department == dept)

        docs = q.limit(10).all()
        matches = []
        for doc in docs:
            if not query_text or query_text in doc.content.lower():
                matches.append({
                    "id": doc.id,
                    "department": doc.department,
                    "doc_type": doc.doc_type,
                    "excerpt": doc.content[:400],
                    "authority": doc.source_authority,
                })

        return {"query": query_text, "matches": matches, "total": len(matches)}

    async def _exec_knowledge_search_sources(
        self, payload: Dict[str, Any], db: Session, tenant_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        from app.models.knowledge_connectors import KnowledgeConnector, ConnectorPermission

        query_text = (payload.get("query") or "").lower().strip()
        dept = payload.get("department") or (context.get("department") if context else "general")
        acting_agent_id = context.get("agent_id") if context else None

        connectors = db.query(KnowledgeConnector).filter(
            KnowledgeConnector.tenant_id == tenant_id,
            KnowledgeConnector.state == "active",
        ).all()

        results = []
        for c in connectors:
            perms = db.query(ConnectorPermission).filter_by(connector_id=c.id).all()
            if perms:
                allowed = any(
                    (p.department.lower() in ("general", dept.lower(), "*"))
                    and (p.agent_id is None or p.agent_id == acting_agent_id)
                    for p in perms
                )
                if not allowed:
                    continue

            if not query_text or query_text in c.name.lower() or (c.description and query_text in c.description.lower()):
                results.append({
                    "connector_id": c.id,
                    "slug": c.slug,
                    "name": c.name,
                    "type": c.connector_type,
                    "description": c.description,
                })

        return {"query": query_text, "sources": results, "total": len(results)}

    async def _exec_knowledge_describe_source(
        self, payload: Dict[str, Any], db: Session, tenant_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        from app.models.knowledge_connectors import KnowledgeConnector, ConnectorConfigVersion, ConnectorSchemaVersion

        conn_id = payload.get("connector_id") or payload.get("slug")
        connector = db.query(KnowledgeConnector).filter(
            (KnowledgeConnector.id == conn_id) | (KnowledgeConnector.slug == conn_id),
            KnowledgeConnector.tenant_id == tenant_id,
        ).first()

        if not connector:
            return {"error": f"Connector '{conn_id}' not found."}

        active_config = db.query(ConnectorConfigVersion).filter_by(
            connector_id=connector.id,
            version=connector.current_config_version,
        ).first()

        latest_schema = db.query(ConnectorSchemaVersion).filter_by(
            connector_id=connector.id
        ).order_by(ConnectorSchemaVersion.observed_at.desc()).first()

        return {
            "connector_id": connector.id,
            "name": connector.name,
            "slug": connector.slug,
            "type": connector.connector_type,
            "parameter_schema": active_config.parameter_schema if active_config else {},
            "observed_fields": latest_schema.observed_fields if latest_schema else {},
            "schema_fingerprint": latest_schema.schema_fingerprint if latest_schema else None,
        }

    async def _exec_knowledge_live_fetch(
        self, payload: Dict[str, Any], db: Session, tenant_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import uuid
        from app.services.knowledge_connectors.service import ConnectorService
        from app.services.knowledge_connectors.contracts import ConnectorInvocation, ExecutionContext

        conn_id = payload.get("connector_id") or payload.get("slug")
        params = payload.get("params", {})
        force_refresh = payload.get("force_refresh", False)

        exec_context = ExecutionContext(
            tenant_id=tenant_id,
            acting_agent_id=context.get("agent_id") if context else None,
            department=context.get("department", "general") if context else "general",
            request_id=context.get("flow_run_id") or f"agent_req_{uuid.uuid4().hex[:8]}",
        )

        invocation = ConnectorInvocation(
            connector_id=conn_id,
            operation="read",
            params=params,
            force_refresh=force_refresh,
        )

        result = await ConnectorService.execute_query(db, conn_id, exec_context, invocation)
        return result.model_dump(mode="json")

    async def _exec_knowledge_get_execution_status(
        self, payload: Dict[str, Any], db: Session, tenant_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        from app.models.knowledge_connectors import ConnectorExecution

        req_id = payload.get("request_id")
        exec_record = db.query(ConnectorExecution).filter_by(
            request_id=req_id,
            tenant_id=tenant_id,
        ).order_by(ConnectorExecution.executed_at.desc()).first()

        if not exec_record:
            return {"error": f"Execution '{req_id}' not found."}

        return {
            "request_id": exec_record.request_id,
            "connector_id": exec_record.connector_id,
            "status": exec_record.status,
            "records_returned": exec_record.records_returned,
            "truncated": exec_record.truncated,
            "duration_ms": exec_record.duration_ms,
            "executed_at": exec_record.executed_at.isoformat() if exec_record.executed_at else None,
            "provenance": exec_record.provenance,
        }

    async def _exec_app_connector_action(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        from app.services.agents.connected_systems import check_app_connector, format_connector_prompt

        app_name = str(payload.get("app") or payload.get("provider") or payload.get("platform") or "").strip()
        operation = str(payload.get("operation") or "write").strip().lower()
        action_name = str(payload.get("action") or operation).strip().lower()
        params = dict(payload.get("params") or payload.get("data") or {})

        if not app_name:
            return {"success": False, "message": "Missing 'app' in app.connector_action payload."}

        from app.services.agents.kernel.connector_grants import connector_action_allowed
        granted, reason = connector_action_allowed(
            app_name,
            operation,
            action_name,
            connector_tools=(context or {}).get("connector_tools"),
            connector_scopes=(context or {}).get("connector_scopes"),
        )
        if not granted:
            return {"success": False, "status": "denied", "error": reason}

        conn = check_app_connector(db, tenant_id, app_name)
        social_apps = ("instagram", "facebook", "linkedin", "twitter", "x", "tiktok", "buffer")
        if not conn.get("connected") and conn.get("app") in social_apps:
            from app.services.social.publish_helpers import resolve_buffer_channel_id

            platform = str(conn.get("app") or "")
            if platform == "buffer":
                platform = str(params.get("platform") or "")
            if platform:
                channel_id = await resolve_buffer_channel_id(db, tenant_id, platform)
                if channel_id:
                    conn = {
                        **conn,
                        "connected": True,
                        "source": "buffer",
                        "buffer_channel_id": channel_id,
                        "missing_reason": None,
                    }
        if not conn.get("connected"):
            return {
                "success": False,
                "status": "connector_required",
                "connector_required": True,
                "connector": conn,
                "pending_action": {
                    "type": "connector_action",
                    "app": conn["app"],
                    "operation": operation,
                    "action": action_name,
                    "params": params,
                },
                "message": format_connector_prompt(conn, f"{operation} data with {conn['label']}"),
            }

        app_key = conn["app"]
        if app_key in ("instagram", "facebook", "linkedin", "buffer") and operation == "write":
            from app.services.agents.section_registry import section_registry

            post_payload = {
                **params,
                "platform": app_key if app_key != "buffer" else (params.get("platform") or "instagram"),
                "publish_now": True,
            }
            if params.get("post_id"):
                return await section_registry.execute_action("marketing", "post.publish", tenant_id, post_payload, db)
            return await section_registry.execute_action("marketing", "post.create", tenant_id, post_payload, db)

        if app_key in ("gmail", "email", "smtp") and operation == "write":
            return await self._exec_email_send(params, db, tenant_id)

        if conn.get("source") == "knowledge_connector" or operation == "read":
            from app.models.knowledge_connectors import KnowledgeConnector

            kc = (
                db.query(KnowledgeConnector)
                .filter(
                    KnowledgeConnector.tenant_id == tenant_id,
                    KnowledgeConnector.status == "active",
                )
                .all()
            )
            matched = next(
                (
                    row
                    for row in kc
                    if (row.connector_type or "").lower() == app_key or app_key in (row.name or "").lower()
                ),
                None,
            )
            if matched:
                return await self._exec_knowledge_live_fetch(
                    {"connector_id": matched.id, "params": params, "force_refresh": True},
                    db,
                    tenant_id,
                    context,
                )

        if app_key == "sendgrid":
            from app.services.integrations.sendgrid_service import SendGridService

            svc = SendGridService(db, tenant_id)
            res = await svc.send_email(
                to_email=params.get("to") or params.get("to_email") or "",
                subject=params.get("subject") or "OctaOS Notification",
                html_content=params.get("body") or params.get("content") or "",
            )
            return {"success": True, "app": app_key, "operation": operation, "result": res}

        if app_key == "twilio":
            from app.services.integrations.twilio_service import TwilioService

            svc = TwilioService(db, tenant_id)
            res = await svc.send_sms(
                to_number=params.get("to") or params.get("phone") or "",
                body=params.get("body") or params.get("message") or "",
            )
            return {"success": True, "app": app_key, "operation": operation, "result": res}

        if app_key == "calendly":
            from app.services.integrations.calendly_service import CalendlyService

            svc = CalendlyService(db, tenant_id)
            res = await svc.list_event_types()
            return {"success": True, "app": app_key, "operation": operation, "result": res}

        if app_key == "zoominfo":
            from app.services.integrations.zoominfo_service import ZoomInfoService

            svc = ZoomInfoService(db, tenant_id)
            res = await svc.enrich_company(domain=params.get("domain") or params.get("company") or "")
            return {"success": True, "app": app_key, "operation": operation, "result": res}

        if app_key in ("zapier", "workato"):
            from app.services.integrations.zapier_workato_service import ZapierWorkatoService

            svc = ZapierWorkatoService(db, tenant_id)
            res = await svc.trigger_automation(provider=app_key, event_name=action_name, payload=params)
            return {"success": True, "app": app_key, "operation": operation, "result": res}

        return {
            "success": True,
            "status": "connected",
            "app": app_key,
            "operation": operation,
            "connector": conn,
            "message": f"{conn['label']} is connected and ready.",
        }

    async def _exec_memory(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Hermes persistent curated memory operation: add, patch, or remove."""
        from app.services.agents.memory.memory_store import TenantMemoryStore
        store = TenantMemoryStore(db=db, tenant_id=tenant_id)
        action = payload.get("action", "add")
        target = payload.get("target", "memory")
        content = payload.get("content")
        old_text = payload.get("old_text")
        return store.execute_action(action=action, target=target, content=content, old_text=old_text)

    async def _exec_session_search(
        self,
        payload: Dict[str, Any],
        db: Session,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Hermes cross-session conversational recall search."""
        from app.services.agents.memory.session_history import search_session_history
        query = payload.get("query")
        session_id = payload.get("session_id")
        limit = int(payload.get("limit", 5) or 5)
        return search_session_history(db=db, tenant_id=tenant_id, query=query, session_id=session_id, limit=limit)

    def _register_default_tools(self):
        # 1. web_search (External READ, low risk)
        self.register(
            ToolDefinition(
                name="web_search",
                description=(
                    "Runs governed multi-channel public research across web search, buyer-language requests, "
                    "public RFP/tender pages, funding and business news, company contact pages, hiring signals, "
                    "and permitted public social searches. Returns evidence-backed contacts plus clearly labeled extras."
                ),
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "description": "Research objective or search terms"},
                        "count": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                        "freshness": {"type": "string", "default": "14_days", "description": "Freshness window such as 14_days or all"},
                        "geography": {"type": "array", "items": {"type": "string"}},
                        "industries": {"type": "array", "items": {"type": "string"}},
                        "buyer_roles": {"type": "array", "items": {"type": "string"}},
                        "exclusions": {"type": "array", "items": {"type": "string"}},
                        "seed_urls": {"type": "array", "items": {"type": "string"}},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "extras": {"type": "array"},
                        "methods": {"type": "array"},
                        "report": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
                required_scopes=["search:read"],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_web_search,
            )
        )

        # 2. email.send (External WRITE, high risk, requires human approval by default)
        self.register(
            ToolDefinition(
                name="email.send",
                description="Sends an outbound email to a customer, prospect, or stakeholder.",
                input_schema={
                    "type": "object",
                    "required": ["to", "subject", "body"],
                    "properties": {
                        "to": {"type": "string", "format": "email"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {"sent": {"type": "boolean"}}},
                required_scopes=["email:send"],
                risk_level="HIGH",
                side_effect="WRITE",
                approval_required=True,
                handler=self._exec_email_send,
            )
        )

        # 3. lead.update (Internal WRITE, medium risk)
        self.register(
            ToolDefinition(
                name="lead.update",
                description="Updates lead scoring, status, notes, or enrichment data in the Sales CRM.",
                input_schema={
                    "type": "object",
                    "required": ["lead_id"],
                    "properties": {
                        "lead_id": {"type": "string"},
                        "score": {"type": "number"},
                        "status": {"type": "string"},
                        "notes": {"type": "string"},
                        "data": {"type": "object"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                required_scopes=["sales:write"],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 4. lead.create (Internal WRITE, medium risk)
        self.register(
            ToolDefinition(
                name="lead.create",
                description="Creates a new qualified lead record in the Sales CRM.",
                input_schema={
                    "type": "object",
                    "required": ["name", "email"],
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "company": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {"lead_id": {"type": "string"}}},
                required_scopes=["sales:write"],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 5. ticket.reply (Internal/Customer WRITE, medium risk)
        self.register(
            ToolDefinition(
                name="ticket.reply",
                description="Posts a resolution reply to a customer support ticket.",
                input_schema={
                    "type": "object",
                    "required": ["ticket_id", "message"],
                    "properties": {
                        "ticket_id": {"type": "string"},
                        "message": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                required_scopes=["support:write"],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 6. knowledge.search (Internal READ, low risk)
        self.register(
            ToolDefinition(
                name="knowledge.search",
                description="Queries verified company documentation and brand truth.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "department": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {"matches": {"type": "array"}}},
                required_scopes=["knowledge:read"],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_knowledge_search,
            )
        )

        # 7. webhook_post (External WRITE, high risk, guarded by SSRF protection)
        self.register(
            ToolDefinition(
                name="webhook_post",
                description="Posts JSON payload to an external webhook endpoint with SSRF protection.",
                input_schema={
                    "type": "object",
                    "required": ["url", "data"],
                    "properties": {
                        "url": {"type": "string"},
                        "data": {"type": "object"},
                        "headers": {"type": "object"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                required_scopes=["webhook:write"],
                risk_level="HIGH",
                side_effect="WRITE",
                approval_required=True,
                handler=self._exec_webhook_post,
            )
        )

        # 7b. external_agent.send_command (Governed Command Dispatch to External Agents)
        self.register(
            ToolDefinition(
                name="external_agent.send_command",
                description="Sends a governed command to an external AI agent controller (e.g. Grok Bot, Claude Agent, n8n webhook) with correlation tracking and callback listener.",
                input_schema={
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "connection_id": {"type": "string", "description": "Target external agent connection ID (optional)"},
                        "command": {"type": "string", "description": "Directive or task instructions for the external controller"},
                        "correlation_id": {"type": "string", "description": "Tracking correlation ID"},
                        "context": {"type": "object", "description": "Structured context, parameters, or file URLs"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "command_id": {"type": "string"},
                        "correlation_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
                required_scopes=["webhook:write"],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
                handler=self._exec_external_agent_send_command,
            )
        )

        # 8. Governed Knowledge Connector: search_sources
        self.register(
            ToolDefinition(
                name="knowledge.search_sources",
                description="Discovers active external data sources (APIs, Google Sheets, databases) matching query intent and permitted for this agent.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keyword or intent, e.g. 'customer orders' or 'billing'"},
                        "department": {"type": "string", "description": "Target department scope, e.g. 'sales' or 'support'"},
                    },
                },
                output_schema={"type": "object", "properties": {"sources": {"type": "array"}}},
                required_scopes=["knowledge:read"],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_knowledge_search_sources,
            )
        )

        # 9. Governed Knowledge Connector: describe_source
        self.register(
            ToolDefinition(
                name="knowledge.describe_source",
                description="Inspects schema, declared parameters, and data classification of an external source without executing a live query.",
                input_schema={
                    "type": "object",
                    "required": ["connector_id"],
                    "properties": {
                        "connector_id": {"type": "string", "description": "The connector ID or slug"},
                    },
                },
                output_schema={"type": "object", "properties": {"parameter_schema": {"type": "object"}}},
                required_scopes=["knowledge:read"],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_knowledge_describe_source,
            )
        )

        # 10. Governed Knowledge Connector: live_fetch
        self.register(
            ToolDefinition(
                name="knowledge.live_fetch",
                description="Fetches verified live business data from an authorized external source with bounded streaming and policy controls.",
                input_schema={
                    "type": "object",
                    "required": ["connector_id"],
                    "properties": {
                        "connector_id": {"type": "string", "description": "Connector ID or slug to query"},
                        "params": {"type": "object", "description": "Declared query parameters, e.g. {'email': 'user@domain.com'}"},
                        "force_refresh": {"type": "boolean", "description": "Bypass policy cache and force live network fetch"},
                    },
                },
                output_schema={"type": "object", "properties": {"status": {"type": "string"}, "data": {"type": "object"}}},
                required_scopes=["knowledge:read"],
                risk_level="MEDIUM",
                side_effect="READ",
                approval_required=False,
                timeout_seconds=15,
                handler=self._exec_knowledge_live_fetch,
            )
        )

        # 11. Governed Knowledge Connector: get_execution_status
        self.register(
            ToolDefinition(
                name="knowledge.get_execution_status",
                description="Retrieves the result and execution provenance of a prior live fetch request without re-executing.",
                input_schema={
                    "type": "object",
                    "required": ["request_id"],
                    "properties": {
                        "request_id": {"type": "string", "description": "Execution request ID to check"},
                    },
                },
                output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
                required_scopes=["knowledge:read"],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_knowledge_get_execution_status,
            )
        )

        # 12. agent.consult (Governed Inter-Agent Cross-Department Communication)
        self.register(
            ToolDefinition(
                name="agent.consult",
                description="Consults another OctaOS specialist AI agent ('sales_ai', 'marketing_ai', 'support_ai', 'finance_ai', 'hr_ai', 'ceo_ai') for cross-department expertise without overstepping role boundaries.",
                input_schema={
                    "type": "object",
                    "required": ["target_agent", "task"],
                    "properties": {
                        "target_agent": {
                            "type": "string",
                            "description": "Target agent slug, e.g. 'sales_ai', 'marketing_ai', 'support_ai', 'finance_ai', 'hr_ai', 'ceo_ai'",
                        },
                        "task": {
                            "type": "string",
                            "description": "The specific inquiry, question, or request to consult the specialist on",
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "target_agent": {"type": "string"},
                        "status": {"type": "string"},
                        "response": {"type": "string"},
                    },
                },
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                timeout_seconds=60,
                handler=self._exec_agent_consult,
            )
        )

        # 12b. agent.delegate (Hierarchical Task Delegation & Durable Subtask Spawning)
        self.register(
            ToolDefinition(
                name="agent.delegate",
                description="Delegates a structured subtask to a specialist employee. Spawns an independently verified subtask with clear acceptance criteria and reports verified outcomes back to the delegating manager.",
                input_schema={
                    "type": "object",
                    "required": ["target_agent", "title", "task"],
                    "properties": {
                        "target_agent": {"type": "string", "description": "Specialist agent slug, e.g. 'sales_manager', 'marketing_copywriter', 'support_agent', 'research_analyst'"},
                        "title": {"type": "string", "description": "Concise title of the delegated work item"},
                        "task": {"type": "string", "description": "Specific, actionable instructions and expectations for the specialist"},
                        "department": {"type": "string", "description": "Department domain ('sales', 'marketing', 'support', 'hr', 'finance', 'operations')"},
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "Measurable criteria the deliverable must fulfill before completion"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "status": {"type": "string"},
                        "verification_status": {"type": "string"},
                        "output": {"type": "string"},
                        "score": {"type": "number"},
                    },
                },
                required_scopes=[],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
                timeout_seconds=120,
                handler=self._exec_agent_delegate,
            )
        )

        # 12c. work_graph.create (Durable Multi-Department Project Decomposition)
        self.register(
            ToolDefinition(
                name="work_graph.create",
                description="Creates a durable multi-department project plan with milestones, dependencies, and assigned AI employees.",
                input_schema={
                    "type": "object",
                    "required": ["title", "goal", "subtasks"],
                    "properties": {
                        "title": {"type": "string", "description": "Overall project title"},
                        "goal": {"type": "string", "description": "High-level company objective"},
                        "department": {"type": "string", "description": "Owning department (default 'executive')"},
                        "assigned_agent": {"type": "string", "description": "Coordinating manager slug (default 'chief-of-staff')"},
                        "subtasks": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "assigned_agent_slug"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "goal": {"type": "string"},
                                    "department": {"type": "string"},
                                    "assigned_agent_slug": {"type": "string"},
                                    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                                    "dependencies": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "root_task_id": {"type": "string"},
                        "title": {"type": "string"},
                        "subtask_count": {"type": "integer"},
                        "status": {"type": "string"},
                    },
                },
                required_scopes=[],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
                timeout_seconds=30,
                handler=self._exec_work_graph_create,
            )
        )

        # 13. post.create (Marketing Social Post & Visual Spot Creation)
        self.register(
            ToolDefinition(
                name="post.create",
                description="Creates a marketing content post draft with copy, hashtags, and optional AI visual creative image generation.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "description": "Target platform (e.g. 'instagram', 'linkedin', 'twitter', 'facebook')", "default": "instagram"},
                        "content": {"type": "string", "description": "Full post content including copy and hashtags"},
                        "caption": {"type": "string", "description": "Direct promotional caption or hook"},
                        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "List of hashtags (e.g. ['#AlienhouseDiwali', '#FestiveVibes'])"},
                        "image_prompt": {"type": "string", "description": "Detailed visual creative prompt to synthesize the campaign image asset"},
                        "generate_image": {"type": "boolean", "default": True, "description": "Whether to generate an AI visual image for this post"},
                        "image_url": {"type": "string", "description": "Optional pre-existing image URL"},
                        "topic": {"type": "string", "description": "Campaign theme or subject topic"},
                        "publish_now": {
                            "type": "boolean",
                            "default": False,
                            "description": "Set true when the user explicitly asks to post or publish directly to the platform right now",
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "post_id": {"type": "string"},
                        "platform": {"type": "string"},
                        "image_url": {"type": "string"},
                        "caption": {"type": "string"},
                        "hashtags": {"type": "array"},
                        "status": {"type": "string"},
                        "approval_status": {"type": "string"},
                    },
                },
                required_scopes=["marketing:write"],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 14. post.publish (Marketing Post Publishing to Social Channels)
        self.register(
            ToolDefinition(
                name="post.publish",
                description="Publishes an approved marketing content post to the live social platform.",
                input_schema={
                    "type": "object",
                    "required": ["post_id"],
                    "properties": {
                        "post_id": {"type": "string", "description": "ID of the ContentPost to publish"},
                        "platform": {"type": "string", "description": "Target platform name"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "post_id": {"type": "string"}}},
                required_scopes=["marketing:write"],
                risk_level="HIGH",
                side_effect="WRITE",
                approval_required=True,
            )
        )

        # 15. lead.score (Sales Lead Scoring)
        self.register(
            ToolDefinition(
                name="lead.score",
                description="Scores and qualifies a CRM sales lead based on firmographic fit and engagement.",
                input_schema={
                    "type": "object",
                    "required": ["lead_id"],
                    "properties": {
                        "lead_id": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 100},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                required_scopes=["sales:write"],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 16. ticket.create (Customer Support Ticket Creation)
        self.register(
            ToolDefinition(
                name="ticket.create",
                description="Creates a new customer support ticket in the Support Helpdesk.",
                input_schema={
                    "type": "object",
                    "required": ["subject"],
                    "properties": {
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "customer_email": {"type": "string"},
                        "priority": {"type": "string", "default": "medium"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "ticket_id": {"type": "string"}}},
                required_scopes=["support:write"],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 17. ticket.close (Customer Support Ticket Closure)
        self.register(
            ToolDefinition(
                name="ticket.close",
                description="Closes an identified customer support ticket upon resolution.",
                input_schema={
                    "type": "object",
                    "required": ["ticket_id"],
                    "properties": {
                        "ticket_id": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                required_scopes=["support:write"],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 18. applicant.create (HR Talent Acquisition)
        self.register(
            ToolDefinition(
                name="applicant.create",
                description="Creates a candidate profile in HR applicant tracking.",
                input_schema={
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "candidate_id": {"type": "string"}}},
                required_scopes=["hr:write"],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 19. applicant.score (HR Applicant Scorecard Evaluation)
        self.register(
            ToolDefinition(
                name="applicant.score",
                description="Evaluates candidate competency and updates applicant scorecard.",
                input_schema={
                    "type": "object",
                    "required": ["candidate_id"],
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "scorecard": {"type": "object"},
                    },
                },
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                required_scopes=["hr:write"],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
            )
        )

        # 20. app.connector_action (Check & Execute Read/Write on External App Connectors)
        self.register(
            ToolDefinition(
                name="app.connector_action",
                description=(
                    "Checks whether an external app connector (e.g. 'instagram', 'facebook', 'linkedin', 'buffer', "
                    "'gmail', 'sendgrid', 'twilio', 'whatsapp', 'calendly', 'zoominfo', 'zapier', 'workato', "
                    "'google_sheets', 'slack', 'notion') is connected, and either executes the read/write action "
                    "directly or returns the connection link and credential prompt if not connected."
                ),
                input_schema={
                    "type": "object",
                    "required": ["app", "operation"],
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "Target app or connector slug (e.g. 'instagram', 'linkedin', 'sendgrid', 'google_sheets', 'slack')",
                        },
                        "operation": {
                            "type": "string",
                            "enum": ["read", "write"],
                            "default": "write",
                            "description": "Whether to read from or write/post to the external app",
                        },
                        "action": {
                            "type": "string",
                            "description": "Specific action name (e.g. 'publish_post', 'send_message', 'fetch_rows')",
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the read/write operation (e.g. caption, hashtags, query, to, body)",
                        },
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "status": {"type": "string"},
                        "connector_required": {"type": "boolean"},
                        "connector": {"type": "object"},
                        "message": {"type": "string"},
                    },
                },
                required_scopes=[],
                risk_level="MEDIUM",
                side_effect="WRITE",
                approval_required=False,
                handler=self._exec_app_connector_action,
            )
        )

        # 21. memory (Hermes Persistent Curated Memory)
        self.register(
            ToolDefinition(
                name="memory",
                description=(
                    "Persistently remembers or updates key facts, user preferences, instructions, and lessons learned across sessions. "
                    "Use action 'add' to record a new fact, 'patch' to edit an existing entry via old_text substring, or 'remove' to drop outdated entries. "
                    "Target 'user' is for user profile/preferences; target 'memory' is for agent personal notes/company facts/environment conventions."
                ),
                input_schema={
                    "type": "object",
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["add", "patch", "remove"], "description": "Memory operation to perform"},
                        "target": {"type": "string", "enum": ["memory", "user"], "default": "memory", "description": "Whether this is agent personal notes ('memory') or user profile ('user')"},
                        "content": {"type": "string", "description": "The information to remember (required for 'add' and 'patch')"},
                        "old_text": {"type": "string", "description": "Unique substring matching the entry to update or remove (required for 'patch' and 'remove')"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                        "capacity": {"type": "object"},
                    },
                },
                required_scopes=[],
                risk_level="LOW",
                side_effect="WRITE",
                approval_required=False,
                handler=self._exec_memory,
            )
        )

        # 22. session_search (Hermes Cross-Session Conversation Recall)
        self.register(
            ToolDefinition(
                name="session_search",
                description=(
                    "Searches past conversation sessions and previous talks using fast keyword search. "
                    "Use this whenever the user asks 'do you remember what we talked about', refers to past decisions, "
                    "or when you need context from prior conversations."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword terms to search across past conversation transcripts"},
                        "session_id": {"type": "string", "description": "Optional specific session ID to inspect"},
                        "limit": {"type": "integer", "default": 5, "description": "Maximum number of historical turns to retrieve"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "count": {"type": "integer"},
                        "matches": {"type": "array"},
                    },
                },
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_session_search,
            )
        )
        self.register(
            ToolDefinition(
                name="agent.notify",
                description="Records a notice for a person or another employee. Does not call tools or change business data.",
                input_schema={
                    "type": "object",
                    "required": ["message"],
                    "properties": {"message": {"type": "string"}},
                },
                output_schema={"type": "object", "properties": {"recorded": {"type": "boolean"}, "outcome": {"type": "string"}}},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_agent_notify,
            )
        )
        from app.services.agents.kernel.browser_session import register_browser_tools
        register_browser_tools(self)

        self.register(
            ToolDefinition(
                name="orodruin.signals",
                description="Fetch live global OSINT signals (GDELT news, USGS earthquakes, NASA EONET hazards) for a topic or region.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "default": "technology"},
                        "region": {"type": "string"},
                        "limit": {"type": "integer", "default": 8},
                    },
                },
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_signals,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.geolocate_ip",
                description="Geolocate an IP address (city, country, ISP/ASN) using OSINT geolocation.",
                input_schema={
                    "type": "object",
                    "required": ["ip"],
                    "properties": {"ip": {"type": "string"}},
                },
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_geolocate,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.cyber_lookup",
                description="Inspect exposed ports, services, and CVEs for an IP via Shodan InternetDB.",
                input_schema={"type": "object", "required": ["ip"], "properties": {"ip": {"type": "string"}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_cyber,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.ransomware",
                description="Fetch recent ransomware victim disclosures (victim, group, country, sector).",
                input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_ransomware,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.finance_awards",
                description="Search US federal contract awards (USASpending) by keyword.",
                input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 8}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_awards,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.research_papers",
                description="Search recent ArXiv research papers on a topic.",
                input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 8}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_papers,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.markets",
                description="Fetch live crypto/market indicators (BTC, ETH, SOL).",
                input_schema={"type": "object", "properties": {}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_markets,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.prediction_markets",
                description="Fetch active Polymarket prediction markets and volumes.",
                input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 8}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_prediction,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.search_sanctions",
                description="Screen an entity or person against OpenSanctions global watchlists.",
                input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 8}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_sanctions,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.ui_action",
                description="Emit a UI control action for the Global Intelligence Map (focus_map, toggle_layer, apply_filters, open_camera).",
                input_schema={
                    "type": "object",
                    "required": ["action"],
                    "properties": {
                        "action": {"type": "string", "enum": ["focus_map", "toggle_layer", "apply_filters", "open_camera"]},
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "zoom": {"type": "number"},
                        "layer": {"type": "string"},
                        "topic": {"type": "string"},
                        "camera_id": {"type": "string"},
                    },
                },
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_ui_action,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.cameras",
                description="Fetch live geolocated public traffic/city cameras (TfL London, LTA Singapore) with image and MP4 URLs.",
                input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 40}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_cameras,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.flights",
                description="Fetch live ADS-B aircraft positions from OpenSky Network.",
                input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 150}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_flights,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.disasters",
                description="Fetch live GDACS global disaster alerts (earthquakes, cyclones, floods, volcanoes).",
                input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 30}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_disasters,
            )
        )
        self.register(
            ToolDefinition(
                name="orodruin.deep_search",
                description="Run deep web + OSINT search combining OctaOS web research with live GDELT intelligence.",
                input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "count": {"type": "integer", "default": 8}}},
                output_schema={"type": "object"},
                required_scopes=[],
                risk_level="LOW",
                side_effect="READ",
                approval_required=False,
                handler=self._exec_orodruin_deep_search,
            )
        )
        for tname, tdesc, tschema, thandler in [
            ("orodruin.weather", "Get live weather for coordinates (Open-Meteo).", {"type": "object", "required": ["lat", "lon"], "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}}}, self._exec_orodruin_weather),
            ("orodruin.air_quality", "Get live air quality (PM2.5, NO2, CO, O3) for coordinates.", {"type": "object", "required": ["lat", "lon"], "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}}}, self._exec_orodruin_aq),
            ("orodruin.space_weather", "Get NOAA SWPC planetary Kp index & space weather.", {"type": "object", "properties": {}}, self._exec_orodruin_spacewx),
            ("orodruin.geocode", "Geocode a place or address into lat/lon coordinates.", {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}}, self._exec_orodruin_geocode),
            ("orodruin.route", "Compute a driving route between two lat/lon coordinates.", {"type": "object", "required": ["from_lat", "from_lon", "to_lat", "to_lon"], "properties": {"from_lat": {"type": "number"}, "from_lon": {"type": "number"}, "to_lat": {"type": "number"}, "to_lon": {"type": "number"}}}, self._exec_orodruin_route),
            ("orodruin.breaches", "List recent public data breaches (Have I Been Pwned).", {"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}, self._exec_orodruin_breaches),
            ("orodruin.news", "Fetch live world RSS news headlines.", {"type": "object", "properties": {"limit": {"type": "integer", "default": 12}}}, self._exec_orodruin_news),
            ("orodruin.cables", "Fetch TeleGeography global submarine cable GeoJSON.", {"type": "object", "properties": {"limit": {"type": "integer", "default": 60}}}, self._exec_orodruin_cables),
            ("orodruin.satellites", "Fetch CelesTrak active orbital stations.", {"type": "object", "properties": {"limit": {"type": "integer", "default": 30}}}, self._exec_orodruin_satellites),
            ("orodruin.area_intel", "Run unified area intelligence briefing (weather + air quality) for lat/lon.", {"type": "object", "required": ["lat", "lon"], "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}}}, self._exec_orodruin_area_intel),
            ("orodruin.find_leads", "Use deep browser/web search + OSINT to discover evidence-backed company leads and optionally save to CRM.", {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "industry": {"type": "string"}, "geography": {"type": "string"}, "count": {"type": "integer", "default": 8}, "save_to_crm": {"type": "boolean", "default": False}}}, self._exec_orodruin_find_leads),
            ("orodruin.site_report", "Analyze tenant-registered sites, cameras, and production feeds with local weather/hazards to generate an AI operational report.", {"type": "object", "properties": {"site_id": {"type": "string"}, "focus": {"type": "string"}}}, self._exec_orodruin_site_report),
        ]:
            self.register(
                ToolDefinition(
                    name=tname,
                    description=tdesc,
                    input_schema=tschema,
                    output_schema={"type": "object"},
                    required_scopes=[],
                    risk_level="LOW",
                    side_effect="READ",
                    approval_required=False,
                    handler=thandler,
                )
            )

    async def _exec_orodruin_signals(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_signals(
            topic=str(args.get("topic") or "technology"),
            region=args.get("region"),
            limit=int(args.get("limit") or 8),
        )

    async def _exec_orodruin_geolocate(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().geolocate_ip(str(args["ip"]))

    async def _exec_orodruin_cyber(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().cyber_lookup(str(args["ip"]))

    async def _exec_orodruin_ransomware(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().get_ransomware(limit=int(args.get("limit") or 10))}

    async def _exec_orodruin_awards(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().finance_awards(str(args["query"]), limit=int(args.get("limit") or 8))}

    async def _exec_orodruin_papers(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().research_papers(str(args["query"]), limit=int(args.get("limit") or 8))}

    async def _exec_orodruin_markets(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().get_markets()

    async def _exec_orodruin_prediction(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().get_prediction_markets(limit=int(args.get("limit") or 8))}

    async def _exec_orodruin_sanctions(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().search_sanctions(str(args["query"]), limit=int(args.get("limit") or 8))}

    async def _exec_orodruin_ui_action(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"ui_action": args, "applied": True}

    async def _exec_orodruin_cameras(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_cameras(limit=int(args.get("limit") or 40))

    async def _exec_orodruin_flights(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_flights(limit=int(args.get("limit") or 150))

    async def _exec_orodruin_disasters(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_disasters(limit=int(args.get("limit") or 30))

    async def _exec_orodruin_deep_search(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().deep_search(db, tenant_id, str(args["query"]), count=int(args.get("count") or 8))

    async def _exec_orodruin_weather(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_weather(float(args["lat"]), float(args["lon"]))

    async def _exec_orodruin_aq(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_air_quality(float(args["lat"]), float(args["lon"]))

    async def _exec_orodruin_spacewx(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_space_weather()

    async def _exec_orodruin_geocode(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"results": await OrodruinIntelService().geocode(str(args["query"]))}

    async def _exec_orodruin_route(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().route(float(args["from_lat"]), float(args["from_lon"]), float(args["to_lat"]), float(args["to_lon"]))

    async def _exec_orodruin_breaches(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().fetch_breaches(limit=int(args.get("limit") or 10))}

    async def _exec_orodruin_news(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return {"items": await OrodruinIntelService().fetch_news_rss(limit=int(args.get("limit") or 12))}

    async def _exec_orodruin_cables(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_submarine_cables(limit=int(args.get("limit") or 60))

    async def _exec_orodruin_satellites(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().fetch_satellites(limit=int(args.get("limit") or 30))

    async def _exec_orodruin_area_intel(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().area_intel(float(args["lat"]), float(args["lon"]))

    async def _exec_orodruin_find_leads(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().find_company_leads(
            db,
            tenant_id,
            query=str(args["query"]),
            industry=args.get("industry"),
            geography=args.get("geography"),
            count=int(args.get("count") or 8),
            save_to_crm=bool(args.get("save_to_crm", False)),
        )

    async def _exec_orodruin_site_report(self, db: Session, tenant_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.orodruin_intel import OrodruinIntelService
        return await OrodruinIntelService().generate_site_report(
            db,
            tenant_id,
            site_id=args.get("site_id"),
            focus=args.get("focus"),
        )


tool_registry = ToolRegistry()
