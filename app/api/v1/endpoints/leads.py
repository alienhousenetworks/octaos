from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from pydantic import BaseModel
import csv
import io
import json
from app.api import deps
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User, APICredential
from app.schemas import verticals as schemas
from app.models import verticals as models
from app.services.verticals.sales import SalesService
from app.worker.tasks import score_lead_task
from datetime import datetime, timedelta

router = APIRouter()


class WhatsAppOptInRequest(BaseModel):
    opted_in: bool
    source: str
    notes: Optional[str] = None

@router.post("/", response_model=schemas.Lead)
async def create_lead(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.CREATE)),
    lead_in: schemas.LeadCreate
) -> Any:
    lead_data = lead_in.dict()
    if not lead_data.get("room_id") or lead_data.get("room_id") == "sales-default":
        from app.models.rooms import SectionRoom
        default_room = db.query(SectionRoom).filter(
            SectionRoom.tenant_id == tenant_id,
            SectionRoom.section == "sales",
            SectionRoom.slug == "default"
        ).first()
        lead_data["room_id"] = default_room.id if default_room else None
    lead = models.Lead(**lead_data, tenant_id=tenant_id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    # Trigger async scoring
    try:
        score_lead_task.delay(tenant_id, lead.id)
    except Exception:
        pass
    
    return lead

@router.get("/", response_model=List[schemas.Lead])
def read_leads(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.READ)),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    time_filter: Optional[str] = None,
    assigned_to: Optional[str] = None,
    room_id: Optional[str] = None,
    room_slug: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    from sqlalchemy import or_
    from app.models.rooms import SectionRoom

    query = db.query(models.Lead).filter(models.Lead.tenant_id == tenant_id)
    
    if room_slug:
        r = db.query(SectionRoom).filter(
            SectionRoom.tenant_id == tenant_id,
            SectionRoom.section == "sales",
            SectionRoom.slug == room_slug
        ).first()
        if r:
            if room_slug == "default":
                query = query.filter(or_(models.Lead.room_id == r.id, models.Lead.room_id.is_(None), models.Lead.room_id == "sales-default"))
            else:
                query = query.filter(models.Lead.room_id == r.id)
    elif room_id:
        r = db.query(SectionRoom).filter(SectionRoom.id == room_id).first()
        if r and r.slug == "default":
            query = query.filter(or_(models.Lead.room_id == room_id, models.Lead.room_id.is_(None), models.Lead.room_id == "sales-default"))
        elif room_id == "sales-default":
            default_room = db.query(SectionRoom).filter(
                SectionRoom.tenant_id == tenant_id,
                SectionRoom.section == "sales",
                SectionRoom.slug == "default"
            ).first()
            if default_room:
                query = query.filter(or_(models.Lead.room_id == default_room.id, models.Lead.room_id.is_(None), models.Lead.room_id == "sales-default"))
            else:
                query = query.filter(or_(models.Lead.room_id.is_(None), models.Lead.room_id == "sales-default"))
        else:
            query = query.filter(models.Lead.room_id == room_id)
    
    if status and status != "all":
        query = query.filter(models.Lead.status == status)
    if priority and priority != "all":
        query = query.filter(models.Lead.priority == priority)
    if assigned_to and assigned_to != "all":
        query = query.filter(models.Lead.assigned_to == assigned_to)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (models.Lead.name.like(search_filter)) | 
            (models.Lead.company.like(search_filter)) | 
            (models.Lead.email.like(search_filter)) |
            (models.Lead.personal_email.like(search_filter)) |
            (models.Lead.company_email.like(search_filter))
        )
    if time_filter and time_filter != "all":
        now = datetime.utcnow()
        if time_filter == "day":
            query = query.filter(models.Lead.created_at >= now - timedelta(days=1))
        elif time_filter == "week":
            query = query.filter(models.Lead.created_at >= now - timedelta(days=7))
        elif time_filter == "month":
            query = query.filter(models.Lead.created_at >= now - timedelta(days=30))
            
    leads = query.order_by(models.Lead.created_at.desc()).offset(skip).limit(limit).all()
    return leads

@router.patch("/{lead_id}", response_model=schemas.Lead)
def update_lead(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
    lead_id: str,
    lead_in: dict
) -> Any:
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Update fields
    for field, value in lead_in.items():
        if hasattr(lead, field):
            setattr(lead, field, value)
            
    db.commit()
    db.refresh(lead)
    return lead

@router.post("/{lead_id}/whatsapp-opt-in")
def update_whatsapp_opt_in(
    lead_id: str,
    payload: WhatsAppOptInRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    actor: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    phone = lead.phone or lead.mobile_no or lead.company_contact_no
    if not phone:
        raise HTTPException(status_code=422, detail="A recipient phone number is required to record WhatsApp consent.")

    source = (payload.source or "").strip()
    if not source or source.lower() in {"unknown", "n/a", "not recorded"}:
        raise HTTPException(status_code=400, detail="Record the actual consent source; do not infer opt-in.")

    from app.services.sales_os.governance.suppression import SuppressionService
    suppression = SuppressionService(db, tenant_id)
    lead_data = dict(lead.data or {})
    now = datetime.utcnow().isoformat() + "Z"

    if payload.opted_in:
        suppressed = suppression.is_suppressed(phone=phone, channel="whatsapp")
        if suppressed:
            raise HTTPException(
                status_code=409,
                detail="This recipient is suppressed for WhatsApp. Resolve the suppression through the authorized process before recording new consent.",
            )
        lead_data["whatsapp_opt_in"] = True
        lead_data["whatsapp_opt_in_source"] = source
        lead_data["whatsapp_opt_in_at"] = now
        lead_data.pop("whatsapp_opt_out_at", None)
    else:
        lead_data["whatsapp_opt_in"] = False
        lead_data["whatsapp_opt_in_source"] = source
        lead_data["whatsapp_opt_in_at"] = now
        lead_data["whatsapp_opt_out_at"] = now
        suppression.add_suppression(
            "phone",
            phone,
            reason="recipient_whatsapp_opt_out",
            origin="user",
            notes=payload.notes or source,
            channel="whatsapp",
        )

    # Keep the recipient-level contact object and top-level compatibility fields in sync.
    consent_fields = {
        key: lead_data[key]
        for key in ("whatsapp_opt_in", "whatsapp_opt_in_source", "whatsapp_opt_in_at", "whatsapp_opt_out_at")
        if key in lead_data
    }
    contact_data = lead_data.get("contact") if isinstance(lead_data.get("contact"), dict) else {}
    contact_data = dict(contact_data)
    contact_data.update(consent_fields)
    lead_data["contact"] = contact_data

    lead.data = lead_data
    db.commit()
    db.refresh(lead)
    return {
        "status": "recorded",
        "opted_in": bool(payload.opted_in),
        "lead_id": lead.id,
        "recorded_at": now,
        "message": "Recipient consent state recorded; outbound channel and evidence gates still apply.",
    }


@router.post("/{lead_id}/outreach")
async def generate_outreach(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    service = SalesService(db, tenant_id)
    try:
        message = await service.generate_outreach(lead_id)
    except ValueError as e:
        ve_str = str(e)
        provider = None
        for p in ["linkedin", "meta", "facebook", "instagram", "twitter", "gmail", "whatsapp", "apollo", "hunter", "google_places", "google_calendar", "smtp", "greenhouse", "lever", "openai", "anthropic", "gemini"]:
            if p in ve_str.lower():
                provider = p
                break
        if provider:
            msg = (
                f"Configure the {provider} integration in OctaOS Settings. "
                "Do not paste API keys, SMTP passwords, or other secrets into chat."
            )
            return {"status": "action_required", "sent": False, "message": msg}
        raise HTTPException(status_code=400, detail=str(e))

    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not isinstance(message, str) or not message.strip():
        return {
            "status": "blocked_no_draft",
            "sent": False,
            "message": "No outreach draft was produced. Nothing was sent.",
        }

    # This endpoint creates a draft only. A draft is not a provider receipt and
    # must never advance the lead to contacted or populate sent-at fields.
    now = datetime.utcnow().isoformat()
    subject = f"Partnership Opportunity - {lead.company or 'Prospect'}"
    lead_data = dict(lead.data or {})
    lead_data["outreach_draft"] = {
        "channel": "email",
        "subject": subject,
        "body": message.strip(),
        "status": "draft",
        "created_at": now,
        "requires_authorization": True,
    }
    lead_data["draft_subject"] = subject
    lead_data["draft_body"] = message.strip()
    lead.data = lead_data
    db.commit()
    db.refresh(lead)

    return {
        "status": "draft_ready",
        "sent": False,
        "requires_authorization": True,
        "lead_id": lead.id,
        "subject": subject,
        "message": message.strip(),
    }

@router.post("/{lead_id}/schedule_meeting")
async def schedule_meeting(
    lead_id: str,
    payload: dict | None = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = dict(lead.data or {})
    reply_classification = lead_data.get("reply_classification")
    reply_classification = reply_classification if isinstance(reply_classification, dict) else {}
    suggested_time = (
        (payload or {}).get("suggested_time")
        or lead_data.get("meeting_requested_at")
        or reply_classification.get("suggested_time")
    )
    if not suggested_time:
        return {
            "status": "needs_time_confirmation",
            "booked": False,
            "message": "No explicit meeting time is recorded. Confirm a date, time, and timezone with the prospect before booking.",
        }

    from app.services.sales.meeting_booking import book_meeting_for_lead

    try:
        booked = book_meeting_for_lead(
            db,
            tenant_id,
            lead,
            suggested_time=str(suggested_time),
        )
    except ValueError as exc:
        return {
            "status": "action_required",
            "booked": False,
            "message": str(exc),
        }

    db.refresh(lead)
    if not booked:
        return {
            "status": "already_scheduled",
            "booked": False,
            "meeting_time": lead.data.get("meeting_time"),
            "meeting_link": lead.data.get("meeting_link"),
        }
    return {
        "status": "booked",
        "booked": True,
        "meeting_time": lead.data.get("meeting_time"),
        "meeting_link": lead.data.get("meeting_link"),
        "message": "Google Calendar confirmed the meeting event.",
    }


def get_case_insensitive_value(d: dict, keys: list, default: Any = None) -> Any:
    for k in keys:
        k_norm = k.strip().lower().replace("_", "").replace(" ", "")
        for dict_key, dict_val in d.items():
            if not dict_key:
                continue
            dict_key_norm = str(dict_key).strip().lower().replace("_", "").replace(" ", "").strip('"').strip("'")
            if dict_key_norm == k_norm:
                if isinstance(dict_val, str):
                    return dict_val.strip().strip('"').strip("'")
                return dict_val
    return default


@router.post("/upload")
async def upload_leads(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.CREATE)),
    file: UploadFile = File(...),
    handle_with_ai: bool = Form(False),
    room_id: Optional[str] = Form(None),
    room_slug: Optional[str] = Form(None)
) -> Any:
    target_room_id = room_id
    if (not target_room_id or target_room_id == "sales-default") and room_slug:
        from app.models.rooms import SectionRoom
        r = db.query(SectionRoom).filter(
            SectionRoom.tenant_id == tenant_id,
            SectionRoom.section == "sales",
            SectionRoom.slug == room_slug
        ).first()
        if r:
            target_room_id = r.id
    if not target_room_id or target_room_id == "sales-default":
        from app.models.rooms import SectionRoom
        r = db.query(SectionRoom).filter(
            SectionRoom.tenant_id == tenant_id,
            SectionRoom.section == "sales",
            SectionRoom.slug == "default"
        ).first()
        if r:
            target_room_id = r.id

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")
    
    leads_to_create = []
    
    # Try parsing as JSON first if the filename ends with .json
    if file.filename.endswith(".json"):
        try:
            data = json.loads(decoded)
            if isinstance(data, dict):
                for key in ["leads", "data", "results"]:
                    if key in data and isinstance(data[key], list):
                        data = data[key]
                        break
            if not isinstance(data, list):
                raise HTTPException(status_code=400, detail="JSON must be an array of lead objects or contain a 'leads' list")
            
            for item in data:
                leads_to_create.append({
                    "name": get_case_insensitive_value(item, ["name", "lead name", "full name", "lead_name", "fullname"]),
                    "company": get_case_insensitive_value(item, ["company", "company name", "organization", "company_name", "org"]),
                    "email": get_case_insensitive_value(item, ["email", "email address", "email_address"]),
                    "phone": get_case_insensitive_value(item, ["phone", "phone number", "mobile", "telephone", "phone_number"]),
                    "source": get_case_insensitive_value(item, ["source"], "Uploaded JSON"),
                    "priority": get_case_insensitive_value(item, ["priority"], "medium"),
                    "personal_email": get_case_insensitive_value(item, ["personal_email", "personal email", "personalemail"]),
                    "company_email": get_case_insensitive_value(item, ["company_email", "company email", "companyemail"]),
                    "mobile_no": get_case_insensitive_value(item, ["mobile_no", "mobile number", "mobile_number", "mobile"]),
                    "company_contact_no": get_case_insensitive_value(item, ["company_contact_no", "company contact number", "company_contact_number", "company contact no", "company contact"]),
                    "need_of_what": get_case_insensitive_value(item, ["need_of_what", "need", "requirement", "needs", "need of what"]),
                    "how_much": get_case_insensitive_value(item, ["how_much", "budget", "value", "deal size", "deal_size", "how much"]),
                    "why": get_case_insensitive_value(item, ["why", "pain points", "pain_points", "pain point", "pain_point"]),
                    "target_context": get_case_insensitive_value(item, ["target_context", "context", "target context"]),
                })
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file format")
    else:
        # Default to CSV parsing
        try:
            f = io.StringIO(decoded)
            reader = csv.DictReader(f)
            
            for row in reader:
                mapped = {
                    "name": get_case_insensitive_value(row, ["name", "lead name", "full name", "lead_name", "fullname"]),
                    "company": get_case_insensitive_value(row, ["company", "company name", "organization", "company_name", "org"]),
                    "email": get_case_insensitive_value(row, ["email", "email address", "email_address"]),
                    "phone": get_case_insensitive_value(row, ["phone", "phone number", "mobile", "telephone", "phone_number"]),
                    "source": get_case_insensitive_value(row, ["source"]),
                    "priority": get_case_insensitive_value(row, ["priority"]),
                    "personal_email": get_case_insensitive_value(row, ["personal_email", "personal email", "personalemail"]),
                    "company_email": get_case_insensitive_value(row, ["company_email", "company email", "companyemail"]),
                    "mobile_no": get_case_insensitive_value(row, ["mobile_no", "mobile number", "mobile_number", "mobile"]),
                    "company_contact_no": get_case_insensitive_value(row, ["company_contact_no", "company contact number", "company_contact_number", "company contact no", "company contact"]),
                    "need_of_what": get_case_insensitive_value(row, ["need_of_what", "need", "requirement", "needs", "need of what"]),
                    "how_much": get_case_insensitive_value(row, ["how_much", "budget", "value", "deal size", "deal_size", "how much"]),
                    "why": get_case_insensitive_value(row, ["why", "pain points", "pain_points", "pain point", "pain_point"]),
                    "target_context": get_case_insensitive_value(row, ["target_context", "context", "target context"]),
                }
                
                if not mapped.get("name") and not mapped.get("email"):
                    continue
                
                mapped["source"] = mapped.get("source") or "Uploaded CSV"
                mapped["priority"] = mapped.get("priority") or "medium"
                leads_to_create.append(mapped)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV file format: {str(e)}")
            
    if not leads_to_create:
        raise HTTPException(status_code=400, detail="No valid leads found in the file")
        
    created_leads = []
    for lead_data in leads_to_create:
        lead = models.Lead(
            tenant_id=tenant_id,
            name=lead_data.get("name"),
            company=lead_data.get("company"),
            email=lead_data.get("email"),
            phone=lead_data.get("phone"),
            source=lead_data.get("source"),
            personal_email=lead_data.get("personal_email"),
            company_email=lead_data.get("company_email"),
            mobile_no=lead_data.get("mobile_no"),
            company_contact_no=lead_data.get("company_contact_no"),
            need_of_what=lead_data.get("need_of_what"),
            how_much=lead_data.get("how_much"),
            why=lead_data.get("why"),
            target_context=lead_data.get("target_context"),
            priority=lead_data.get("priority", "medium"),
            status="captured",
            room_id=target_room_id
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        created_leads.append(lead)
        
        if handle_with_ai:
            from app.worker.tasks import handle_lead_with_ai_task
            handle_lead_with_ai_task.delay(tenant_id, lead.id)
        else:
            score_lead_task.delay(tenant_id, lead.id)
            
    return {"message": f"Successfully uploaded and queued {len(created_leads)} leads."}


class TimelineNoteRequest(BaseModel):
    content: str
    channel: Optional[str] = "note"
    direction: Optional[str] = "internal"
    author: Optional[str] = None


@router.post("/{lead_id}/timeline-note", response_model=schemas.Lead)
def add_timeline_note(
    *,
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
    lead_id: str,
    req: TimelineNoteRequest
) -> Any:
    tenant_id = current_user.tenant_id
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    author_name = req.author or current_user.name or current_user.email or "Human Agent"
        
    conv = list((lead.data or {}).get("conversation") or [])
    conv.append({
        "direction": req.direction or "internal",
        "channel": req.channel or "note",
        "content": req.content,
        "subject": "Human Update",
        "author": author_name,
        "at": datetime.utcnow().isoformat()
    })
    
    lead.data = {
        **(lead.data or {}),
        "conversation": conv
    }
    
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/business-profile", response_model=schemas.BusinessProfile)
def get_business_profile(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        # Create an empty default profile
        profile = models.BusinessProfile(
            tenant_id=tenant_id,
            company_name="",
            website="",
            industry="",
            service_description="",
            target_countries=[],
            target_industries=[],
            target_company_size="",
            target_budget_range="",
            target_decision_makers=[],
            usp="",
            case_studies="",
            offer_details="",
            calendars=[],
            communication_channels=[],
            v3_workflow_status={},
            sales_emails=[],
            support_emails=[]
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.post("/business-profile", response_model=schemas.BusinessProfile)
def update_business_profile(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.CREATE)),
    profile_in: schemas.BusinessProfileCreate
) -> Any:
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        profile = models.BusinessProfile(tenant_id=tenant_id)
        db.add(profile)
    
    for field, value in profile_in.dict(exclude_unset=True).items():
        if field == "calendars" and value is not None and isinstance(profile.calendars, list):
            existing_events = [c for c in profile.calendars if isinstance(c, dict)]
            if isinstance(value, list):
                new_urls = [c for c in value if isinstance(c, str)]
                new_events = [c for c in value if isinstance(c, dict)]
                setattr(profile, field, new_urls + (new_events or existing_events))
            else:
                setattr(profile, field, value)
        else:
            setattr(profile, field, value)
        
    db.commit()
    db.refresh(profile)
    return profile


class RunWorkflowRequest(BaseModel):
    provider: Optional[str] = "auto"
    model: Optional[str] = None
    review_plan: Optional[bool] = False
    count: Optional[int] = 50
    freshness: Optional[str] = "30_days"

class RunPromptAgentRequest(BaseModel):
    prompt: str
    count: Optional[int] = 50
    freshness: Optional[str] = "30_days"
    provider: Optional[str] = "auto"
    model: Optional[str] = None

@router.post("/run-prompt-agent")
async def run_prompt_agent(
    req: RunPromptAgentRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """
    Launch Prompt-Based Sales Agent using natural language prompt directive without altering structured BusinessProfile.
    """
    import asyncio
    import logging
    from datetime import datetime
    lead_logger = logging.getLogger(__name__)

    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        profile = models.BusinessProfile(
            tenant_id=tenant_id,
            company_name="Organization",
            industry="B2B"
        )
        db.add(profile)
        db.commit()

    prompt_text = (req.prompt or "").strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail="Prompt instructions cannot be empty.")

    # Initialize workflow status tagged as prompt_agent
    profile.v3_workflow_status = {
        "workflow_type": "prompt_agent",
        "workflow_name": "Prompt-Based Sales Agent",
        "instructions": prompt_text,
        "status": "executing",
        "current_step": 1,
        "steps": {
            "1": { "name": "Understand Directive & Synthesize Criteria", "status": "executing", "result": "Analyzing prompt directive..." },
            "2": { "name": "Market Discovery", "status": "pending", "result": "" },
            "3": { "name": "Lead Qualification", "status": "pending", "result": "" },
            "4": { "name": "Pain Point Discovery", "status": "pending", "result": "" },
            "5": { "name": "Decision Maker Discovery", "status": "pending", "result": "" },
            "6": { "name": "Lead Scoring", "status": "pending", "result": "" },
            "7": { "name": "Outreach Generation", "status": "pending", "result": "" },
            "8": { "name": "Multi-Channel Outreach", "status": "pending", "result": "" },
            "9": { "name": "Conversation AI", "status": "pending", "result": "" },
            "10": { "name": "Meeting Conversion", "status": "pending", "result": "" }
        },
        "logs": [
            "Initializing OCTAOS Prompt-Based Sales Agent...",
            f"Research prompt: {prompt_text[:80]}..."
        ]
    }
    db.commit()

    actual_provider = req.provider
    actual_model = req.model
    if not actual_provider or actual_provider.lower() in ("auto", "none", "default", "env_default", "system_default"):
        from app.services.ai_gateway import ai_gateway
        configured_providers = ai_gateway._get_configured_providers(db, tenant_id)
        if configured_providers:
            try:
                actual_provider, actual_model = ai_gateway.selectProvider(
                    configured_providers, complexity="high"
                )
            except Exception:
                actual_provider = None
                actual_model = None
    elif actual_provider.lower() in ("nvidia", "nim", "nvidia_nim") and not actual_model:
        actual_model = "meta/llama-3.3-70b-instruct"

    actual_freshness = req.freshness or "30_days"

    async def _execute_prompt_background():
        from app.db.session import SessionLocal
        from app.services.agents.sales import SalesAgent
        bg_db = SessionLocal()
        try:
            agent = SalesAgent(bg_db, tenant_id)
            await agent.run_sales_ai_v3_workflow(
                provider=actual_provider,
                model=actual_model,
                count=req.count or 50,
                freshness=actual_freshness,
                mode="prompt_agent",
                prompt_instructions=prompt_text,
            )
        except Exception as e:
            lead_logger.error(f"Error in background Prompt Agent execution: {e}", exc_info=True)
            p = bg_db.query(models.BusinessProfile).filter_by(tenant_id=tenant_id).first()
            if p and p.v3_workflow_status:
                st = dict(p.v3_workflow_status)
                st["status"] = "failed"
                logs_list = list(st.get("logs", []))
                logs_list.append(f"[{datetime.now().strftime('%H:%M:%S')}] Workflow execution error: {str(e)}")
                st["logs"] = logs_list
                p.v3_workflow_status = st
                bg_db.commit()
        finally:
            bg_db.close()

    try:
        from app.worker.tasks import run_sales_v3_task
        run_sales_v3_task.delay(
            tenant_id=tenant_id,
            provider=actual_provider,
            model=actual_model,
            count=req.count or 50,
            freshness=actual_freshness,
            mode="prompt_agent",
            prompt_instructions=prompt_text,
        )
    except Exception:
        asyncio.create_task(_execute_prompt_background())

    return {"message": "⚡ Prompt-Based Sales Agent launched successfully!"}

@router.post("/run-v3-workflow")
async def run_v3_workflow(
    req: RunWorkflowRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """
    Launch Configured Sales Engine using structured BusinessProfile ICP parameters.
    """
    import asyncio
    import logging
    from datetime import datetime
    lead_logger = logging.getLogger(__name__)

    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Please configure your Business Profile first.")
        
    # Reset workflow status to starting state tagged as configured_engine
    profile.v3_workflow_status = {
        "workflow_type": "configured_engine",
        "workflow_name": "Configured Sales Engine",
        "status": "executing",
        "current_step": 1,
        "steps": {
            "1": { "name": "Understand Service & Generate ICP", "status": "executing", "result": "Analyzing your product/service parameters..." },
            "2": { "name": "Market Discovery", "status": "pending", "result": "" },
            "3": { "name": "Lead Qualification", "status": "pending", "result": "" },
            "4": { "name": "Pain Point Discovery", "status": "pending", "result": "" },
            "5": { "name": "Decision Maker Discovery", "status": "pending", "result": "" },
            "6": { "name": "Lead Scoring", "status": "pending", "result": "" },
            "7": { "name": "Outreach Generation", "status": "pending", "result": "" },
            "8": { "name": "Multi-Channel Outreach", "status": "pending", "result": "" },
            "9": { "name": "Conversation AI", "status": "pending", "result": "" },
            "10": { "name": "Meeting Conversion", "status": "pending", "result": "" }
        },
        "logs": [
            "Initializing OCTAOS Configured Sales Engine...",
            "Loading structured business profile & ICP parameters."
        ]
    }
    db.commit()
    
    # Check if provider is auto
    actual_provider = req.provider
    actual_model = req.model
    if not actual_provider or actual_provider.lower() in ("auto", "none", "default", "env_default", "system_default"):
        from app.services.ai_gateway import ai_gateway
        configured_providers = ai_gateway._get_configured_providers(db, tenant_id)
        if configured_providers:
            try:
                actual_provider, actual_model = ai_gateway.selectProvider(
                    configured_providers, complexity="high"
                )
            except Exception:
                actual_provider = None
                actual_model = None
    elif actual_provider.lower() in ("nvidia", "nim", "nvidia_nim") and not actual_model:
        actual_model = "meta/llama-3.3-70b-instruct"
    
    actual_freshness = req.freshness or getattr(profile, "lead_freshness", "30_days") or "30_days"
    
    # Execute directly in background event loop to avoid prefork worker deadlocks
    async def _execute_v3_background():
        from app.db.session import SessionLocal
        from app.services.agents.sales import SalesAgent
        bg_db = SessionLocal()
        try:
            agent = SalesAgent(bg_db, tenant_id)
            await agent.run_sales_ai_v3_workflow(
                provider=actual_provider,
                model=actual_model,
                count=req.count,
                freshness=actual_freshness,
                mode="configured_engine",
            )
        except Exception as e:
            lead_logger.error(f"Error in background Sales V3 execution: {e}", exc_info=True)
            p = bg_db.query(models.BusinessProfile).filter_by(tenant_id=tenant_id).first()
            if p and p.v3_workflow_status:
                st = dict(p.v3_workflow_status)
                st["status"] = "failed"
                logs_list = list(st.get("logs", []))
                logs_list.append(f"[{datetime.now().strftime('%H:%M:%S')}] Workflow execution error: {str(e)}")
                st["logs"] = logs_list
                p.v3_workflow_status = st
                bg_db.commit()
        finally:
            bg_db.close()

    try:
        from app.worker.tasks import run_sales_v3_task
        run_sales_v3_task.delay(
            tenant_id=tenant_id,
            provider=actual_provider,
            model=actual_model,
            count=req.count,
            freshness=actual_freshness,
            mode="configured_engine",
        )
    except Exception:
        asyncio.create_task(_execute_v3_background())
    
    return {"message": f"Autonomous Configured Sales Engine launched successfully using {actual_provider or 'default'}/{actual_model or 'default'} (Freshness: {actual_freshness})!"}



@router.get("/v3-workflow-status")
def get_v3_workflow_status(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        return {"status": "idle", "current_step": 0, "steps": {}, "logs": []}
    return profile.v3_workflow_status or {"status": "idle", "current_step": 0, "steps": {}, "logs": []}


@router.post("/run-sequence")
def run_sequence_stub(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    # Trigger AI outreach for all leads needing it
    from app.worker.tasks import handle_lead_with_ai_task
    leads = db.query(models.Lead).filter(models.Lead.tenant_id == tenant_id, models.Lead.status.in_(["captured", "scored"])).all()
    for lead in leads:
        handle_lead_with_ai_task.delay(tenant_id, lead.id)
    return {"message": "Outbound outreach sequence launched!"}


@router.post("/run-auto-agent")
def run_auto_agent_stub(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    # Trigger Sales V3 workflow as the primary action
    from app.worker.tasks import run_sales_v3_task
    run_sales_v3_task.delay(tenant_id)
    return {"message": "Sales Agent Auto-Prospector launched!"}


@router.post("/{lead_id}/score")
def trigger_scoring(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    score_lead_task.delay(tenant_id, lead.id)
    return {"message": "Lead scoring triggered successfully!"}


@router.get("/email-config-status")
def get_email_config_status(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """Return which email channels are configured for this tenant."""
    from app.services.email.sender import check_smtp_configured, check_gmail_configured
    smtp_ok = check_smtp_configured(db, tenant_id)
    gmail_ok = check_gmail_configured(db, tenant_id)
    return {
        "smtp_configured": smtp_ok,
        "gmail_configured": gmail_ok,
        "any_configured": smtp_ok or gmail_ok,
        "recommended_channel": "gmail" if gmail_ok else ("smtp" if smtp_ok else None),
    }


@router.get("/sales-settings")
def get_sales_settings(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.READ)),
) -> Any:
    """Sales automation mode: review_first vs auto_send for prospect replies."""
    from app.models.base import APICredential
    defaults = {
        "sales_auto_reply": True,
        "reply_mode": "review_first",
        "auto_book_meetings": True,
        "sales_ai_auto_send_enabled": False,
        "outbound_permission_state": "unknown",
        "whatsapp_permission_state": "unknown",
    }
    cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="sales").first()
    if cred and cred.settings:
        defaults.update(cred.settings)
    return defaults


@router.post("/sales-settings")
def save_sales_settings(
    payload: dict,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    from app.models.base import APICredential
    mode = str(payload.get("reply_mode") or "review_first").lower()
    if mode not in ("review_first", "auto_send"):
        raise HTTPException(400, "reply_mode must be review_first or auto_send")
    outbound_permission = str(payload.get("outbound_permission_state") or "unknown").lower()
    whatsapp_permission = str(payload.get("whatsapp_permission_state") or "unknown").lower()
    allowed_permission_states = {"unknown", "granted", "denied"}
    if outbound_permission not in allowed_permission_states:
        raise HTTPException(400, "outbound_permission_state must be unknown, granted, or denied")
    if whatsapp_permission not in allowed_permission_states:
        raise HTTPException(400, "whatsapp_permission_state must be unknown, granted, or denied")

    settings = {
        "sales_auto_reply": bool(payload.get("sales_auto_reply", True)),
        "reply_mode": mode,
        "auto_book_meetings": bool(payload.get("auto_book_meetings", True)),
        "sales_ai_auto_send_enabled": bool(payload.get("sales_ai_auto_send_enabled", False)),
        "outbound_permission_state": outbound_permission,
        "whatsapp_permission_state": whatsapp_permission,
    }
    for key in ("follow_up_cadence_days", "max_ai_touchpoints", "meeting_duration_minutes", "buffer_minutes"):
        if payload.get(key) is not None:
            settings[key] = int(payload[key])
    cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="sales").first()
    if not cred:
        cred = APICredential(
            tenant_id=tenant_id,
            provider="sales",
            encrypted_key="",
            settings=settings,
        )
        db.add(cred)
    else:
        merged = dict(cred.settings or {})
        merged.update(settings)
        cred.settings = merged
    db.commit()
    db.refresh(cred)
    return {"status": "success", "settings": cred.settings}


@router.get("/{lead_id}/email-status")
def get_lead_email_status(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """Return email send/reply status for a specific lead."""
    from app.services.email.sender import check_smtp_configured, check_gmail_configured
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    data = lead.data or {}
    conversation = data.get("conversation", [])
    
    outbound_emails = [m for m in conversation if m.get("direction") == "outbound" and m.get("channel") in ("smtp", "gmail", "email")]
    inbound_replies = [m for m in conversation if m.get("direction") == "inbound"]
    
    smtp_ok = check_smtp_configured(db, tenant_id)
    gmail_ok = check_gmail_configured(db, tenant_id)
    
    return {
        "lead_id": lead_id,
        "email": lead.email,
        "smtp_configured": smtp_ok,
        "gmail_configured": gmail_ok,
        "email_configured": smtp_ok or gmail_ok,
        "emails_sent": len(outbound_emails),
        "last_sent_at": outbound_emails[-1].get("at") if outbound_emails else None,
        "last_sent_subject": data.get("outbound_subject"),
        "replies_received": len(inbound_replies),
        "last_reply_at": data.get("last_inbound_at"),
        "last_reply_channel": data.get("last_inbound_channel"),
        "prospect_interested": data.get("prospect_interested", False),
        "reply_intent": data.get("reply_intent"),
        "sent_actual": data.get("sent_actual", False),
        "email_send_status": data.get("email_send_status", "not_attempted"),
        "outreach_sent_at": data.get("outreach_sent_at"),
        "conversation": conversation,
    }


@router.post("/check-replies")
def check_replies_for_tenant(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    """Manually trigger Gmail inbox polling for this tenant to check for new prospect replies."""
    from app.services.sales.gmail_poll import poll_gmail_inbox_for_sales
    from app.services.email.sender import check_gmail_configured
    
    if not check_gmail_configured(db, tenant_id):
        return {
            "queued": 0,
            "message": "Gmail is not configured. Connect your Gmail account in API Management to enable reply tracking.",
            "gmail_configured": False,
        }
    
    try:
        queued = poll_gmail_inbox_for_sales(db, tenant_id)
        return {
            "queued": queued,
            "gmail_configured": True,
            "message": f"Inbox polled successfully. {queued} new reply(ies) queued for processing." if queued else "No new replies found in the last 7 days.",
        }
    except Exception as e:
        return {
            "queued": 0,
            "gmail_configured": True,
            "message": f"Gmail poll error: {str(e)}",
        }


@router.post("/{lead_id}/outreach/draft")
async def generate_outreach_draft(
    lead_id: str,
    payload: dict = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    """Generate an editable outreach draft (not sent). Optional payload.instructions steers tone/angle."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    instructions = str((payload or {}).get("instructions") or "").strip()
    try:
        body = await SalesService(db, tenant_id).generate_outreach(lead_id, instructions=instructions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    subject = f"Partnership Opportunity - {lead.company or 'Your Company'}"
    lead.data = {**(lead.data or {}), "draft_subject": subject, "draft_body": body}
    db.commit()
    return {"subject": subject, "body": body}


@router.patch("/{lead_id}/follow-up-schedule")
def save_follow_up_schedule(
    lead_id: str,
    payload: dict,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    schedule = payload.get("schedule")
    if not isinstance(schedule, list):
        raise HTTPException(status_code=400, detail="schedule must be a list")
    lead.data = {**(lead.data or {}), "outreach_schedule": schedule}
    db.commit()
    return {"status": "success", "schedule": schedule}


@router.post("/{lead_id}/send-outreach-smart")
async def send_outreach_smart(
    lead_id: str,
    payload: dict = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.UPDATE)),
) -> Any:
    """Send a reviewed draft through the central policy-gated dispatcher."""
    from app.services.email.sender import check_smtp_configured, check_gmail_configured
    from app.services.sales.touch_dispatcher import dispatch_sales_touch
    from app.services.sales_os.quality_gates import assess_outreach_readiness

    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    smtp_ok = check_smtp_configured(db, tenant_id)
    gmail_ok = check_gmail_configured(db, tenant_id)
    custom_body = str((payload or {}).get("body") or "").strip()
    custom_subject = str((payload or {}).get("subject") or "").strip()
    message = custom_body or None
    if not message:
        try:
            message = await SalesService(db, tenant_id).generate_outreach(lead_id)
        except Exception:
            message = None

    if not isinstance(message, str) or not message.strip():
        return {
            "lead_id": lead_id,
            "status": "blocked_no_draft",
            "sent": False,
            "message": "No outreach draft was produced. Nothing was sent.",
            "email_configured": bool(smtp_ok or gmail_ok),
            "smtp_configured": smtp_ok,
            "gmail_configured": gmail_ok,
        }

    data = dict(lead.data or {})
    contact_data = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    qualification = data.get("qualification") if isinstance(data.get("qualification"), dict) else {}
    contact_name = contact_data.get("name") or data.get("contact_name")
    if not contact_name and lead.name and lead.name.strip().casefold() != (lead.company or "").strip().casefold():
        contact_name = lead.name
    recipient_email = lead.email or lead.company_email or lead.personal_email
    evidence_payload = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    if not recipient_email:
        return {
            "lead_id": lead_id,
            "status": "blocked_no_email_route",
            "sent": False,
            "message": "No email address is available for this lead. Nothing was sent.",
        }

    prospect = {
        "contact_status": data.get("contact_status") or contact_data.get("contact_status") or qualification.get("contact_status"),
        "evidence_url": data.get("evidence_url") or getattr(lead, "evidence_url", None),
        "evidence_quote": data.get("evidence_quote") or evidence_payload.get("quote"),
        "buying_signal": data.get("buying_signal"),
        "news": data.get("news") or [],
        "jobs": data.get("jobs") or [],
        "contact": {
            "name": contact_name,
            "email": recipient_email,
            "phone": lead.phone or lead.mobile_no or lead.company_contact_no,
        },
    }
    sales_credential = db.query(APICredential).filter_by(
        tenant_id=tenant_id, provider="sales"
    ).first()
    policy_settings = (sales_credential.settings if sales_credential else {}) or {}
    readiness = assess_outreach_readiness(
        prospect,
        auto_send_enabled=bool(policy_settings.get("sales_ai_auto_send_enabled", False)),
        permission_state=policy_settings.get("outbound_permission_state"),
        suppressed=bool(data.get("suppressed") or data.get("do_not_contact")),
        human_approved=True,
    )
    subject = custom_subject or f"Partnership Opportunity - {lead.company or 'Prospect'}"
    if not readiness["ready"]:
        data["outreach_draft"] = {
            "channel": "email",
            "subject": subject,
            "body": message.strip(),
            "status": "blocked",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "blockers": readiness["blockers"],
        }
        data["draft_subject"] = subject
        data["draft_body"] = message.strip()
        data["outreach_readiness"] = readiness
        lead.data = data
        db.commit()
        return {
            "lead_id": lead_id,
            "status": "blocked",
            "sent": False,
            "message": "Outbound blocked by readiness checks: " + ", ".join(readiness["blockers"]),
            "blockers": readiness["blockers"],
            "email_configured": bool(smtp_ok or gmail_ok),
            "smtp_configured": smtp_ok,
            "gmail_configured": gmail_ok,
        }

    send_result = dispatch_sales_touch(
        db,
        tenant_id,
        lead,
        channel="email",
        subject=subject,
        body=message.strip(),
        step_number=1,
        human_approved=True,
    )
    sent = bool(send_result.get("sent"))
    now = datetime.utcnow().isoformat() + "Z"
    data = dict(lead.data or {})
    data["outreach_attempt"] = {
        "channel": send_result.get("channel") or "email",
        "attempted_at": now,
        "sent": sent,
        "reason": send_result.get("reason"),
        "message": send_result.get("message"),
        "provider_message_id": send_result.get("message_id") or send_result.get("provider_message_id"),
    }
    data["outreach_readiness"] = readiness
    data["outreach_draft"] = {
        "channel": "email",
        "subject": subject,
        "body": message.strip(),
        "status": "sent" if sent else "blocked",
        "created_at": now,
        "blockers": [] if sent else send_result.get("blockers", [send_result.get("reason") or "dispatch_failed"]),
    }
    data["draft_subject"] = subject
    data["draft_body"] = message.strip()
    if sent:
        conversation = list(data.get("conversation") or [])
        conversation.append({
            "direction": "outbound",
            "channel": send_result.get("channel") or "email",
            "content": message.strip(),
            "subject": subject,
            "author": "Sales AI Agent",
            "at": now,
            "sent": True,
            "send_status": "sent",
            "provider_message_id": send_result.get("message_id") or send_result.get("provider_message_id"),
        })
        data["conversation"] = conversation
        data["outreach_channel"] = send_result.get("channel") or "email"
        data["outbound_subject"] = subject
        data["outbound_body"] = message.strip()
        data["outreach_sent_at"] = now
        data["sent_actual"] = True
        lead.status = "contacted"
    else:
        data["sent_actual"] = False
    lead.data = data
    db.commit()
    db.refresh(lead)

    return {
        "lead_id": lead_id,
        "status": "sent" if sent else "blocked",
        "message": message.strip(),
        "email_configured": bool(smtp_ok or gmail_ok),
        "smtp_configured": smtp_ok,
        "gmail_configured": gmail_ok,
        "sent": sent,
        "channel": send_result.get("channel"),
        "send_status": "sent" if sent else "blocked",
        "send_message": send_result.get("message", ""),
        "blockers": [] if sent else send_result.get("blockers", [send_result.get("reason") or "dispatch_failed"]),
        "lead": {"id": lead.id, "status": lead.status, "email": lead.email, "name": lead.name, "company": lead.company},
    }

class ClarifyReplyRequest(BaseModel):
    answer: str
    channel: Optional[str] = "email"
    add_to_kb: bool = True
    kb_title: Optional[str] = None


@router.get("/clarifications/pending")
def get_pending_clarifications(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Return all leads awaiting human clarification for unanswered prospect questions."""
    leads = db.query(models.Lead).filter(models.Lead.tenant_id == tenant_id).all()
    pending = []
    for l in leads:
        d = l.data or {}
        if d.get("awaiting_user_clarification"):
            pending.append({
                "lead_id": l.id,
                "name": l.name,
                "company": l.company,
                "email": l.email,
                "phone": l.phone,
                "pending_question": d.get("pending_question"),
                "clarification_requested_at": d.get("clarification_requested_at"),
                "conversation": d.get("conversation", []),
            })
    return pending


@router.post("/{lead_id}/clarify-reply")
async def clarify_and_reply(
    lead_id: str,
    payload: ClarifyReplyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Submit human answer to prospect question, dispatch reply, and index into Knowledge Base."""
    from app.services.sales.reply_handler import SalesReplyHandler
    handler = SalesReplyHandler(db, tenant_id)
    result = await handler.submit_human_clarification(
        lead_id=lead_id,
        answer=payload.answer,
        channel=payload.channel or "email",
        add_to_kb=payload.add_to_kb,
        kb_title=payload.kb_title,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message", "Error submitting clarification"))
    return result


class BulkDeleteLeadsRequest(BaseModel):
    lead_ids: List[str]


@router.delete("/{lead_id}")
def delete_lead(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.DELETE)),
) -> Any:
    """Permanently delete a lead by ID."""
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        from app.models.sales_intelligence import SourceOutcome
        db.query(SourceOutcome).filter(SourceOutcome.lead_id == lead_id).update(
            {SourceOutcome.lead_id: None}, synchronize_session=False
        )
    except Exception:
        pass

    db.delete(lead)
    db.commit()
    return {"status": "success", "message": "Lead deleted successfully", "id": lead_id}


@router.post("/bulk-delete")
def bulk_delete_leads(
    payload: BulkDeleteLeadsRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.LEADS, Action.DELETE)),
) -> Any:
    """Permanently delete multiple leads by IDs in a single operation."""
    if not payload.lead_ids:
        return {"status": "success", "deleted_count": 0}

    try:
        from app.models.sales_intelligence import SourceOutcome
        db.query(SourceOutcome).filter(SourceOutcome.lead_id.in_(payload.lead_ids)).update(
            {SourceOutcome.lead_id: None}, synchronize_session=False
        )
    except Exception:
        pass

    deleted_count = db.query(models.Lead).filter(
        models.Lead.id.in_(payload.lead_ids),
        models.Lead.tenant_id == tenant_id
    ).delete(synchronize_session=False)

    db.commit()
    return {"status": "success", "deleted_count": deleted_count}

