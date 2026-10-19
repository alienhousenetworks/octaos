"""Security, SSRF, and isolation tests for Governed Knowledge Connectors."""
import pytest
from app.services.knowledge_connectors.security.url_validation import (
    validate_and_resolve_destination,
)
from app.services.knowledge_connectors.errors import SSRFProtectionError, ConnectorSecurityError
from app.services.knowledge_connectors.security.redaction import redact_dictionary, mask_secret_string
from app.services.knowledge_connectors.normalizer import (
    compute_schema_fingerprint,
    detect_schema_drift,
)


def test_ssrf_blocks_cloud_metadata():
    with pytest.raises(SSRFProtectionError) as exc:
        validate_and_resolve_destination("http://169.254.169.254/latest/meta-data/")
    assert "scheme" in str(exc.value).lower() or "metadata" in str(exc.value).lower()

    # Even with HTTPS
    with pytest.raises(SSRFProtectionError):
        validate_and_resolve_destination("https://169.254.169.254/secret")


def test_ssrf_blocks_cloud_metadata_hostname():
    with pytest.raises(SSRFProtectionError):
        validate_and_resolve_destination("https://metadata.google.internal/computeMetadata/v1/")


def test_ssrf_blocks_private_tlds():
    with pytest.raises(SSRFProtectionError):
        validate_and_resolve_destination("https://service.internal/api")
    with pytest.raises(SSRFProtectionError):
        validate_and_resolve_destination("https://myhost.local/data")


def test_ssrf_blocks_non_https_scheme_by_default():
    with pytest.raises(SSRFProtectionError) as exc:
        validate_and_resolve_destination("http://api.github.com/events")
    assert "only https is permitted" in str(exc.value).lower()


def test_ssrf_blocks_loopback_destinations():
    # If 127.0.0.1 is passed
    with pytest.raises(SSRFProtectionError):
        validate_and_resolve_destination("https://127.0.0.1/admin")


def test_redaction_masks_denied_and_sensitive_fields():
    raw_payload = {
        "customer_id": "cust_123",
        "email": "alice@company.com",
        "password": "supersecretpassword",
        "nested": {
            "credit_card": "4111222233334444",
            "tier": "Enterprise",
        },
    }
    redacted = redact_dictionary(raw_payload, denied_fields=["email"])
    assert redacted["customer_id"] == "cust_123"
    assert redacted["email"] == "[REDACTED_BY_POLICY]"
    assert redacted["password"] == "[REDACTED_SENSITIVE]"
    assert redacted["nested"]["credit_card"] == "[REDACTED_SENSITIVE]"
    assert redacted["nested"]["tier"] == "Enterprise"


def test_mask_secret_string():
    assert mask_secret_string("sk-1234567890abcdef") == "sk-****cdef"
    assert mask_secret_string("short") == "********"


def test_schema_fingerprint_and_drift_detection():
    data_v1 = {
        "customer_id": "cust_1",
        "status": "active",
        "arr": 50000,
    }
    fingerprint_1, fields_1 = compute_schema_fingerprint(data_v1)
    assert len(fingerprint_1) == 64
    assert fields_1["customer_id"] == "string"
    assert fields_1["arr"] == "integer"

    # Drift scenario: field 'arr' is missing in v2
    data_v2 = {
        "customer_id": "cust_1",
        "status": "active",
    }
    fingerprint_2, fields_2 = compute_schema_fingerprint(data_v2)
    assert fingerprint_1 != fingerprint_2

    drift, warnings = detect_schema_drift(fields_2, fields_1)
    assert drift is True
    assert any("arr" in w for w in warnings)
