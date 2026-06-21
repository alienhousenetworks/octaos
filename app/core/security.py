from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None, tenant_id: str = None, organization_id: str = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    if tenant_id:
        to_encode["tenant_id"] = tenant_id
    if organization_id:
        to_encode["organization_id"] = organization_id
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

from cryptography.fernet import Fernet
import base64
import hashlib

# Derive a 32-url-safe base64 key from settings.SECRET_KEY
key_material = settings.SECRET_KEY.encode('utf-8')
fernet_key = base64.urlsafe_b64encode(hashlib.sha256(key_material).digest())
fernet = Fernet(fernet_key)

def encrypt_api_key(key: str) -> str:
    if not key:
        return key
    return fernet.encrypt(key.encode('utf-8')).decode('utf-8')

import logging

def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return ""
    try:
        return fernet.decrypt(encrypted_key.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Secure decryption failed: {e}")
        raise ValueError("Secure decryption failed") from e
