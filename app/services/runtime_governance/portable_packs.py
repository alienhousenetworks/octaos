"""Portable, tenant-safe agent/team pack manifest validation."""
from __future__ import annotations

import copy
import re
from typing import Any, Mapping


PACK_SCHEMA_VERSION = 1
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")

_SECRET_KEYS = {
    "api_key", "access_token", "refresh_token", "password", "secret",
    "client_secret", "authorization", "cookie", "private_key",
}
_TENANT_DATA_KEYS = {
    "tenant_id", "organization_id", "conversation_history", "messages",
    "run_history", "execution_history", "customer_records", "lead_records",
    "candidate_records", "personal_data",
}


class PackValidationError(ValueError):
    pass


def _reject_sensitive(value: Any, path: str = "manifest") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                raise PackValidationError(f"Secret-like field is not exportable: {path}.{key}")
            if normalized in _TENANT_DATA_KEYS:
                raise PackValidationError(f"Tenant-specific data is not exportable: {path}.{key}")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def build_portable_pack(
    *,
    name: str,
    version: str,
    description: str,
    agents: list[Mapping[str, Any]],
    workflows: list[Mapping[str, Any]],
    required_tools: list[str] | None = None,
    tests: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not name.strip() or len(name) > 160:
        raise PackValidationError("Pack name must be 1–160 characters.")
    if not _SEMVER.fullmatch(version):
        raise PackValidationError("Pack version must use semantic versioning.")
    manifest = {
        "schema_version": PACK_SCHEMA_VERSION,
        "name": name.strip(),
        "version": version,
        "description": description[:2000],
        "agents": copy.deepcopy(agents),
        "workflows": copy.deepcopy(workflows),
        "required_tools": sorted(set(required_tools or [])),
        "tests": copy.deepcopy(tests or []),
    }
    _reject_sensitive(manifest)
    return manifest


def prepare_pack_install(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a portable pack and produce a safe, inactive installation preview."""
    if manifest.get("schema_version") != PACK_SCHEMA_VERSION:
        raise PackValidationError("Unsupported pack schema version.")
    if not isinstance(manifest.get("agents"), list) or not isinstance(manifest.get("workflows"), list):
        raise PackValidationError("Pack must include agents and workflows arrays.")
    _reject_sensitive(manifest)
    preview = copy.deepcopy(dict(manifest))
    preview["install_defaults"] = {
        "connections_enabled": False,
        "schedules_enabled": False,
        "require_connection_reauthorization": True,
        "require_workflow_validation": True,
        "require_admin_review": True,
    }
    return preview
