from __future__ import annotations

import ipaddress
import re
from html import unescape
from urllib import parse
from urllib import request


class WebKnowledgeFetcher:
    def __init__(
        self,
        timeout_seconds: int = 10,
        user_agent: str = "learn-new/0.1",
        max_bytes: int = 512_000,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_bytes = max_bytes

    def fetch(self, url: str) -> dict[str, str]:
        parsed = parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are supported")
        self._validate_target(parsed)

        req = request.Request(
            url,
            headers={"User-Agent": self.user_agent},
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            content_type = self._normalize_content_type(response.headers.get("Content-Type", ""))
            if content_type and content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                raise RuntimeError(f"Unsupported content type: {content_type}")
            raw_body = response.read(self.max_bytes + 1)
        if len(raw_body) > self.max_bytes:
            raise RuntimeError("Fetched page exceeded size limit")

        body = raw_body.decode("utf-8", errors="ignore")
        if content_type == "text/plain":
            title = url
            content = " ".join(body.split())
        else:
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

    def _validate_target(self, parsed: parse.ParseResult) -> None:
        if parsed.username or parsed.password:
            raise ValueError("Authenticated URLs are not supported")
        host = (parsed.hostname or "").strip().lower()
        if not host:
            raise ValueError("URL must include a hostname")
        if host in {"localhost", "localhost.localdomain"}:
            raise ValueError("Private or local network URLs are not supported")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise ValueError("Private or local network URLs are not supported")

    @staticmethod
    def _normalize_content_type(content_type: str) -> str:
        return content_type.split(";", 1)[0].strip().lower()
