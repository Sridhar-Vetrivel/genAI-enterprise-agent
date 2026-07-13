"""Vector store abstraction.

Two implementations behind one protocol:

  AgentFieldVectorStore — the real thing: AgentField's vector memory fabric
      (`memory.set_vector` / `memory.similarity_search`). Used when the docs agent
      runs against the control plane.

  LocalVectorStore — an in-process store with the same semantics, persisted to JSON.
      It keeps the RAG index, the CLI demo and the whole test suite runnable without a
      control plane, which is what makes ≥80% coverage achievable offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from psiog_kendra.llm import cosine_similarity


class VectorStore(Protocol):
    async def set_vector(
        self, key: str, embedding: list[float], metadata: dict[str, Any]
    ) -> None: ...

    async def similarity_search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]: ...


class LocalVectorStore:
    """In-process cosine-similarity store, optionally persisted to disk."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._vectors: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        if path and path.exists():
            self.load()

    def __len__(self) -> int:
        return len(self._vectors)

    async def set_vector(self, key: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        self._vectors[key] = list(embedding)
        self._metadata[key] = dict(metadata)

    async def similarity_search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        scored = [
            {
                "key": key,
                "score": cosine_similarity(query_embedding, vec),
                "text": self._metadata.get(key, {}).get("text", ""),
                "metadata": self._metadata.get(key, {}),
            }
            for key, vec in self._vectors.items()
        ]
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def save(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"vectors": self._vectors, "metadata": self._metadata}, indent=2)
        )

    def load(self) -> None:
        if not self._path or not self._path.exists():
            return
        data = json.loads(self._path.read_text())
        self._vectors = {k: list(v) for k, v in data.get("vectors", {}).items()}
        self._metadata = dict(data.get("metadata", {}))

    def orphans(self) -> list[str]:
        """Chunks whose metadata is missing a field a citation needs.

        The Week 7 data-validation gate asserts this is empty.
        """
        required = ("source", "section", "citation", "text")
        return [
            key
            for key in self._vectors
            if any(not self._metadata.get(key, {}).get(f) for f in required)
        ]


class AgentFieldVectorStore:
    """Adapter over an AgentField agent's vector memory."""

    def __init__(self, memory: Any) -> None:
        self._memory = memory

    async def set_vector(self, key: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        await self._memory.set_vector(key, embedding, metadata=metadata)

    async def similarity_search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results = await self._memory.similarity_search(query_embedding, top_k=top_k)
        # AgentField returns key/score/text; keep the shape identical to LocalVectorStore.
        return [
            {
                "key": r.get("key", ""),
                "score": float(r.get("score", 0.0)),
                "text": r.get("text", ""),
                "metadata": r.get("metadata", {}) or {},
            }
            for r in results
        ]
