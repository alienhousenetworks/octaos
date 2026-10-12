"""Epsilon-greedy source allocation. Can be disabled or overridden per tenant."""
import random
from typing import Callable


def routing_utility(
    *,
    expected_yield: float,
    quality: float,
    compliance: float,
    latency_ms: float | None,
    cost: float | None,
) -> float | None:
    if cost is None or cost < 0 or latency_ms is None or latency_ms < 0:
        return None
    latency_factor = 1.0 / (1.0 + (latency_ms / 1000.0))
    denominator = cost if cost > 0 else 0.01
    return (expected_yield * quality * compliance * latency_factor) / denominator


def choose_provider(
    providers: list[str],
    observations: dict[str, dict],
    *,
    epsilon: float = 0.1,
    exploration_floor: int = 3,
    disabled: bool = False,
    override: str | None = None,
    rng: Callable[[], float] | None = None,
) -> dict:
    if not providers:
        return {"provider": None, "reason": "no_providers"}
    if override:
        if override not in providers:
            raise ValueError(f"Override provider is not available: {override}")
        return {"provider": override, "reason": "manual_override"}
    if disabled:
        return {"provider": providers[0], "reason": "bandit_disabled"}
    roll = rng() if rng else random.random()
    under_explored = [
        key for key in providers
        if int((observations.get(key) or {}).get("pulls") or 0) < exploration_floor
    ]
    if under_explored and roll < max(epsilon, 0.0):
        return {"provider": under_explored[0], "reason": "exploration_floor"}
    if roll < epsilon:
        return {"provider": providers[int(roll * len(providers)) % len(providers)], "reason": "epsilon_explore"}

    def value(key: str) -> float:
        stats = observations.get(key) or {}
        utility = stats.get("utility")
        if utility is None:
            return -1.0
        return float(utility)

    ranked = sorted(providers, key=value, reverse=True)
    return {"provider": ranked[0], "reason": "exploit_utility"}
