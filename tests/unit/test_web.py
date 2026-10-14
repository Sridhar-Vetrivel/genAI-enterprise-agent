"""The web UI's backend: status, the ask endpoint, and the single-flight lock.

Runs fully offline: a FakeLLM-backed Coordinator is injected directly into the module's
lazy singleton, so these tests never touch Ollama or require `make index` to have run.
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

import psiog_kendra.web as web
from psiog_kendra.coordinator import Coordinator
from psiog_kendra.schemas import RoutingDecision
from tests.conftest import FakeLLM, answer, routing
from tests.unit.test_coordinator import StubSpecialist


@pytest.fixture(autouse=True)
def _reset_copilot():
    """Each test gets a fresh module-level singleton and lock — state must not leak."""
    web._copilot = None
    web._lock = asyncio.Lock()
    yield
    web._copilot = None


def _install(fake_llm: FakeLLM, **specialists: StubSpecialist) -> None:
    by_domain = {s.domain: s for s in specialists.values()}
    web._copilot = Coordinator(fake_llm, by_domain)  # type: ignore[arg-type]


class TestPage:
    def test_serves_the_chat_page(self) -> None:
        client = TestClient(web.app)
        r = client.get("/")
        assert r.status_code == 200
        assert "Psiog Kendra" in r.text
        assert "<script>" in r.text  # it's the real page, not an empty shell


class TestStatus:
    def test_reports_the_configured_models_and_idle(self) -> None:
        client = TestClient(web.app)
        r = client.get("/api/status")
        body = r.json()
        assert body["busy"] is False
        assert "model_complex" in body and "model_simple" in body


class TestAsk:
    def test_rejects_an_empty_question(self) -> None:
        client = TestClient(web.app)
        r = client.post("/api/ask", json={"query": "   "})
        assert r.status_code == 400
        assert "error" in r.json()

    def test_routes_and_returns_citations_and_agent_name(self, fake_llm: FakeLLM) -> None:
        fake_llm.responses[RoutingDecision] = routing("crm")
        _install(
            fake_llm, crm=StubSpecialist("crm", answer("Acme is in Negotiation", "CRM deal #1"))
        )

        client = TestClient(web.app)
        r = client.post("/api/ask", json={"query": "What is the deal status for Acme?"})

        assert r.status_code == 200
        body = r.json()
        assert body["answer"] == "Acme is in Negotiation"
        assert body["citations"] == ["CRM deal #1"]
        assert body["agents"] == ["crm-agent"]
        assert body["was_queued"] is False
        assert body["elapsed_seconds"] >= 0

    def test_an_unknown_field_is_rejected_not_silently_ignored(self, fake_llm: FakeLLM) -> None:
        # Pydantic's extra="forbid" on every schema is a project rule (CLAUDE.md #4) -
        # the request body is no exception.
        client = TestClient(web.app)
        r = client.post("/api/ask", json={"query": "hi", "evil": "ignored?"})
        assert r.status_code == 422

    def test_a_coordinator_failure_is_a_clean_502_with_a_hint_not_a_crash(
        self, fake_llm: FakeLLM
    ) -> None:
        fake_llm.responses[RoutingDecision] = Exception("ollama unreachable")
        _install(fake_llm, crm=StubSpecialist("crm", answer("unused")))

        client = TestClient(web.app)
        r = client.post("/api/ask", json={"query": "anything"})

        assert r.status_code == 502
        body = r.json()
        assert "ollama unreachable" in body["error"]
        assert "hint" in body

    def test_an_answer_with_no_citations_still_comes_back_cleanly(self, fake_llm: FakeLLM) -> None:
        # The web layer must not assume every answer is grounded - the frontend is what
        # flags "no citations" to the user; the API just has to pass an empty list through.
        fake_llm.responses[RoutingDecision] = routing("crm")
        _install(fake_llm, crm=StubSpecialist("crm", answer("unverified text")))

        client = TestClient(web.app)
        r = client.post("/api/ask", json={"query": "anything"})

        assert r.status_code == 200
        assert r.json()["citations"] == []


class TestSingleFlight:
    async def test_a_second_ask_waits_for_the_first_rather_than_racing_it(
        self, fake_llm: FakeLLM
    ) -> None:
        # gemma3:4b needs ~4 GiB free RAM for one generation (CLAUDE.md); a second
        # concurrent call must queue behind the lock, not run alongside the first, or both
        # would contend for the same RAM. Drives the real endpoint function end to end
        # (not the lock in isolation) so it proves what actually happens on a real request.
        fake_llm.responses[RoutingDecision] = routing("crm")
        delay = 0.12
        _install(fake_llm, crm=StubSpecialist("crm", answer("ok"), delay=delay))

        start = time.monotonic()
        r1, r2 = await asyncio.gather(
            web.ask(web.AskRequest(query="first")),
            web.ask(web.AskRequest(query="second")),
        )
        elapsed = time.monotonic() - start

        # Serialized: two delay-long specialist calls back to back, not overlapped.
        assert elapsed >= delay * 1.8, f"ran in {elapsed:.3f}s - looks parallel, not serialized"

        b1, b2 = json.loads(r1.body), json.loads(r2.body)
        assert b1["answer"] == b2["answer"] == "ok"
        # Exactly one of the two found the lock already held - which one depends on
        # asyncio's scheduling order, not on anything this test should assume.
        assert {b1["was_queued"], b2["was_queued"]} == {True, False}
