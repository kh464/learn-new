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


def test_backup_and_restore_scripts_include_operational_safety_guards() -> None:
    backup_script = Path("scripts/backup.ps1").read_text(encoding="utf-8")
    restore_script = Path("scripts/restore.ps1").read_text(encoding="utf-8")

    assert "[switch]$IncludeConfig" in backup_script
    assert "backup-manifest.json" in backup_script
    assert "Copy-Item -LiteralPath" in backup_script

    assert "[switch]$Force" in restore_script
    assert "backup-manifest.json" in restore_script
    assert "throw \"Backup archive does not contain backup-manifest.json" in restore_script
    assert "throw \"Refusing to remove existing .learn without -Force." in restore_script
