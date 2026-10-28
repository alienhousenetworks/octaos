"""Live Terminal and Real-Time Process Monitor for External AI Connectors and Custom Software."""
from __future__ import annotations

import collections
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.base import SystemSetting

logger = logging.getLogger(__name__)

# In-memory ring buffer storing the latest 300 terminal events per tenant
_TERMINAL_BUFFERS: Dict[str, collections.deque] = {}
MAX_BUFFER_LINES = 300


class TerminalLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3])
    iso_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    category: str = Field(description="'inbound', 'outbound', 'bridge', 'policy', 'quarantine', 'system'")
    level: str = Field(default="info", description="'info', 'warn', 'error', 'success'")
    source: str = Field(default="system")
    target: str = Field(default="octaos")
    message: str
    details: Optional[Dict[str, Any]] = None


class ProcessStatusResponse(BaseModel):
    status: str = Field(description="'RUNNING' or 'STOPPED'")
    is_active: bool
    active_listeners: int
    total_events_logged: int
    tenant_id: str
    last_toggled_at: Optional[str] = None


class LiveTerminalManager:
    """
    Manages live terminal log streaming and process ON/OFF controls for external
    AI brains, custom software, and external MCP servers.
    """

    @classmethod
    def _get_buffer(cls, tenant_id: str) -> collections.deque:
        if tenant_id not in _TERMINAL_BUFFERS:
            buf = collections.deque(maxlen=MAX_BUFFER_LINES)
            # Add initial system boot lines so terminal displays clear state
            now_iso = datetime.now(timezone.utc).isoformat()
            buf.append(TerminalLogEntry(
                category="system",
                level="info",
                source="kernel",
                target="collaboration_gateway",
                message="OctaOS External AI Collaboration Listener initialized.",
            ))
            buf.append(TerminalLogEntry(
                category="system",
                level="success",
                source="mcp_server",
                target="plugins_router",
                message="Listening on /api/v1/plugin/*, /collaboration/*, and MCP SSE streams.",
            ))
            buf.append(TerminalLogEntry(
                category="system",
                level="info",
                source="security_guard",
                target="quarantine",
                message="Polymorphic media quarantine & magic byte validation active.",
            ))
            _TERMINAL_BUFFERS[tenant_id] = buf
        return _TERMINAL_BUFFERS[tenant_id]

    @classmethod
    def log_event(
        cls,
        tenant_id: str,
        category: str,
        message: str,
        level: str = "info",
        source: str = "system",
        target: str = "octaos",
        details: Optional[Dict[str, Any]] = None,
    ) -> TerminalLogEntry:
        """Appends a new event to the live terminal stream."""
        entry = TerminalLogEntry(
            category=category,
            level=level,
            source=source,
            target=target,
            message=message,
            details=details,
        )
        buf = cls._get_buffer(tenant_id)
        buf.append(entry)
        return entry

    @classmethod
    def get_logs(
        cls,
        tenant_id: str,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[TerminalLogEntry]:
        """Returns recent terminal logs, optionally filtered by category."""
        buf = cls._get_buffer(tenant_id)
        items = list(buf)
        if category and category != "all":
            items = [e for e in items if e.category.lower() == category.lower()]
        return items[-limit:]

    @classmethod
    def clear_logs(cls, tenant_id: str) -> None:
        """Clears the terminal log buffer for the tenant."""
        buf = cls._get_buffer(tenant_id)
        buf.clear()
        cls.log_event(
            tenant_id=tenant_id,
            category="system",
            level="info",
            source="terminal",
            target="screen",
            message="Terminal log buffer cleared by operator.",
        )

    @classmethod
    def is_process_active(cls, db: Session, tenant_id: str) -> bool:
        """
        Checks whether the external collaboration listener process is turned ON.
        Defaults to True.
        """
        setting_key = f"collab_listener_active:{tenant_id}"
        row = db.query(SystemSetting).filter(SystemSetting.key == setting_key).first()
        if not row:
            return True
        return str(row.value).lower() in ("true", "1", "yes", "running")

    @classmethod
    def set_process_active(cls, db: Session, tenant_id: str, active: bool) -> ProcessStatusResponse:
        """
        Toggles the external collaboration listener process ON or OFF.
        Persists state to database and logs state transition in the live terminal.
        """
        setting_key = f"collab_listener_active:{tenant_id}"
        row = db.query(SystemSetting).filter(SystemSetting.key == setting_key).first()
        val_str = "true" if active else "false"

        if not row:
            row = SystemSetting(key=setting_key, value=val_str)
            db.add(row)
        else:
            row.value = val_str

        db.commit()

        status_str = "RUNNING" if active else "STOPPED"
        if active:
            cls.log_event(
                tenant_id=tenant_id,
                category="system",
                level="success",
                source="operator",
                target="gateway_listener",
                message="External AI Collaboration Listener STARTED. Accepting incoming & outgoing agent tasks.",
            )
        else:
            cls.log_event(
                tenant_id=tenant_id,
                category="system",
                level="warn",
                source="operator",
                target="gateway_listener",
                message="External AI Collaboration Listener STOPPED. Incoming connector traffic paused.",
            )

        buf = cls._get_buffer(tenant_id)
        return ProcessStatusResponse(
            status=status_str,
            is_active=active,
            active_listeners=1 if active else 0,
            total_events_logged=len(buf),
            tenant_id=tenant_id,
            last_toggled_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def get_process_status(cls, db: Session, tenant_id: str) -> ProcessStatusResponse:
        """Returns the current process status (RUNNING vs STOPPED)."""
        active = cls.is_process_active(db, tenant_id)
        buf = cls._get_buffer(tenant_id)
        return ProcessStatusResponse(
            status="RUNNING" if active else "STOPPED",
            is_active=active,
            active_listeners=1 if active else 0,
            total_events_logged=len(buf),
            tenant_id=tenant_id,
        )
