"""Secret management and envelope encryption for connector credentials."""
from __future__ import annotations

import json
from typing import Any, Dict
from sqlalchemy.orm import Session
from app.core.security import encrypt_api_key, decrypt_api_key
from app.models.knowledge_connectors import ConnectorSecretReference, KnowledgeConnector


class ConnectorSecretVault:
    """Manages versioned, encrypted connector credentials."""

    @staticmethod
    def store_secrets(
        db: Session,
        connector: KnowledgeConnector,
        secret_payload: Dict[str, Any],
        secret_provider: str = "fernet_vault",
    ) -> ConnectorSecretReference:
        """Encrypts and stores a new versioned secret reference."""
        json_str = json.dumps(secret_payload)
        encrypted_data = encrypt_api_key(json_str)

        # Retire previous current secrets
        existing = db.query(ConnectorSecretReference).filter_by(
            connector_id=connector.id,
            rotation_status="current",
        ).all()
        for ref in existing:
            ref.rotation_status = "retired"

        new_version = (max([r.version for r in existing], default=0)) + 1
        secret_ref = ConnectorSecretReference(
            connector_id=connector.id,
            secret_provider=secret_provider,
            encrypted_key_material=encrypted_data,
            version=new_version,
            rotation_status="current",
        )
        db.add(secret_ref)
        db.commit()
        db.refresh(secret_ref)
        return secret_ref

    @staticmethod
    def retrieve_secrets(
        db: Session,
        connector_id: str,
    ) -> Dict[str, Any]:
        """Retrieves and decrypts the active secret material for a connector."""
        ref = db.query(ConnectorSecretReference).filter_by(
            connector_id=connector_id,
            rotation_status="current",
        ).order_by(ConnectorSecretReference.version.desc()).first()

        if not ref or not ref.encrypted_key_material:
            return {}

        decrypted_json = decrypt_api_key(ref.encrypted_key_material)
        if not decrypted_json:
            return {}

        try:
            return json.loads(decrypted_json)
        except Exception:
            return {"raw_token": decrypted_json}
