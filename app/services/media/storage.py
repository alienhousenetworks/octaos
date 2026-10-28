"""Media storage with public URLs for social platform APIs."""
import base64
import hashlib
import logging
import mimetypes
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DATA_URL_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)

MAX_MEDIA_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB limit (video, cad, archives)
MAX_DOCUMENT_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB limit
FORBIDDEN_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".py", ".bin", ".elf", ".dll",
    ".so", ".dylib", ".vbs", ".ps1", ".msi", ".scr", ".pif", ".com",
    ".jar", ".apk",
}

# Executable / binary headers that must be quarantined regardless of file extension
EXECUTABLE_HEADERS = [
    (b"\x7fELF", "Linux ELF executable"),
    (b"MZ", "Windows PE executable / DLL"),
    (b"\xfe\xed\xfa\xce", "Mach-O 32-bit executable"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit executable"),
    (b"\xce\xfa\xed\xfe", "Mach-O reverse executable"),
    (b"\xcf\xfa\xed\xfe", "Mach-O reverse executable"),
    (b"#!", "Script shebang binary"),
    (b"\xca\xfe\xba\xbe", "Java bytecode class"),
]


def validate_and_quarantine_media(
    content: bytes,
    declared_mime: Optional[str] = None,
    filename: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """
    Validates any media, document, archive, or data payload against size limits,
    forbidden executable extensions, and malicious binary magic bytes.
    Supports ALL safe formats: Video, Audio, Image, Document (PDF/Office/Text),
    Archive (ZIP/TAR/GZ), CAD/3D, and Data (CSV/JSON/Parquet/SQLite).
    Returns (is_valid, resolved_mime, error_message).
    """
    raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
    if not raw_bytes:
        return False, "", "Empty payload."

    if len(raw_bytes) > MAX_MEDIA_SIZE_BYTES:
        return False, "", f"Payload size ({len(raw_bytes) // (1024 * 1024)}MB) exceeds maximum limit of {MAX_MEDIA_SIZE_BYTES // (1024 * 1024)}MB."

    ext = Path(str(filename)).suffix.lower() if filename else ""
    if ext in FORBIDDEN_EXTENSIONS:
        return False, "", f"File extension '{ext}' is forbidden for security quarantine."

    content = raw_bytes


    # Binary executable signature quarantine (prevents renamed .exe/.elf files)
    for sig, desc in EXECUTABLE_HEADERS:
        if content.startswith(sig):
            # Special case: #! is only forbidden if not explicitly text/plain or markdown
            if sig == b"#!" and ext in (".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml"):
                continue
            return False, "", f"Malicious binary header detected ({desc}). Quarantined."

    detected_mime = declared_mime or ""

    # 1. Images
    if content.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        detected_mime = "image/gif"
    elif content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        detected_mime = "image/webp"
    elif content.startswith(b"BM"):
        detected_mime = "image/bmp"
    elif content.startswith((b"II*\x00", b"MM\x00*")):
        detected_mime = "image/tiff"
    elif b"<svg" in content[:2048] or (b"<?xml" in content[:256] and b"<svg" in content[:4096]):
        detected_mime = "image/svg+xml"

    # 2. Audio
    elif content.startswith(b"ID3") or content.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        detected_mime = "audio/mpeg"
    elif content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WAVE":
        detected_mime = "audio/wav"
    elif content.startswith(b"OggS"):
        detected_mime = "audio/ogg"
    elif content.startswith(b"fLaC"):
        detected_mime = "audio/flac"
    elif len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in (b"M4A ", b"mp42", b"isom"):
        if ext in (".m4a", ".aac") or "audio" in (declared_mime or ""):
            detected_mime = "audio/mp4"

    # 3. Video
    elif len(content) >= 12 and content[4:8] == b"ftyp":
        detected_mime = "video/mp4"
    elif content.startswith(b"\x1a\x45\xdf\xa3"):
        detected_mime = "video/webm"
    elif content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"AVI ":
        detected_mime = "video/x-msvideo"

    # 4. Documents & Archives
    elif content.startswith(b"%PDF-"):
        detected_mime = "application/pdf"
    elif content.startswith(b"{\\rtf"):
        detected_mime = "application/rtf"
    elif content.startswith(b"PK\x03\x04"):
        if ext in (".docx", ".docm") or (declared_mime and "word" in declared_mime):
            detected_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in (".xlsx", ".xlsm") or (declared_mime and "excel" in declared_mime):
            detected_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext in (".pptx", ".pptm") or (declared_mime and "presentation" in declared_mime):
            detected_mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif ext == ".epub":
            detected_mime = "application/epub+zip"
        else:
            detected_mime = declared_mime or "application/zip"
    elif content.startswith(b"\x1f\x8b"):
        detected_mime = "application/gzip"
    elif content.startswith(b"7z\xbc\xaf\x27\x1c"):
        detected_mime = "application/x-7z-compressed"
    elif content.startswith(b"SQLite format 3\x00"):
        detected_mime = "application/x-sqlite3"
    elif content.startswith(b"PAR1") or (len(content) >= 4 and content[-4:] == b"PAR1"):
        detected_mime = "application/vnd.apache.parquet"

    # 5. Text / Data / Web Formats
    elif declared_mime in (
        "text/plain", "text/csv", "application/json", "text/markdown",
        "application/xml", "text/xml", "text/html", "application/yaml", "text/yaml",
        "text/tab-separated-values"
    ) or ext in (".txt", ".csv", ".json", ".md", ".xml", ".html", ".yaml", ".yml", ".tsv"):
        if b"\x00" in content[:1024]:
            return False, "", "Corrupted or binary payload disguised as text."
        if filename:
            guessed, _ = mimetypes.guess_type(filename)
            detected_mime = guessed or declared_mime or "text/plain"
        else:
            detected_mime = declared_mime or "text/plain"

    # 6. Fallback with filename extension inspection
    if not detected_mime and filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            detected_mime = guessed

    if not detected_mime:
        detected_mime = declared_mime or "application/octet-stream"

    return True, detected_mime, ""


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
    mime_lower = (mime_type or "").lower()
    if "jpeg" in mime_lower or "jpg" in mime_lower:
        return "jpg"
    if "png" in mime_lower:
        return "png"
    if "webp" in mime_lower:
        return "webp"
    if "svg" in mime_lower:
        return "svg"
    if "mp4" in mime_lower:
        return "mp4"
    if "webm" in mime_lower:
        return "webm"
    if "mpeg" in mime_lower or "mp3" in mime_lower:
        return "mp3"
    if "wav" in mime_lower:
        return "wav"
    if "ogg" in mime_lower:
        return "ogg"
    if "flac" in mime_lower:
        return "flac"
    if "pdf" in mime_lower:
        return "pdf"
    if "wordprocessingml" in mime_lower or "docx" in mime_lower:
        return "docx"
    if "spreadsheetml" in mime_lower or "xlsx" in mime_lower:
        return "xlsx"
    if "presentationml" in mime_lower or "pptx" in mime_lower:
        return "pptx"
    if "json" in mime_lower:
        return "json"
    if "csv" in mime_lower:
        return "csv"
    if "markdown" in mime_lower:
        return "md"
    if "zip" in mime_lower:
        return "zip"
    if "gzip" in mime_lower:
        return "gz"
    return default


def _write_bytes(content: bytes, mime_type: str, prefix: str = "asset") -> str:
    digest = hashlib.sha256(content).hexdigest()[:16]
    ext = _guess_extension(mime_type)
    filename = f"{prefix}_{digest}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = _upload_dir() / filename
    filepath.write_bytes(content)
    return public_url(filename)


def store_media_bytes(
    content: bytes,
    filename: Optional[str] = None,
    declared_mime: Optional[str] = None,
    prefix: str = "asset",
) -> Dict[str, Any]:
    """
    Stores content safely after quarantine validation.
    Returns rich metadata: url, filename, mime_type, size_bytes, sha256.
    """
    valid, detected_mime, err = validate_and_quarantine_media(
        content, declared_mime=declared_mime, filename=filename
    )
    if not valid:
        raise ValueError(f"Quarantine rejection: {err}")

    sha256 = hashlib.sha256(content).hexdigest()
    digest = sha256[:16]
    ext = Path(filename).suffix.lstrip(".").lower() if filename else _guess_extension(detected_mime)
    stored_name = f"{prefix}_{digest}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = _upload_dir() / stored_name
    filepath.write_bytes(content)

    return {
        "url": public_url(stored_name),
        "filename": filename or stored_name,
        "stored_name": stored_name,
        "mime_type": detected_mime,
        "size_bytes": len(content),
        "sha256": sha256,
    }


def get_media_asset(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Resolves any media identifier (filename, public URL, or stored name)
    and returns its metadata.
    """
    if not identifier:
        return None
    raw = str(identifier).strip()
    if "/media/" in raw:
        filename = raw.split("/media/", 1)[-1]
    else:
        filename = Path(raw).name

    filepath = _upload_dir() / filename
    if not filepath.exists() or not filepath.is_file():
        return None

    size = filepath.stat().st_size
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    content = filepath.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    return {
        "filename": filename,
        "filepath": str(filepath),
        "url": public_url(filename),
        "mime_type": mime,
        "size_bytes": size,
        "sha256": sha256,
    }


def read_media_asset_bytes(
    identifier: str, max_bytes: Optional[int] = None
) -> Optional[Tuple[bytes, str, int]]:
    """
    Reads media asset bytes with an optional byte ceiling.
    Returns (content_bytes, mime_type, total_size).
    """
    asset = get_media_asset(identifier)
    if not asset:
        return None
    filepath = Path(asset["filepath"])
    total_size = asset["size_bytes"]
    if max_bytes and max_bytes > 0:
        with open(filepath, "rb") as f:
            chunk = f.read(max_bytes)
        return chunk, asset["mime_type"], total_size
    return filepath.read_bytes(), asset["mime_type"], total_size


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

    # Defensive fallback: raw base64 payload without data: prefix with strict length ceiling
    if 100 < len(source) <= (MAX_MEDIA_SIZE_BYTES * 4 // 3) and not source.startswith("/"):
        try:
            content = base64.b64decode(source)
            return _write_bytes(content, default_mime, prefix=prefix)
        except Exception:
            pass

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
    No public URL required - used for direct binary upload to Meta / LinkedIn.
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
    # Async wrapper for _write_bytes, ignoring filename to use standard naming.
    prefix = filename.split('_')[0] if '_' in filename else 'upload'
    return _write_bytes(content, mime_type, prefix=prefix)

