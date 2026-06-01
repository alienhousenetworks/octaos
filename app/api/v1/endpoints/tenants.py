from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any
from app.api import deps
from app.models import base
from pydantic import BaseModel

router = APIRouter()

class TenantBase(BaseModel):
    name: str
    subdomain: str

class TenantCreate(TenantBase):
    pass

class Tenant(TenantBase):
    id: str
    is_active: bool

    class Config:
        from_attributes = True

@router.get("/", response_model=List[Tenant])
def read_tenants(db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100) -> Any:
    tenants = db.query(base.Tenant).offset(skip).limit(limit).all()
    return tenants

@router.post("/", response_model=Tenant)
def create_tenant(*, db: Session = Depends(deps.get_db), tenant_in: TenantCreate) -> Any:
    tenant = base.Tenant(name=tenant_in.name, subdomain=tenant_in.subdomain)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant
