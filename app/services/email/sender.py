"""Shared outbound email delivery for Sales, HR, and Workflow agents."""
import json
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.services.credentials import get_credential


def parse_smtp_credentials(key_str: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = urllib.parse.urlparse(key_str.strip())
        if parsed.scheme == "smtp":
            return {
                "username": parsed.username or "",
                "password": parsed.password or "",
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 587,
            }
    except Exception:
        pass
    return None


def send_smtp_email(smtp_cred: dict, to_email: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart()
    from_addr = smtp_cred.get("from_addr") or smtp_cred.get("username")
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    port = int(smtp_cred.get("port") or 587)
    host = smtp_cred.get("host") or "smtp.gmail.com"

    # Port 465 uses direct SSL; Port 587 uses STARTTLS
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        if smtp_cred.get("use_tls", True):
            server.starttls()

    server.login(smtp_cred["username"], smtp_cred["password"])
    server.send_message(msg)
    server.quit()
    return True


def send_gmail_email(creds_dict: dict, to_email: str, subject: str, body: str):
    import base64
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes"),
    )
    service = build("gmail", "v1", credentials=creds)

    message = MIMEMultipart()
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
    return {
        "ok": True,
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
    }


def check_universal_email_configured(db: Session, tenant_id: str) -> bool:
    try:
        from app.services.email.universal_provider import get_universal_mailbox_provider
        provider = get_universal_mailbox_provider(db, tenant_id)
        return bool(provider and provider.is_configured())
    except Exception:
        return False


def check_gmail_configured(db: Session, tenant_id: str) -> bool:
    cred = get_credential(db, tenant_id, "gmail")
    return bool(cred and cred.encrypted_key)


def get_system_smtp_credentials() -> Optional[Dict[str, Any]]:
    from app.core.config import settings
    if (
        getattr(settings, "SMTP_USER", None)
        and "your_smtp_user" not in settings.SMTP_USER
        and getattr(settings, "SMTP_PASSWORD", None)
        and "your_smtp_password" not in settings.SMTP_PASSWORD
    ):
        return {
            "username": settings.SMTP_USER,
            "password": settings.SMTP_PASSWORD,
            "host": getattr(settings, "SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com",
            "port": int(getattr(settings, "SMTP_PORT", 587) or 587),
            "from_addr": getattr(settings, "SMTP_FROM", None) or settings.SMTP_USER,
            "use_tls": getattr(settings, "EMAIL_USE_TLS", True),
        }
    return None


def check_smtp_configured(db: Session, tenant_id: str) -> bool:
    cred = get_credential(db, tenant_id, "smtp")
    if cred and cred.encrypted_key:
        if bool(parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))):
            return True
    return bool(get_system_smtp_credentials())


def send_email(
    db: Session,
    tenant_id: str,
    to_email: str,
    subject: str,
    body: str,
    channel: str = "smtp",
) -> Dict[str, Any]:
    if channel in ("universal", "unipile", "emailengine"):
        from app.services.email.universal_provider import get_universal_mailbox_provider
        provider = get_universal_mailbox_provider(db, tenant_id)
        if provider and provider.is_configured():
            return provider.send_email(to_email, subject, body)
        return {"sent": False, "reason": "Universal email provider not configured"}

    if channel == "gmail":
        if not check_gmail_configured(db, tenant_id):
            return {"sent": False, "reason": "Gmail not configured"}
        cred = get_credential(db, tenant_id, "gmail")
        try:
            creds_dict = json.loads(decrypt_api_key(cred.encrypted_key))
            result = send_gmail_email(creds_dict, to_email, subject, body)
            return {"sent": True, "details": result}
        except Exception as e:
            return {"sent": False, "reason": str(e)}

    smtp = None
    cred = get_credential(db, tenant_id, "smtp")
    if cred and cred.encrypted_key:
        smtp = parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
    if not smtp:
        smtp = get_system_smtp_credentials()

    if not smtp:
        return {"sent": False, "reason": "SMTP not configured"}
    
    try:
        send_smtp_email(smtp, to_email, subject, body)
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "reason": str(e)}


def send_email_with_status(
    db: Session,
    tenant_id: str,
    to_email: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
) -> dict:
    """
    Try to send email via Universal Mailbox (Google/Outlook/IMAP) first,
    then Gmail OAuth, then SMTP.
    Always returns a structured dict: {sent, channel, reason, message}.
    Never raises — safe to call without try/except.
    """
    universal_ok = check_universal_email_configured(db, tenant_id)
    gmail_ok = check_gmail_configured(db, tenant_id)
    smtp_ok = check_smtp_configured(db, tenant_id)

    if not universal_ok and not gmail_ok and not smtp_ok:
        return {
            "sent": False,
            "channel": None,
            "reason": "no_email_configured",
            "message": "No email provider configured. Connect Google Workspace, Microsoft 365, or SMTP in API Management.",
        }

    if not to_email:
        return {
            "sent": False,
            "channel": None,
            "reason": "no_recipient",
            "message": "No email address available for this lead.",
        }

    # 1. Try Universal Mailbox first (Unipile, EmailEngine, Aurinko)
    if universal_ok:
        try:
            from app.services.email.universal_provider import get_universal_mailbox_provider
            provider = get_universal_mailbox_provider(db, tenant_id)
            if provider and provider.is_configured():
                res = provider.send_email(
                    to_email,
                    subject,
                    body,
                    thread_id=thread_id,
                    in_reply_to=in_reply_to,
                )
                if res.get("sent"):
                    return {
                        "sent": True,
                        "channel": "universal",
                        "provider": provider.name,
                        "reason": "success",
                        "message": f"Sent via Universal Mailbox ({provider.name})",
                        "details": res,
                    }
        except Exception:
            pass  # Fall through to Gmail or SMTP

    # 2. Try Gmail next
    if gmail_ok:
        try:
            cred = get_credential(db, tenant_id, "gmail")
            creds_dict = json.loads(decrypt_api_key(cred.encrypted_key))
            result = send_gmail_email(creds_dict, to_email, subject, body)
            if result and result.get("ok"):
                return {"sent": True, "channel": "gmail", "reason": "success", "message": "Sent via Gmail"}
        except Exception as e:
            pass  # Fall through to SMTP

    # 3. Try SMTP fallback
    if smtp_ok:
        try:
            smtp = None
            cred = get_credential(db, tenant_id, "smtp")
            if cred and cred.encrypted_key:
                smtp = parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
            if not smtp:
                smtp = get_system_smtp_credentials()
            if smtp and send_smtp_email(smtp, to_email, subject, body):
                return {"sent": True, "channel": "smtp", "reason": "success", "message": "Sent via SMTP"}
        except Exception as e:
            return {"sent": False, "channel": "smtp", "reason": "send_failed", "message": f"SMTP send error: {str(e)}"}

    return {"sent": False, "channel": None, "reason": "all_failed", "message": "All email channels failed."}


def send_global_smtp_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email using global SMTP settings from configuration."""
    from app.core.config import settings
    import logging
    
    # Check if SMTP settings are missing or contain placeholder values
    is_placeholder = (
        not settings.SMTP_USER 
        or "your_smtp_user" in settings.SMTP_USER 
        or not settings.SMTP_PASSWORD 
        or "your_smtp_password" in settings.SMTP_PASSWORD
    )
    
    if is_placeholder:
        logging.warning(
            f"[EMAIL NOT SENT] SMTP is not configured. "
            f"Please go to Platform Setup \u2192 API Settings and add your SMTP credentials. "
            f"Attempted to send to: {to_email} | Subject: {subject}"
        )
        return False

    smtp_cred = {
        "username": settings.SMTP_USER,
        "password": settings.SMTP_PASSWORD,
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "from_addr": settings.SMTP_FROM,
        "use_tls": getattr(settings, "EMAIL_USE_TLS", True)
    }
    
    try:
        return send_smtp_email(smtp_cred, to_email, subject, body)
    except Exception as e:
        logging.error(
            f"[EMAIL FAILED] SMTP send error: {e}. "
            f"Please verify your SMTP credentials under Platform Setup \u2192 API Settings."
        )
        return False
