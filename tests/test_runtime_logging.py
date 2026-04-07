from pathlib import Path

from app.runtime_ops import AppEventLogger, AuditLogger


def test_audit_logger_trims_old_entries_when_retention_limit_is_set(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.jsonl", max_lines=2)

    logger.append({"event": "first"})
    logger.append({"event": "second"})
    logger.append({"event": "third"})

    items = logger.read_recent(limit=10)
    assert [item["event"] for item in items] == ["third", "second"]


def test_app_event_logger_trims_old_entries_when_retention_limit_is_set(tmp_path: Path) -> None:
    logger = AppEventLogger(tmp_path / "app.jsonl", max_lines=1)

    logger.append({"event": "first"})
    logger.append({"event": "second"})

    items = logger.read_recent(limit=10)
    assert [item["event"] for item in items] == ["second"]
