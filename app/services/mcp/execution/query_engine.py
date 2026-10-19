"""Typed Safe Query DSL validator and parser for MCP data queries."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

ALLOWED_OPERATORS = {
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "contains",
    "is_null",
}

MAX_FILTER_DEPTH = 3
DEFAULT_QUERY_LIMIT = 50


class QueryValidationError(Exception):
    pass


def validate_query_dsl(
    query: Dict[str, Any],
    max_allowed_limit: int = 100,
    valid_fields: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Validates and normalizes an incoming query DSL object.
    Guarantees:
    - Bounded query limit
    - Valid comparison operators
    - Bounded nesting depth of logical clauses
    - Safe field names (alphanumeric + underscores)
    """
    if not isinstance(query, dict):
        raise QueryValidationError("Query payload must be a JSON object.")

    # 1. Limit validation
    limit = query.get("limit", DEFAULT_QUERY_LIMIT)
    if not isinstance(limit, int) or limit <= 0:
        limit = DEFAULT_QUERY_LIMIT
    limit = min(limit, max_allowed_limit)

    # 2. Field projection validation
    fields = query.get("fields")
    if fields is not None:
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise QueryValidationError("'fields' must be a list of string field names.")
        for f in fields:
            _check_field_identifier(f)
            if valid_fields and f not in valid_fields:
                raise QueryValidationError(f"Field '{f}' is not in discoverable object schema.")

    # 3. Filter validation
    filter_clause = query.get("filter")
    if filter_clause is not None:
        _validate_filter_node(filter_clause, depth=1, valid_fields=valid_fields)

    # 4. Sort validation
    sort_list = query.get("sort", [])
    if not isinstance(sort_list, list):
        raise QueryValidationError("'sort' must be a list of sort directives.")
    for s in sort_list:
        if not isinstance(s, dict) or "field" not in s:
            raise QueryValidationError("Each sort directive must specify a 'field'.")
        _check_field_identifier(s["field"])
        direction = s.get("direction", "asc").lower()
        if direction not in ("asc", "desc"):
            raise QueryValidationError(f"Sort direction must be 'asc' or 'desc', got '{direction}'.")

    return {
        "fields": fields,
        "filter": filter_clause,
        "sort": sort_list,
        "limit": limit,
        "cursor": query.get("cursor"),
    }


def _check_field_identifier(field_name: str) -> None:
    """Ensures field names are safe identifiers and not SQL injection vectors."""
    if not field_name or not field_name.replace("_", "").isalnum():
        raise QueryValidationError(f"Invalid field name identifier: '{field_name}'. Only alphanumeric and underscores allowed.")


def _validate_filter_node(
    node: Any,
    depth: int,
    valid_fields: Optional[Set[str]] = None,
) -> None:
    if depth > MAX_FILTER_DEPTH:
        raise QueryValidationError(f"Filter clause exceeds maximum nesting depth of {MAX_FILTER_DEPTH}.")

    if not isinstance(node, dict):
        raise QueryValidationError("Filter nodes must be JSON objects.")

    if "and" in node:
        clauses = node["and"]
        if not isinstance(clauses, list) or len(clauses) == 0:
            raise QueryValidationError("'and' clause must be a non-empty list of filter clauses.")
        for child in clauses:
            _validate_filter_node(child, depth + 1, valid_fields)
    elif "or" in node:
        clauses = node["or"]
        if not isinstance(clauses, list) or len(clauses) == 0:
            raise QueryValidationError("'or' clause must be a non-empty list of filter clauses.")
        for child in clauses:
            _validate_filter_node(child, depth + 1, valid_fields)
    else:
        # Atomic filter condition
        field = node.get("field")
        op = node.get("operator", "eq").lower()

        if not field:
            raise QueryValidationError("Filter condition missing 'field' attribute.")
        _check_field_identifier(field)

        if valid_fields and field not in valid_fields:
            raise QueryValidationError(f"Filter field '{field}' is not in discoverable object schema.")

        if op not in ALLOWED_OPERATORS:
            raise QueryValidationError(f"Unsupported query operator '{op}'. Supported: {sorted(list(ALLOWED_OPERATORS))}")

        if op == "in" and not isinstance(node.get("value"), list):
            raise QueryValidationError("Operator 'in' requires a list value.")
