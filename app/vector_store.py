from __future__ import annotations

import json
import math
from urllib import request

from app.models import KnowledgeChunk


class QdrantKnowledgeIndex:
    def __init__(
        self,
        base_url: str,
        collection_name: str,
        vector_size: int = 16,
        transport=None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.transport = transport or self._request_json
        self._ensure_collection()

    def upsert(self, session_id: str, chunks: list[KnowledgeChunk]) -> None:
        points = []
        for chunk in chunks:
            points.append(
                {
                    "id": chunk.chunk_id,
                    "vector": self._embed(f"{chunk.title}\n{chunk.content}\n{' '.join(chunk.tags)}"),
                    "payload": {
                        "session_id": session_id,
                        "chunk_id": chunk.chunk_id,
                        "title": chunk.title,
                        "content": chunk.content,
                        "source": chunk.source,
                        "tags": chunk.tags,
                    },
                }
            )
        self.transport(
            "PUT",
            f"{self.base_url}/collections/{self.collection_name}/points",
            {"points": points},
        )

    def search(self, session_id: str, query: str, limit: int = 3) -> list[KnowledgeChunk]:
        payload = self.transport(
            "POST",
            f"{self.base_url}/collections/{self.collection_name}/points/search",
            {
                "vector": self._embed(query),
                "limit": limit,
                "with_payload": True,
                "filter": {"must": [{"key": "session_id", "match": {"value": session_id}}]},
            },
        )
        results = []
        for item in payload.get("result", []):
            raw = item.get("payload", {})
            results.append(
                KnowledgeChunk(
                    chunk_id=raw.get("chunk_id", str(item.get("id"))),
                    title=raw.get("title", ""),
                    content=raw.get("content", ""),
                    source=raw.get("source", ""),
                    tags=list(raw.get("tags", [])),
                    score=float(item.get("score", 0.0)),
                )
            )
        return results

    def _ensure_collection(self) -> None:
        self.transport(
            "PUT",
            f"{self.base_url}/collections/{self.collection_name}",
            {"vectors": {"size": self.vector_size, "distance": "Cosine"}},
        )

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.vector_size
        tokens = [token for token in text.lower().replace("\n", " ").split(" ") if token]
        for token in tokens:
            slot = sum(ord(char) for char in token) % self.vector_size
            vector[slot] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def _request_json(self, method: str, url: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}
