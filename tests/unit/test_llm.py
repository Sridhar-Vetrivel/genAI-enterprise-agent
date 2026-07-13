"""The LLM gateway: model tiering, schema sanitising, JSON recovery, OOM fallback."""

from __future__ import annotations

import httpx
import pytest
import respx

from psiog_kendra.config import reset_settings, settings
from psiog_kendra.llm import (
    Complexity,
    LLMError,
    ModelUnavailable,
    OllamaGateway,
    cosine_similarity,
    strip_unsupported,
)
from psiog_kendra.schemas import RoutingDecision

CHAT_URL = "http://localhost:11434/api/chat"
EMBED_URL = "http://localhost:11434/api/embed"


def chat_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"content": content}})


def oom() -> httpx.Response:
    return httpx.Response(
        500, json={"error": "model requires more system memory (4.0 GiB) than is available (3.5)"}
    )


class TestStripUnsupported:
    def test_removes_enum_which_ollama_rejects(self) -> None:
        schema = {"properties": {"d": {"type": "string", "enum": ["a", "b"]}}}
        assert "enum" not in strip_unsupported(schema)["properties"]["d"]

    def test_strips_enum_nested_in_array_items(self) -> None:
        schema = {
            "properties": {"d": {"type": "array", "items": {"type": "string", "enum": ["a"]}}}
        }
        assert "enum" not in strip_unsupported(schema)["properties"]["d"]["items"]

    def test_keeps_the_structure_the_model_needs(self) -> None:
        out = strip_unsupported(RoutingDecision.model_json_schema())
        assert out["type"] == "object"
        assert out["properties"]["domains"]["type"] == "array"

    def test_real_schema_carries_no_enum_anywhere(self) -> None:
        import json

        assert "enum" not in json.dumps(strip_unsupported(RoutingDecision.model_json_schema()))


class TestModelTiering:
    def test_complexity_selects_the_configured_model(self) -> None:
        gw = OllamaGateway()
        assert gw.model_for(Complexity.COMPLEX) == "gemma3:4b"
        assert gw.model_for(Complexity.SIMPLE) == "gemma3:1b"

    def test_models_come_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_MODEL_COMPLEX", "llama4:scout")
        monkeypatch.setenv("AI_MODEL_SIMPLE", "tiny:1b")
        reset_settings()
        gw = OllamaGateway()
        assert gw.model_for(Complexity.COMPLEX) == "llama4:scout"
        assert gw.model_for(Complexity.SIMPLE) == "tiny:1b"


class TestStructured:
    """Note: respx must be applied via the `respx_mock` fixture, not as a class
    decorator — a class-level @respx.mock stops pytest collecting the class at all."""

    async def test_happy_path_parses_into_the_schema(self, respx_mock: respx.Router) -> None:
        respx_mock.post(CHAT_URL).mock(
            return_value=chat_reply('{"domains":["crm"],"reasoning":"r","is_cross_domain":false}')
        )
        got = await OllamaGateway().structured(
            system="s", user="u", schema=RoutingDecision, complexity=Complexity.COMPLEX
        )
        assert got.domains == ["crm"]

    async def test_sends_the_requested_model(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(CHAT_URL).mock(return_value=chat_reply('{"domains":["crm"]}'))
        await OllamaGateway().structured(
            system="s", user="u", schema=RoutingDecision, complexity=Complexity.SIMPLE
        )
        assert "gemma3:1b" in route.calls.last.request.read().decode()

    async def test_recovers_json_wrapped_in_prose(self, respx_mock: respx.Router) -> None:
        respx_mock.post(CHAT_URL).mock(
            return_value=chat_reply('Sure! Here you go:\n{"domains":["docs"]}\nHope that helps.')
        )
        got = await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)
        assert got.domains == ["docs"]

    async def test_recovers_fenced_json(self, respx_mock: respx.Router) -> None:
        respx_mock.post(CHAT_URL).mock(return_value=chat_reply('```json\n{"domains":["crm"]}\n```'))
        got = await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)
        assert got.domains == ["crm"]

    async def test_retries_then_succeeds_on_malformed_json(self, respx_mock: respx.Router) -> None:
        respx_mock.post(CHAT_URL).mock(
            side_effect=[chat_reply("not json at all"), chat_reply('{"domains":["crm"]}')]
        )
        got = await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)
        assert got.domains == ["crm"]

    async def test_retry_prompt_tells_the_model_it_sent_bad_json(
        self, respx_mock: respx.Router
    ) -> None:
        route = respx_mock.post(CHAT_URL).mock(
            side_effect=[chat_reply("nope"), chat_reply('{"domains":["crm"]}')]
        )
        await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)
        assert "not valid JSON" in route.calls[1].request.read().decode()

    async def test_raises_when_every_attempt_is_malformed(self, respx_mock: respx.Router) -> None:
        respx_mock.post(CHAT_URL).mock(return_value=chat_reply("still not json"))
        with pytest.raises(LLMError, match="not produced"):
            await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)

    async def test_http_error_is_wrapped(self, respx_mock: respx.Router) -> None:
        respx_mock.post(CHAT_URL).mock(return_value=httpx.Response(503, text="unavailable"))
        with pytest.raises(LLMError):
            await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)

    async def test_the_schema_sent_to_ollama_carries_no_enum(
        self, respx_mock: respx.Router
    ) -> None:
        route = respx_mock.post(CHAT_URL).mock(return_value=chat_reply('{"domains":["crm"]}'))
        await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)
        # Ollama 0.23 returns HTTP 500 for any schema containing `enum`.
        assert "enum" not in route.calls.last.request.read().decode()


class TestOOMFallback:
    async def test_complex_falls_back_to_simple_when_it_will_not_fit(
        self, respx_mock: respx.Router
    ) -> None:
        route = respx_mock.post(CHAT_URL).mock(
            side_effect=[oom(), chat_reply('{"domains":["crm"]}')]
        )
        got = await OllamaGateway().structured(
            system="s", user="u", schema=RoutingDecision, complexity=Complexity.COMPLEX
        )
        assert got.domains == ["crm"]
        # First attempt used the complex model, the retry used the simple one.
        assert "gemma3:4b" in route.calls[0].request.read().decode()
        assert "gemma3:1b" in route.calls[1].request.read().decode()

    async def test_fallback_can_be_disabled(
        self, respx_mock: respx.Router, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_FALLBACK_ON_OOM", "false")
        reset_settings()
        respx_mock.post(CHAT_URL).mock(return_value=oom())
        with pytest.raises(ModelUnavailable, match="does not fit"):
            await OllamaGateway().structured(system="s", user="u", schema=RoutingDecision)

    async def test_simple_model_oom_is_not_swallowed(self, respx_mock: respx.Router) -> None:
        # There is nothing smaller to fall back to, so this must surface.
        respx_mock.post(CHAT_URL).mock(return_value=oom())
        with pytest.raises(ModelUnavailable):
            await OllamaGateway().structured(
                system="s", user="u", schema=RoutingDecision, complexity=Complexity.SIMPLE
            )


class TestEmbed:
    async def test_returns_the_vector(self, respx_mock: respx.Router) -> None:
        respx_mock.post(EMBED_URL).mock(
            return_value=httpx.Response(200, json={"embeddings": [[0.1, 0.2, 0.3]]})
        )
        assert await OllamaGateway().embed("hello") == [0.1, 0.2, 0.3]

    async def test_uses_the_configured_embedding_model(self, respx_mock: respx.Router) -> None:
        route = respx_mock.post(EMBED_URL).mock(
            return_value=httpx.Response(200, json={"embeddings": [[1.0]]})
        )
        await OllamaGateway().embed("x")
        assert settings().embed_model in route.calls.last.request.read().decode()

    async def test_empty_embedding_is_an_error_not_a_silent_zero_vector(
        self, respx_mock: respx.Router
    ) -> None:
        respx_mock.post(EMBED_URL).mock(return_value=httpx.Response(200, json={"embeddings": []}))
        with pytest.raises(LLMError, match="no vector"):
            await OllamaGateway().embed("x")


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        assert cosine_similarity([1.0, 2.0], [1.0, 2.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    @pytest.mark.parametrize(
        ("a", "b"),
        [([], [1.0]), ([1.0], []), ([1.0, 2.0], [1.0]), ([0.0, 0.0], [1.0, 1.0])],
    )
    def test_degenerate_inputs_yield_zero_not_a_crash(self, a: list[float], b: list[float]) -> None:
        assert cosine_similarity(a, b) == 0.0
