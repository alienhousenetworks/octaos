"""Regression tests for deterministic, evidence-first Orchestra analytics primitives."""
import pytest

from app.services.data_intelligence.core import (
    EvidenceLedger, EvidenceRef, Finding, PlanTask, ValidatedPlan,
    canonical_json_sha256, profile_records, sha256_bytes, validate_findings,
)


def test_plan_topological_order_and_dependencies():
    plan = ValidatedPlan(goal="profile sales", tasks=[
        PlanTask(task_id="load", description="Load authorized records", specialist="source"),
        PlanTask(task_id="profile", description="Profile records", specialist="quality", dependencies=["load"]),
        PlanTask(task_id="report", description="Report results", specialist="report", dependencies=["profile"]),
    ])
    assert plan.topological_order() == ["load", "profile", "report"]


@pytest.mark.parametrize("tasks", [
    [PlanTask(task_id="x", description="a", specialist="s"), PlanTask(task_id="x", description="b", specialist="s")],
    [PlanTask(task_id="x", description="a", specialist="s", dependencies=["missing"])],
    [PlanTask(task_id="x", description="a", specialist="s", dependencies=["y"]), PlanTask(task_id="y", description="b", specialist="s", dependencies=["x"])],
])
def test_invalid_graphs_fail_closed(tasks):
    with pytest.raises(ValueError):
        ValidatedPlan(goal="invalid", tasks=tasks)


def test_profile_uses_actual_records_and_handles_empty_input():
    profile = profile_records([
        {"revenue": 10, "region": "east"},
        {"revenue": 20, "region": "west"},
        {"revenue": 20, "region": "west"},
        {"revenue": None, "region": "east"},
    ])
    assert profile["row_count"] == 4
    assert profile["duplicate_row_count"] == 1
    assert profile["columns"]["revenue"]["null_count"] == 1
    assert profile["columns"]["revenue"]["numeric"]["sum"] == 50
    assert profile["columns"]["revenue"]["numeric"]["mean"] == pytest.approx(50 / 3)
    empty = profile_records([])
    assert empty["status"] == "empty"
    assert empty["columns"] == {}
    assert empty["limitations"]


def test_profile_rejects_oversized_and_non_record_inputs():
    with pytest.raises(ValueError):
        profile_records([{"x": 1}, {"x": 2}], max_rows=1)
    with pytest.raises(TypeError):
        profile_records(["not a record"])


def test_evidence_ledger_rejects_missing_refs_and_id_collisions():
    ledger = EvidenceLedger()
    evidence = EvidenceRef(evidence_id="ev_001", kind="calculation", source_name="profile", locator="columns.revenue.numeric.sum")
    ledger.add(evidence)
    finding = Finding(finding_id="f_001", title="Revenue total", statement="Revenue sums to 50", method="Sum of parsed revenue values", evidence_ids=["ev_001"])
    assert validate_findings([finding], ledger) == [finding]
    with pytest.raises(ValueError, match="missing evidence"):
        validate_findings([finding.model_copy(update={"evidence_ids": ["ev_missing"]})], ledger)
    with pytest.raises(ValueError, match="collision"):
        ledger.add(evidence.model_copy(update={"locator": "different"}))


def test_hashes_are_deterministic():
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert canonical_json_sha256({"a": 1, "b": 2}) == canonical_json_sha256({"b": 2, "a": 1})


@pytest.mark.asyncio
async def test_sandbox_fails_closed_without_trusted_image(tmp_path):
    from app.services.data_intelligence.sandbox import DockerAnalysisSandbox
    workspace = tmp_path / "tenant" / "run-1"
    workspace.mkdir(parents=True)
    (workspace / "analysis.py").write_text("print('not executed')", encoding="utf-8")
    sandbox = DockerAnalysisSandbox(image="", workspace_root=tmp_path)
    result = await sandbox.run(workspace)
    assert result.status == "unavailable"
    assert "not executed" not in result.stdout
    assert "not executed" not in result.stderr
