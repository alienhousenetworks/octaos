"""Bounded streaming response consumption with byte and time enforcement."""
from __future__ import annotations

import httpx
from typing import Tuple
from app.services.knowledge_connectors.errors import ConnectorBudgetExceededError


async def read_stream_bounded(
    response: httpx.Response,
    max_bytes: int = 2 * 1024 * 1024,
    chunk_size: int = 65536,
) -> Tuple[bytes, bool, str | None]:
    """
    Reads a streaming HTTP response up to max_bytes.
    Returns (content_bytes, truncated: bool, truncation_reason: Optional[str]).
    """
    chunks = []
    total_bytes = 0
    truncated = False
    reason = None

    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
        if total_bytes + len(chunk) > max_bytes:
            # Consume only remaining allowed bytes and abort
            allowed = max_bytes - total_bytes
            if allowed > 0:
                chunks.append(chunk[:allowed])
                total_bytes += allowed
            truncated = True
            reason = f"Response exceeded byte budget of {max_bytes} bytes."
            break
        chunks.append(chunk)
        total_bytes += len(chunk)

    return b"".join(chunks), truncated, reason
