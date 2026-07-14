"""Run the 12 test queries through the control plane so each one leaves a trace to screenshot.

    python -m scripts.trace_queries              # all 12
    python -m scripts.trace_queries --only 3,9   # just those
    python -m scripts.trace_queries --resume     # skip the ones already traced

Every query goes through `coordinator.ask`, not straight to a specialist. That is the whole
point: the coordinator classifies intent with the LLM, dispatches to the specialists with
`app.call()` -- which the control plane records as a DAG -- and synthesises one cited answer.
A trace of `data-agent.answer_data_question` shows one agent answering; a trace of
`coordinator.ask` shows the architecture.

Writes `data/trace_manifest.json` and `docs/qa/traces.md`: query id -> execution id, so you
can find each run in the UI instead of hunting through a list of hashes.

Two things this has to survive, both learned the hard way:

* A node can be evicted from the registry mid-run (its heartbeat stops during a long
  inference) while its process stays alive and its port keeps answering. Every query after
  that fails. So the fleet is health-checked before each query and restarted if broken.
* Local CPU inference is slow -- 1-2 minutes for a single-domain query, longer for the
  cross-domain ones that fan out to four specialists. The run is checkpointed after every
  query, so a killed run is not a lost run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from typing import Any

import httpx

from agents.health import check
from psiog_kendra.config import settings
from psiog_kendra.qa.test_queries import TEST_QUERIES, TestQuery

MANIFEST = "data/trace_manifest.json"
TRACES_PAGE = "docs/qa/traces.md"


def _execute_url(reasoner: str) -> str:
    cfg = settings()
    return f"{cfg.agentfield_server.rstrip('/')}{cfg.agentfield_execute_path}/{reasoner}"


async def _fleet_is_healthy() -> bool:
    return all(node.ok for node in await check())


async def _ensure_fleet() -> None:
    """Restart the fleet if any node is dead or has been evicted from the registry."""
    if await _fleet_is_healthy():
        return
    print("  ! fleet unhealthy -- restarting the nodes", flush=True)
    subprocess.run(["make", "agents-down"], check=False, capture_output=True)
    subprocess.run(["make", "agents"], check=False, capture_output=True)
    if not await _fleet_is_healthy():
        raise SystemExit("fleet will not come up. Check `make up` and data/agents/*.log")


async def trace_one(client: httpx.AsyncClient, q: TestQuery, timeout: float) -> dict[str, Any]:
    """Run one query through coordinator.ask and record where its trace landed."""
    started = time.monotonic()
    try:
        resp = await client.post(
            _execute_url(f"{settings().node_coordinator}.ask"),
            json={"input": {"query": q.query}},
            timeout=timeout,
        )
        body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "id": q.id,
            "query": q.query,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "seconds": round(time.monotonic() - started, 1),
        }

    result = body.get("result") or {}
    return {
        "id": q.id,
        "query": q.query,
        "expected_domains": sorted(q.expected_domains),
        "status": body.get("status", "unknown"),
        "execution_id": body.get("execution_id", ""),
        "run_id": body.get("run_id", ""),
        "error": body.get("error", ""),
        "domains": sorted(result.get("domains") or []),
        "answer": result.get("answer", ""),
        "citations": result.get("citations") or [],
        "seconds": round(time.monotonic() - started, 1),
    }


def _load() -> dict[int, dict[str, Any]]:
    try:
        with open(MANIFEST) as fh:
            return {int(t["id"]): t for t in json.load(fh)["traces"]}
    except (OSError, ValueError, KeyError):
        return {}


def _save(traces: dict[int, dict[str, Any]]) -> None:
    ordered = [traces[i] for i in sorted(traces)]
    with open(MANIFEST, "w") as fh:
        json.dump({"traces": ordered}, fh, indent=2)
    with open(TRACES_PAGE, "w") as fh:
        fh.write(_render(ordered))


def _render(traces: list[dict[str, Any]]) -> str:
    cfg = settings()
    ui = f"{cfg.agentfield_server.rstrip('/')}/ui/"
    good = [t for t in traces if t["status"] == "succeeded"]

    lines = [
        "# Control-Plane Traces — one execution per test query",
        "",
        "Each of the 12 test queries was run through `coordinator.ask` on the AgentField",
        "control plane. The coordinator classifies intent with the LLM, dispatches to the",
        "specialist agents with `app.call()` (recorded as a DAG), and synthesises one cited",
        "answer — so a single trace evidences routing, the multi-agent architecture, and",
        "grounding together.",
        "",
        f"Open **<{ui}>** and find the execution by its ID.",
        "",
        f"Traced: **{len(good)} of {len(TEST_QUERIES)} succeeded**.",
        "",
        "## 📸 How to take the screenshot",
        "",
        f"1. Open <{ui}> and select the execution ID for the query you want.",
        "2. Stay on the **Inputs & Outputs** tab: the input query on the left, the",
        "   `answer` / `citations` / `confidence` on the right. The citation is the proof",
        "   the answer is grounded — make sure it is readable.",
        "3. Capture the **whole browser window**, including the reasoner name, the",
        "   `data-agent`/`coordinator` node badge, the green **Succeeded** status and the",
        "   duration. Full-size, no crop, no collage.",
        "4. For the cross-domain queries (Q9–Q12) also capture the **Debug**/DAG view: it",
        "   shows the coordinator calling more than one specialist, which is the single",
        "   clearest picture of the multi-agent design.",
        "",
        "## Executions",
        "",
        "| Q | Query | Routed to | Status | Time | Execution ID |",
        "|---|---|---|---|---|---|",
    ]
    for t in traces:
        mark = "✅" if t["status"] == "succeeded" else "❌"
        domains = ", ".join(t.get("domains") or []) or "—"
        exec_id = t.get("execution_id") or "—"
        lines.append(
            f"| Q{t['id']:02d} | {t['query']} | `{domains}` | {mark} {t['status']} "
            f"| {t['seconds']}s | `{exec_id}` |"
        )

    lines += ["", "## Answers as traced", ""]
    for t in traces:
        lines += [f"### Q{t['id']:02d} — {t['query']}", ""]
        if t["status"] != "succeeded":
            lines += [f"> **{t['status']}** — {t.get('error') or 'no result'}", ""]
            continue
        lines += [
            f"- **Execution ID:** `{t['execution_id']}`",
            f"- **Run ID:** `{t['run_id']}`",
            f"- **Routed to:** `{', '.join(t['domains']) or '—'}` "
            f"(expected `{', '.join(t['expected_domains'])}`)",
            "",
            f"{t['answer']}",
            "",
            "**Citations**",
            "",
        ]
        lines += [f"- {c}" for c in t["citations"]] or ["- _none_"]
        lines.append("")
    return "\n".join(lines) + "\n"


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="comma-separated query ids, e.g. 3,9")
    parser.add_argument("--resume", action="store_true", help="skip queries already traced")
    args = parser.parse_args()

    traces = _load()
    wanted = TEST_QUERIES
    if args.only:
        ids = {int(i) for i in args.only.split(",")}
        wanted = tuple(q for q in TEST_QUERIES if q.id in ids)
    if args.resume:
        done = {i for i, t in traces.items() if t["status"] == "succeeded"}
        wanted = tuple(q for q in wanted if q.id not in done)
        if done:
            print(f"resuming: {len(done)} already traced, {len(wanted)} to go\n")

    if not wanted:
        print("nothing to do -- every requested query is already traced")
        return 0

    timeout = float(settings().query_timeout_seconds)
    print(
        f"tracing {len(wanted)} queries through coordinator.ask on "
        f"{settings().agentfield_server}\n"
        f"local CPU inference: expect 1-2 min for a single-domain query, longer for the "
        f"cross-domain ones\n"
    )

    async with httpx.AsyncClient() as client:
        for n, q in enumerate(wanted, 1):
            await _ensure_fleet()
            print(f"[{n}/{len(wanted)}] Q{q.id:02d}  {q.query}", flush=True)
            trace = await trace_one(client, q, timeout)
            traces[q.id] = trace
            _save(traces)  # checkpoint: a killed run is not a lost run

            if trace["status"] == "succeeded":
                routed = ", ".join(trace["domains"]) or "—"
                print(
                    f"         ✅ {trace['seconds']}s  routed={routed}  "
                    f"{len(trace['citations'])} citation(s)  {trace['execution_id']}\n",
                    flush=True,
                )
            else:
                print(f"         ❌ {trace['status']}: {trace.get('error')}\n", flush=True)

    good = sum(1 for t in traces.values() if t["status"] == "succeeded")
    print(f"{good}/{len(traces)} traced. Manifest: {MANIFEST}  Page: {TRACES_PAGE}")
    print(f"Open {settings().agentfield_server.rstrip('/')}/ui/ to screenshot them.")
    return 0 if good == len(traces) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
