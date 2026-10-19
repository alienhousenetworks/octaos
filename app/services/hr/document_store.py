import hashlib
from pathlib import Path

from app.core.config import settings


def private_root() -> Path:
    configured = getattr(settings, "HR_PRIVATE_DIR", None) or "var/hr-private"
    root = Path(configured)
    root.mkdir(parents=True, exist_ok=True)
    return root


class LocalPrivateDocumentStore:
    def put(self, tenant_id: str, object_id: str, data: bytes) -> str:
        directory = private_root() / tenant_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / object_id
        path.write_bytes(data)
        return str(path)

    def stat(self, storage_key: str) -> int:
        return Path(storage_key).stat().st_size

    def open(self, storage_key: str) -> bytes:
        return Path(storage_key).read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
