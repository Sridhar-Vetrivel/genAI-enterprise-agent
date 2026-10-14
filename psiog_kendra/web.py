"""A ChatGPT/Claude-style web UI for the copilot — in-process, same path as `make ask`.

    make web      # http://localhost:8090

This is the Track A path from docs/DEMO_RUNBOOK.md: it calls Coordinator.ask() directly,
in-process, with no AgentField control plane and no agent nodes required — just Ollama
serving and the local RAG index built (`make index`). For the full multi-agent
control-plane path (Track B), use `make up && make agents` and the AgentField UI instead.

One request is answered at a time. `gemma3:4b` needs ~4 GiB of free RAM for one generation;
a second concurrent one does not run faster in parallel, it risks starving or OOM-killing the
first (see CLAUDE.md's RAM note). A single asyncio.Lock makes a second question queue behind
the first rather than race it for memory.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict

from psiog_kendra.app import build_copilot
from psiog_kendra.config import settings
from psiog_kendra.coordinator import Coordinator
from psiog_kendra.domains import agent_for

app = FastAPI(title="Psiog Kendra")

_PAGE = (Path(__file__).parent / "static" / "chat.html").read_text()

_copilot: Coordinator | None = None
_lock = asyncio.Lock()


def _get_copilot() -> Coordinator:
    # Built once, lazily, on first request — not at import time, so `uvicorn --reload`
    # and a bare `import psiog_kendra.web` (e.g. for tests) don't eagerly load Ollama.
    global _copilot
    if _copilot is None:
        _copilot = build_copilot()
    return _copilot


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _PAGE


@app.get("/api/status")
async def status() -> dict:
    cfg = settings()
    return {
        "model_complex": cfg.model_complex,
        "model_simple": cfg.model_simple,
        "busy": _lock.locked(),
    }


@app.post("/api/ask")
async def ask(req: AskRequest) -> JSONResponse:
    query = req.query.strip()
    if not query:
        return JSONResponse({"error": "Ask something first."}, status_code=400)

    queued = _lock.locked()
    async with _lock:
        started = time.monotonic()
        try:
            response = await _get_copilot().ask(query)
        except Exception as exc:  # noqa: BLE001 - surface it to the chat, don't 500 blindly
            return JSONResponse(
                {
                    "error": f"{type(exc).__name__}: {exc}",
                    "hint": "Is Ollama running (`ollama serve`) with gemma3:4b pulled, "
                    "and has `make index` been run at least once?",
                },
                status_code=502,
            )
        elapsed = time.monotonic() - started

    agents = [agent_for(d) for d in response.domains_used] or ["none"]
    return JSONResponse(
        {
            "answer": response.answer,
            "citations": response.citations,
            "agents": agents,
            "routing_reasoning": response.routing_reasoning,
            "elapsed_seconds": round(elapsed, 1),
            "was_queued": queued,
        }
    )
