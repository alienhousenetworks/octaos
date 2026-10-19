"""Dynamic normalization, schema fingerprinting, and drift detection."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Set, Tuple


def infer_type_name(val: Any) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "boolean"
    if isinstance(val, int):
        return "integer"
    if isinstance(val, float):
        return "float"
    if isinstance(val, str):
        return "string"
    if isinstance(val, list):
        return "array"
    if isinstance(val, dict):
        return "object"
    return "unknown"


def extract_schema_structure(data: Any, prefix: str = "", max_depth: int = 5) -> Dict[str, str]:
    """Recursively traverses JSON object or array to extract field paths and inferred types."""
    fields = {}
    if max_depth <= 0:
        return fields

    if isinstance(data, dict):
        for k, v in data.items():
            field_path = f"{prefix}.{k}" if prefix else str(k)
            t_name = infer_type_name(v)
            fields[field_path] = t_name
            if isinstance(v, (dict, list)):
                fields.update(extract_schema_structure(v, field_path, max_depth - 1))
    elif isinstance(data, list) and data:
        # Sample first 3 elements of list
        for idx, item in enumerate(data[:3]):
            field_path = f"{prefix}[]" if prefix else "[]"
            if isinstance(item, dict):
                fields.update(extract_schema_structure(item, field_path, max_depth - 1))
            else:
                fields[field_path] = infer_type_name(item)

    return fields


def compute_schema_fingerprint(data: Any) -> Tuple[str, Dict[str, str]]:
    """
    Computes a deterministic SHA256 fingerprint from the sorted field path types.
    Returns (fingerprint_hash, observed_fields_dict).
    """
    fields = extract_schema_structure(data)
    sorted_pairs = sorted([f"{k}:{v}" for k, v in fields.items()])
    raw_signature = "|".join(sorted_pairs)
    fingerprint = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()
    return fingerprint, fields


def detect_schema_drift(
    current_fields: Dict[str, str],
    baseline_fields: Dict[str, str],
) -> Tuple[bool, List[str]]:
    """
    Checks if previously observed fields are missing or have changed types.
    Returns (drift_detected: bool, warnings: List[str]).
    """
    warnings = []
    drift = False

    for baseline_key, baseline_type in baseline_fields.items():
        if baseline_key not in current_fields:
            warnings.append(f"Field '{baseline_key}' expected in baseline schema is missing.")
            drift = True
        elif current_fields[baseline_key] != baseline_type and current_fields[baseline_key] != "null":
            warnings.append(
                f"Field '{baseline_key}' type changed from '{baseline_type}' to '{current_fields[baseline_key]}'."
            )
            drift = True

    return drift, warnings
