"""Databricks source client — job runs and pipeline status.

Live path: Databricks Jobs API 2.1 (`/api/2.1/jobs/runs/list`).
Mock path: data/mock/databricks.json.
"""

from __future__ import annotations

from typing import Any

import httpx

from psiog_kendra.config import settings
from psiog_kendra.sources.base import SourceError, get_json, load_mock

CITATION_PREFIX = "Databricks"


def _citation(run: dict[str, Any]) -> str:
    return f"{CITATION_PREFIX} Job #{run['job_id']} ({run['job_name']}) run #{run['run_id']}"


class DatabricksClient:
    """Reads job-run history from Databricks (or the fixture when mocked)."""

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._cfg = settings()
        self._http = http

    async def _runs(self) -> list[dict[str, Any]]:
        cfg = self._cfg
        if cfg.use_mock_sources:
            return list(load_mock("databricks")["runs"])
        if not cfg.databricks_host or not cfg.databricks_token:
            raise SourceError("DATABRICKS_HOST/DATABRICKS_TOKEN not set and mocks disabled")
        payload = await get_json(
            cfg.databricks_runs_url,
            headers={"Authorization": f"Bearer {cfg.databricks_token}"},
            params={"limit": cfg.databricks_page_size, "expand_tasks": "false"},
            client=self._http,
        )
        return list(payload.get("runs", []))

    async def list_runs(self, job_name: str | None = None) -> list[dict[str, Any]]:
        """Most-recent-first run history, optionally narrowed to one job."""
        runs = await self._runs()
        if job_name:
            needle = job_name.strip().lower()
            runs = [r for r in runs if needle in str(r.get("job_name", "")).lower()]
        return sorted(runs, key=lambda r: str(r.get("start_time", "")), reverse=True)

    async def latest_run(self, job_name: str | None = None) -> dict[str, Any] | None:
        """The most recent run, or None when nothing matches."""
        runs = await self.list_runs(job_name)
        return runs[0] if runs else None

    async def last_failed_run(self, job_name: str | None = None) -> dict[str, Any] | None:
        """The most recent FAILED run — backs 'what was the error in the last failed job?'."""
        runs = await self.list_runs(job_name)
        failed = [r for r in runs if str(r.get("result_state", "")).upper() == "FAILED"]
        return failed[0] if failed else None

    async def fetch(self, job_name: str | None = None) -> tuple[list[dict[str, Any]], list[str]]:
        """Return (runs, citations) — the grounding payload for the data agent."""
        runs = await self.list_runs(job_name)
        return runs, [_citation(r) for r in runs]
