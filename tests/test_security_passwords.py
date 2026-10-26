"""Regression tests for secure password hashing in OctaOS."""
import pytest

from app.core.security import get_password_hash, verify_password


def test_password_hash_is_bcrypt_and_round_trips():
    hashed = get_password_hash("Correct Horse Battery Staple 2026!")
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert verify_password("Correct Horse Battery Staple 2026!", hashed)
    assert not verify_password("incorrect password", hashed)


def test_password_verification_fails_closed_for_legacy_sha256_digest():
    import hashlib

    legacy_digest = hashlib.sha256(b"old-password").hexdigest()
    assert not verify_password("old-password", legacy_digest)


def test_password_verification_fails_closed_for_malformed_hash():
    assert not verify_password("password", "not-a-password-hash")
    assert not verify_password("password", "")


@pytest.mark.parametrize("password", ["", None])
def test_hash_rejects_empty_or_non_string_password(password):
    with pytest.raises(ValueError):
        get_password_hash(password)


def test_hash_rejects_password_over_bcrypt_byte_limit():
    with pytest.raises(ValueError, match="72-byte limit"):
        get_password_hash("é" * 37)
