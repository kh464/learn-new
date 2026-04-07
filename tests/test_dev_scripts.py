from pathlib import Path


def test_dev_scripts_enable_utf8_console_and_python() -> None:
    dev_script = Path("scripts/dev.ps1").read_text(encoding="utf-8")
    test_script = Path("scripts/test.ps1").read_text(encoding="utf-8")

    assert "chcp 65001" in dev_script
    assert "$env:PYTHONUTF8='1'" in dev_script
    assert "uvicorn app.main:app --reload" in dev_script

    assert "chcp 65001" in test_script
    assert "$env:PYTHONUTF8='1'" in test_script
    assert "pytest tests -q" in test_script
