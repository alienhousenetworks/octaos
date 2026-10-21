"""Enterprise Typed Tool Registry with Authorization, Suppression Enforcement, and Result Verification."""
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.agent_runtime import ToolInvocation
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    def __init__(self, message: str, code: str = "tool_error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        permission: str = "sales:read",
        is_external: bool = False,
        verifier: Optional[Callable[[Session, str, Any, Dict[str, Any]], Tuple[bool, str]]] = None,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.permission = permission
        self.is_external = is_external
        self.verifier = verifier


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        permission: str = "sales:read",
        is_external: bool = False,
        verifier: Optional[Callable[[Session, str, Any, Dict[str, Any]], Tuple[bool, str]]] = None,
    ):
        """Decorator to register a typed agent tool."""
        def decorator(func: Callable):
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                handler=func,
                permission=permission,
                is_external=is_external,
                verifier=verifier,
            )
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "name": tool.name,
                "description": tool.description,
                "permission": tool.permission,
                "is_external": tool.is_external,
            }
            for name, tool in self._tools.items()
        }

    async def execute(
        self,
        tool_name: str,
        tenant_id: str,
        parameters: Dict[str, Any],
        db: Session,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: str = "unknown_agent",
    ) -> Dict[str, Any]:
        """
        Executes a typed tool under strict tenant isolation, compliance suppression checks,
        and side-effect verification.
        """
        if not tenant_id:
            raise ToolExecutionError("Tenant ID is required for tool execution.", code="missing_tenant")

        tool = self.get_tool(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool '{tool_name}' not registered in ToolRegistry.", code="unknown_tool")

        # 1. Global Compliance & Suppression Gate for outbound communications
        if tool.is_external:
            target_email = parameters.get("email") or parameters.get("recipient_email")
            target_domain = parameters.get("domain") or parameters.get("canonical_domain")
            target_phone = parameters.get("phone")

            suppression = SuppressionService(db, tenant_id)
            if target_email and suppression.is_suppressed(email=target_email):
                raise ToolExecutionError(
                    f"Outbound dispatch blocked: Email '{target_email}' is on the tenant suppression list.",
                    code="suppressed_email",
                )
            if target_domain and suppression.is_suppressed(domain=target_domain):
                raise ToolExecutionError(
                    f"Outbound dispatch blocked: Domain '{target_domain}' is on the tenant suppression list.",
                    code="suppressed_domain",
                )
            if target_phone and suppression.is_suppressed(phone=target_phone):
                raise ToolExecutionError(
                    f"Outbound dispatch blocked: Phone '{target_phone}' is on the tenant suppression list.",
                    code="suppressed_phone",
                )

        # 2. Execution with Latency and Parameter Hashing
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        param_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()

        start_time = time.perf_counter()
        verified = True
        verification_details = "Default auto-verified"
        error_msg = None
        result = None

        try:
            # Inspect if handler is async or sync
            import inspect
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(db=db, tenant_id=tenant_id, **parameters)
            else:
                result = tool.handler(db=db, tenant_id=tenant_id, **parameters)

            # 3. Consequential Side-Effect Verification
            if tool.verifier:
                try:
                    verified, verification_details = tool.verifier(db, tenant_id, result, parameters)
                except Exception as verif_err:
                    verified = False
                    verification_details = f"Verification failed with exception: {verif_err}"

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Error executing tool {tool_name} for tenant {tenant_id}: {e}")
            raise ToolExecutionError(f"Failed to execute tool '{tool_name}': {e}", code="execution_failed")

        finally:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # 4. Immutable Audit Log Persistence
            try:
                invocation = ToolInvocation(
                    run_id=run_id,
                    task_id=task_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    parameters=parameters,
                    parameters_hash=param_hash,
                    result=result if isinstance(result, (dict, list, str, int, float, bool)) else {"status": "executed"},
                    verified=verified,
                    verification_details=verification_details,
                    latency_ms=latency_ms,
                    cost_usd=parameters.get("estimated_cost", 0.0),
                )
                db.add(invocation)
                db.flush()
            except Exception as audit_err:
                logger.error(f"Failed to log ToolInvocation: {audit_err}")

        return {
            "tool_name": tool_name,
            "status": "success" if verified else "unverified_side_effect",
            "verified": verified,
            "verification_details": verification_details,
            "latency_ms": latency_ms,
            "data": result,
        }


# Global tool registry instance
tool_registry = ToolRegistry()


# --- Core Registered Enterprise Tools ---

@tool_registry.register(
    name="query_account_360",
    description="Loads complete account canonical profile, buying committee, signals, and deal room state.",
    permission="sales:read",
    is_external=False,
)
def tool_query_account_360(db: Session, tenant_id: str, company_id: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
    from app.models.sales_intelligence import SalesCompany, AccountContact, SalesOpportunity, SalesSignal
    from app.models.deal_room import DealRoom, BuyingCommitteeMember
    from app.services.sales_os.discovery.identity import canonical_domain

    dom = canonical_domain(domain) if domain else None
    company = None
    if company_id:
        company = db.query(SalesCompany).filter_by(id=company_id, tenant_id=tenant_id).first()
    elif dom:
        company = db.query(SalesCompany).filter_by(canonical_domain=dom, tenant_id=tenant_id).first()

    if not company:
        return {"found": False, "message": "Account not found in canonical Sales OS."}

    contacts = db.query(AccountContact).filter_by(company_id=company.id, tenant_id=tenant_id).all()
    opportunities = db.query(SalesOpportunity).filter_by(company_id=company.id, tenant_id=tenant_id).all()
    signals = db.query(SalesSignal).filter_by(company_id=company.id, tenant_id=tenant_id).limit(20).all()

    deal_room = None
    committee = []
    if company.deal_room_id:
        deal_room = db.query(DealRoom).filter_by(id=company.deal_room_id, tenant_id=tenant_id).first()
        if deal_room:
            committee = db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, tenant_id=tenant_id).all()

    return {
        "found": True,
        "company": {
            "id": company.id,
            "legal_name": company.legal_name,
            "display_name": company.display_name,
            "canonical_domain": company.canonical_domain,
            "industry": company.industry,
            "employee_count": company.employee_count,
            "hq_country": company.hq_country,
            "hq_city": company.hq_city,
            "website": company.website,
            "icp_score": company.icp_score,
            "intent_score": company.intent_score,
        },
        "contacts_count": len(contacts),
        "contacts": [
            {
                "id": c.id,
                "full_name": c.full_name,
                "role_title": c.role_title,
                "seniority": c.seniority,
                "email": c.email,
                "phone": c.phone,
                "linkedin_url": c.linkedin_url,
            }
            for c in contacts
        ],
        "opportunities": [
            {"id": o.id, "stage": o.stage, "score": o.score, "confidence": o.confidence}
            for o in opportunities
        ],
        "signals_count": len(signals),
        "deal_room_id": deal_room.id if deal_room else None,
        "buying_committee": [
            {
                "id": m.id,
                "name": m.name,
                "email": m.email,
                "title": m.title,
                "role_type": m.role_type,
                "engagement_state": m.engagement_state,
            }
            for m in committee
        ],
    }


def _verify_buying_committee_member_saved(db: Session, tenant_id: str, result: Any, parameters: Dict[str, Any]) -> Tuple[bool, str]:
    from app.models.deal_room import BuyingCommitteeMember
    member_id = result.get("member_id") if isinstance(result, dict) else None
    if not member_id:
        return False, "Result did not return a member_id."
    record = db.query(BuyingCommitteeMember).filter_by(id=member_id, tenant_id=tenant_id).first()
    if not record:
        return False, f"Verification failed: Member '{member_id}' not found in database."
    return True, f"Verified BuyingCommitteeMember '{record.email}' successfully committed."


@tool_registry.register(
    name="upsert_buying_committee_member",
    description="Registers or updates a stakeholder on the account's Buying Committee with designated role.",
    permission="sales:write",
    is_external=False,
    verifier=_verify_buying_committee_member_saved,
)
def tool_upsert_buying_committee_member(
    db: Session,
    tenant_id: str,
    deal_room_id: str,
    name: str,
    email: str,
    title: str,
    role_type: str = "influencer",
    phone: Optional[str] = None,
    linkedin_url: Optional[str] = None,
) -> Dict[str, Any]:
    from app.models.deal_room import DealRoom, BuyingCommitteeMember

    deal_room = db.query(DealRoom).filter_by(id=deal_room_id, tenant_id=tenant_id).first()
    if not deal_room:
        raise ToolExecutionError(f"DealRoom '{deal_room_id}' not found.", code="deal_room_missing")

    member = db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room_id, email=email).first()
    if member:
        member.name = name
        member.title = title
        member.role_type = role_type
        if phone:
            member.phone = phone
        if linkedin_url:
            member.linkedin_url = linkedin_url
    else:
        member = BuyingCommitteeMember(
            deal_room_id=deal_room_id,
            tenant_id=tenant_id,
            name=name,
            email=email,
            phone=phone,
            title=title,
            role_type=role_type,
            linkedin_url=linkedin_url,
            engagement_state="uncontacted",
        )
        db.add(member)

    # Check multi-threading status
    total_members = db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room_id).count()
    if total_members >= 2:
        deal_room.is_multi_threaded = True

    db.flush()
    return {"status": "saved", "member_id": member.id, "email": member.email, "role_type": member.role_type}
