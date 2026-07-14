"""AgentField node: the Data Platform specialist.

    python -m agents.data_agent

    curl -X POST http://localhost:8080/api/v1/execute/data-agent.answer_data_question \
      -H "Content-Type: application/json" \
      -d '{"input": {"query": "Did yesterday'\''s ETL pipeline run successfully?"}}'
"""

from __future__ import annotations

from typing import Any

from agents._runtime import make_agent, serve
from psiog_kendra.config import settings
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.specialists.data_agent import DataAgent

app = make_agent(
    settings().node_data,
    description="Databricks specialist: pipeline runs, ETL job history, job failures.",
    tags=["data-platform", "databricks"],
)

_agent = DataAgent(OllamaGateway())


@app.skill()
async def fetch_job_runs(query: str) -> list[dict[str, Any]]:
    """Deterministic: pull the Databricks job-run records relevant to a query."""
    runs, _ = await _agent.fetch_runs(query)
    return runs


@app.reasoner()
async def answer_data_question(query: str) -> AgentResponse:
    """LLM: turn the run records into a grounded, cited answer."""
    return await _agent.answer(query)


if __name__ == "__main__":
    serve(app)
