from __future__ import annotations

import re
from html import unescape
from urllib import parse
from urllib import request


class WebKnowledgeFetcher:
    def __init__(self, timeout_seconds: int = 10, user_agent: str = "learn-new/0.1") -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch(self, url: str) -> dict[str, str]:
        parsed = parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")
        req = request.Request(
            url,
            headers={"User-Agent": self.user_agent},
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="ignore")
        title = self._extract_title(body) or url
        content = self._extract_text(body)
        if not content.strip():
            raise RuntimeError("Fetched page did not contain readable text")
        return {
            "title": title,
            "content": content.strip(),
            "source": url,
        }

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return " ".join(unescape(match.group(1)).split())

    def _extract_text(self, html: str) -> str:
        without_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", without_scripts)
        text = unescape(text)
        return " ".join(text.split())
