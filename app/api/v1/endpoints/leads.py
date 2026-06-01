from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any
from app.api import deps
from app.schemas import verticals as schemas
from app.models import verticals as models
from app.services.verticals.sales import SalesService
from app.worker.tasks import score_lead_task

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
    skip: int = 0,
    limit: int = 100
) -> Any:
    leads = db.query(models.Lead).filter(models.Lead.tenant_id == tenant_id).offset(skip).limit(limit).all()
    return leads

@router.post("/{lead_id}/outreach")
async def generate_outreach(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    service = SalesService(db, tenant_id)
    message = await service.generate_outreach(lead_id)
    return {"message": message}
