from pathlib import Path


def test_source_files_do_not_contain_known_mojibake_markers() -> None:
    markers = [
        "寮傛",
        "澶嶄範",
        "銆?",
        "锛?",
        "鎺屾彙",
        "鐞嗚В",
    ]
    roots = [Path("app"), Path("tests")]
    offenders: list[str] = []

    for root in roots:
        for path in root.rglob("*.py"):
            if path.name == "test_encoding_cleanup.py":
                continue
            text = path.read_text(encoding="utf-8")
            if any(marker in text for marker in markers):
                offenders.append(str(path))

    assert offenders == []
