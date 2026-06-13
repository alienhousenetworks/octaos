from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os, uuid, shutil

from app.api import deps
from app.models.base import User, Tenant, APICredential, ProviderUsage, SystemSetting

router = APIRouter()

def check_system_admin(current_user: User = Depends(deps.get_current_user)):
    if not current_user.is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global system admins can access this resource"
        )
    return current_user

@router.get("/stats")
def get_stats(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    from sqlalchemy import func
    
    tenant_count = db.query(func.count(Tenant.id)).scalar() or 0
    user_count = db.query(func.count(User.id)).scalar() or 0
    
    usage_stats = db.query(
        func.sum(ProviderUsage.cost),
        func.count(ProviderUsage.id)
    ).first()
    
    total_spend = usage_stats[0] or 0.0
    total_calls = usage_stats[1] or 0
    
    return {
        "tenants_count": tenant_count,
        "users_count": user_count,
        "total_spend": total_spend,
        "total_calls": total_calls
    }

@router.get("/tenants")
def list_tenants(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    from sqlalchemy import func
    
    tenants = db.query(Tenant).all()
    
    user_counts = db.query(
        User.tenant_id,
        func.count(User.id)
    ).group_by(User.tenant_id).all()
    user_counts_dict = {tenant_id: count for tenant_id, count in user_counts}
    
    spend_stats = db.query(
        ProviderUsage.tenant_id,
        func.sum(ProviderUsage.cost)
    ).group_by(ProviderUsage.tenant_id).all()
    spend_dict = {tenant_id: float(cost or 0.0) for tenant_id, cost in spend_stats}
    
    api_creds = db.query(APICredential).all()
    api_creds_dict = {}
    for cred in api_creds:
        if cred.tenant_id not in api_creds_dict:
            api_creds_dict[cred.tenant_id] = []
        if cred.encrypted_key:
            api_creds_dict[cred.tenant_id].append(cred.provider.lower())
            
    result = []
    for t in tenants:
        result.append({
            "id": t.id,
            "name": t.name,
            "subdomain": t.subdomain,
            "is_active": t.is_active,
            "users_count": user_counts_dict.get(t.id, 0),
            "spend": spend_dict.get(t.id, 0.0),
            "configured_keys": api_creds_dict.get(t.id, [])
        })
        
    return result

@router.post("/tenants/{tenant_id}/toggle-active")
def toggle_tenant_active(
    tenant_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    tenant.is_active = not tenant.is_active
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "is_active": tenant.is_active
    }

@router.get("/users")
def list_system_users(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    users = db.query(User).all()
    tenants = db.query(Tenant).all()
    tenant_names = {t.id: t.name for t in tenants}
    
    return [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "is_active": u.is_active,
        "is_system_admin": u.is_system_admin,
        "tenant_id": u.tenant_id,
        "tenant_name": tenant_names.get(u.tenant_id, "Unknown")
    } for u in users]


@router.get("/settings")
def get_branding_settings(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    """Get all system branding settings."""
    rows = db.query(SystemSetting).all()
    return {row.key: row.value for row in rows}


def _upsert_setting(db: Session, key: str, value: str):
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row:
        row.value = value
    else:
        row = SystemSetting(key=key, value=value)
        db.add(row)
    db.commit()


@router.post("/settings/upload-logo")
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    """Upload a logo image and save its public URL as the site logo."""
    from app.core.config import settings as app_settings
    upload_dir = os.path.join(app_settings.MEDIA_UPLOAD_DIR, "branding")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "logo.png")[1] or ".png"
    filename = f"logo_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    public_url = f"{app_settings.PUBLIC_BASE_URL}/media/branding/{filename}"
    _upsert_setting(db, "logo_url", public_url)
    return {"logo_url": public_url}


@router.post("/settings/upload-favicon")
def upload_favicon(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    """Upload a favicon image and save its public URL."""
    from app.core.config import settings as app_settings
    upload_dir = os.path.join(app_settings.MEDIA_UPLOAD_DIR, "branding")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "favicon.ico")[1] or ".ico"
    filename = f"favicon_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    public_url = f"{app_settings.PUBLIC_BASE_URL}/media/branding/{filename}"
    _upsert_setting(db, "favicon_url", public_url)
    return {"favicon_url": public_url}


@router.delete("/settings/logo")
def remove_logo(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    """Remove the custom site logo (revert to default)."""
    row = db.query(SystemSetting).filter(SystemSetting.key == "logo_url").first()
    if row:
        db.delete(row)
        db.commit()
    return {"message": "Logo removed"}


@router.delete("/settings/favicon")
def remove_favicon(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(check_system_admin)
):
    """Remove the custom favicon (revert to default)."""
    row = db.query(SystemSetting).filter(SystemSetting.key == "favicon_url").first()
    if row:
        db.delete(row)
        db.commit()
    return {"message": "Favicon removed"}
