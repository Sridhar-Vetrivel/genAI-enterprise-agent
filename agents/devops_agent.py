"""AgentField node: the DevOps specialist.

python -m agents.devops_agent
"""

from __future__ import annotations

from typing import Any

from agents._runtime import make_agent
from psiog_kendra.config import settings
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.specialists.devops_agent import DevOpsAgent

app = make_agent(
    settings().node_devops,
    description="CI/CD specialist: deployments, build status, quality gates.",
    tags=["devops", "github-actions"],
)

_agent = DevOpsAgent(OllamaGateway())


@app.skill()
async def fetch_workflow_runs(query: str) -> list[dict[str, Any]]:
    """Deterministic: pull the workflow runs and their quality gates."""
    runs, _ = await _agent.fetch_runs(query)
    return runs


@app.reasoner()
async def answer_devops_question(query: str) -> AgentResponse:
    """LLM: explain why a deployment passed or failed, gate by gate, with citations."""
    return await _agent.answer(query)


if __name__ == "__main__":
    app.run()
