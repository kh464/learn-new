from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.models import KnowledgeChunk
from app.workspace import WorkspaceManager


class KnowledgeService:
    def __init__(self, manager: WorkspaceManager) -> None:
        self.manager = manager

    def ingest_text(self, session_id: str, title: str, content: str, source: str) -> list[KnowledgeChunk]:
        upload_path = self.manager.session_root(session_id) / "user_uploads" / f"{title}.txt"
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        upload_path.write_text(content, encoding="utf-8")

        chunks = [
            KnowledgeChunk(
                chunk_id=uuid4().hex,
                title=title,
                content=part.strip(),
                source=source,
                tags=self._extract_tags(part),
            )
            for part in self._chunk_text(content)
            if part.strip()
        ]
        self.manager.append_knowledge_chunks(session_id, chunks)
        if self.manager.knowledge_index is not None:
            self.manager.knowledge_index.upsert(session_id=session_id, chunks=chunks)
        return chunks

    def retrieve(self, session_id: str, query: str, limit: int = 3) -> list[KnowledgeChunk]:
        if self.manager.knowledge_index is not None:
            indexed = self.manager.knowledge_index.search(session_id=session_id, query=query, limit=limit)
            if indexed:
                return indexed
        tokens = set(self._tokenize(query))
        scored: list[KnowledgeChunk] = []
        for chunk in self.manager.read_knowledge_chunks(session_id):
            overlap = len(tokens.intersection(self._tokenize(chunk.content + " " + " ".join(chunk.tags))))
            if overlap == 0:
                continue
            scored.append(chunk.model_copy(update={"score": float(overlap)}))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def list_chunks(self, session_id: str) -> list[KnowledgeChunk]:
        return self.manager.read_knowledge_chunks(session_id)

    def extract_focus_keywords(self, session_id: str, limit: int = 4) -> list[str]:
        counts: dict[str, int] = {}
        for chunk in self.manager.read_knowledge_chunks(session_id):
            for phrase in self._extract_phrases(chunk.content):
                counts[phrase] = counts.get(phrase, 0) + 2
            for token in self._tokenize(chunk.content + " " + " ".join(chunk.tags)):
                if len(token) < 4:
                    continue
                counts[token] = counts.get(token, 0) + 1
        ranked = sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                0 if " " in item[0] else 1,
                item[0],
            ),
        )
        return [token for token, _count in ranked[:limit]]

    def _chunk_text(self, content: str, max_chars: int = 220) -> list[str]:
        normalized = content.replace("\r\n", "\n")
        paragraphs = [item.strip() for item in normalized.split("\n") if item.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= max_chars:
                current = f"{current}\n{paragraph}".strip()
            else:
                if current:
                    chunks.append(current)
                current = paragraph
        if current:
            chunks.append(current)
        return chunks or [normalized]

    def _extract_tags(self, text: str) -> list[str]:
        candidates = self._tokenize(text)
        return sorted({token for token in candidates if len(token) >= 4})[:8]

    def _extract_phrases(self, text: str) -> list[str]:
        normalized = (
            text.replace("。", ",")
            .replace("，", ",")
            .replace("、", ",")
            .replace("；", ",")
            .replace(";", ",")
            .replace("\n", ",")
        )
        phrases: list[str] = []
        for part in normalized.split(","):
            cleaned = " ".join(part.lower().strip().split())
            if not cleaned:
                continue
            if 4 <= len(cleaned) <= 32 and " " in cleaned:
                phrases.append(cleaned)
        phrases.extend(
            match.group(0)
            for match in re.finditer(r"[a-z][a-z0-9_]*(?: [a-z][a-z0-9_]*)+", text.lower())
        )
        return phrases

    def _tokenize(self, text: str) -> list[str]:
        cleaned = text.lower()
        for char in [
            ",",
            ".",
            ":",
            ";",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "`",
            "\n",
            "\t",
            "。",
            "，",
            "：",
            "、",
            "！",
            "？",
        ]:
            cleaned = cleaned.replace(char, " ")
        tokens: list[str] = []
        for token in cleaned.split(" "):
            normalized = re.sub(r"[^a-z0-9_\-\u4e00-\u9fff]+", "", token)
            if normalized:
                tokens.append(normalized)
        return tokens
