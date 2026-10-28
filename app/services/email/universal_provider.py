"""Universal Mailbox Provider Interface & Adapters.

Enables OctaOS AI agents to connect to, send from, and read from any company email
(Google Workspace, Microsoft 365 / Outlook, and corporate IMAP/SMTP) via unified APIs
(Unipile, EmailEngine, Aurinko).
"""
from __future__ import annotations

import hmac
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential
from app.services.credentials import get_credential

logger = logging.getLogger(__name__)


class BaseUniversalMailboxAdapter(ABC):
    """Abstract base class for universal mailbox sync engines."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if required API credentials exist."""
        pass

    @abstractmethod
    def create_connect_session(
        self,
        tenant_id: str,
        redirect_url: Optional[str] = None,
        provider_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a hosted onboarding link for the user to link their mailbox."""
        pass

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        *,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        account_id: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email through the user's connected mailbox."""
        pass

    @abstractmethod
    def parse_inbound_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Normalize vendor-specific webhook payload into a canonical inbound message."""
        pass

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, signature: Optional[str]) -> bool:
        """Verify authenticity of the incoming webhook."""
        pass


class UnipileAdapter(BaseUniversalMailboxAdapter):
    """
    Adapter for Unipile (https://www.unipile.com).
    Connects Google Workspace, Microsoft 365 / Outlook, IMAP/SMTP, WhatsApp, and LinkedIn.
    """

    name = "unipile"

    def __init__(self, api_key: str, api_url: Optional[str] = None, webhook_secret: Optional[str] = None):
        self.api_key = api_key.strip() if api_key else ""
        self.api_url = (api_url or os.environ.get("UNIPILE_API_URL") or "https://api1.unipile.com:13142").rstrip("/")
        self.webhook_secret = webhook_secret or os.environ.get("UNIPILE_WEBHOOK_SECRET", "")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-KEY": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def create_connect_session(
        self,
        tenant_id: str,
        redirect_url: Optional[str] = None,
        provider_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a hosted account link via Unipile.
        provider_type can be 'MAIL' (for Google/Outlook/IMAP), 'LINKEDIN', or 'WHATSAPP'.
        """
        if not self.is_configured():
            return {"ok": False, "error": "Unipile API key not configured"}

        url = f"{self.api_url}/api/v1/hosted/accounts/link"
        payload = {
            "type": "create",
            "providers": [provider_type.upper()] if provider_type else ["MAIL"],
            "api_url": self.api_url,
            "expiresOn": "24h",
            "name": f"tenant_{tenant_id}",
            "notify_url": redirect_url or "",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "ok": True,
                        "connect_url": data.get("url"),
                        "expires_on": data.get("expiresOn"),
                        "provider": "unipile",
                    }
                return {"ok": False, "error": f"Unipile link failed: {res.text}"}
        except Exception as exc:
            logger.error(f"Unipile connect session error: {exc}")
            return {"ok": False, "error": str(exc)}

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        *,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        account_id: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches an outbound email through the connected Unipile mailbox."""
        if not self.is_configured():
            return {"sent": False, "reason": "Unipile not configured"}

        target_account = account_id
        if not target_account:
            accounts = self.list_accounts()
            for acc in accounts:
                if acc.get("provider_type") in ("MAIL", "GOOGLE", "OUTLOOK", "IMAP") or "mail" in str(acc.get("type", "")).lower():
                    target_account = acc.get("id")
                    break

        if not target_account:
            return {
                "sent": False,
                "reason": "no_connected_mailbox",
                "message": "No connected mailbox found in Unipile for this tenant.",
            }

        url = f"{self.api_url}/api/v1/messages/email"
        payload: Dict[str, Any] = {
            "account_id": target_account,
            "to": [{"identifier": to_email}],
            "subject": subject,
            "body": body,
        }
        if thread_id:
            payload["thread_id"] = thread_id
        if in_reply_to:
            payload["in_reply_to"] = in_reply_to

        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "sent": True,
                        "channel": "unipile",
                        "message_id": data.get("id") or data.get("message_id"),
                        "thread_id": data.get("thread_id") or thread_id,
                        "account_id": target_account,
                    }
                return {
                    "sent": False,
                    "channel": "unipile",
                    "reason": "send_failed",
                    "message": f"Unipile error {res.status_code}: {res.text}",
                }
        except Exception as exc:
            logger.error(f"Unipile send_email failed: {exc}")
            return {"sent": False, "channel": "unipile", "reason": "exception", "message": str(exc)}

    def list_accounts(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{self.api_url}/api/v1/accounts", headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return data.get("items") or data.get("accounts") or []
        except Exception as exc:
            logger.warning(f"Unipile list_accounts failed: {exc}")
        return []

    def verify_webhook(self, raw_body: bytes, signature: Optional[str]) -> bool:
        if not self.webhook_secret:
            return True
        if not signature:
            return False
        computed = hmac.new(self.webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_inbound_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Parses Unipile email event webhook into canonical format."""
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return None

        event = data.get("event") or data.get("type", "")
        msg_data = data.get("data") or data

        from_data = msg_data.get("from")
        sender = ""
        if isinstance(from_data, dict):
            sender = from_data.get("identifier") or from_data.get("email") or ""
        elif isinstance(from_data, str):
            sender = from_data

        to_data = msg_data.get("to") or []
        recipient = ""
        if isinstance(to_data, list) and to_data:
            first_to = to_data[0]
            recipient = first_to.get("identifier") or first_to.get("email", "") if isinstance(first_to, dict) else str(first_to)

        body = (
            msg_data.get("body_plain")
            or msg_data.get("text")
            or msg_data.get("body")
            or msg_data.get("content")
            or ""
        )
        subject = msg_data.get("subject") or ""
        external_id = msg_data.get("id") or msg_data.get("message_id")
        thread_id = msg_data.get("thread_id")

        if not sender and not body:
            return None

        return {
            "provider": "unipile",
            "event": event,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "message_id": external_id,
            "thread_id": thread_id,
            "account_id": msg_data.get("account_id"),
            "raw": data,
        }


class EmailEngineAdapter(BaseUniversalMailboxAdapter):
    """
    Adapter for EmailEngine (Self-Hosted Docker gateway: https://emailengine.app).
    Connects Gmail, Microsoft 365, and IMAP/SMTP mailboxes on your own private server.
    """

    name = "emailengine"

    def __init__(self, base_url: str, access_token: str, secret: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("EMAILENGINE_URL", "http://localhost:3000")).rstrip("/")
        self.access_token = access_token.strip() if access_token else os.environ.get("EMAILENGINE_TOKEN", "")
        self.secret = secret or os.environ.get("EMAILENGINE_SECRET", "")

    def is_configured(self) -> bool:
        return bool(self.base_url and self.access_token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def create_connect_session(
        self,
        tenant_id: str,
        redirect_url: Optional[str] = None,
        provider_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """EmailEngine hosted authentication form for end-users."""
        if not self.is_configured():
            return {"ok": False, "error": "EmailEngine gateway not configured"}

        url = f"{self.base_url}/v1/authentication/form"
        payload = {
            "account": f"tenant_{tenant_id}",
            "redirectUrl": redirect_url or "",
            "type": provider_type or "auto",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "ok": True,
                        "connect_url": data.get("url"),
                        "provider": "emailengine",
                    }
                return {"ok": False, "error": f"EmailEngine auth error: {res.text}"}
        except Exception as exc:
            logger.error(f"EmailEngine connect session error: {exc}")
            return {"ok": False, "error": str(exc)}

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        *,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        account_id: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {"sent": False, "reason": "EmailEngine not configured"}

        target_acc = account_id or "default"
        url = f"{self.base_url}/v1/account/{target_acc}/submit"
        payload: Dict[str, Any] = {
            "to": [{"address": to_email}],
            "subject": subject,
            "text": body,
        }
        if in_reply_to:
            payload["reference"] = {"messageId": in_reply_to}

        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, json=payload, headers=self._headers())
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "sent": True,
                        "channel": "emailengine",
                        "message_id": data.get("messageId"),
                        "queue_id": data.get("queueId"),
                    }
                return {
                    "sent": False,
                    "channel": "emailengine",
                    "reason": "send_failed",
                    "message": f"EmailEngine error {res.status_code}: {res.text}",
                }
        except Exception as exc:
            return {"sent": False, "channel": "emailengine", "reason": "exception", "message": str(exc)}

    def verify_webhook(self, raw_body: bytes, signature: Optional[str]) -> bool:
        return True

    def parse_inbound_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return None

        event = data.get("event")
        data_block = data.get("data") or {}
        from_info = data_block.get("from") or {}
        sender = from_info.get("address") or ""
        subject = data_block.get("subject") or ""
        text_body = data_block.get("text") or data_block.get("intro") or ""
        msg_id = data_block.get("id") or data_block.get("messageId")

        return {
            "provider": "emailengine",
            "event": event,
            "sender": sender,
            "recipient": (data_block.get("to") or [{}])[0].get("address", ""),
            "subject": subject,
            "body": text_body,
            "message_id": msg_id,
            "thread_id": data_block.get("threadId"),
            "account_id": data.get("account"),
            "raw": data,
        }


class AurinkoAdapter(BaseUniversalMailboxAdapter):
    """
    Adapter for Aurinko (https://www.aurinko.io).
    Developer-First Virtual REST API for Email and Calendar across Google Workspace,
    Microsoft 365, Exchange, and generic IMAP/SMTP.
    """

    name = "aurinko"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        api_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.client_id = (client_id or os.environ.get("AURINKO_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.environ.get("AURINKO_CLIENT_SECRET", "")).strip()
        self.access_token = (access_token or os.environ.get("AURINKO_ACCESS_TOKEN", "")).strip()
        self.api_url = (api_url or os.environ.get("AURINKO_API_URL") or "https://api.aurinko.io/v1").rstrip("/")
        self.webhook_secret = webhook_secret or os.environ.get("AURINKO_WEBHOOK_SECRET", "")

    def is_configured(self) -> bool:
        return bool(self.access_token or (self.client_id and self.client_secret))

    def _headers(self, account_token: Optional[str] = None) -> Dict[str, str]:
        token = account_token or self.access_token
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self.client_id and self.client_secret:
            import base64
            auth_str = f"{self.client_id}:{self.client_secret}"
            headers["Authorization"] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        return headers

    def create_connect_session(
        self,
        tenant_id: str,
        redirect_url: Optional[str] = None,
        provider_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates Aurinko hosted authentication link.
        Supports Google, Office365, MSExchange, and Imap.
        """
        if not self.client_id:
            return {"ok": False, "error": "Aurinko Client ID not configured"}

        service_map = {
            "google": "Google",
            "gmail": "Google",
            "microsoft": "Office365",
            "outlook": "Office365",
            "office365": "Office365",
            "imap": "Imap",
            "mail": "Google,Office365,Imap",
        }
        service_type = service_map.get((provider_type or "mail").lower(), "Google,Office365,Imap")

        scopes = "Mail.Read Mail.Send Mail.Drafts Calendar.ReadWrite"
        params = {
            "clientId": self.client_id,
            "serviceType": service_type,
            "scopes": scopes,
            "responseType": "code",
            "user": f"tenant_{tenant_id}",
        }
        if redirect_url:
            params["returnUrl"] = redirect_url

        from urllib.parse import urlencode
        connect_url = f"{self.api_url}/auth/authorize?{urlencode(params)}"
        return {
            "ok": True,
            "connect_url": connect_url,
            "provider": "aurinko",
            "service_type": service_type,
        }

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        *,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        account_id: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            return {"sent": False, "reason": "Aurinko not configured"}

        url = f"{self.api_url}/email/messages"
        payload: Dict[str, Any] = {
            "to": [{"address": to_email}],
            "subject": subject,
            "body": body,
        }
        if thread_id:
            payload["threadId"] = thread_id
        if in_reply_to:
            payload["inReplyTo"] = in_reply_to

        headers = self._headers()
        if account_id:
            headers["X-Aurinko-Account-Id"] = str(account_id)

        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "sent": True,
                        "channel": "aurinko",
                        "message_id": data.get("id") or data.get("messageId"),
                        "thread_id": data.get("threadId") or thread_id,
                    }
                return {
                    "sent": False,
                    "channel": "aurinko",
                    "reason": "send_failed",
                    "message": f"Aurinko error {res.status_code}: {res.text}",
                }
        except Exception as exc:
            logger.error(f"Aurinko send_email failed: {exc}")
            return {"sent": False, "channel": "aurinko", "reason": "exception", "message": str(exc)}

    def verify_webhook(self, raw_body: bytes, signature: Optional[str]) -> bool:
        if not self.webhook_secret:
            return True
        if not signature:
            return False
        computed = hmac.new(self.webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_inbound_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Parses Aurinko push webhook notification into canonical format."""
        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return None

        event = data.get("eventType") or data.get("event") or "message.created"
        payload = data.get("payload") or data.get("data") or data

        from_list = payload.get("from") or []
        sender = ""
        if isinstance(from_list, list) and from_list:
            first_from = from_list[0]
            sender = first_from.get("address") or first_from.get("email") if isinstance(first_from, dict) else str(first_from)
        elif isinstance(from_list, dict):
            sender = from_list.get("address") or from_list.get("email") or ""
        elif isinstance(from_list, str):
            sender = from_list

        to_list = payload.get("to") or []
        recipient = ""
        if isinstance(to_list, list) and to_list:
            first_to = to_list[0]
            recipient = first_to.get("address") or first_to.get("email") if isinstance(first_to, dict) else str(first_to)

        subject = payload.get("subject") or ""
        body = payload.get("body") or payload.get("snippet") or payload.get("text") or ""
        msg_id = payload.get("id") or payload.get("messageId")
        thread_id = payload.get("threadId")

        if not sender and not body:
            return None

        return {
            "provider": "aurinko",
            "event": event,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "message_id": msg_id,
            "thread_id": thread_id,
            "account_id": data.get("accountId"),
            "raw": data,
        }


def get_universal_mailbox_provider(db: Session, tenant_id: str) -> Optional[BaseUniversalMailboxAdapter]:
    """
    Factory function resolving configured Universal Mailbox Adapter for a tenant.
    Checks APICredential for 'aurinko', 'unipile', 'emailengine', or 'universal_email'.
    Falls back to global environment settings if present.
    """
    # 1. Check tenant Aurinko credential
    cred_aurinko = get_credential(db, tenant_id, "aurinko")
    if cred_aurinko and cred_aurinko.encrypted_key:
        try:
            decrypted = decrypt_api_key(cred_aurinko.encrypted_key)
            settings = cred_aurinko.settings or {}
            client_id = settings.get("client_id")
            client_secret = settings.get("client_secret") or decrypted
            access_token = settings.get("access_token")
            api_url = settings.get("api_url")
            webhook_secret = settings.get("webhook_secret")
            if decrypted.startswith("{"):
                parsed = json.loads(decrypted)
                client_id = parsed.get("client_id") or client_id
                client_secret = parsed.get("client_secret") or client_secret
                access_token = parsed.get("access_token") or access_token
                webhook_secret = parsed.get("webhook_secret") or webhook_secret
                api_url = parsed.get("api_url") or api_url
            return AurinkoAdapter(
                client_id=client_id,
                client_secret=client_secret,
                access_token=access_token,
                api_url=api_url,
                webhook_secret=webhook_secret,
            )
        except Exception as exc:
            logger.warning(f"Failed to parse Aurinko credential for {tenant_id}: {exc}")

    # 2. Check tenant Unipile credential
    cred_unipile = get_credential(db, tenant_id, "unipile")
    if cred_unipile and cred_unipile.encrypted_key:
        try:
            decrypted = decrypt_api_key(cred_unipile.encrypted_key)
            settings = cred_unipile.settings or {}
            api_key = decrypted
            api_url = settings.get("api_url")
            webhook_secret = settings.get("webhook_secret")
            if decrypted.startswith("{"):
                parsed = json.loads(decrypted)
                api_key = parsed.get("api_key") or api_key
                api_url = parsed.get("api_url") or api_url
                webhook_secret = parsed.get("webhook_secret") or webhook_secret
            return UnipileAdapter(api_key=api_key, api_url=api_url, webhook_secret=webhook_secret)
        except Exception as exc:
            logger.warning(f"Failed to parse Unipile credential for {tenant_id}: {exc}")

    # 3. Check tenant EmailEngine credential
    cred_ee = get_credential(db, tenant_id, "emailengine")
    if cred_ee and cred_ee.encrypted_key:
        try:
            decrypted = decrypt_api_key(cred_ee.encrypted_key)
            settings = cred_ee.settings or {}
            base_url = settings.get("url") or "http://localhost:3000"
            token = decrypted
            return EmailEngineAdapter(base_url=base_url, access_token=token)
        except Exception as exc:
            logger.warning(f"Failed to parse EmailEngine credential for {tenant_id}: {exc}")

    # 4. Check environment-level Aurinko configuration
    env_aurinko_client_id = os.environ.get("AURINKO_CLIENT_ID")
    if env_aurinko_client_id or os.environ.get("AURINKO_ACCESS_TOKEN"):
        return AurinkoAdapter(
            client_id=env_aurinko_client_id,
            client_secret=os.environ.get("AURINKO_CLIENT_SECRET"),
            access_token=os.environ.get("AURINKO_ACCESS_TOKEN"),
            api_url=os.environ.get("AURINKO_API_URL"),
            webhook_secret=os.environ.get("AURINKO_WEBHOOK_SECRET"),
        )

    # 5. Check environment-level Unipile configuration
    env_unipile_key = os.environ.get("UNIPILE_API_KEY")
    if env_unipile_key:
        return UnipileAdapter(
            api_key=env_unipile_key,
            api_url=os.environ.get("UNIPILE_API_URL"),
            webhook_secret=os.environ.get("UNIPILE_WEBHOOK_SECRET"),
        )

    # 6. Check environment-level EmailEngine configuration
    env_ee_token = os.environ.get("EMAILENGINE_TOKEN")
    if env_ee_token:
        return EmailEngineAdapter(
            base_url=os.environ.get("EMAILENGINE_URL", "http://localhost:3000"),
            access_token=env_ee_token,
            secret=os.environ.get("EMAILENGINE_SECRET"),
        )

    return None
