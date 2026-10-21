"""Enterprise Sales CRM and Account 360 endpoints: canonical accounts, buying committee, opportunities, and agent runs."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import Tenant, User
from app.models.sales_intelligence import SalesCompany, AccountContact, SalesOpportunity, SalesSignal
from app.models.deal_room import DealRoom, BuyingCommitteeMember, DealActivity, DealObjection
from app.models.agent_runtime import AgentRun, AgentTask, ToolInvocation
from app.services.sales.sync_bridge import SalesSyncBridge
from app.services.sales_os.runtime.orchestrator import SalesOrchestrator
from app.services.sales_os.runtime.tool_registry import tool_registry

router = APIRouter(dependencies=[Depends(deps.check_access("sales"))])


class CommitteeMemberCreate(BaseModel):
    name: str
    email: str
    title: str
    role_type: str = Field(default="influencer", description="economic_buyer | champion | technical_evaluator | legal_procurement | blocker | influencer")
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class AgentRunCreate(BaseModel):
    goal: str
    agent_id: str = "sales_orchestrator"
    company_id: Optional[str] = None
    deal_room_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


@router.get("/accounts")
def list_canonical_accounts(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    stage: Optional[str] = None,
):
    """Lists canonical accounts with aggregated buying committee and opportunity status."""
    query = db.query(SalesCompany).filter(SalesCompany.tenant_id == tenant_id)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((SalesCompany.display_name.ilike(s)) | (SalesCompany.canonical_domain.ilike(s)))

    companies = query.order_by(SalesCompany.updated_at.desc()).limit(limit).all()

    accounts = []
    for c in companies:
        deal_room = None
        committee_count = 0
        if c.deal_room_id:
            deal_room = db.query(DealRoom).filter_by(id=c.deal_room_id, tenant_id=tenant_id).first()
            if deal_room:
                committee_count = db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id).count()

        latest_opp = db.query(SalesOpportunity).filter_by(company_id=c.id, tenant_id=tenant_id).order_by(SalesOpportunity.updated_at.desc()).first()

        current_stage = deal_room.stage if deal_room else (latest_opp.stage if latest_opp else "discovered")
        if stage and stage != "all" and current_stage != stage:
            continue

        accounts.append({
            "id": c.id,
            "display_name": c.display_name or (c.canonical_domain.split('.')[0].capitalize() if c.canonical_domain else "Unnamed Account"),
            "legal_name": c.legal_name,
            "canonical_domain": c.canonical_domain,
            "industry": c.industry or "Technology",
            "employee_count": c.employee_count,
            "employee_band": c.employee_band or "50-250",
            "hq_country": c.hq_country,
            "hq_city": c.hq_city,
            "website": c.website or (f"https://{c.canonical_domain}" if c.canonical_domain else None),
            "stage": current_stage,
            "deal_room_id": c.deal_room_id,
            "committee_count": committee_count,
            "is_multi_threaded": deal_room.is_multi_threaded if deal_room else (committee_count >= 2),
            "icp_score": c.icp_score or 75.0,
            "intent_score": c.intent_score or 65.0,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        })

    return accounts


@router.get("/accounts/{company_id}/360")
def get_account_360(
    company_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Retrieves full Account 360 payload including buying committee, signals, activities, and AI recommendations."""
    company = db.query(SalesCompany).filter_by(id=company_id, tenant_id=tenant_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Account not found.")

    deal_room = None
    committee = []
    activities = []
    objections = []

    if company.deal_room_id:
        deal_room = db.query(DealRoom).filter_by(id=company.deal_room_id, tenant_id=tenant_id).first()
        if deal_room:
            committee = db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id).all()
            activities = db.query(DealActivity).filter_by(deal_room_id=deal_room.id).order_by(DealActivity.created_at.desc()).limit(30).all()
            objections = db.query(DealObjection).filter_by(deal_room_id=deal_room.id).all()

    contacts = db.query(AccountContact).filter_by(company_id=company.id, tenant_id=tenant_id).all()
    opportunities = db.query(SalesOpportunity).filter_by(company_id=company.id, tenant_id=tenant_id).all()
    signals = db.query(SalesSignal).filter_by(company_id=company.id, tenant_id=tenant_id).order_by(SalesSignal.observed_at.desc()).limit(20).all()

    # Active agent recommendation derived from deal strategist
    stage = deal_room.stage if deal_room else "discovered"
    recommendation = {
        "recommended_action": "Expand Buying Committee" if len(committee) < 2 else "Schedule Discovery Deep-Dive",
        "rationale": "Single-threaded account risk. Enterprise deals require at least an Economic Buyer and Champion." if len(committee) < 2 else "Multiple stakeholders engaged. Position proof-of-concept and ROI metrics.",
        "urgency": "high" if len(committee) < 2 else "medium",
        "target_persona": "Head of Engineering / VP Sales" if len(committee) < 2 else "Economic Buyer",
    }

    return {
        "company": {
            "id": company.id,
            "display_name": company.display_name,
            "legal_name": company.legal_name,
            "canonical_domain": company.canonical_domain,
            "industry": company.industry,
            "employee_count": company.employee_count,
            "employee_band": company.employee_band,
            "hq_country": company.hq_country,
            "hq_city": company.hq_city,
            "website": company.website,
            "icp_score": company.icp_score,
            "intent_score": company.intent_score,
            "deal_room_id": company.deal_room_id,
            "version": company.version,
        },
        "deal_room": {
            "id": deal_room.id if deal_room else None,
            "stage": stage,
            "is_multi_threaded": deal_room.is_multi_threaded if deal_room else False,
            "annual_revenue_usd": deal_room.annual_revenue_usd if deal_room else None,
            "risk_flags": deal_room.risk_flags if deal_room else [],
        } if deal_room else None,
        "buying_committee": [
            {
                "id": m.id,
                "name": m.name,
                "email": m.email,
                "title": m.title,
                "role_type": m.role_type,
                "engagement_state": m.engagement_state,
                "phone": m.phone,
                "linkedin_url": m.linkedin_url,
                "last_contacted_at": m.last_contacted_at.isoformat() if m.last_contacted_at else None,
            }
            for m in committee
        ],
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
            {
                "id": o.id,
                "stage": o.stage,
                "score": o.score,
                "confidence": o.confidence,
                "explanation": o.explanation,
                "rationale": o.rationale,
            }
            for o in opportunities
        ],
        "signals": [
            {
                "id": s.id,
                "signal_type": s.signal_type,
                "family": s.family,
                "summary": s.summary,
                "base_strength": s.base_strength,
                "observed_at": s.observed_at.isoformat() if s.observed_at else None,
                "source_key": s.source_key,
            }
            for s in signals
        ],
        "activities": [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "channel": a.channel,
                "direction": a.direction,
                "subject": a.subject,
                "content": a.content,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in activities
        ],
        "objections": [
            {
                "id": obj.id,
                "objection_category": obj.objection_category,
                "prospect_statement": obj.prospect_statement,
                "applied_counter_argument": obj.applied_counter_argument,
                "status": obj.status,
            }
            for obj in objections
        ],
        "agent_recommendation": recommendation,
    }


@router.post("/accounts/{company_id}/committee")
def add_buying_committee_member(
    company_id: str,
    member: CommitteeMemberCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Registers a stakeholder into the account's Buying Committee."""
    company = db.query(SalesCompany).filter_by(id=company_id, tenant_id=tenant_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Account not found.")

    bridge = SalesSyncBridge(db, tenant_id)
    # Ensure deal room exists
    deal_room = None
    if company.deal_room_id:
        deal_room = db.query(DealRoom).filter_by(id=company.deal_room_id, tenant_id=tenant_id).first()

    if not deal_room:
        deal_room = DealRoom(
            tenant_id=tenant_id,
            company_name=company.display_name or company.canonical_domain or "Account",
            domain=company.canonical_domain or "account.com",
            website=company.website,
            stage="discovered",
        )
        db.add(deal_room)
        db.flush()
        company.deal_room_id = deal_room.id

    bcm = BuyingCommitteeMember(
        deal_room_id=deal_room.id,
        tenant_id=tenant_id,
        name=member.name,
        email=member.email,
        title=member.title,
        role_type=member.role_type,
        phone=member.phone,
        linkedin_url=member.linkedin_url,
        engagement_state="uncontacted",
    )
    db.add(bcm)

    # Check multi-threading
    total = db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id).count() + 1
    if total >= 2:
        deal_room.is_multi_threaded = True

    db.commit()
    db.refresh(bcm)

    return {
        "status": "created",
        "id": bcm.id,
        "name": bcm.name,
        "email": bcm.email,
        "role_type": bcm.role_type,
        "is_multi_threaded": deal_room.is_multi_threaded,
    }


@router.post("/reconcile")
def reconcile_leads(
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Executes bulk transactional reconciliation between legacy leads and canonical entities."""
    bridge = SalesSyncBridge(db, tenant_id)
    result = bridge.reconcile_tenant_leads_to_canonical(limit=limit)
    return result


@router.get("/agents/runs")
def list_agent_runs(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    limit: int = Query(30, ge=1, le=100),
):
    """Lists observable agent runs with status, goals, and metrics."""
    runs = (
        db.query(AgentRun)
        .filter_by(tenant_id=tenant_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "status": r.status,
            "goal": r.goal,
            "deal_room_id": r.deal_room_id,
            "company_id": r.company_id,
            "tokens_used": r.tokens_used,
            "cost_usd": r.cost_usd,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.post("/agents/run")
def trigger_agent_run(
    req: AgentRunCreate,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Dispatches a durable agent task session."""
    orchestrator = SalesOrchestrator(db, tenant_id)
    run = orchestrator.start_run(
        goal=req.goal,
        agent_id=req.agent_id,
        deal_room_id=req.deal_room_id,
        company_id=req.company_id,
        input_payload=req.parameters,
    )
    return {"status": "started", "run_id": run.id, "agent_id": run.agent_id}


class SignalIngestRequest(BaseModel):
    company_id: str
    signal_type: str = Field(..., description="ats_hiring_surge | series_funding | tech_migration | executive_hire")
    family: str = Field(..., description="hiring | funding | technographic | leadership | reviews")
    summary: str
    base_strength: float = 75.0
    source_confidence: float = 0.90
    half_life_days: int = 30
    source_key: str = "ats_greenhouse"
    source_url: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


@router.post("/signals/ingest")
def ingest_intent_signal(
    req: SignalIngestRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Ingests a verified intent signal into the Intent Signal Bus with provenance and convergence."""
    from app.services.sales_os.signals.bus import IntentSignalBus
    bus = IntentSignalBus(db, tenant_id)
    return bus.ingest_signal(
        company_id=req.company_id,
        signal_type=req.signal_type,
        family=req.family,
        summary=req.summary,
        base_strength=req.base_strength,
        source_confidence=req.source_confidence,
        half_life_days=req.half_life_days,
        source_key=req.source_key,
        source_url=req.source_url,
        payload=req.payload,
    )


@router.get("/signals/feed")
def get_tenant_signals_feed(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    limit: int = Query(50, ge=1, le=200),
):
    """Returns chronological feed of verified intent signals across all tenant accounts."""
    from app.services.sales_os.signals.bus import IntentSignalBus
    bus = IntentSignalBus(db, tenant_id)
    return bus.get_tenant_signal_feed(limit=limit)


@router.get("/signals/accounts/{company_id}")
def get_account_signals_detail(
    company_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Fetches decayed intent signals and convergence bonus for an account."""
    from app.services.sales_os.signals.bus import IntentSignalBus
    bus = IntentSignalBus(db, tenant_id)
    return bus.get_account_signals(company_id=company_id)


@router.get("/territory/plan")
async def get_territory_route_plan(
    rep_id: str = Query("rep_field_1", description="Sales rep identifier"),
    lat: float = Query(37.7749, description="Starting GPS latitude"),
    lon: float = Query(-122.4194, description="Starting GPS longitude"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Generates an optimized territory route plan and field visit itinerary with contingencies."""
    from app.services.sales_os.agents.territory_route import TerritoryRoutePlannerAgent
    agent = TerritoryRoutePlannerAgent(db, tenant_id)
    res = await agent.execute(
        parameters={
            "rep_id": rep_id,
            "start_latitude": lat,
            "start_longitude": lon,
        }
    )
    if res.data:
        return res.data.dict() if hasattr(res.data, "dict") else res.data
    return {"plan": None, "evidence": [e.dict() for e in res.evidence]}


@router.get("/intelligence/source-roi")
def get_source_roi_summary(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Returns multi-touch source ROI attribution across prospecting sources."""
    from app.models.sales_intelligence import SourceCost
    from app.services.sales_os.attribution.source_roi import summarize_roi

    costs = db.query(SourceCost).filter(SourceCost.tenant_id == tenant_id).all()
    cost_dicts = [
        {
            "provider_key": c.provider_key,
            "actual_amount": c.actual_amount,
            "estimated_amount": c.estimated_amount,
        }
        for c in costs
    ]

    rooms = db.query(DealRoom).filter(DealRoom.tenant_id == tenant_id).all()
    outcomes = []
    for r in rooms:
        meta = r.room_metadata or {}
        prov = meta.get("source_provider") or "apollo"
        outcomes.append({
            "provider_key": prov,
            "outcome_type": "meeting" if r.stage in ("meeting_booked", "proposal", "closing", "won") else "verified_lead",
            "amount": float(r.annual_revenue_usd or 0) if r.stage == "won" else None,
            "touch_role": "first",
        })

    return summarize_roi(costs=cost_dicts, outcomes=outcomes)


# ── PHASE 4: CPQ, DEAL DESK & STAGE GATEKEEPER ENDPOINTS ──

class CPQCalculateRequest(BaseModel):
    deal_room_id: Optional[str] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    requested_discount_pct: float = 0.0
    contract_term_months: int = 12
    payment_terms: str = "Net 30"


class CreateQuoteRequest(BaseModel):
    deal_room_id: str
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    requested_discount_pct: float = 0.0
    contract_term_months: int = 12
    payment_terms: str = "Net 30"


class GenerateProposalRequest(BaseModel):
    deal_room_id: str
    client_signatory_name: Optional[str] = None
    client_signatory_title: Optional[str] = None
    custom_notes: Optional[str] = None


class StageAdvanceRequest(BaseModel):
    target_stage: str
    loss_reason: Optional[str] = None
    notes: Optional[str] = None


@router.get("/cpq/catalog")
def get_cpq_catalog():
    """Returns standard product catalog and pricing for CPQ quote generation."""
    from app.services.sales_os.cpq.pricing_engine import STANDARD_CATALOG
    return STANDARD_CATALOG


@router.post("/cpq/calculate")
def calculate_cpq_quote(req: CPQCalculateRequest):
    """Calculates deterministic quote totals, tiered discounts, ROI, and approval policies."""
    from app.services.sales_os.cpq.pricing_engine import CPQPricingEngine
    res = CPQPricingEngine.calculate_quote(
        line_items_input=req.line_items,
        requested_discount_pct=req.requested_discount_pct,
        contract_term_months=req.contract_term_months,
        payment_terms=req.payment_terms,
    )
    return res.dict()


@router.post("/cpq/quotes/create")
def create_and_persist_quote(
    req: CreateQuoteRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Calculates and saves quote into the deal room, creating an approval request if discount requires sign-off."""
    from app.services.sales_os.cpq.pricing_engine import CPQPricingEngine
    from app.models.enterprise import ApprovalRequest

    deal_room = (
        db.query(DealRoom)
        .filter(DealRoom.id == req.deal_room_id, DealRoom.tenant_id == tenant_id)
        .first()
    )
    if not deal_room:
        raise HTTPException(status_code=404, detail="DealRoom not found")

    calc = CPQPricingEngine.calculate_quote(
        line_items_input=req.line_items,
        requested_discount_pct=req.requested_discount_pct,
        contract_term_months=req.contract_term_months,
        payment_terms=req.payment_terms,
    )

    # Save to DealRoom
    brief = dict(deal_room.account_brief or {})
    brief["latest_quote"] = calc.dict()
    deal_room.account_brief = brief
    deal_room.annual_revenue_usd = calc.net_total_usd

    # If requires approval, queue in ApprovalRequest
    approval_id = None
    if calc.policy_status in ("requires_manager_approval", "requires_vp_approval"):
        appr = ApprovalRequest(
            tenant_id=tenant_id,
            action_type="cpq_quote_approval",
            agent_name="deal_desk_agent",
            resource_type="deal_room",
            resource_id=deal_room.id,
            title=f"CPQ Discount Approval ({calc.total_discount_pct:.1f}%) for {deal_room.company_name}",
            payload=calc.dict(),
            confidence=1.0,
            status="pending",
            policy_reason=calc.policy_reason,
            requested_by="deal_desk",
        )
        db.add(appr)
        db.flush()
        approval_id = appr.id

    # Log activity
    act = DealActivity(
        deal_room_id=deal_room.id,
        tenant_id=tenant_id,
        activity_type="quote_created",
        channel="cpq",
        direction="internal",
        subject=f"Quote {calc.quote_number} generated (${calc.net_total_usd:,.2f})",
        content=f"Pricing quote {calc.quote_number} calculated with {calc.total_discount_pct:.1f}% total discount. Policy status: {calc.policy_status}",
        metadata_json={
            "quote_number": calc.quote_number,
            "net_total_usd": calc.net_total_usd,
            "policy_status": calc.policy_status,
            "approval_id": approval_id,
        },
    )
    db.add(act)
    db.commit()

    return {
        "success": True,
        "deal_room_id": deal_room.id,
        "quote": calc.dict(),
        "approval_id": approval_id,
    }


@router.get("/cpq/quotes/{deal_room_id}")
def get_deal_room_quote(
    deal_room_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Retrieves active quote, proposal, and approval status for a deal room."""
    deal_room = (
        db.query(DealRoom)
        .filter(DealRoom.id == deal_room_id, DealRoom.tenant_id == tenant_id)
        .first()
    )
    if not deal_room:
        raise HTTPException(status_code=404, detail="DealRoom not found")

    brief = deal_room.account_brief or {}
    latest_quote = brief.get("latest_quote")
    latest_proposal = brief.get("latest_proposal")

    return {
        "deal_room_id": deal_room.id,
        "company_name": deal_room.company_name,
        "stage": deal_room.stage,
        "deal_size": deal_room.annual_revenue_usd,
        "latest_quote": latest_quote,
        "latest_proposal": latest_proposal,
    }


@router.post("/cpq/proposals/generate")
def generate_commercial_proposal(
    req: GenerateProposalRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Generates official commercial proposal and contract markdown with cryptographic SHA-256 integrity hash."""
    from app.services.sales_os.cpq.pricing_engine import CPQPricingEngine, QuoteCalculationResult
    from app.services.sales_os.cpq.proposal_generator import ProposalDocumentGenerator

    deal_room = (
        db.query(DealRoom)
        .filter(DealRoom.id == req.deal_room_id, DealRoom.tenant_id == tenant_id)
        .first()
    )
    if not deal_room:
        raise HTTPException(status_code=404, detail="DealRoom not found")

    brief = deal_room.account_brief or {}
    raw_quote = brief.get("latest_quote")
    if not raw_quote:
        # Generate default quote on the fly if none exists
        calc = CPQPricingEngine.calculate_quote(line_items_input=[])
    else:
        calc = QuoteCalculationResult(**raw_quote)

    gen = ProposalDocumentGenerator(db, tenant_id)
    proposal = gen.generate_proposal(
        deal_room=deal_room,
        quote=calc,
        client_signatory_name=req.client_signatory_name,
        client_signatory_title=req.client_signatory_title,
        custom_notes=req.custom_notes,
    )
    return proposal


@router.post("/cpq/quotes/{deal_room_id}/approve")
def approve_deal_quote(
    deal_room_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Approves a pending commercial quote and marks policy status as approved."""
    from app.models.enterprise import ApprovalRequest
    from datetime import datetime, timezone

    deal_room = (
        db.query(DealRoom)
        .filter(DealRoom.id == deal_room_id, DealRoom.tenant_id == tenant_id)
        .first()
    )
    if not deal_room:
        raise HTTPException(status_code=404, detail="DealRoom not found")

    brief = dict(deal_room.account_brief or {})
    quote_data = brief.get("latest_quote")
    if not quote_data:
        raise HTTPException(status_code=400, detail="No active quote to approve")

    quote_data["policy_status"] = "auto_approved"
    quote_data["policy_reason"] = f"Approved by manager {current_user.email} on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    brief["latest_quote"] = quote_data
    deal_room.account_brief = brief

    # Update ApprovalRequest if exists
    appr = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.tenant_id == tenant_id,
            ApprovalRequest.resource_id == deal_room.id,
            ApprovalRequest.action_type == "cpq_quote_approval",
            ApprovalRequest.status == "pending",
        )
        .first()
    )
    if appr:
        appr.status = "approved"
        appr.reviewed_by = current_user.id
        appr.reviewed_at = datetime.now(timezone.utc)
        appr.review_note = "Approved by manager via Deal Desk"

    # Log DealActivity
    act = DealActivity(
        deal_room_id=deal_room.id,
        tenant_id=tenant_id,
        activity_type="quote_approved",
        channel="deal_desk",
        direction="internal",
        subject=f"Quote {quote_data.get('quote_number')} approved",
        content=f"Commercial discount approved by {current_user.email}",
        metadata_json={"approved_by": current_user.email, "quote_number": quote_data.get("quote_number")},
    )
    db.add(act)
    db.commit()

    return {"success": True, "message": "Quote discount approved successfully", "quote": quote_data}


@router.get("/deal-rooms/{deal_room_id}/stage-check")
def check_stage_readiness(
    deal_room_id: str,
    target_stage: str = Query(..., description="Stage to evaluate advancement to"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Evaluates whether deal room meets entry criteria for target stage without advancing it."""
    from app.services.sales_os.cpq.stage_gatekeeper import StageTransitionGatekeeper

    deal_room = (
        db.query(DealRoom)
        .filter(DealRoom.id == deal_room_id, DealRoom.tenant_id == tenant_id)
        .first()
    )
    if not deal_room:
        raise HTTPException(status_code=404, detail="DealRoom not found")

    gatekeeper = StageTransitionGatekeeper(db, tenant_id)
    allowed, reason, missing = gatekeeper.evaluate_transition(deal_room, target_stage)

    return {
        "deal_room_id": deal_room.id,
        "current_stage": deal_room.stage,
        "target_stage": target_stage,
        "allowed": allowed,
        "reason": reason,
        "missing_criteria": missing,
    }


@router.patch("/deal-rooms/{deal_room_id}/stage")
def advance_deal_room_stage(
    deal_room_id: str,
    req: StageAdvanceRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
):
    """Validates criteria and advances deal stage across DealRoom, Opportunity, and Lead."""
    from app.services.sales_os.cpq.stage_gatekeeper import StageTransitionGatekeeper

    gatekeeper = StageTransitionGatekeeper(db, tenant_id)
    res = gatekeeper.execute_transition(
        deal_room_id=deal_room_id,
        target_stage=req.target_stage,
        loss_reason=req.loss_reason,
        notes=req.notes,
        user_id=current_user.id if current_user else None,
    )
    if not res.get("success"):
        raise HTTPException(
            status_code=400,
            detail={
                "message": res.get("reason"),
                "missing_criteria": res.get("missing_criteria"),
            },
        )
    return res


# ── PHASE 5: REVENUE LIFECYCLE, FORECASTING & WIN/LOSS ENDPOINTS ──

@router.get("/lifecycle/forecast")
def get_executive_pipeline_forecast(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Returns probabilistic pipeline forecasting (Commit, Best Case, Coverage, At-Risk Audits, Monday Brief)."""
    from app.services.sales_os.lifecycle.revenue_lifecycle import RevenueLifecycleEngine
    engine = RevenueLifecycleEngine(db, tenant_id)
    return engine.get_executive_forecast()


@router.get("/lifecycle/win-loss")
def get_win_loss_intelligence(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Returns win/loss root cause analytics, competitor head-to-head records, and sales cycle velocities."""
    from app.services.sales_os.lifecycle.revenue_lifecycle import RevenueLifecycleEngine
    engine = RevenueLifecycleEngine(db, tenant_id)
    return engine.get_win_loss_intelligence()


@router.get("/lifecycle/cohorts")
def get_renewal_and_expansion_cohorts(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
):
    """Returns 30/60/90-day renewal watchlist with churn risk scores and expansion/upsell opportunities."""
    from app.services.sales_os.lifecycle.revenue_lifecycle import RevenueLifecycleEngine
    engine = RevenueLifecycleEngine(db, tenant_id)
    return engine.get_renewal_and_expansion_cohorts()


