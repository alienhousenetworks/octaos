"""Server-side plan entitlement and usage-budget enforcement primitives."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping


class EntitlementDenied(PermissionError):
    pass


@dataclass(frozen=True)
class PlanEntitlements:
    plan_id: str
    enabled_features: frozenset[str]
    max_concurrent_runs: int
    monthly_task_limit: int
    monthly_cost_limit: Decimal
    allowed_providers: frozenset[str]

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "PlanEntitlements":
        try:
            limit = Decimal(str(value["monthly_cost_limit"]))
            max_concurrent = int(value["max_concurrent_runs"])
            task_limit = int(value["monthly_task_limit"])
        except (KeyError, ValueError, InvalidOperation) as exc:
            raise ValueError("Plan entitlement configuration is incomplete or invalid.") from exc
        if limit < 0 or max_concurrent < 0 or task_limit < 0:
            raise ValueError("Plan limits cannot be negative.")
        features = value.get("enabled_features", [])
        providers = value.get("allowed_providers", [])
        if not isinstance(features, (list, tuple, set, frozenset)) or not all(isinstance(x, str) for x in features):
            raise ValueError("enabled_features must be a collection of strings.")
        if not isinstance(providers, (list, tuple, set, frozenset)) or not all(isinstance(x, str) for x in providers):
            raise ValueError("allowed_providers must be a collection of strings.")
        return cls(
            plan_id=str(value.get("plan_id", "")),
            enabled_features=frozenset(features),
            max_concurrent_runs=max_concurrent,
            monthly_task_limit=task_limit,
            monthly_cost_limit=limit,
            allowed_providers=frozenset(providers),
        )


def enforce_feature(plan: PlanEntitlements, feature: str) -> None:
    if feature not in plan.enabled_features:
        raise EntitlementDenied(f"Feature '{feature}' is not enabled for plan '{plan.plan_id}'.")


def enforce_run_admission(
    plan: PlanEntitlements,
    *,
    active_runs: int,
    monthly_tasks: int,
    monthly_cost: Decimal | str | float,
    requested_provider: str,
    estimated_cost: Decimal | str | float = Decimal("0"),
) -> None:
    """Fail closed before starting a run if a plan, provider, or budget would be exceeded."""
    if requested_provider not in plan.allowed_providers:
        raise EntitlementDenied("Requested AI provider is not enabled for this tenant plan.")
    if active_runs >= plan.max_concurrent_runs:
        raise EntitlementDenied("Tenant concurrent-run limit reached.")
    if monthly_tasks >= plan.monthly_task_limit:
        raise EntitlementDenied("Tenant monthly task limit reached.")
    try:
        current_cost = Decimal(str(monthly_cost))
        next_cost = Decimal(str(estimated_cost))
    except InvalidOperation as exc:
        raise ValueError("Usage cost must be a valid decimal amount.") from exc
    if current_cost < 0 or next_cost < 0:
        raise ValueError("Usage cost cannot be negative.")
    if current_cost + next_cost > plan.monthly_cost_limit:
        raise EntitlementDenied("Tenant monthly AI budget would be exceeded.")
