"""DevOps source client — deployments, build status and quality gates.

Live path: GitHub Actions API (`/repos/{repo}/actions/runs`).
Mock path: data/mock/devops.json.
"""

from __future__ import annotations

from typing import Any

import httpx

from psiog_kendra.config import settings
from psiog_kendra.sources.base import SourceError, get_json, load_mock

CITATION_PREFIX = "GitHub Actions"


def _citation(run: dict[str, Any]) -> str:
    return (
        f"{CITATION_PREFIX} run #{run['run_id']} "
        f"({run['workflow_name']}, commit {run['commit_sha']})"
    )


class DevOpsClient:
    """Reads workflow runs and their quality gates."""

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._cfg = settings()
        self._http = http

    async def _runs(self) -> list[dict[str, Any]]:
        cfg = self._cfg
        if cfg.use_mock_sources:
            return list(load_mock("devops")["workflow_runs"])
        if not cfg.github_token:
            raise SourceError("GITHUB_TOKEN not set and mocks disabled")
        payload = await get_json(
            cfg.github_runs_url,
            headers={
                "Authorization": f"Bearer {cfg.github_token}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": cfg.github_page_size},
            client=self._http,
        )
        return list(payload.get("workflow_runs", []))

    async def list_runs(self, service: str | None = None) -> list[dict[str, Any]]:
        """Most-recent-first deployment history, optionally narrowed to one service."""
        runs = await self._runs()
        if service:
            needle = service.strip().lower().replace("-service", "").replace(" ", "")
            runs = [
                r
                for r in runs
                if needle
                in str(r.get("service", "")).lower().replace("-service", "").replace(" ", "")
            ]
        return sorted(runs, key=lambda r: str(r.get("deployed_at", "")), reverse=True)

    async def latest_run(self, service: str | None = None) -> dict[str, Any] | None:
        runs = await self.list_runs(service)
        return runs[0] if runs else None

    @staticmethod
    def failed_gates(run: dict[str, Any]) -> list[dict[str, Any]]:
        """Only the gates that did not pass — what the reasoner must explain."""
        return [g for g in run.get("quality_gates", []) if g.get("status") != "passed"]

    async def fetch(self, service: str | None = None) -> tuple[list[dict[str, Any]], list[str]]:
        """Return (runs, citations) — the grounding payload for the devops agent."""
        runs = await self.list_runs(service)
        return runs, [_citation(r) for r in runs]
