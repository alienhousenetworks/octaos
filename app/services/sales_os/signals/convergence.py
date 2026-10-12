"""Reward independent evidence. Copies of one payload do not stack."""
from app.services.sales_os.signals.dedupe import dedupe_signals

BONUS_CAP = 25.0

# Larger leadership bundle replaces the smaller funding+hiring bonus.
_LEADERSHIP_BUNDLE = frozenset({"funding", "hiring", "leadership"})
_FUNDING_HIRING = frozenset({"funding", "hiring"})
_MIGRATION = frozenset({"reviews", "technographic"})


def convergence_bonus(signals: list[dict]) -> dict:
    independent = dedupe_signals(
        [
            {
                **signal,
                "independent_key": signal.get("independent_key") or signal.get("payload_hash") or signal.get("evidence_hash"),
            }
            for signal in signals
        ]
    )
    families = {signal.get("family") for signal in independent if signal.get("family")}
    bonus = 0.0
    reasons: list[str] = []
    if _LEADERSHIP_BUNDLE <= families:
        bonus += 15.0
        reasons.append("funding_hiring_leadership")
    elif _FUNDING_HIRING <= families:
        bonus += 8.0
        reasons.append("funding_and_hiring")
    if _MIGRATION <= families:
        bonus += 12.0
        reasons.append("migration_play")
    applied = min(bonus, BONUS_CAP)
    return {
        "bonus": applied,
        "uncapped_bonus": bonus,
        "capped": bonus > BONUS_CAP,
        "reasons": reasons,
        "independent_families": sorted(families),
        "independent_count": len(independent),
        "dropped_duplicates": len(signals) - len(independent),
    }
