"""Durable execution history, independent of the control plane's own retention.

Confirmed live against this control plane image: `POST /api/v1/settings/webhooks` 404s and
the SSE stream at `/api/ui/v1/executions/events` never responds -- both documented in the
control plane's own knowledge base (`GET /api/v1/agentic/kb/articles/...`), neither actually
wired up here. And the control plane does not keep what it has: an execution traced on
2026-09-03 came back `{"error": "execution not found"}` by 2026-10-13, six weeks later.

So this captures by pulling, not by a push subscription the control plane doesn't honour:
`GET /api/ui/v1/workflows/{run_id}/dag` returns the whole execution tree (the coordinator and
every specialist it called via `app.call()`), and `GET /api/v1/executions/{id}` returns one
node's full result. Walking the DAG and fetching each node's result captures the entire
multi-agent trace, not just the coordinator's synthesised answer.

    python -m scripts.execution_history --from-manifest   # backfill every run_id already
                                                            # traced in data/trace_manifest.json
    python -m scripts.execution_history --run-id <run_id> # capture one ad-hoc run (the id is
                                                            # in the execute response, or in
                                                            # the control-plane UI)
    python -m scripts.execution_history --list            # print what's recorded so far

Writes data/execution_history.db (sqlite -- queryable with any tool, indefinitely) and mirrors
every row into data/execution_history.json (plain text, git-diffable, no tooling needed to
read it). Upserts on execution_id, so re-running this is always safe.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from psiog_kendra.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    node TEXT NOT NULL,
    reasoner TEXT NOT NULL,
    status TEXT NOT NULL,
    parent_execution_id TEXT,
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    result_json TEXT,
    captured_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _connect() -> sqlite3.Connection:
    path = settings().history_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def _flatten(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Walk a DAG node and its children into a flat list, dropping the nested shape."""
    rows = [{k: v for k, v in node.items() if k != "children"}]
    for child in node.get("children") or []:
        rows.extend(_flatten(child))
    return rows


async def _fetch_result(client: httpx.AsyncClient, execution_id: str) -> dict[str, Any] | None:
    cfg = settings()
    url = f"{cfg.agentfield_server.rstrip('/')}{cfg.agentfield_executions_path}/{execution_id}"
    try:
        resp = await client.get(url, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


def _export_json(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT * FROM executions ORDER BY started_at").fetchall()
    out = []
    for row in rows:
        rec = dict(row)
        raw = rec.pop("result_json", None)
        rec["result"] = json.loads(raw) if raw else None
        out.append(rec)
    settings().history_export_path.write_text(json.dumps(out, indent=2))


async def capture_run(client: httpx.AsyncClient, run_id: str) -> int:
    """Pull the full DAG for one run_id and upsert every node it contains."""
    cfg = settings()
    dag_url = f"{cfg.agentfield_server.rstrip('/')}{cfg.agentfield_dag_path.format(run_id=run_id)}"
    resp = await client.get(dag_url, timeout=30.0)
    resp.raise_for_status()
    nodes = _flatten(resp.json()["dag"])

    conn = _connect()
    captured_at = _now_iso()
    for node in nodes:
        full = await _fetch_result(client, node["execution_id"])
        result_json = json.dumps(full.get("result")) if full else None
        conn.execute(
            """INSERT INTO executions
               (execution_id, run_id, node, reasoner, status, parent_execution_id,
                started_at, completed_at, duration_ms, result_json, captured_at)
               VALUES (:execution_id, :run_id, :node, :reasoner, :status,
                       :parent_execution_id, :started_at, :completed_at, :duration_ms,
                       :result_json, :captured_at)
               ON CONFLICT(execution_id) DO UPDATE SET
                 status = excluded.status,
                 completed_at = excluded.completed_at,
                 duration_ms = excluded.duration_ms,
                 result_json = excluded.result_json,
                 captured_at = excluded.captured_at""",
            {
                "execution_id": node["execution_id"],
                "run_id": node["workflow_id"],
                "node": node["agent_node_id"],
                "reasoner": node["reasoner_id"],
                "status": node["status"],
                "parent_execution_id": node.get("parent_execution_id"),
                "started_at": node.get("started_at"),
                "completed_at": node.get("completed_at"),
                "duration_ms": node.get("duration_ms"),
                "result_json": result_json,
                "captured_at": captured_at,
            },
        )
    conn.commit()
    _export_json(conn)
    conn.close()
    return len(nodes)


def _manifest_run_ids(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text())
    seen: list[str] = []
    for trace in data["traces"]:
        run_id = trace.get("run_id")
        if run_id and run_id not in seen:
            seen.append(run_id)
    return seen


def _print_history() -> None:
    conn = _connect()
    rows = conn.execute(
        "SELECT run_id, node, reasoner, status, duration_ms, captured_at "
        "FROM executions ORDER BY started_at"
    ).fetchall()
    conn.close()
    if not rows:
        print("nothing recorded yet -- run with --from-manifest or --run-id first")
        return
    for r in rows:
        print(
            f"{r['run_id']}  {r['node']:<14} {r['reasoner']:<28} "
            f"{r['status']:<10} {r['duration_ms'] or 0:>7}ms  captured {r['captured_at']}"
        )
    print(f"\n{len(rows)} execution(s) in {settings().history_db_path}")


async def _capture(run_ids: list[str]) -> int:
    total = 0
    async with httpx.AsyncClient() as client:
        for run_id in run_ids:
            try:
                n = await capture_run(client, run_id)
                print(f"{run_id}: captured {n} execution(s)")
                total += n
            except httpx.HTTPStatusError as exc:
                print(f"{run_id}: FAILED -- {exc}")
    return total


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--from-manifest",
        action="store_true",
        help="backfill every run_id already traced in data/trace_manifest.json",
    )
    group.add_argument("--run-id", help="capture one run_id you already have")
    group.add_argument("--list", action="store_true", help="print everything recorded so far")
    args = parser.parse_args()

    if args.list:
        _print_history()
        return 0

    run_ids = (
        _manifest_run_ids(Path("data/trace_manifest.json")) if args.from_manifest else [args.run_id]
    )
    total = await _capture(run_ids)
    print(f"\ndone -- {total} execution(s) now in {settings().history_db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
