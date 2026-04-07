from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.web_fetch import WebKnowledgeFetcher


def test_import_knowledge_from_url_ingests_remote_text(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: 1",
                "llm:",
                "  default_provider: siliconflow",
                "  default_profile: chat",
                "  providers:",
                "    siliconflow:",
                "      enabled: true",
                "      base_url: https://api.siliconflow.cn/v1",
                "      api_key:",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    app.state.web_fetcher = lambda url: {
        "title": "Async Notes",
        "content": "asyncio.create_task schedules concurrent coroutines.",
        "source": url,
    }
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    session_id = created.json()["session_id"]

    imported = client.post(
        f"/api/sessions/{session_id}/knowledge/import-url",
        json={"url": "https://example.com/async"},
    )
    searched = client.get(
        f"/api/sessions/{session_id}/knowledge/search",
        params={"query": "create_task concurrent coroutines"},
    )

    assert imported.status_code == 201
    assert imported.json()["chunks_added"] >= 1
    assert searched.status_code == 200
    assert searched.json()["items"][0]["source"] == "https://example.com/async"


def test_import_knowledge_from_url_is_idempotent_for_same_source(tmp_path: Path) -> None:
    config_path = tmp_path / "llm.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: 1",
                "llm:",
                "  default_provider: siliconflow",
                "  default_profile: chat",
                "  providers:",
                "    siliconflow:",
                "      enabled: true",
                "      base_url: https://api.siliconflow.cn/v1",
                "      api_key:",
                "      models:",
                "        chat: Qwen/Qwen2.5-7B-Instruct",
                "  routing:",
                "    profiles:",
                "      chat:",
                "        provider: siliconflow",
                "        model: Qwen/Qwen2.5-7B-Instruct",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(workspace_root=tmp_path / ".learn", config_path=config_path)
    app.state.web_fetcher = lambda url: {
        "title": "Async Notes",
        "content": "asyncio.create_task schedules concurrent coroutines.",
        "source": url,
    }
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        json={"domain": "Python async programming", "goal": "Master async/await"},
    )
    session_id = created.json()["session_id"]

    first = client.post(
        f"/api/sessions/{session_id}/knowledge/import-url",
        json={"url": "https://example.com/async"},
    )
    second = client.post(
        f"/api/sessions/{session_id}/knowledge/import-url",
        json={"url": "https://example.com/async"},
    )
    searched = client.get(
        f"/api/sessions/{session_id}/knowledge/search",
        params={"query": "create_task concurrent coroutines", "limit": 10},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["chunks_added"] >= 1
    assert second.json()["chunks_added"] == 0
    assert len(searched.json()["items"]) == 1


def test_web_fetcher_rejects_non_http_urls() -> None:
    fetcher = WebKnowledgeFetcher()

    with pytest.raises(ValueError):
        fetcher.fetch("file:///tmp/secrets.txt")


class _FakeWebResponse:
    def __init__(self, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self._body
        return self._body[:size]

    def __enter__(self) -> "_FakeWebResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_web_fetcher_rejects_private_network_hosts() -> None:
    fetcher = WebKnowledgeFetcher()

    with pytest.raises(ValueError):
        fetcher.fetch("http://127.0.0.1/internal")

    with pytest.raises(ValueError):
        fetcher.fetch("http://localhost/internal")


def test_web_fetcher_rejects_non_text_content_type(monkeypatch) -> None:
    fetcher = WebKnowledgeFetcher()

    monkeypatch.setattr(
        "app.web_fetch.request.urlopen",
        lambda req, timeout=0: _FakeWebResponse(b"%PDF-1.4", content_type="application/pdf"),
    )

    with pytest.raises(RuntimeError):
        fetcher.fetch("https://example.com/file.pdf")


def test_web_fetcher_rejects_oversized_response(monkeypatch) -> None:
    fetcher = WebKnowledgeFetcher(timeout_seconds=3)

    monkeypatch.setattr(
        "app.web_fetch.request.urlopen",
        lambda req, timeout=0: _FakeWebResponse(b"a" * 600_000, content_type="text/plain"),
    )

    with pytest.raises(RuntimeError):
        fetcher.fetch("https://example.com/huge")
