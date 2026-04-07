import subprocess

from app.sandbox import DockerPythonSandbox, PythonSandbox


def test_python_sandbox_executes_code_and_reports_success() -> None:
    sandbox = PythonSandbox(timeout_seconds=5)
    result = sandbox.run(
        user_code=(
            "import asyncio\n"
            "async def build_tasks():\n"
            "    async def work(x):\n"
            "        return x * 2\n"
            "    tasks = [asyncio.create_task(work(i)) for i in range(3)]\n"
            "    return await asyncio.gather(*tasks)\n"
        ),
        test_code=(
            "import asyncio\n"
            "result = asyncio.run(build_tasks())\n"
            "assert result == [0, 2, 4]\n"
            "print('ok')\n"
        ),
    )

    assert result.passed is True
    assert "ok" in result.stdout


def test_python_sandbox_reports_failure() -> None:
    sandbox = PythonSandbox(timeout_seconds=5)
    result = sandbox.run(
        user_code="def add(a, b):\n    return a - b\n",
        test_code="assert add(2, 3) == 5\n",
    )

    assert result.passed is False
    assert "AssertionError" in result.stderr


def test_docker_python_sandbox_uses_isolated_container_flags() -> None:
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    sandbox = DockerPythonSandbox(
        timeout_seconds=5,
        image="python:3.12-alpine",
        memory_mb=128,
        cpu_limit=0.5,
        command_runner=fake_run,
    )
    result = sandbox.run(
        user_code="def add(a, b):\n    return a + b\n",
        test_code="assert add(2, 3) == 5\nprint('ok')\n",
    )

    assert result.passed is True
    assert commands
    command = commands[0]
    assert command[:4] == ["docker", "run", "--rm", "--network"]
    assert "none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt" in command
    assert "no-new-privileges" in command
    assert "--user" in command
    assert "65534:65534" in command
    assert "--pids-limit" in command
    assert "64" in command
    assert "--ulimit" in command
    assert "nofile=64:64" in command
    assert "--tmpfs" in command
    assert "--memory" in command
    assert "128m" in command
    assert "--cpus" in command
    assert "0.5" in command


def test_docker_python_sandbox_reports_missing_docker_binary() -> None:
    def fake_run(command, **kwargs):
        raise FileNotFoundError("docker")

    sandbox = DockerPythonSandbox(command_runner=fake_run)
    result = sandbox.run(
        user_code="print('hi')\n",
        test_code="print('ok')\n",
    )

    assert result.passed is False
    assert "Docker executable not found" in result.stderr
