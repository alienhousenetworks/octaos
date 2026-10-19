"""Credential lifecycle, hashing, and token verification for OctaOS MCP."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.models.mcp import SystemMCPCredential, CapabilityGrant


MCP_KEY_PREFIX = "octa_mcp_"


def generate_mcp_key() -> Tuple[str, str, str]:
    """
    Generates a secure, high-entropy MCP API key.
    Returns:
        raw_key: Plaintext key (e.g. 'octa_mcp_...') - shown to user only once.
        key_hash: SHA-256 hash stored in DB.
        key_prefix: First 16 characters for identification in UI.
    """
    random_part = secrets.token_hex(24) # 48 hex chars
    raw_key = f"{MCP_KEY_PREFIX}{random_part}"
    key_hash = hash_token(raw_key)
    key_prefix = raw_key[:16]
    return raw_key, key_hash, key_prefix


def authenticate_mcp_key(db: Session, raw_key: str) -> Optional[SystemMCPCredential]:
    """
    Validates a raw MCP key against the database.
    Checks:
    - Key format and hash
    - Active status
    - Expiration date
    Updates last_used_at on successful authentication.
    """
    if not raw_key or not raw_key.startswith(MCP_KEY_PREFIX):
        return None

    key_hash = hash_token(raw_key.strip())
    cred = (
        db.query(SystemMCPCredential)
        .filter(SystemMCPCredential.key_hash == key_hash)
        .first()
    )

    if not cred or not cred.is_active:
        return None

    # Check expiration
    if cred.expires_at:
        now = datetime.now(timezone.utc)
        exp = cred.expires_at if cred.expires_at.tzinfo else cred.expires_at.replace(tzinfo=timezone.utc)
        if exp < now:
            return None

    # Update last_used_at
    try:
        cred.last_used_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()

    return cred


def create_credential_with_grants(
    db: Session,
    tenant_id: str,
    name: str,
    user_id: Optional[str] = None,
    client_type: str = "generic",
    role: str = "read_only",
    grants: Optional[List[Dict[str, Any]]] = None,
    rate_limit_rpm: int = 120,
    max_records_per_query: int = 100,
    expires_at: Optional[datetime] = None,
) -> Tuple[SystemMCPCredential, str]:
    """
    Creates a new SystemMCPCredential and associates object/field capability grants.
    Returns (credential_model, raw_key).
    """
    raw_key, key_hash, key_prefix = generate_mcp_key()

    cred = SystemMCPCredential(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name,
        client_type=client_type,
        key_hash=key_hash,
        key_prefix=key_prefix,
        role=role,
        rate_limit_rpm=rate_limit_rpm,
        max_records_per_query=max_records_per_query,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(cred)
    db.flush()

    # Assign default grants based on role if no explicit grants passed
    assigned_grants = grants or get_default_grants_for_role(role)
    for g in assigned_grants:
        grant_row = CapabilityGrant(
            credential_id=cred.id,
            tenant_id=tenant_id,
            connector_slug=g.get("connector_slug", "octaos"),
            object_name=g.get("object_name", "*"),
            allowed_actions=g.get("allowed_actions", ["read", "query"]),
            permitted_fields=g.get("permitted_fields", []),
            denied_fields=g.get("denied_fields", []),
            requires_approval=g.get("requires_approval", False),
        )
        db.add(grant_row)

    db.commit()
    db.refresh(cred)
    return cred, raw_key


def get_default_grants_for_role(role: str) -> List[Dict[str, Any]]:
    """Returns safe baseline capability grants according to role."""
    norm = (role or "read_only").lower()
    if norm in ("admin", "super_admin"):
        return [
            {
                "connector_slug": "*",
                "object_name": "*",
                "allowed_actions": ["discover", "read", "query", "create", "update", "delete", "invoke"],
                "permitted_fields": [],
                "denied_fields": [],
                "requires_approval": False,
            }
        ]
    elif norm in ("standard_operator", "manager", "agent"):
        return [
            {
                "connector_slug": "*",
                "object_name": "*",
                "allowed_actions": ["discover", "read", "query", "create", "update", "invoke"],
                "permitted_fields": [],
                "denied_fields": ["password", "hashed_password", "otp", "encrypted_key", "secret"],
                "requires_approval": False,
            }
        ]
    else:  # read_only default
        return [
            {
                "connector_slug": "*",
                "object_name": "*",
                "allowed_actions": ["discover", "read", "query"],
                "permitted_fields": [],
                "denied_fields": ["password", "hashed_password", "otp", "encrypted_key", "secret"],
                "requires_approval": False,
            }
        ]
