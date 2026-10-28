"""Live records of the systems the OctaOS assistant can use.

The assistant writes its own answer from these records. This module only
looks up what is saved and what is absent. It does not call a provider or
send mail, and it does not author the sentence the user reads.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.rag.hybrid_engine import _near, query_requests_company_knowledge


_CONNECTION_STEMS = ("grok", "connected", "connection", "connector")
_WORK_VERBS = ("find", "draft", "send", "create", "hire", "source", "generate", "launch", "publish")
# Words that point at a saved system. The provider key is separate from an MCP client.
_SYSTEM_ALIASES = (
    ("claude", "anthropic", "Claude"),
    ("anthropic", "anthropic", "Claude"),
    ("grok", "grok", "Grok"),
    ("xai", "grok", "Grok"),
    ("deepseek", "deepseek", "DeepSeek"),
    ("cursor", None, "Cursor"),
    ("openai", "openai", "OpenAI"),
    ("chatgpt", "openai", "OpenAI"),
    ("gemini", "gemini", "Gemini"),
    ("whatsapp", None, "WhatsApp"),
    ("mailbox", None, "Mailbox"),
    ("email", None, "Mailbox"),
)

_KNOWLEDGE_DENIALS = (
    "don't have specific information",
    "do not have specific information",
    "don't have any information",
    "knowledge base is empty",
    "no information about",
    "couldn't find any information",
    "could not find any information",
    "don't see the actual crawled",
    "do not see the actual crawled",
    "share what was found",
    "paste the",
    "paste website",
    "paste crawled",
)


def request_asks_to_message_connection(text: str) -> bool:
    """True when the user wants a message placed on a connected MCP client."""
    lowered = (text or "").lower()
    if not re.search(r"\b(message|tell|text|notify|ping)\w*", lowered):
        return False
    if "mcp" in lowered:
        return True
    tokens = re.findall(r"[a-z0-9]{4,}", lowered)
    for token in tokens:
        for stem in ("grok", "claude", "cursor", "deepseek"):
            if _near(token, stem):
                return True
    return bool(re.search(r"\b(bot|client)\b", lowered))


def clients_addressed_by(snapshot: Dict[str, Any], request: str) -> List[Dict[str, Any]]:
    """Pick the MCP clients named in the request. One saved client matches a generic ask."""
    clients = [client for client in (snapshot.get("mcp_clients") or []) if client.get("active", True)]
    lowered = (request or "").lower()
    # Three-letter words such as "you" are within edit distance of "bot".
    # A client is selected from a real name token, or from an explicit bot/client ask below.
    tokens = re.findall(r"[a-z0-9]{4,}", lowered)
    chosen = []
    for client in clients:
        blob = f"{client.get('name') or ''} {client.get('client_type') or ''}".lower()
        parts = re.findall(r"[a-z0-9]{3,}", blob)
        if any(token in blob or any(_near(token, part) for part in parts) for token in tokens):
            chosen.append(client)
    if not chosen and len(clients) == 1 and re.search(r"\b(mcp|bot|client)\b", lowered):
        return clients
    return chosen


def request_asks_about_connections(text: str) -> bool:
    """True when this turn is asking to inspect MCP, Grok, or connected systems."""
    lowered = (text or "").lower()
    if not lowered.strip():
        return False
    if any(re.search(rf"\b{verb}\b", lowered) for verb in _WORK_VERBS):
        return False
    if "mcp" in lowered:
        return True
    tokens = re.findall(r"[a-z0-9]{4,}", lowered)
    for token in tokens:
        for stem in _CONNECTION_STEMS:
            if _near(token, stem):
                return True
    return bool(re.search(r"\breach\b", lowered) and re.search(r"\bbot\b", lowered))


def request_checks_company_services(text: str) -> bool:
    """True when the user is asking what the company offers, not to launch the work."""
    lowered = (text or "").lower()
    if any(re.search(rf"\b{verb}\b", lowered) for verb in ("send", "create", "launch", "publish", "generate", "source")):
        return False
    asks = bool(re.search(r"\b(check|does|offer|offers|service|services)\b", lowered) or " do " in f" {lowered} ")
    return asks and bool(
        re.search(r"\b(consult\w*|market\w*|hir\w*|recruit\w*|ai\s*house|alienhouse|company)\b", lowered)
        or "house" in lowered
    )


def reply_denies_stored_knowledge(reply: str) -> bool:
    lowered = (reply or "").lower()
    return any(phrase in lowered for phrase in _KNOWLEDGE_DENIALS)


def reply_claims_live_send(reply: str) -> bool:
    lowered = (reply or "").lower()
    if "cannot be sent" in lowered or "not connected" in lowered or "draft" in lowered and "will not" in lowered:
        return False
    return bool(re.search(r"\b(can send|i can send|send outreach|via email and whatsapp|via email or whatsapp)\b", lowered))


def load_connected_systems(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Read connection rows. Secrets stay in the credential store."""
    snapshot: Dict[str, Any] = {
        "mcp_clients": [],
        "connectors": [],
        "collaboration": "unknown",
        "outbound_providers": [],
        "mailbox_connected": False,
        "whatsapp_configured": False,
    }
    try:
        from app.models.mcp import DynamicConnector, SystemMCPCredential

        clients = (
            db.query(SystemMCPCredential)
            .filter(SystemMCPCredential.tenant_id == tenant_id)
            .all()
        )
        snapshot["mcp_clients"] = [
            {
                "id": row.id,
                "name": row.name,
                "client_type": row.client_type,
                "role": row.role,
                "active": bool(row.is_active),
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            }
            for row in clients
        ]
        connectors = (
            db.query(DynamicConnector)
            .filter(DynamicConnector.tenant_id == tenant_id)
            .all()
        )
        snapshot["connectors"] = [
            {
                "name": row.name,
                "slug": row.slug,
                "connector_type": row.connector_type,
                "status": row.status,
            }
            for row in connectors
        ]
    except Exception:
        snapshot["mcp_clients"] = []
        snapshot["connectors"] = []

    try:
        from app.services.collaboration.live_terminal import LiveTerminalManager

        snapshot["collaboration"] = "RUNNING" if LiveTerminalManager.is_process_active(db, tenant_id) else "STOPPED"
    except Exception:
        snapshot["collaboration"] = "unknown"

    try:
        from app.services.collaboration.provider_registry import AIProviderRegistry

        providers = []
        for provider in AIProviderRegistry.get_connected_providers(db, tenant_id):
            providers.append({
                "name": provider.provider,
                "display_name": provider.display_name,
                "configured": bool(provider.is_configured),
            })
        snapshot["providers"] = providers
        snapshot["outbound_providers"] = [item["name"] for item in providers if item["configured"]]
    except Exception:
        snapshot["providers"] = []
        snapshot["outbound_providers"] = []

    try:
        from app.core.config import settings

        snapshot["inbuilt_model_route"] = getattr(settings, "DEFAULT_AI_PROVIDER", None) or ""
    except Exception:
        snapshot["inbuilt_model_route"] = ""

    try:
        from app.models.base import APICredential

        whatsapp = (
            db.query(APICredential)
            .filter(APICredential.tenant_id == tenant_id, APICredential.provider == "whatsapp")
            .first()
        )
        snapshot["whatsapp_configured"] = bool(whatsapp and whatsapp.encrypted_key)
    except Exception:
        snapshot["whatsapp_configured"] = False

    try:
        from app.services.email.universal_provider import get_universal_mailbox_provider

        snapshot["mailbox_connected"] = get_universal_mailbox_provider(db, tenant_id) is not None
    except Exception:
        snapshot["mailbox_connected"] = False
    return snapshot


def _public_client(client: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": client.get("name"),
        "client_type": client.get("client_type"),
        "role": client.get("role"),
        "active": client.get("active", True),
        "last_used_at": client.get("last_used_at"),
    }


def _client_matches(client: Dict[str, Any], alias: str) -> bool:
    blob = f"{client.get('name') or ''} {client.get('client_type') or ''}".lower()
    if alias in blob:
        return True
    parts = re.findall(r"[a-z0-9]{3,}", blob)
    return any(_near(alias, part) for part in parts)


def systems_named_in_request(snapshot: Dict[str, Any], request: str) -> List[Dict[str, Any]]:
    """Which systems this turn names, and whether each one is saved."""
    lowered = (request or "").lower()
    tokens = re.findall(r"[a-z0-9]{4,}", lowered)
    providers = list(snapshot.get("providers") or [])
    configured_names = set(snapshot.get("outbound_providers") or [])
    found: List[Dict[str, Any]] = []
    seen = set()
    for token in tokens:
        for alias, provider_name, label in _SYSTEM_ALIASES:
            if label in seen or not _near(token, alias):
                continue
            if label in ("Mailbox", "WhatsApp") and not request_asks_about_connections(request):
                if alias == "email" or alias not in lowered:
                    continue
            seen.add(label)
            entry: Dict[str, Any] = {
                "name": label,
                "mcp_clients": [
                    _public_client(client)
                    for client in (snapshot.get("mcp_clients") or [])
                    if _client_matches(client, alias if alias != "email" else label.lower())
                ],
            }
            if provider_name:
                match = next((item for item in providers if item.get("name") == provider_name), None)
                entry["provider"] = provider_name
                entry["provider_configured"] = bool(
                    (match and match.get("configured")) or provider_name in configured_names
                )
            if label == "Mailbox":
                entry["connected"] = bool(snapshot.get("mailbox_connected"))
            if label == "WhatsApp":
                entry["configured"] = bool(snapshot.get("whatsapp_configured"))
            found.append(entry)
    return found


def connection_facts(snapshot: Dict[str, Any], request: str = "") -> str:
    """Records the assistant reads before it answers. This is data, not a reply."""
    providers = snapshot.get("providers")
    if not providers:
        providers = [
            {"name": name, "configured": True}
            for name in (snapshot.get("outbound_providers") or [])
        ]
    payload: Dict[str, Any] = {
        "mcp_clients": [_public_client(client) for client in (snapshot.get("mcp_clients") or [])],
        "connectors": snapshot.get("connectors") or [],
        "collaboration_listener": snapshot.get("collaboration") or "unknown",
        "providers": providers,
        "mailbox_connected": bool(snapshot.get("mailbox_connected")),
        "whatsapp_configured": bool(snapshot.get("whatsapp_configured")),
        "inbuilt_model_route": snapshot.get("inbuilt_model_route") or "",
    }
    asked = systems_named_in_request(snapshot, request) if request else []
    if asked:
        payload["asked_about"] = asked
    return json.dumps(payload, default=str)


def ensure_mcp_message_task(tasks: Optional[List[Dict[str, Any]]], request: str) -> List[Dict[str, Any]]:
    """Queue a real MCP handoff when the user asked to message a client.

    A reach or status question does not add this task. The model's own words
    stay in the reply; this only makes the send happen.
    """
    items = [task for task in (tasks or []) if isinstance(task, dict)]
    if not request_asks_to_message_connection(request):
        return items
    if any(task.get("department") == "System" and task.get("action") == "message_mcp_client" for task in items):
        return items
    items.append({
        "department": "System",
        "action": "message_mcp_client",
        "parameters": {"client": request, "text": request},
    })
    return items


def mcp_handoff_note(placed: Dict[str, Any]) -> str:
    """One factual line about a message that was actually queued or pushed."""
    name = placed.get("client_name") or "MCP client"
    streams = int(placed.get("open_streams") or 0)
    if streams:
        where = f"pushed to {streams} open stream(s) and kept for the next call"
    else:
        where = "queued because no stream is open; it is included in the client's next OctaOS call"
    return (
        f"MCP handoff: {name} status {placed.get('status') or 'queued'} ({where}). "
        "This is not a claim that the client displayed it."
    )


def format_connection_report(snapshot: Dict[str, Any]) -> str:
    """Backward-compatible name. The assistant writes the answer; this is only the lookup."""
    return connection_facts(snapshot)


def grounded_company_answer(hits: List[Dict[str, Any]]) -> str:
    """Cite stored pages when the model claims the library is empty."""
    lines = ["These points are already stored from the crawled company website:"]
    seen = set()
    for hit in hits or []:
        url = str(hit.get("source_url") or "").strip()
        if not url or url in seen:
            continue
        text = re.sub(r"https?://\S+", " ", str(hit.get("content") or ""))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 40:
            continue
        seen.add(url)
        lines.append(f"- {url}: {text[:420]}")
        if len(seen) >= 4:
            break
    if len(seen) == 0:
        return ""
    return "\n".join(lines)


def active_mcp_clients(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [client for client in (snapshot.get("mcp_clients") or []) if client.get("active", True)]


def correct_assistant_reply(
    message: str,
    request: str,
    hits: Optional[List[Dict[str, Any]]],
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """Replace a refusal that contradicts stored company pages.

    Connection answers are left to the model. A denial is not overwritten
    with a connection script.
    """
    text = (message or "").strip()
    drop_tasks = request_checks_company_services(request)
    company_question = drop_tasks or query_requests_company_knowledge(
        request, [str(hit.get("source_url") or "") for hit in (hits or [])],
    )
    provider_down = "could not reach the language model" in text.lower()
    if hits and (reply_denies_stored_knowledge(text) or (company_question and (not text or provider_down))):
        grounded = grounded_company_answer(hits)
        if grounded:
            text = grounded
    if not snapshot.get("mailbox_connected") and reply_claims_live_send(text):
        text = (
            text.rstrip()
            + "\n\nA mailbox is not connected, so email cannot be sent. "
            + "WhatsApp has no saved credential. Unsent drafts can still be stored."
        )
    return {"message": text, "drop_tasks": drop_tasks}
