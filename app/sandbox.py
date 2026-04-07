from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from app.models import SandboxResult


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
