"""The Coordinator Agent.

Three jobs:
  1. Classify the query's intent with an LLM and pick the domain(s)  -> RoutingDecision
  2. Dispatch the selected specialists, in parallel for cross-domain queries
  3. Synthesise their cited answers into one grounded reply          -> CopilotResponse

The coordinator holds no domain knowledge of its own and never answers from the model's
training data: its answer is assembled strictly from what the specialists returned.

Routing is LLM intent classification. There is deliberately no keyword branch here.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from psiog_kendra.config import settings
from psiog_kendra.domains import ALL_DOMAINS, agent_for, domain_catalog
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.prompting import clean_answer
from psiog_kendra.schemas import AgentResponse, CopilotResponse, RoutingDecision, SynthesisResult

ROUTING_SYSTEM = f"""You are the coordinator of the Psiog enterprise copilot.
Classify the user's question and choose which specialist domain(s) must answer it.

The domains are:
{domain_catalog()}

Use the exact domain labels: {", ".join(ALL_DOMAINS)}.

THE RULE THAT MATTERS MOST: pick the FEWEST domains that can answer the question.
Most questions need exactly ONE. Adding a domain the user did not ask about is an error —
it makes the copilot cite sources nobody wanted.

Add a second domain ONLY when the question genuinely asks two separate things (usually
joined by "and", or by asking about an effect on something else).

What a question is ABOUT is decided by what it ASKS FOR, not by the nouns it mentions:
- "Did the nightly billing job finish?" -> ["data-platform"]
  It asks for a job's status. It does NOT ask for a runbook, so do not add docs.
- "Why did the checkout service build fail?" -> ["devops"]
  It asks about a build. Do not add data-platform just because a service touches data.
- "What does the runbook say about disk pressure?" -> ["docs"]
  It asks what the documentation says. The pipeline it mentions is only context,
  so do not add data-platform.
- "Who owns the Globex account?" -> ["crm"]

Genuinely multi-domain questions, for contrast:
- "The billing job failed - what does the runbook say to do?" -> ["data-platform", "docs"]
  Two asks: the failure, and the documented fix.
- "Did the ETL outage affect any customer records?" -> ["data-platform", "crm"]
  Two asks: the outage, and its customer impact.

Two phrases carry weight and are routinely missed:

1. "known issues", "open incidents", "any incidents", "anything we know about" all ask for
   INCIDENT RECORDS, which live in docs. They are a SEPARATE ask that adds docs.
   - "Is the latest release healthy and are there any known issues?" -> ["devops", "docs"]
     The release status is devops; the known issues are docs.

2. A request for a FULL, OVERALL or COMPLETE status update means ALL FOUR domains.
   When such a request is followed by a list of systems, that list is a set of EXAMPLES
   of what the user has in mind - it is NOT the limit of what they want. "Full" means the
   whole estate, so crm is always included, even when customers are never mentioned.
   - "Give me a complete status update - jobs, releases, and anything open" -> all four,
     including crm, despite customers not appearing anywhere in the question.

Explain your choice in one sentence.
"""

SYNTHESIS_SYSTEM = """You are the coordinator of the Psiog enterprise copilot.
Several specialist agents have each answered part of the user's question.

Write ONE unified answer.

Rules you must not break:
- Use ONLY what the specialists reported. Add no fact of your own.
- Where the specialist answers connect (a pipeline failure explaining a stale CRM record,
  a runbook explaining a job error), make that connection explicit.
- Keep every citation. Copy citation strings verbatim from the specialist answers.
- Be concise: 3-6 sentences.
"""


class Specialist(Protocol):
    """What the coordinator needs from any specialist. Keeps dispatch swappable."""

    node_id: str
    domain: str

    async def answer(self, query: str) -> AgentResponse: ...


class Coordinator:
    """The coordinator agent. Its node id comes from NODE_COORDINATOR."""

    def __init__(self, llm: LLMGateway, specialists: dict[str, Specialist]) -> None:
        self.node_id = settings().node_coordinator
        self._llm = llm
        self._specialists = specialists

    async def route(self, query: str) -> RoutingDecision:
        """Reasoner: LLM intent classification over the domain vocabulary."""
        try:
            decision = await self._llm.structured(
                system=ROUTING_SYSTEM,
                user=f"Question: {query}",
                schema=RoutingDecision,
                complexity=Complexity.COMPLEX,
            )
        except LLMError as exc:
            raise LLMError(f"routing failed for query {query!r}: {exc}") from exc

        if not decision.domains:
            # The model produced no usable domain. Ask once more, forcefully, rather than
            # falling back to a keyword rule -- keyword routing is explicitly out of scope.
            decision = await self._llm.structured(
                system=ROUTING_SYSTEM,
                user=(
                    f"Question: {query}\n\n"
                    f"You must return at least one domain from this exact list: "
                    f"{', '.join(ALL_DOMAINS)}."
                ),
                schema=RoutingDecision,
                complexity=Complexity.COMPLEX,
            )
        return decision

    async def dispatch(self, query: str, domains: list[str]) -> dict[str, AgentResponse]:
        """Call each selected specialist. Cross-domain queries fan out in parallel."""
        targets = [d for d in domains if d in self._specialists]
        if not targets:
            return {}

        results = await asyncio.gather(
            *(self._specialists[d].answer(query) for d in targets),
            return_exceptions=True,
        )

        answers: dict[str, AgentResponse] = {}
        for domain, result in zip(targets, results, strict=True):
            if isinstance(result, BaseException):
                # One specialist failing must not sink the whole query.
                answers[domain] = AgentResponse(
                    answer=f"The {agent_for(domain)} could not be reached.",
                    citations=[],
                    confidence="low",
                )
            else:
                answers[domain] = result
        return answers

    async def synthesize(
        self, query: str, answers: dict[str, AgentResponse]
    ) -> tuple[str, list[str]]:
        """Merge specialist answers. A single specialist passes straight through."""
        citations = list(dict.fromkeys(c for a in answers.values() for c in a.citations))

        if len(answers) == 1:
            only = next(iter(answers.values()))
            return only.answer, only.citations

        reports = "\n\n".join(
            f"[{agent_for(d)}] {a.answer}\nCitations: {', '.join(a.citations) or 'none'}"
            for d, a in answers.items()
        )
        user = (
            f"User question: {query}\n\n"
            f"Specialist reports:\n{reports}\n\n"
            f"Write the unified answer, preserving every citation."
        )
        try:
            result = await self._llm.structured(
                system=SYNTHESIS_SYSTEM,
                user=user,
                schema=SynthesisResult,
                complexity=Complexity.COMPLEX,
            )
        except LLMError:
            # Degrade to concatenation rather than lose the grounded specialist answers.
            merged = " ".join(a.answer for a in answers.values())
            return merged, citations

        kept = [c for c in result.citations if c in citations]
        return clean_answer(result.answer), kept or citations

    async def ask(self, query: str) -> CopilotResponse:
        """The full lifecycle: route -> dispatch -> synthesise."""
        decision = await self.route(query)
        answers = await self.dispatch(query, decision.domains)

        if not answers:
            return CopilotResponse(
                answer="No specialist agent is available for this question.",
                citations=[],
                domains_used=[],
                routing_reasoning=decision.reasoning,
            )

        answer, citations = await self.synthesize(query, answers)
        return CopilotResponse(
            answer=answer,
            citations=citations,
            domains_used=list(answers.keys()),
            routing_reasoning=decision.reasoning,
        )
