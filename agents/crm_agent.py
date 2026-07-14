"""AgentField node: the CRM specialist.

python -m agents.crm_agent
"""

from __future__ import annotations

from typing import Any

from agents._runtime import make_agent, serve
from psiog_kendra.config import settings
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.specialists.crm_agent import CRMAgent

app = make_agent(
    settings().node_crm,
    description="CRM specialist: accounts, deals, deal stages, owners, contacts.",
    tags=["crm", "customer"],
)

_agent = CRMAgent(OllamaGateway())


@app.skill()
async def fetch_crm_records(query: str) -> dict[str, Any]:
    """Deterministic: pull the account, deal and contact records for a customer."""
    records, _ = await _agent.fetch_records(query)
    return records


@app.reasoner()
async def answer_crm_question(query: str) -> AgentResponse:
    """LLM: answer the customer question from the records, flagging stale data."""
    return await _agent.answer(query)


if __name__ == "__main__":
    serve(app)
