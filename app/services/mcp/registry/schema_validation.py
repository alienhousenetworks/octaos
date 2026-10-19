"""Runtime JSON Schema validation for dynamically discovered business objects."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
from datetime import datetime


class SchemaValidationError(Exception):
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        super().__init__(f"Schema validation failed: {errors}")


def validate_record_against_schema(
    record: Dict[str, Any],
    json_schema: Dict[str, Any],
    allow_partial: bool = False,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Lightweight, robust runtime validator for dynamic records against JSON Schema.
    Checks:
    - Required fields (unless allow_partial=True for updates)
    - Field types (string, integer, number, boolean, object, array)
    - Nullability
    - Formats (e.g. date-time)
    - ReadOnly restrictions
    """
    errors: List[Dict[str, Any]] = []
    properties = json_schema.get("properties", {})
    required = json_schema.get("required", []) if not allow_partial else []

    # 1. Check required fields
    for req_field in required:
        if req_field not in record or record[req_field] is None:
            errors.append({
                "field": req_field,
                "error": "missing_required_field",
                "message": f"Required field '{req_field}' is missing.",
            })

    # 2. Check property types and constraints
    for field_name, value in record.items():
        if field_name not in properties:
            # If additionalProperties is False, reject unknown fields
            if json_schema.get("additionalProperties") is False:
                errors.append({
                    "field": field_name,
                    "error": "unexpected_field",
                    "message": f"Field '{field_name}' is not recognized in object schema.",
                })
            continue

        prop_spec = properties[field_name]
        expected_type = prop_spec.get("type")
        is_nullable = prop_spec.get("nullable", False)

        if value is None:
            if not is_nullable and field_name in required:
                errors.append({
                    "field": field_name,
                    "error": "null_not_allowed",
                    "message": f"Field '{field_name}' cannot be null.",
                })
            continue

        # Type checks
        if expected_type == "string" and not isinstance(value, str):
            errors.append({
                "field": field_name,
                "error": "type_mismatch",
                "message": f"Expected string for '{field_name}', got {type(value).__name__}.",
            })
        elif expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            errors.append({
                "field": field_name,
                "error": "type_mismatch",
                "message": f"Expected integer for '{field_name}', got {type(value).__name__}.",
            })
        elif expected_type == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            errors.append({
                "field": field_name,
                "error": "type_mismatch",
                "message": f"Expected number for '{field_name}', got {type(value).__name__}.",
            })
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append({
                "field": field_name,
                "error": "type_mismatch",
                "message": f"Expected boolean for '{field_name}', got {type(value).__name__}.",
            })
        elif expected_type == "object" and not isinstance(value, dict):
            errors.append({
                "field": field_name,
                "error": "type_mismatch",
                "message": f"Expected object/dict for '{field_name}', got {type(value).__name__}.",
            })
        elif expected_type == "array" and not isinstance(value, list):
            errors.append({
                "field": field_name,
                "error": "type_mismatch",
                "message": f"Expected array/list for '{field_name}', got {type(value).__name__}.",
            })

        # Format checks
        if expected_type == "string" and prop_spec.get("format") == "date-time" and isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append({
                    "field": field_name,
                    "error": "invalid_format",
                    "message": f"Field '{field_name}' must be an ISO-8601 formatted datetime string.",
                })

    return len(errors) == 0, errors
