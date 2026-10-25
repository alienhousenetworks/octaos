"""Governed, deterministic primitives for Orchestra Data Intelligence.

This module deliberately contains no LLM calls, database connections, or code execution.
It is the trust boundary used by higher-level planners: validate a plan, profile actual
records, and attach findings to explicit source evidence before narrative generation.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, deque
from datetime import datetime, timezone
from statistics import mean, median, pstdev
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    description: str = Field(min_length=1, max_length=4000)
    specialist: str = Field(min_length=1, max_length=100)
    dependencies: list[str] = Field(default_factory=list, max_length=100)
    required_permissions: list[str] = Field(default_factory=list, max_length=100)


class ValidatedPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1, max_length=8000)
    tasks: list[PlanTask] = Field(min_length=1, max_length=100)
    plan_version: str = "1"

    @model_validator(mode="after")
    def validate_graph(self) -> "ValidatedPlan":
        ids = [task.task_id for task in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError("Plan contains duplicate task_id values")
        known = set(ids)
        for task in self.tasks:
            if task.task_id in task.dependencies:
                raise ValueError(f"Task {task.task_id} cannot depend on itself")
            missing = set(task.dependencies) - known
            if missing:
                raise ValueError(f"Task {task.task_id} has unknown dependencies: {sorted(missing)}")
            if len(task.dependencies) != len(set(task.dependencies)):
                raise ValueError(f"Task {task.task_id} contains duplicate dependencies")

        indegree = {task.task_id: len(task.dependencies) for task in self.tasks}
        children: dict[str, list[str]] = {task_id: [] for task_id in ids}
        for task in self.tasks:
            for parent in task.dependencies:
                children[parent].append(task.task_id)
        queue = deque(task_id for task_id, degree in indegree.items() if degree == 0)
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for child in children[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if visited != len(ids):
            raise ValueError("Plan dependencies contain a cycle")
        return self

    def topological_order(self) -> list[str]:
        """Return a deterministic topological ordering, preserving input order on ties."""
        by_id = {task.task_id: task for task in self.tasks}
        remaining = {task.task_id: set(task.dependencies) for task in self.tasks}
        result: list[str] = []
        while remaining:
            ready = [task_id for task_id, deps in remaining.items() if not deps]
            if not ready:
                raise ValueError("Plan dependencies contain a cycle")
            for task_id in ready:
                result.append(task_id)
                remaining.pop(task_id)
            for deps in remaining.values():
                deps.difference_update(ready)
        return result


class EvidenceRef(BaseModel):
    """A reference to an actual source or deterministic computation; never narrative-only."""
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(min_length=1, max_length=160)
    kind: Literal["file", "database", "api", "calculation", "execution", "manual_review"]
    source_name: str = Field(min_length=1, max_length=500)
    locator: str = Field(min_length=1, max_length=2000)
    content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=500)
    statement: str = Field(min_length=1, max_length=5000)
    method: str = Field(min_length=1, max_length=3000)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    confidence: Literal["high", "medium", "low", "unassessed"] = "unassessed"


class EvidenceLedger:
    """Small append-only in-memory ledger primitive; persistence is the caller's responsibility."""
    def __init__(self) -> None:
        self._records: dict[str, EvidenceRef] = {}

    def add(self, record: EvidenceRef) -> EvidenceRef:
        prior = self._records.get(record.evidence_id)
        if prior is not None and prior != record:
            raise ValueError(f"Evidence ID collision: {record.evidence_id}")
        self._records[record.evidence_id] = record
        return record

    def validate_finding(self, finding: Finding) -> None:
        missing = set(finding.evidence_ids) - self._records.keys()
        if missing:
            raise ValueError(f"Finding references missing evidence: {sorted(missing)}")

    def snapshot(self) -> list[dict[str, Any]]:
        return [record.model_dump(mode="json") for _, record in sorted(self._records.items())]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def profile_records(records: Iterable[dict[str, Any]], *, max_rows: int = 100_000) -> dict[str, Any]:
    """Profile real in-memory records without silently fabricating values.

    The caller must enforce source-level authorization and row limits before supplying data.
    Values that are not finite numbers are excluded from numeric statistics and counted.
    """
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    rows: list[dict[str, Any]] = []
    for record in records:
        if len(rows) >= max_rows:
            raise ValueError(f"Input exceeds the configured {max_rows} row profiling limit")
        if not isinstance(record, dict):
            raise TypeError("Each record must be a dictionary")
        rows.append(record)

    columns = sorted({key for row in rows for key in row.keys()})
    column_profiles: dict[str, Any] = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        non_null = [value for value in values if value is not None and value != ""]
        numeric: list[float] = []
        invalid_numeric = 0
        for value in non_null:
            if isinstance(value, bool):
                invalid_numeric += 1
                continue
            try:
                number = float(value)
                if math.isfinite(number):
                    numeric.append(number)
                else:
                    invalid_numeric += 1
            except (TypeError, ValueError, OverflowError):
                invalid_numeric += 1

        profile: dict[str, Any] = {
            "row_count": len(rows),
            "non_null_count": len(non_null),
            "null_count": len(rows) - len(non_null),
            "null_fraction": (len(rows) - len(non_null)) / len(rows) if rows else None,
            "distinct_count": len({str(value) for value in non_null}),
            "sample_values": [str(value)[:200] for value in non_null[:5]],
        }
        if numeric and invalid_numeric == 0:
            profile["numeric"] = {
                "count": len(numeric),
                "min": min(numeric),
                "max": max(numeric),
                "mean": mean(numeric),
                "median": median(numeric),
                "population_stddev": pstdev(numeric),
                "sum": sum(numeric),
            }
        elif numeric:
            profile["numeric_candidate"] = {
                "parsed_count": len(numeric),
                "unparsed_count": invalid_numeric,
                "note": "Numeric statistics omitted because the column contains mixed or invalid values.",
            }
        profile["type_counts"] = dict(Counter(type(value).__name__ for value in non_null))
        column_profiles[str(column)] = profile

    canonical_rows = [json.dumps(row, sort_keys=True, default=str, ensure_ascii=False) for row in rows]
    duplicate_count = len(canonical_rows) - len(set(canonical_rows))
    return {
        "status": "empty" if not rows else "complete",
        "row_count": len(rows),
        "column_count": len(columns),
        "duplicate_row_count": duplicate_count,
        "columns": column_profiles,
        "dataset_sha256": canonical_json_sha256(rows),
        "limitations": [] if rows else ["No records were supplied; no analytical findings can be computed."],
    }


def validate_findings(findings: Iterable[Finding], ledger: EvidenceLedger) -> list[Finding]:
    validated = list(findings)
    ids = [finding.finding_id for finding in validated]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate finding_id values")
    for finding in validated:
        ledger.validate_finding(finding)
    return validated
