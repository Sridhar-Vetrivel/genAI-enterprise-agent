"""DevOps specialist — deployments, builds and quality gates.

Skill (deterministic): pull workflow runs and their gate results.
Reasoner (LLM): explain WHY a deployment failed, gate by gate — not just the status code.
"""

from __future__ import annotations

import json
import re
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.domains import DEVOPS
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.sources.devops import DevOpsClient

SYSTEM = """You are the DevOps specialist for the Psiog enterprise copilot.
You answer questions about deployments, builds, and quality gates.

Rules you must not break:
- Use ONLY the workflow-run records given to you. They are the single source of truth.
- Never invent a commit SHA, run id, timestamp or gate result.
- When a deployment failed, name each failing gate and explain what it means -
  do not just report the status.
- When every gate passed, say so and name the gates.
- Every citation must be one of the citation strings supplied to you, copied verbatim.
- Be concise: 2-4 sentences.
"""


def infer_service(query: str, known_services: list[str]) -> str | None:
    """Which service is this query about?

    Candidates come from the source records themselves, so no service name is
    hardcoded here. This only narrows the API pull; it never decides the answer.
    """
    q = query.lower()
    for service in known_services:
        # "payments-service" should match a query that says "payments".
        stem = service.lower().replace("-service", "").strip()
        if stem and re.search(rf"\b{re.escape(stem)}\b", q):
            return service
    return None


class DevOpsAgent:
    """The devops specialist. Its node id comes from NODE_DEVOPS_AGENT."""

    domain = DEVOPS

    def __init__(self, llm: LLMGateway, client: DevOpsClient | None = None) -> None:
        cfg = settings()
        self.node_id = cfg.node_devops
        self._max_records = cfg.max_records_in_prompt
        self._llm = llm
        self._client = client or DevOpsClient()

    async def fetch_runs(self, query: str) -> tuple[list[dict[str, Any]], list[str]]:
        """Skill: pull the workflow runs relevant to this query."""
        all_runs, all_citations = await self._client.fetch(None)
        service = infer_service(query, [str(r.get("service", "")) for r in all_runs])

        runs, citations = (all_runs, all_citations)
        if service:
            narrowed, narrowed_citations = await self._client.fetch(service)
            if narrowed:
                runs, citations = narrowed, narrowed_citations
        return runs[: self._max_records], citations[: self._max_records]

    async def answer(self, query: str) -> AgentResponse:
        """Reasoner: produce a grounded, cited answer."""
        runs, citations = await self.fetch_runs(query)
        if not runs:
            return AgentResponse(
                answer="No deployment or build records matched this question.",
                citations=[],
                confidence="low",
            )

        # Surface the failing gates explicitly so the model does not have to find them.
        enriched = [dict(r, failing_gates=DevOpsClient.failed_gates(r)) for r in runs]
        user = (
            f"Question: {query}\n\n"
            f"Workflow-run records (the only facts you may use):\n"
            f"{json.dumps(enriched, indent=2)}\n\n"
            f"Citation strings you may use, verbatim:\n"
            + "\n".join(f"- {c}" for c in citations)
            + "\n\nAnswer the question from these records and cite the runs you used."
        )
        try:
            response = await self._llm.structured(
                system=SYSTEM, user=user, schema=AgentResponse, complexity=Complexity.COMPLEX
            )
        except LLMError:
            top = runs[0]
            gates = DevOpsClient.failed_gates(top)
            verdict = (
                "passed all quality gates"
                if not gates
                else "failed these gates: " + ", ".join(g["name"] for g in gates)
            )
            return AgentResponse(
                answer=f"Deployment of {top.get('service')} ({top.get('commit_sha')}) {verdict}.",
                citations=citations[:1],
                confidence="low",
            )
        response.citations = [c for c in response.citations if c in citations] or citations[:1]
        return response
