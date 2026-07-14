"""AgentField node: the Coordinator.

Routes with an LLM, dispatches to the specialists through the control plane via
`app.call()` (so every query is traced as a DAG), then synthesises one cited answer.

    python -m agents.coordinator

    curl -X POST http://localhost:8080/api/v1/execute/coordinator.ask \
      -H "Content-Type: application/json" \
      -d '{"input": {"query": "Did last night'\''s pipeline failure affect any CRM sync?"}}'
"""

from __future__ import annotations

from agents._runtime import make_agent, serve
from psiog_kendra.config import settings
from psiog_kendra.coordinator import Coordinator
from psiog_kendra.domains import agent_for
from psiog_kendra.llm import OllamaGateway
from psiog_kendra.schemas import AgentResponse, CopilotResponse, RoutingDecision

cfg = settings()

app = make_agent(
    cfg.node_coordinator,
    description="Routes enterprise questions to specialist agents and synthesises the answer.",
    tags=["coordinator", "router"],
)

_llm = OllamaGateway()

# Which reasoner on each specialist node answers a question.
REASONER = {
    cfg.node_data: "answer_data_question",
    cfg.node_devops: "answer_devops_question",
    cfg.node_crm: "answer_crm_question",
    cfg.node_docs: "answer_docs_question",
}


class RemoteSpecialist:
    """A specialist reached through the AgentField control plane.

    Satisfies the same protocol as the in-process specialists, so the Coordinator does
    not know or care whether a specialist is local or remote.
    """

    def __init__(self, domain: str) -> None:
        self.domain = domain
        self.node_id = agent_for(domain)

    async def answer(self, query: str) -> AgentResponse:
        # `app.call()` takes the target reasoner's parameters as KEYWORD ARGUMENTS. It does
        # not take an `input=` envelope -- that is the shape of the REST execute API, not of
        # the SDK call, and passing it sends a parameter literally named "input", leaving the
        # specialist's own `query` unset: `agent error (422): Missing required field: query`.
        result = await app.call(f"{self.node_id}.{REASONER[self.node_id]}", query=query)
        # Re-validate: a specialist's reply is untrusted input to the coordinator.
        return AgentResponse.model_validate(result)


_coordinator = Coordinator(
    _llm, {d: RemoteSpecialist(d) for d in ("data-platform", "devops", "crm", "docs")}
)


@app.reasoner()
async def route_query(query: str) -> RoutingDecision:
    """LLM intent classification. Not keyword matching."""
    return await _coordinator.route(query)


@app.reasoner()
async def ask(query: str) -> CopilotResponse:
    """The full lifecycle: route -> dispatch specialists -> synthesise a cited answer."""
    return await _coordinator.ask(query)


if __name__ == "__main__":
    serve(app)
