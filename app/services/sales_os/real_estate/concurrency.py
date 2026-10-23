"""
Enterprise High-Concurrency Distributed Inventory Lock.
Guarantees mutual exclusion for real estate unit holds and bookings during high-volume launch days.
Backs with Redis distributed locks and falls back to a thread-safe in-memory expiring lock if Redis is unavailable.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Generator, Optional
from fastapi import HTTPException

from app.services.ai_gateway.caching import get_redis_client

logger = logging.getLogger(__name__)

# Fallback in-memory lock store: unit_id -> (token: str, expires_at: float)
_local_locks: dict[str, tuple[str, float]] = {}
_local_lock_mutex = threading.Lock()

_redis_checked_at = 0.0
_redis_is_online = False
_REDIS_CHECK_COOLDOWN = 15.0


def _get_active_redis():
    global _redis_checked_at, _redis_is_online
    now = time.time()
    if not _redis_is_online and (now - _redis_checked_at < _REDIS_CHECK_COOLDOWN):
        return None

    client = get_redis_client()
    _redis_checked_at = now
    _redis_is_online = client is not None
    return client


_LUA_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def acquire_inventory_lock(unit_id: str, timeout_seconds: int = 300) -> Optional[str]:
    """
    Attempts to acquire a distributed lock on a property unit.
    Returns a unique concurrency token if successful, or None if already locked.
    """
    token = str(uuid.uuid4())
    key = f"re:lock:unit:{unit_id}"

    # 1. Try Redis distributed lock
    redis_client = _get_active_redis()
    if redis_client:
        try:
            acquired = redis_client.set(key, token, nx=True, ex=timeout_seconds)
            if acquired:
                return token
            return None
        except Exception as e:
            logger.warning(f"Redis lock error for unit {unit_id}: {e}. Falling back to in-memory lock.")

    # 2. Fallback to thread-safe in-memory lock
    now = time.time()
    with _local_lock_mutex:
        existing = _local_locks.get(unit_id)
        if existing:
            existing_token, expires_at = existing
            if now < expires_at:
                # Still actively locked
                return None
            # Expired lock can be purged
            del _local_locks[unit_id]

        _local_locks[unit_id] = (token, now + timeout_seconds)
        return token


def release_inventory_lock(unit_id: str, token: str) -> bool:
    """
    Safely releases the distributed lock for a unit if the token matches.
    Prevents releasing a lock that has expired and been acquired by another process.
    """
    key = f"re:lock:unit:{unit_id}"
    released = False

    # 1. Try Redis release
    redis_client = _get_active_redis()
    if redis_client:
        try:
            res = redis_client.eval(_LUA_RELEASE_SCRIPT, 1, key, token)
            released = bool(res)
        except Exception as e:
            logger.warning(f"Redis lock release error for unit {unit_id}: {e}")

    # 2. Also clear in-memory fallback
    with _local_lock_mutex:
        existing = _local_locks.get(unit_id)
        if existing and existing[0] == token:
            del _local_locks[unit_id]
            released = True

    return released


@contextmanager
def inventory_unit_lock(unit_id: str, timeout_seconds: int = 300) -> Generator[str, None, None]:
    """
    Context manager for transactional unit reservation.
    Raises HTTPException 409 Conflict if unit is locked by an ongoing concurrent request.
    """
    token = acquire_inventory_lock(unit_id, timeout_seconds=timeout_seconds)
    if not token:
        raise HTTPException(
            status_code=409,
            detail=f"Unit {unit_id} is currently locked in an active reservation checkout. Please retry shortly.",
        )
    try:
        yield token
    finally:
        release_inventory_lock(unit_id, token)
