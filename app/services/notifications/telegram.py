import httpx
from sqlalchemy.orm import Session
from app.models.base import APICredential
from app.core.security import decrypt_api_key


async def send_telegram_notification(
    db: Session, tenant_id: str, message: str, *, parse_mode: str | None = "Markdown"
) -> bool:
    """
    Sends a message via Telegram bot if credentials are provided in the database.
    Requires an APICredential with provider='telegram'.
    settings should contain 'chat_id' and encrypted_key is the Bot Token.
    """
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "telegram"
    ).first()

    if not cred or not cred.encrypted_key or not cred.settings:
        return False

    bot_token = decrypt_api_key(cred.encrypted_key)
    chat_id = cred.settings.get("chat_id")

    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code == 200:
                return True
            else:
                print(f"Telegram API Error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False
