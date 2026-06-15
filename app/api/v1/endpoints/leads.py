from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Any, Optional
from pydantic import BaseModel
import csv
import io
import json
from app.api import deps
from app.schemas import verticals as schemas
from app.models import verticals as models
from app.services.verticals.sales import SalesService
from app.worker.tasks import score_lead_task
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/", response_model=schemas.Lead)
async def create_lead(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    lead_in: schemas.LeadCreate
) -> Any:
    lead = models.Lead(**lead_in.dict(), tenant_id=tenant_id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    # Trigger async scoring
    score_lead_task.delay(tenant_id, lead.id)
    
    return lead

@router.get("/", response_model=List[schemas.Lead])
def read_leads(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    time_filter: Optional[str] = None,
    assigned_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> Any:
    query = db.query(models.Lead).filter(models.Lead.tenant_id == tenant_id)
    
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

@router.post("/{lead_id}/outreach")
async def generate_outreach(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    service = SalesService(db, tenant_id)
    message = await service.generate_outreach(lead_id)
    
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if lead:
        lead.status = "contacted"
        conv = list((lead.data or {}).get("conversation") or [])
        conv.append({
            "direction": "outbound",
            "channel": "smtp",
            "content": message,
            "subject": f"Partnership Opportunity - {lead.company}",
            "author": "Sales AI Agent",
            "at": datetime.utcnow().isoformat()
        })
        lead.data = {
            **(lead.data or {}),
            "outreach_channel": "smtp",
            "outbound_subject": f"Partnership Opportunity - {lead.company}",
            "outbound_body": message,
            "outreach_sent_at": datetime.utcnow().isoformat(),
            "conversation": conv
        }
        db.commit()
        db.refresh(lead)
        
    return {"message": message}

@router.post("/{lead_id}/schedule_meeting")
async def schedule_meeting(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead.status = "meeting_scheduled"
    meeting_link = f"https://meet.google.com/sales-{lead.id[:4]}-{lead.company[:3].lower()}"
    meeting_time = "Next Tuesday at 2:00 PM EST"
    
    conv = list((lead.data or {}).get("conversation") or [])
    conv.append({
        "direction": "outbound",
        "channel": "google_calendar",
        "content": f"Meeting scheduled for {meeting_time}. Join link: {meeting_link}",
        "subject": "Meeting Confirmation",
        "author": "Sales AI Agent",
        "at": datetime.utcnow().isoformat()
    })
    lead.data = {
        **(lead.data or {}),
        "meeting_link": meeting_link,
        "meeting_time": meeting_time,
        "prospect_interested": True,
        "conversation": conv
    }
    db.commit()
    db.refresh(lead)
    return {"message": "Meeting scheduled successfully", "meeting_time": meeting_time, "meeting_link": meeting_link}


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
    file: UploadFile = File(...),
    handle_with_ai: bool = Form(False)
) -> Any:
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
            status="captured"
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
            v3_workflow_status={}
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
    profile_in: schemas.BusinessProfileCreate
) -> Any:
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        profile = models.BusinessProfile(tenant_id=tenant_id)
        db.add(profile)
    
    for field, value in profile_in.dict(exclude_unset=True).items():
        setattr(profile, field, value)
        
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/run-v3-workflow")
def run_v3_workflow(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    profile = db.query(models.BusinessProfile).filter(models.BusinessProfile.tenant_id == tenant_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Please configure your Business Profile first.")
        
    # Reset workflow status to starting state
    profile.v3_workflow_status = {
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
            "Initializing OCTAOS Sales AI V3...",
            "Sourcing settings & launch guidelines."
        ]
    }
    db.commit()
    
    # Import and trigger Celery task
    from app.worker.tasks import run_sales_v3_task
    run_sales_v3_task.delay(tenant_id)
    
    return {"message": "Autonomous Sales AI V3 workflow launched successfully!"}


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

