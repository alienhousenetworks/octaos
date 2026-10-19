"""Versioned Sales OS agent and prompt contracts.

A system prompt is not a security boundary. Schema validation, tool
allowlists, and the policy engine still apply when a model ignores it.
"""
from app.services.sales_os.contracts.registry import (
    execution_record,
    get_contract,
    prompt_digest,
    render_prompts,
    validate_registry,
)

__all__ = [
    "execution_record",
    "get_contract",
    "prompt_digest",
    "render_prompts",
    "validate_registry",
]
