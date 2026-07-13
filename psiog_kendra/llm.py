"""The single LLM gateway. Every structured LLM call in the system goes through here.

Two tiers, both local and free:
  Complexity.COMPLEX -> gemma3:4b  (routing, cross-domain synthesis, grounding judge)
  Complexity.SIMPLE  -> gemma3:1b  (phrasing one already-retrieved record)

Structured output uses Ollama's `format` field with the Pydantic model's JSON schema,
then validates the reply with Pydantic. Two constraints drive the design:

  * Ollama 0.23 returns HTTP 500 if the schema contains `enum`, so schemas are
    stripped of enum/const before being sent and correctness is re-established by
    the Pydantic validators (see psiog_kendra.schemas).
  * A 1B/4B model still occasionally emits malformed JSON, so a failed parse is
    retried before giving up.
"""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from psiog_kendra.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class Complexity(StrEnum):
    """Which model tier a call needs."""

    SIMPLE = "simple"
    COMPLEX = "complex"


class LLMError(RuntimeError):
    """Raised when the LLM cannot produce a valid structured response."""


class ModelUnavailable(LLMError):
    """The requested model could not be loaded — almost always host RAM."""


def _is_oom(body: str) -> bool:
    """Ollama reports an unloadable model as a 500 with this message."""
    return "more system memory" in body.lower() or "requires more" in body.lower()


class LLMGateway(Protocol):
    """Injected into every agent so tests can substitute a fake."""

    async def structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        complexity: Complexity = Complexity.COMPLEX,
    ) -> T: ...

    async def embed(self, text: str) -> list[float]: ...


def strip_unsupported(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove JSON-schema keywords Ollama 0.23 rejects (notably `enum`).

    Also drops the Pydantic bookkeeping keys that add no value to the prompt.
    """
    drop = {"enum", "const", "$defs", "definitions", "additionalProperties", "discriminator"}
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key in drop:
            continue
        if isinstance(value, dict):
            out[key] = strip_unsupported(value)
        elif isinstance(value, list):
            out[key] = [strip_unsupported(v) if isinstance(v, dict) else v for v in value]
        else:
            out[key] = value
    return out


def _extract_json(raw: str) -> dict[str, Any]:
    """Parse the model's reply, tolerating prose or fences around the JSON object."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :] if "{" in text else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LLMError(f"no JSON object in model reply: {raw[:200]!r}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"malformed JSON in model reply: {raw[:200]!r}") from exc


class OllamaGateway:
    """Talks to the local Ollama server. Zero cost, no data leaves the host."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        cfg = settings()
        self._cfg = cfg
        self._host = cfg.ollama_host.rstrip("/")
        self._models = {
            Complexity.SIMPLE: cfg.model_simple,
            Complexity.COMPLEX: cfg.model_complex,
        }
        self._embed_model = cfg.embed_model
        self._timeout = cfg.llm_timeout
        self._retries = max(1, cfg.llm_retries)
        self._client = client

    def model_for(self, complexity: Complexity) -> str:
        return self._models[complexity]

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async def send(client: httpx.AsyncClient) -> dict[str, Any]:
            resp = await client.post(f"{self._host}{path}", json=payload)
            if resp.status_code >= 400 and _is_oom(resp.text):
                raise ModelUnavailable(
                    f"{payload.get('model')} does not fit in host memory: {resp.text.strip()}"
                )
            resp.raise_for_status()
            return resp.json()

        if self._client is not None:
            return await send(self._client)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await send(client)

    async def _chat(self, model: str, system: str, user: str, fmt: dict[str, Any]) -> str:
        payload = {
            "model": model,
            "stream": False,
            "options": {
                "temperature": self._cfg.llm_temperature,
                "num_ctx": self._cfg.llm_num_ctx,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": fmt,
        }
        data = await self._post(self._cfg.ollama_chat_path, payload)
        return data.get("message", {}).get("content", "")

    async def structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[T],
        complexity: Complexity = Complexity.COMPLEX,
    ) -> T:
        fmt = strip_unsupported(schema.model_json_schema())
        model = self.model_for(complexity)
        prompt = user

        last: Exception | None = None
        for _attempt in range(self._retries):
            try:
                return schema.model_validate(
                    _extract_json(await self._chat(model, system, prompt, fmt))
                )
            except ModelUnavailable as exc:
                last = exc
                fallback = self.model_for(Complexity.SIMPLE)
                # The complex model does not fit in RAM right now. Degrading to the small
                # model is strictly better than failing the query — but it is a quality
                # regression, so it is surfaced, never silent.
                if self._cfg.fallback_on_oom and model != fallback:
                    logger.warning(
                        "%s does not fit in host memory; falling back to %s for this call. "
                        "Free ~4 GiB of RAM to restore full routing quality.",
                        model,
                        fallback,
                    )
                    model = fallback
                    continue
                raise
            except (LLMError, ValidationError, httpx.HTTPError) as exc:
                last = exc
                # Nudge the model toward valid JSON on the retry.
                prompt = (
                    f"{user}\n\nYour previous reply was not valid JSON for the required "
                    f"schema. Reply with the JSON object only."
                )
        raise LLMError(f"{schema.__name__} not produced after {self._retries} attempts: {last}")

    async def embed(self, text: str) -> list[float]:
        data = await self._post(
            self._cfg.ollama_embed_path, {"model": self._embed_model, "input": text}
        )
        vectors = data.get("embeddings") or []
        if not vectors or not vectors[0]:
            raise LLMError(f"embedding model {self._embed_model} returned no vector")
        return [float(x) for x in vectors[0]]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity, used by the in-process vector store and RAG tests."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)
