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
    msg["From"] = smtp_cred["username"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(smtp_cred["host"], smtp_cred["port"])
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


def send_email(
    db: Session,
    tenant_id: str,
    to_email: str,
    subject: str,
    body: str,
    channel: str = "smtp",
) -> bool:
    if channel == "gmail":
        cred = get_credential(db, tenant_id, "gmail")
        if cred and cred.encrypted_key:
            try:
                creds_dict = json.loads(decrypt_api_key(cred.encrypted_key))
                result = send_gmail_email(creds_dict, to_email, subject, body)
                return bool(result and result.get("ok"))
            except Exception:
                return False
        return False

    cred = get_credential(db, tenant_id, "smtp")
    if cred and cred.encrypted_key:
        smtp = parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
        if smtp:
            try:
                return send_smtp_email(smtp, to_email, subject, body)
            except Exception:
                return False
    return False


def send_global_smtp_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email using global SMTP settings from configuration."""
    from app.core.config import settings
    
    # Check if SMTP settings are missing or contain placeholder values
    is_placeholder = (
        not settings.SMTP_USER 
        or "your_smtp_user" in settings.SMTP_USER 
        or not settings.SMTP_PASSWORD 
        or "your_smtp_password" in settings.SMTP_PASSWORD
    )
    
    if is_placeholder:
        print(f"\n========================================================")
        print(f"[MOCK EMAIL] TO: {to_email}")
        print(f"[MOCK EMAIL] SUBJECT: {subject}")
        print(f"[MOCK EMAIL] BODY:\n{body}")
        print(f"========================================================\n")
        return True

    smtp_cred = {
        "username": settings.SMTP_USER,
        "password": settings.SMTP_PASSWORD,
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT
    }
    
    try:
        return send_smtp_email(smtp_cred, to_email, subject, body)
    except Exception as e:
        print(f"Error sending global SMTP email: {e}")
        if settings.DEV:
            print(f"\n========================================================")
            print(f"[SMTP FAIL - FALLBACK MOCK EMAIL] TO: {to_email}")
            print(f"[SMTP FAIL - FALLBACK MOCK EMAIL] SUBJECT: {subject}")
            print(f"[SMTP FAIL - FALLBACK MOCK EMAIL] BODY:\n{body}")
            print(f"========================================================\n")
            return True
        return False
