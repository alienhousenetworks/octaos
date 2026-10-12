"""Tenant provider keys for sales-os. Selects only the columns it reads."""
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential


def configured_providers(db: Session, tenant_id: str) -> set[str]:
    rows = db.query(APICredential.provider).filter(APICredential.tenant_id == tenant_id).all()
    return {provider for (provider,) in rows if provider}


def provider_secrets(db: Session, tenant_id: str, providers: set[str]) -> dict[str, str]:
    if not providers:
        return {}
    rows = (
        db.query(APICredential.provider, APICredential.encrypted_key)
        .filter(APICredential.tenant_id == tenant_id, APICredential.provider.in_(providers))
        .all()
    )
    secrets: dict[str, str] = {}
    for provider, encrypted in rows:
        if not provider or not encrypted:
            continue
        try:
            key = decrypt_api_key(encrypted)
        except Exception:
            continue
        if key:
            secrets[provider] = key
    return secrets
