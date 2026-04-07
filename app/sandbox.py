from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from app.config import AppConfig
from app.models import SandboxResult


class CodeSandbox(Protocol):
    def run(self, user_code: str, test_code: str) -> SandboxResult:
        ...


class PythonSandbox:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, user_code: str, test_code: str) -> SandboxResult:
        with TemporaryDirectory() as tmp:
            runner = Path(tmp) / "runner.py"
            runner.write_text(f"{user_code}\n\n{test_code}\n", encoding="utf-8")
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", str(runner)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=tmp,
                )
                return SandboxResult(
                    passed=completed.returncode == 0,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                )
            except subprocess.TimeoutExpired as exc:
                return SandboxResult(
                    passed=False,
                    stdout=exc.stdout or "",
                    stderr=(exc.stderr or "") + "\nExecution timed out.",
                    exit_code=124,
                )


class DockerPythonSandbox:
    def __init__(
        self,
        timeout_seconds: int = 10,
        image: str = "python:3.12-slim",
        memory_mb: int = 256,
        cpu_limit: float = 1.0,
        command_runner=subprocess.run,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.image = image
        self.memory_mb = memory_mb
        self.cpu_limit = cpu_limit
        self.command_runner = command_runner

    def run(self, user_code: str, test_code: str) -> SandboxResult:
        with TemporaryDirectory() as tmp:
            runner = Path(tmp) / "runner.py"
            runner.write_text(f"{user_code}\n\n{test_code}\n", encoding="utf-8")
            command = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt",
                "no-new-privileges",
                "--user",
                "65534:65534",
                "--pids-limit",
                "64",
                "--ulimit",
                "nofile=64:64",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=64m",
                "--memory",
                f"{self.memory_mb}m",
                "--cpus",
                str(self.cpu_limit),
                "-v",
                f"{runner.resolve()}:/workspace/runner.py:ro",
                "-w",
                "/workspace",
                self.image,
                "python",
                "-I",
                "/workspace/runner.py",
            ]
            try:
                completed = self.command_runner(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
                return SandboxResult(
                    passed=completed.returncode == 0,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                )
            except FileNotFoundError:
                return SandboxResult(
                    passed=False,
                    stderr="Docker executable not found.",
                    exit_code=127,
                )
            except subprocess.TimeoutExpired as exc:
                return SandboxResult(
                    passed=False,
                    stdout=exc.stdout or "",
                    stderr=(exc.stderr or "") + "\nExecution timed out.",
                    exit_code=124,
                )


def build_sandbox(config: AppConfig | None) -> CodeSandbox:
    if config is None or config.sandbox.backend == "local":
        timeout = config.sandbox.timeout_seconds if config is not None else 10
        return PythonSandbox(timeout_seconds=timeout)
    return DockerPythonSandbox(
        timeout_seconds=config.sandbox.timeout_seconds,
        image=config.sandbox.docker_image,
        memory_mb=config.sandbox.memory_mb,
        cpu_limit=config.sandbox.cpu_limit,
    )
