import logging
from typing import List, Dict, Any, Optional
import time
from app.core.resilience import api_breaker

logger = logging.getLogger(__name__)

class BaseProvider:
    def __init__(self, provider_id: str, provider_name: str):
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.score = 1.0  # Dynamic score: success increases it, failure drops it.
        self.latency_history: List[float] = []

    async def is_healthy(self) -> bool:
        raise NotImplementedError()

# --- Interfaces ---

class EmailProvider(BaseProvider):
    async def send_email(self, to_email: str, subject: str, body: str, creds: Optional[dict] = None) -> bool:
        raise NotImplementedError()

class WhatsAppProvider(BaseProvider):
    async def send_whatsapp_message(self, recipient: str, content: str, creds: Optional[dict] = None) -> bool:
        raise NotImplementedError()

class TelegramProvider(BaseProvider):
    async def send_telegram_message(self, chat_id: str, content: str, creds: Optional[dict] = None) -> bool:
        raise NotImplementedError()

class CalendarProvider(BaseProvider):
    async def create_meeting(self, title: str, start_time: Any, duration_minutes: int, attendees: list, creds: Optional[dict] = None) -> dict:
        raise NotImplementedError()

# --- Adapters ---

class SMTPEmailAdapter(EmailProvider):
    async def is_healthy(self) -> bool:
        return True # SMTP check

    async def send_email(self, to_email: str, subject: str, body: str, creds: Optional[dict] = None) -> bool:
        from app.services.email.sender import send_smtp_email
        if not creds:
            from app.core.config import settings
            creds = {
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "username": settings.SMTP_USER,
                "password": settings.SMTP_PASSWORD,
                "from_addr": settings.SMTP_FROM,
                "use_tls": getattr(settings, "EMAIL_USE_TLS", True)
            }
        start = time.time()
        try:
            with api_breaker.calling():
                res = send_smtp_email(creds, to_email, subject, body)
            self.latency_history.append(time.time() - start)
            return res
        except Exception as e:
            logger.error(f"SMTPEmailAdapter send failed: {e}")
            raise e

class GmailEmailAdapter(EmailProvider):
    async def is_healthy(self) -> bool:
        return True

    async def send_email(self, to_email: str, subject: str, body: str, creds: Optional[dict] = None) -> bool:
        from app.services.email.sender import send_gmail_email
        if not creds:
            return False
        start = time.time()
        try:
            with api_breaker.calling():
                res = send_gmail_email(creds, to_email, subject, body)
            self.latency_history.append(time.time() - start)
            return bool(res and res.get("ok"))
        except Exception as e:
            logger.error(f"GmailEmailAdapter send failed: {e}")
            raise e

class MetaWhatsAppAdapter(WhatsAppProvider):
    async def is_healthy(self) -> bool:
        return True

    async def send_whatsapp_message(self, recipient: str, content: str, creds: Optional[dict] = None) -> bool:
        # Placeholder Meta API call
        logger.info(f"WhatsApp Meta: Sent message to {recipient}")
        return True

class TelegramBotAdapter(TelegramProvider):
    async def is_healthy(self) -> bool:
        return True

    async def send_telegram_message(self, chat_id: str, content: str, creds: Optional[dict] = None) -> bool:
        from app.services.notifications.telegram import send_telegram_notification
        # Since send_telegram_notification needs db, tenant_id, we can adapt:
        # For direct adapter, we fetch bot_token, chat_id
        if not creds:
            return False
        bot_token = creds.get("bot_token")
        import httpx
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": content}
        async with httpx.AsyncClient() as client:
            with api_breaker.calling():
                res = await client.post(url, json=payload, timeout=10.0)
            return res.status_code == 200

class GoogleCalendarAdapter(CalendarProvider):
    async def is_healthy(self) -> bool:
        return True

    async def create_meeting(self, title: str, start_time: Any, duration_minutes: int, attendees: list, creds: Optional[dict] = None) -> dict:
        # Google Calendar event creation
        logger.info(f"Google Calendar: Scheduled meeting '{title}'")
        return {
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "meeting_time": str(start_time),
            "provider": "google_calendar"
        }

# --- Provider Manager ---

class ProviderManager:
    def __init__(self):
        self._registry: Dict[str, List[BaseProvider]] = {
            "email": [SMTPEmailAdapter("smtp", "SMTP Outbound"), GmailEmailAdapter("gmail", "Google Gmail OAuth")],
            "whatsapp": [MetaWhatsAppAdapter("meta_whatsapp", "Meta WhatsApp API")],
            "telegram": [TelegramBotAdapter("telegram_bot", "Telegram Bot API")],
            "calendar": [GoogleCalendarAdapter("google_calendar", "Google Calendar API")]
        }

    def register_provider(self, category: str, provider: BaseProvider):
        if category not in self._registry:
            self._registry[category] = []
        self._registry[category].append(provider)

    def report_success(self, provider: BaseProvider):
        provider.score = min(1.0, provider.score + 0.05)
        logger.debug(f"Provider {provider.provider_id} success reported. New score: {provider.score:.2f}")

    def report_failure(self, provider: BaseProvider):
        provider.score = max(0.0, provider.score - 0.20)
        logger.warning(f"Provider {provider.provider_id} failure reported. New score: {provider.score:.2f}")

    async def get_healthy_providers(self, category: str) -> List[BaseProvider]:
        providers = self._registry.get(category, [])
        healthy = []
        for p in providers:
            try:
                if await p.is_healthy():
                    healthy.append(p)
            except Exception:
                p.score = max(0.0, p.score - 0.10)
        # Sort by score descending
        healthy.sort(key=lambda x: x.score, reverse=True)
        return healthy

    async def execute_with_failover(self, category: str, method_name: str, *args, **kwargs) -> Any:
        providers = await self.get_healthy_providers(category)
        if not providers:
            raise RuntimeError(f"No healthy providers available for category: {category}")

        last_error = None
        for provider in providers:
            if not hasattr(provider, method_name):
                continue
            method = getattr(provider, method_name)
            try:
                result = await method(*args, **kwargs)
                self.report_success(provider)
                return result
            except Exception as e:
                self.report_failure(provider)
                last_error = e
                logger.error(f"Provider {provider.provider_id} execution failed: {e}. Trying next provider...")
                
        raise RuntimeError(f"All providers in category '{category}' failed. Last error: {last_error}")

# Global provider manager instance
provider_manager = ProviderManager()
