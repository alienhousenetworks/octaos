"""Drop repeated copies of the same evidence. Different sources stay independent."""
from typing import Iterable


def dedupe_signals(signals: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    kept: list[dict] = []
    for signal in signals:
        key = signal.get("independent_key") or signal.get("payload_hash") or signal.get("evidence_hash")
        if not key:
            kept.append(signal)
            continue
        if key in seen:
            continue
        seen.add(key)
        kept.append(signal)
    return kept
