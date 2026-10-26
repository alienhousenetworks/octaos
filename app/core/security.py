from datetime import datetime, timedelta
from typing import Any, Optional, Tuple, Union
import secrets
import hashlib
import logging
import base64
import bcrypt  # Required dependency: never fall back to fast, unsalted password hashes.
from jose import jwt
from cryptography.fernet import Fernet


from app.core.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


def _require_secret() -> str:
    key = settings.SECRET_KEY
    if not key or key in ("secret", "changeme", "CHANGE_ME"):
        if settings.DEV or settings.ENVIRONMENT in ("development", "dev", "local", "test"):
            logger.warning(
                "INSECURE SECRET_KEY in use. Set a strong SECRET_KEY in production."
            )
            return key or "dev-only-insecure-secret-key-change-me"
        raise RuntimeError(
            "SECRET_KEY must be set to a strong random value in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    if len(key) < 32 and not (settings.DEV or settings.ENVIRONMENT in ("development", "dev", "local", "test")):
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production.")
    return key


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    tenant_id: str = None,
    organization_id: str = None,
    token_type: str = "access",
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
        expire = datetime.utcnow() + timedelta(minutes=minutes)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": token_type,
    }
    if tenant_id:
        to_encode["tenant_id"] = tenant_id
    if organization_id:
        to_encode["organization_id"] = organization_id
    encoded_jwt = jwt.encode(to_encode, _require_secret(), algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token_pair(
    subject: Union[str, Any],
    tenant_id: str = None,
    organization_id: str = None,
) -> Tuple[str, str, datetime]:
    """Returns access_token, refresh_token_raw, refresh_expires_at."""
    access = create_access_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        tenant_id=tenant_id,
        organization_id=organization_id,
        token_type="access",
    )
    refresh_raw = create_refresh_token_value()
    refresh_expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return access, refresh_raw, refresh_expires


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a bcrypt password hash; fail closed for malformed/legacy hashes.

    Passwords must never be checked using a fast general-purpose digest such as
    SHA-256. Legacy SHA-256 password records require a controlled password-reset
    or re-enrollment flow; they are deliberately not accepted here.
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if not hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError, UnicodeError):
        return False


def get_password_hash(password: str) -> str:
    """Create a bcrypt password hash or fail closed if bcrypt is unavailable."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password exceeds bcrypt's 72-byte limit; choose a shorter password.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")



# Fernet key: prefer ENCRYPTION_KEY, else derive from SECRET_KEY.
# Supports MultiFernet with default dev key fallback for seamless key rotation.
def _fernet() -> Any:
    from cryptography.fernet import MultiFernet
    keys = []

    enc = getattr(settings, "ENCRYPTION_KEY", None)
    if enc:
        try:
            keys.append(Fernet(enc.encode("utf-8") if isinstance(enc, str) else enc))
        except Exception:
            key = base64.urlsafe_b64encode(hashlib.sha256(enc.encode("utf-8")).digest())
            keys.append(Fernet(key))

    key_material = _require_secret().encode("utf-8")
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(key_material).digest())
    keys.append(Fernet(fernet_key))

    # Add default dev key fallback if distinct (handles records created before custom SECRET_KEY set)
    dev_material = b"dev-only-insecure-secret-key-change-me"
    if key_material != dev_material:
        dev_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(dev_material).digest())
        keys.append(Fernet(dev_fernet_key))

    return MultiFernet(keys) if len(keys) > 1 else keys[0]


def encrypt_api_key(key: str) -> str:
    if not key:
        return key
    return _fernet().encrypt(key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key or encrypted_key in ("sales_settings", "ai_mode", "none"):
        return ""
    # Passthrough if already plaintext key
    if any(encrypted_key.startswith(prefix) for prefix in ("sk-", "gsk_", "xai-", "fc-", "AIza", "hf_")):
        return encrypted_key
    try:
        return _fernet().decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Secure decryption failed: {e}")
        raise ValueError("Secure decryption failed") from e


def generate_mfa_secret() -> str:
    # base32-ish secret for TOTP apps
    return secrets.token_hex(20)


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Simple TOTP verification (30s step) without external dependency."""
    import hmac
    import struct
    import time

    if not secret or not code or not code.isdigit():
        return False
    key = hashlib.sha1(secret.encode("utf-8")).digest()
    timestep = int(time.time() // 30)
    for w in range(-window, window + 1):
        msg = struct.pack(">Q", timestep + w)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[19] & 15
        token = (struct.unpack(">I", h[o : o + 4])[0] & 0x7FFFFFFF) % 1000000
        if f"{token:06d}" == code.zfill(6):
            return True
    return False
