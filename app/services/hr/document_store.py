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
        # Sanitize object_id against path traversal
        clean_object_id = Path(object_id).name
        directory = private_root() / tenant_id
        directory.mkdir(parents=True, exist_ok=True)
        path = (directory / clean_object_id).resolve()
        # Verify path stays within tenant root
        if not str(path).startswith(str(directory.resolve())):
            raise ValueError("Path traversal attempt detected in document storage.")
        path.write_bytes(data)
        return str(path)

    def put_artifact(self, tenant_id: str, category: str, content_sha256: str, ext: str, data: bytes) -> str:
        """Stores an immutable artifact under tenant-scoped opaque directory."""
        directory = private_root() / tenant_id / category
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{content_sha256}.{ext.lstrip('.')}"
        path = directory / filename
        path.write_bytes(data)
        return str(path)

    def stat(self, storage_key: str) -> int:
        return Path(storage_key).stat().st_size

    def open(self, storage_key: str) -> bytes:
        return Path(storage_key).read_bytes()

    def verify_hash(self, storage_key: str, expected_sha256: str) -> bool:
        data = self.open(storage_key)
        return sha256_bytes(data) == expected_sha256


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DocumentStore:
    _store = LocalPrivateDocumentStore()

    @classmethod
    def save(cls, tenant_id: str, filename: str, content: bytes, prefix: str = "artifacts") -> str:
        sha = sha256_bytes(content)
        ext = Path(filename).suffix or ".bin"
        return cls._store.put_artifact(tenant_id, prefix, sha, ext, content)

    @classmethod
    def read(cls, storage_key: str) -> bytes:
        return cls._store.open(storage_key)


