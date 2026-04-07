from app.sandbox import PythonSandbox


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
