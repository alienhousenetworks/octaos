"""Live status of the systems the OctaOS assistant is allowed to use.

The assistant used to answer from a fixed department list and tell the user it
could not see MCP. Grok Bot is an inbound MCP client of this workspace, and
the crawled service pages are already stored. This module reports those facts
and does not call a provider or send mail.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.rag.hybrid_engine import _near, query_requests_company_knowledge


_CONNECTION_STEMS = ("grok", "connected", "connection", "connector")
_WORK_VERBS = ("find", "draft", "send", "create", "hire", "source", "generate", "launch", "publish")
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
_MCP_DENIALS = (
    "cannot reach",
    "can't reach",
    "can not reach",
    "no mcp",
    "don't have a direct mcp",
    "do not have a direct mcp",
    "no direct mcp",
    "not connected to grok",
    "cannot reach out to grok",
    "can't reach out to grok",
)


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


def reply_denies_mcp(reply: str) -> bool:
    lowered = (reply or "").lower()
    return any(phrase in lowered for phrase in _MCP_DENIALS)


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

        configured = []
        for provider in AIProviderRegistry.get_connected_providers(db, tenant_id):
            if provider.is_configured:
                configured.append(provider.provider)
        snapshot["outbound_providers"] = configured
    except Exception:
        snapshot["outbound_providers"] = []

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


def format_connection_report(snapshot: Dict[str, Any]) -> str:
    """Plain-language status. This is the answer when the user asks what is connected."""
    lines: List[str] = ["Connected systems for this workspace:"]
    clients = snapshot.get("mcp_clients") or []
    if clients:
        lines.append("MCP clients that can call OctaOS:")
        for client in clients:
            state = "active" if client.get("active") else "inactive"
            used = client.get("last_used_at") or "never"
            lines.append(
                f"- {client.get('name')} ({client.get('client_type')}, role {client.get('role')}, {state}, last used {used})"
            )
    else:
        lines.append("MCP clients that can call OctaOS: none saved.")

    connectors = snapshot.get("connectors") or []
    if connectors:
        lines.append("Data connectors:")
        for connector in connectors:
            lines.append(
                f"- {connector.get('name')} ({connector.get('slug')}, {connector.get('connector_type')}, {connector.get('status')})"
            )
    else:
        lines.append("Data connectors: none saved.")

    lines.append(f"External collaboration listener: {snapshot.get('collaboration') or 'unknown'}.")
    outbound = snapshot.get("outbound_providers") or []
    if outbound:
        lines.append("Outbound AI keys saved: " + ", ".join(outbound) + ".")
    else:
        lines.append("Outbound AI keys saved: none. This assistant still uses the server's inbuilt model route.")

    grok_inbound = any(str(client.get("name") or "").lower().find("grok") >= 0 or str(client.get("client_type") or "").lower().find("grok") >= 0 for client in clients)
    grok_outbound = "grok" in outbound
    if grok_inbound and not grok_outbound:
        lines.append(
            "Grok Bot is connected as an inbound MCP client, so Grok can call OctaOS tools. "
            "No outbound Grok API key is saved, so this assistant cannot open a new chat inside the Grok app."
        )
    elif grok_outbound:
        lines.append("An outbound Grok key is saved. A request to reach Grok uses that key and reports the provider result.")
    else:
        lines.append("Grok is not connected in either direction.")

    if snapshot.get("mailbox_connected"):
        lines.append("Mailbox: connected. Email send is available when you explicitly ask to send.")
    else:
        lines.append("Mailbox: not connected. Email cannot be sent. Unsent drafts can still be stored.")
    if snapshot.get("whatsapp_configured"):
        lines.append("WhatsApp: a credential is saved.")
    else:
        lines.append("WhatsApp: no credential is saved, so a WhatsApp message cannot be sent.")
    return "\n".join(lines)


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
    """Replace a refusal that contradicts stored pages or a live MCP client."""
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
    if active_mcp_clients(snapshot) and reply_denies_mcp(text):
        text = format_connection_report(snapshot)
    if not snapshot.get("mailbox_connected") and reply_claims_live_send(text):
        text = (
            text.rstrip()
            + "\n\nA mailbox is not connected, so email cannot be sent. "
            + "WhatsApp has no saved credential. Unsent drafts can still be stored."
        )
    return {"message": text, "drop_tasks": drop_tasks}
