"""Data Platform specialist — Databricks pipelines and job runs.

Skill (deterministic): pull job-run history from Databricks.
Reasoner (LLM): turn the raw run records into a readable, cited answer.

The reasoner is told the run records are the ONLY permitted source of fact. Anything it
cannot read off a record it must decline, which is what keeps the hallucination rate down.
"""

from __future__ import annotations

import json
import re
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.domains import DATA_PLATFORM
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.sources.databricks import DatabricksClient

SYSTEM = """You are the Data Platform specialist for the Psiog enterprise copilot.
You answer questions about Databricks pipelines, ETL jobs and job runs.

Rules you must not break:
- Use ONLY the job-run records given to you. They are the single source of truth.
- Never invent a job name, run id, timestamp, row count or error message.
- If the records do not contain the answer, say so plainly.
- Quote the exact error message when explaining a failure.
- Every citation must be one of the citation strings supplied to you, copied verbatim.
- Be concise: 2-4 sentences.
"""


def infer_job_name(query: str, known_jobs: list[str]) -> str | None:
    """Which Databricks job is this query about?

    Candidates come from the job records themselves, so no job name is hardcoded here.
    A job name like `ingestion_raw_events` is matched on any of its word parts, so
    "the ingestion job" and "raw events" both resolve to it. This only narrows the API
    pull; it never decides the answer.
    """
    q = query.lower()
    best: tuple[int, str] | None = None
    for job in known_jobs:
        name = job.lower()
        if not name:
            continue
        parts = [p for p in re.split(r"[_\-\s]+", name) if len(p) > 2]
        hits = sum(1 for p in parts if p in q)
        if name in q:
            hits += len(parts)  # a full-name match always outranks a partial one
        if hits and (best is None or hits > best[0]):
            best = (hits, job)
    return best[1] if best else None


def wants_failure(query: str) -> bool:
    """True when the user is asking about an error/failure specifically."""
    return bool(re.search(r"\b(fail|failed|failure|error|broke|broken|crash)\w*\b", query.lower()))


class DataAgent:
    """The data-platform specialist. Its node id comes from NODE_DATA_AGENT."""

    domain = DATA_PLATFORM

    def __init__(self, llm: LLMGateway, client: DatabricksClient | None = None) -> None:
        cfg = settings()
        self.node_id = cfg.node_data
        self._max_records = cfg.max_records_in_prompt
        self._llm = llm
        self._client = client or DatabricksClient()

    async def fetch_runs(self, query: str) -> tuple[list[dict[str, Any]], list[str]]:
        """Skill: pull the run records relevant to this query."""
        all_runs, all_citations = await self._client.fetch(None)
        job = infer_job_name(query, [str(r.get("job_name", "")) for r in all_runs])

        runs, citations = (all_runs, all_citations)
        if job:
            narrowed, narrowed_citations = await self._client.fetch(job)
            # If the named job has no history, keep the full history rather than
            # answering "nothing found" when the platform does have data.
            if narrowed:
                runs, citations = narrowed, narrowed_citations
        if wants_failure(query):
            failed = [r for r in runs if str(r.get("result_state", "")).upper() == "FAILED"]
            if failed:
                keep = {r["run_id"] for r in failed}
                pairs = [
                    (r, c) for r, c in zip(runs, citations, strict=True) if r["run_id"] in keep
                ]
                runs = [r for r, _ in pairs]
                citations = [c for _, c in pairs]
        return runs[: self._max_records], citations[: self._max_records]

    async def answer(self, query: str) -> AgentResponse:
        """Reasoner: produce a grounded, cited answer."""
        runs, citations = await self.fetch_runs(query)
        if not runs:
            return AgentResponse(
                answer="No Databricks job runs matched this question.",
                citations=[],
                confidence="low",
            )

        user = (
            f"Question: {query}\n\n"
            f"Databricks job-run records (the only facts you may use):\n"
            f"{json.dumps(runs, indent=2)}\n\n"
            f"Citation strings you may use, verbatim:\n"
            + "\n".join(f"- {c}" for c in citations)
            + "\n\nAnswer the question from these records and cite the runs you used."
        )
        try:
            response = await self._llm.structured(
                system=SYSTEM, user=user, schema=AgentResponse, complexity=Complexity.COMPLEX
            )
        except LLMError:
            # Never fabricate on an LLM failure — degrade to the raw grounded facts.
            top = runs[0]
            return AgentResponse(
                answer=(
                    f"Job {top.get('job_name')} run {top.get('run_id')} finished with state "
                    f"{top.get('result_state')}."
                ),
                citations=citations[:1],
                confidence="low",
            )
        # The model may still paraphrase a citation; keep only ones we actually supplied.
        response.citations = [c for c in response.citations if c in citations] or citations[:1]
        return response
