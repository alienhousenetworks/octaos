"""Unified API credential lookup with decryption and provider aliases."""
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.models.base import APICredential
from app.core.security import decrypt_api_key, encrypt_api_key

# Providers that share Meta Graph credentials
META_ALIASES = frozenset({"meta", "facebook", "instagram"})

PROVIDER_ALIASES: Dict[str, str] = {
    "facebook": "meta",
    "instagram": "meta",
}


def normalize_provider(provider: str) -> str:
    return PROVIDER_ALIASES.get(provider.lower(), provider.lower())


def get_credential(
    db: Session, tenant_id: str, provider: str
) -> Optional[APICredential]:
    normalized = normalize_provider(provider)
    cred = (
        db.query(APICredential)
        .filter(
            APICredential.tenant_id == tenant_id,
            APICredential.provider == normalized,
        )
        .first()
    )
    if cred:
        return cred
    # Legacy rows stored under platform name instead of "meta"
    if normalized == "meta":
        for alias in ("facebook", "instagram"):
            cred = (
                db.query(APICredential)
                .filter(
                    APICredential.tenant_id == tenant_id,
                    APICredential.provider == alias,
                )
                .first()
            )
            if cred:
                return cred
    return None


def get_decrypted_credential(
    db: Session, tenant_id: str, provider: str
) -> Tuple[Optional[str], Dict[str, Any]]:
    cred = get_credential(db, tenant_id, provider)
    if not cred or not cred.encrypted_key:
        return None, {}
    return decrypt_api_key(cred.encrypted_key), dict(cred.settings or {})


def save_credential(
    db: Session,
    tenant_id: str,
    provider: str,
    key: str,
    settings: Optional[Dict[str, Any]] = None,
    encrypt: bool = True,
) -> APICredential:
    normalized = normalize_provider(provider)
    stored_key = encrypt_api_key(key) if encrypt else key
    cred = get_credential(db, tenant_id, normalized)
    if cred:
        cred.encrypted_key = stored_key
        if settings is not None:
            cred.settings = {**(cred.settings or {}), **settings}
    else:
        cred = APICredential(
            tenant_id=tenant_id,
            provider=normalized,
            encrypted_key=stored_key,
            settings=settings or {},
        )
        db.add(cred)
    db.commit()
    db.refresh(cred)
    return cred
