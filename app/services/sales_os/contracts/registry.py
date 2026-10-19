"""Load, validate, and render agent contracts.

Rendering substitutes task variables only. The system prompt is returned
unchanged so untrusted text cannot rewrite the agent's rules.
"""
import hashlib
import json
import re
import uuid
from typing import Any

from app.services.sales_os.contracts.catalogue import ALIASES, CONTRACTS
from app.services.sales_os.contracts.schema import AgentContract, LifecycleStatus

_PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class ContractError(ValueError):
    pass


def prompt_digest(template: str) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


def placeholders(template: str) -> list[str]:
    return _PLACEHOLDER.findall(template)


def resolve_agent_id(agent_id: str) -> str:
    return ALIASES.get(agent_id, agent_id)


def get_contract(agent_id: str) -> AgentContract:
    canonical = resolve_agent_id(agent_id)
    try:
        return CONTRACTS[canonical]
    except KeyError as exc:
        raise ContractError(f"Unknown agent contract: {agent_id}") from exc


def validate_contract(contract: AgentContract) -> list[str]:
    errors: list[str] = []
    if not contract.uses_llm:
        return errors
    system = contract.system_prompt
    assert system is not None
    if placeholders(system.template):
        errors.append(f"{contract.agent_id} system prompt must not contain task variables")
    task = contract.task_prompt_template
    if task is not None:
        found = placeholders(task.template)
        required = list((contract.prompt_variables_schema or {}).get("required") or [])
        if set(found) != set(required):
            errors.append(
                f"{contract.agent_id} task placeholders {found} do not match required variables {required}"
            )
    for name, extra in contract.task_prompts.items():
        if not placeholders(extra.template):
            errors.append(f"{contract.agent_id} task {name} has no variables")
        if extra.version != extra.version.strip():
            errors.append(f"{contract.agent_id} task {name} version is blank")
    return errors


def validate_registry() -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for agent_id, contract in CONTRACTS.items():
        if contract.agent_id != agent_id:
            errors.append(f"{agent_id} is stored under a different id {contract.agent_id}")
        if agent_id in seen:
            errors.append(f"duplicate contract {agent_id}")
        seen.add(agent_id)
        errors.extend(validate_contract(contract))
    for alias, target in ALIASES.items():
        if target not in CONTRACTS:
            errors.append(f"alias {alias} points at missing contract {target}")
    return errors


def assert_registry_valid() -> None:
    errors = validate_registry()
    if errors:
        raise ContractError("; ".join(errors))


def capability_matrix() -> list[dict[str, str]]:
    rows = []
    for contract in CONTRACTS.values():
        if contract.lifecycle_status == LifecycleStatus.active and not contract.uses_llm:
            readiness = "implemented_deterministic"
        elif contract.lifecycle_status == LifecycleStatus.active:
            readiness = "implemented_hybrid"
        elif contract.lifecycle_status == LifecycleStatus.testing:
            readiness = "modular_skill"
        else:
            readiness = contract.lifecycle_status.value
        rows.append(
            {
                "agent_id": contract.agent_id,
                "version": contract.version,
                "lifecycle_status": contract.lifecycle_status.value,
                "uses_llm": "yes" if contract.uses_llm else "no",
                "prompt_version": contract.prompt_version or "",
                "readiness": readiness,
                "purpose": contract.purpose,
            }
        )
    return rows


def _task_record(contract: AgentContract, task: str):
    if task == "default":
        if contract.task_prompt_template is None:
            raise ContractError(f"{contract.agent_id} has no default task prompt")
        return contract.task_prompt_template, list((contract.prompt_variables_schema or {}).get("required") or [])
    try:
        record = contract.task_prompts[task]
    except KeyError as exc:
        raise ContractError(f"{contract.agent_id} has no task prompt {task}") from exc
    return record, placeholders(record.template)


def render_prompts(agent_id: str, variables: dict[str, Any], task: str = "default") -> dict[str, Any]:
    """Return the system prompt, the rendered task, and the versions that were used."""
    contract = get_contract(agent_id)
    if contract.lifecycle_status in {LifecycleStatus.disabled, LifecycleStatus.deprecated}:
        raise ContractError(f"{contract.agent_id} is {contract.lifecycle_status.value}")
    if not contract.uses_llm or contract.system_prompt is None:
        raise ContractError(f"{contract.agent_id} has no system prompt")
    record, required = _task_record(contract, task)
    missing = [name for name in required if variables.get(name) is None]
    if missing:
        raise ContractError(f"{contract.agent_id} missing task variables: {', '.join(missing)}")
    safe = {
        name: str(variables[name]).replace("{", "{{").replace("}", "}}")
        for name in required
    }
    system = contract.system_prompt.template
    return {
        "agent_id": contract.agent_id,
        "agent_version": contract.version,
        "prompt_version": contract.prompt_version,
        "task_id": record.prompt_id,
        "task_version": record.version,
        "system_prompt": system,
        "system_prompt_sha256": prompt_digest(system),
        "task_prompt": record.template.format(**safe),
        "task_prompt_sha256": prompt_digest(record.template),
        "provider": contract.llm_config.provider if contract.llm_config else None,
        "model_id": contract.llm_config.model_id if contract.llm_config else None,
        "external_actions": contract.tool_permissions.external_actions,
    }


def idempotency_key(agent_id: str, values: dict[str, Any]) -> str:
    contract = get_contract(agent_id)
    payload = {field: values.get(field) for field in contract.idempotency.key_fields}
    raw = json.dumps({"agent_id": contract.agent_id, "version": contract.version, "values": payload}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def execution_record(
    agent_id: str,
    *,
    validation_result: str,
    decision: str,
    latency_ms: int = 0,
    trace_id: str | None = None,
    model_id: str | None = None,
    token_usage: dict | None = None,
    cost: float | None = None,
    task: str = "default",
) -> dict[str, Any]:
    contract = get_contract(agent_id)
    prompt_version = None
    if contract.uses_llm:
        record, _required = _task_record(contract, task)
        prompt_version = f"{contract.prompt_version}:{record.version}"
    return {
        "execution_id": str(uuid.uuid4()),
        "trace_id": trace_id or str(uuid.uuid4()),
        "agent_id": contract.agent_id,
        "agent_version": contract.version,
        "prompt_version": prompt_version,
        "model_id": model_id,
        "latency_ms": latency_ms,
        "token_usage": token_usage or {},
        "cost": cost,
        "decision": decision,
        "validation_result": validation_result,
    }


assert_registry_valid()
