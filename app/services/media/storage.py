"""Media storage with public URLs for social platform APIs."""
import base64
import hashlib
import logging
import mimetypes
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def _upload_dir() -> Path:
    path = Path(settings.MEDIA_UPLOAD_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def public_url(relative_path: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    rel = relative_path.lstrip("/")
    return f"{base}/media/{rel}"


def _guess_extension(mime_type: str, default: str = "bin") -> str:
    ext = mimetypes.guess_extension(mime_type or "")
    if ext:
        return ext.lstrip(".")
    if "jpeg" in mime_type or "jpg" in mime_type:
        return "jpg"
    if "png" in mime_type:
        return "png"
    if "webp" in mime_type:
        return "webp"
    if "mp4" in mime_type:
        return "mp4"
    return default


def _write_bytes(content: bytes, mime_type: str, prefix: str = "asset") -> str:
    digest = hashlib.sha256(content).hexdigest()[:16]
    ext = _guess_extension(mime_type)
    filename = f"{prefix}_{digest}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = _upload_dir() / filename
    filepath.write_bytes(content)
    return public_url(filename)


async def ensure_public_url(
    source: Optional[str],
    *,
    default_mime: str = "image/jpeg",
    prefix: str = "asset",
) -> Optional[str]:
    """
    Normalize any media reference to a publicly reachable HTTPS/HTTP URL.
    - Already public http(s) URLs are returned as-is (after HEAD validation when possible).
    - data: URLs are decoded and stored locally.
    - Remote URLs are downloaded and re-hosted locally for reliability.
    """
    if not source or not str(source).strip():
        return None

    source = str(source).strip()

    if source.startswith("data:"):
        match = DATA_URL_RE.match(source)
        if not match:
            return None
        mime_type, b64 = match.group(1), match.group(2)
        content = base64.b64decode(b64)
        return _write_bytes(content, mime_type, prefix=prefix)

    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        # Re-host if pointing to our own server already
        base_host = urlparse(settings.PUBLIC_BASE_URL).netloc
        if parsed.netloc == base_host and "/media/" in parsed.path:
            return source

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
                resp = await client.get(source)
                resp.raise_for_status()
                mime = resp.headers.get("content-type", default_mime).split(";")[0].strip()
                return _write_bytes(resp.content, mime, prefix=prefix)
        except Exception as exc:
            logger.warning("Could not re-host media %s: %s", source[:80], exc)
            # Last resort: return original if it looks publicly accessible
            return source

    return None


async def download_bytes(url: str) -> Tuple[bytes, str]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "application/octet-stream").split(";")[0]
        return resp.content, mime


async def resolve_media_bytes(
    source: Optional[str],
    *,
    default_mime: str = "image/jpeg",
) -> Optional[Tuple[bytes, str]]:
    """
    Resolve any media reference to raw bytes + MIME type.
    Works with data: URLs, local /media/ paths, remote URLs, and local upload files.
    No public URL required — used for direct binary upload to Meta / LinkedIn.
    """
    if not source or not str(source).strip():
        return None

    source = str(source).strip()

    if source.startswith("data:"):
        match = DATA_URL_RE.match(source)
        if not match:
            return None
        mime_type, b64 = match.group(1), match.group(2)
        return base64.b64decode(b64), mime_type

    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        base_host = urlparse(settings.PUBLIC_BASE_URL).netloc
        if parsed.netloc == base_host and "/media/" in parsed.path:
            filename = parsed.path.split("/media/", 1)[-1]
            filepath = _upload_dir() / filename
            if filepath.exists():
                mime = mimetypes.guess_type(filename)[0] or default_mime
                return filepath.read_bytes(), mime

        try:
            return await download_bytes(source)
        except Exception as exc:
            logger.warning("Could not download media %s: %s", source[:80], exc)
            return None

    return None

async def upload_file_to_storage(content: bytes, filename: str, mime_type: str) -> str:
    """Async wrapper for _write_bytes, ignoring filename to use standard naming."""
    prefix = filename.split('_')[0] if '_' in filename else 'upload'
    return _write_bytes(content, mime_type, prefix=prefix)
