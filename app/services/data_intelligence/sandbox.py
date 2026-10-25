"""Fail-closed Docker sandbox runner for reproducible analytical Python jobs.

This runner is intentionally not wired to HTTP routes by itself. Callers must authorize
and stage tenant-scoped inputs before invoking it. The container image should be pinned
by digest in production and include only approved scientific packages.
"""
from __future__ import annotations

import asyncio
import os
import re
import shutil
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SandboxLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timeout_seconds: int = Field(default=60, ge=1, le=900)
    memory_mb: int = Field(default=1024, ge=128, le=8192)
    cpu_count: float = Field(default=1.0, gt=0, le=4)
    pids_limit: int = Field(default=64, ge=8, le=512)
    max_output_bytes: int = Field(default=5_000_000, ge=1024, le=50_000_000)


class SandboxResult(BaseModel):
    status: Literal["succeeded", "failed", "timeout", "unavailable"]
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int
    reason: str | None = None


class DockerAnalysisSandbox:
    """Execute one staged script with no network, no host root mount, and bounded resources."""

    def __init__(
        self,
        *,
        image: str | None = None,
        workspace_root: str | Path | None = None,
        docker_binary: str = "docker",
    ) -> None:
        self.image = image or os.getenv("OCTAOS_ANALYSIS_SANDBOX_IMAGE", "")
        self.workspace_root = Path(
            workspace_root or os.getenv("OCTAOS_ANALYSIS_WORKSPACE", "/tmp/octaos-analysis")
        ).resolve()
        self.docker_binary = docker_binary

    def _validate_workspace(self, path: str | Path) -> Path:
        resolved = Path(path).resolve(strict=True)
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError("Sandbox workspace must be inside the configured workspace root") from exc
        if not resolved.is_dir():
            raise ValueError("Sandbox workspace must be a directory")
        script = resolved / "analysis.py"
        if not script.is_file() or script.is_symlink():
            raise ValueError("Workspace must contain a regular analysis.py file")
        # Reject symlinked child inputs to prevent staging-time path escapes.
        for child in resolved.iterdir():
            if child.is_symlink():
                raise ValueError("Symlinks are not permitted in sandbox workspaces")
        return resolved

    async def run(self, workspace: str | Path, limits: SandboxLimits | None = None) -> SandboxResult:
        import time
        started = time.monotonic()
        limits = limits or SandboxLimits()

        if not self.image or not re.fullmatch(r"[A-Za-z0-9._/:@-]+", self.image):
            return SandboxResult(
                status="unavailable", duration_ms=0,
                reason="A trusted sandbox image must be configured before analysis execution.",
            )
        if shutil.which(self.docker_binary) is None:
            return SandboxResult(
                status="unavailable", duration_ms=0,
                reason="Docker runtime is unavailable; code was not executed.",
            )

        try:
            path = self._validate_workspace(workspace)
        except (OSError, ValueError) as exc:
            return SandboxResult(
                status="failed", duration_ms=0,
                reason=f"Invalid sandbox workspace: {str(exc)}",
            )

        # The script and inputs are read-only. Only /output is writable and bounded
        # by the workspace filesystem quota enforced by the worker/host deployment.
        output_dir = path / "output"
        output_dir.mkdir(mode=0o700, exist_ok=True)
        if output_dir.is_symlink():
            return SandboxResult(status="failed", duration_ms=0, reason="Output directory cannot be a symlink")

        command = [
            self.docker_binary, "run", "--rm",
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit", str(limits.pids_limit),
            "--memory", f"{limits.memory_mb}m",
            "--cpus", str(limits.cpu_count),
            "--mount", f"type=bind,src={path},dst=/input,readonly",
            "--mount", f"type=bind,src={output_dir.resolve()},dst=/output",
            "--tmpfs", f"/tmp:rw,noexec,nosuid,size=64m",
            "--workdir", "/output",
            self.image,
            "python", "-I", "/input/analysis.py",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"},
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=limits.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return SandboxResult(
                    status="timeout",
                    duration_ms=int((time.monotonic() - started) * 1000),
                    reason=f"Execution exceeded {limits.timeout_seconds} seconds; process terminated.",
                )
            if len(stdout) > limits.max_output_bytes or len(stderr) > limits.max_output_bytes:
                return SandboxResult(
                    status="failed",
                    exit_code=process.returncode,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    reason="Execution output exceeded configured byte limits.",
                )
            succeeded = process.returncode == 0
            return SandboxResult(
                status="succeeded" if succeeded else "failed",
                exit_code=process.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=int((time.monotonic() - started) * 1000),
                reason=None if succeeded else "Analysis process exited with a non-zero status.",
            )
        except OSError as exc:
            return SandboxResult(
                status="unavailable",
                duration_ms=int((time.monotonic() - started) * 1000),
                reason=f"Sandbox runtime could not start ({type(exc).__name__}); code was not executed.",
            )
