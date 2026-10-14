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
from psiog_kendra.prompting import finalize_synthesis
from psiog_kendra.schemas import (
    AgentResponse,
    CopilotResponse,
    RoutingDecision,
    SmallTalkCheck,
    SynthesisResult,
)

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

A question can genuinely match NONE of the four domains - a greeting ("hi", "thanks"),
small talk, or a real question about something this copilot was never built to answer
(the weather, a recipe, general trivia). Returning an empty domain list for one of these
is the CORRECT answer, not a failure. Never pick a domain just to have picked one.

Explain your choice in one sentence.
"""

SMALL_TALK_SYSTEM = """A question did not match any of the Psiog copilot's four domains
(data-platform, devops, crm, docs).

Decide only this: is it a greeting or pleasantry, with no real question in it at all -
rather than an actual question the copilot simply cannot answer? Set is_greeting
accordingly. A casual TONE is not what decides this - an informally-phrased question is
still a question.

- "Hi" -> greeting (no question at all)
- "Good morning!" -> greeting (no question at all)
- "Thanks, that's helpful" -> greeting (no question at all)
- "What's the weather like today?" -> NOT a greeting - it asks something, just not
  something this copilot covers
- "Can you write me a poem?" -> NOT a greeting - same reason

Do not attempt to answer the question itself.
"""

GREETING_REPLY = (
    "Hello! I'm Psiog Kendra, your enterprise copilot. Ask me about data pipelines, "
    'deployments, CRM accounts, or internal documentation - for example, "Did '
    "yesterday's ETL pipeline run successfully?\""
)

OUT_OF_SCOPE_REPLY = (
    "I don't have information to answer that. I can only help with questions about "
    "data pipelines, deployments, CRM accounts, or internal documentation."
)

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
            # One honest second look, not a coerced one: an earlier version of this retry
            # told the model "you must return at least one domain", which forced a wrong
            # pick on every genuinely out-of-scope question (a greeting, small talk, a
            # topic none of the four domains cover) instead of trusting its first, correct
            # answer. A real in-scope question can still be missed on the first pass, so
            # it gets one more careful read -- but empty remains a legitimate outcome.
            decision = await self._llm.structured(
                system=ROUTING_SYSTEM,
                user=(
                    f"Question: {query}\n\n"
                    f"On the first pass this matched no domain. Look again, carefully: "
                    f"does it genuinely concern one of {', '.join(ALL_DOMAINS)}? If so, "
                    f"name it. If this is a greeting, small talk, or a topic none of the "
                    f"four domains cover, return an empty list -- that is still correct."
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

        # Every label in this prompt has been copied into an answer at least once. First it
        # was the bracketed agent tag ("...zero rows synced to CRM [data-agent]"), so that
        # went. Its replacement, a "Sources it used:" line, came back as an unterminated
        # "...column type [Sources. To resolve this..." — the model will echo ANY heading it
        # is given. So nothing here is headed like a field: the reports are plain sentences,
        # and finalize_synthesis scrubs whatever still leaks. Prompt discipline alone has
        # never held at this model size; the strip is the part that actually holds.
        reports = "\n\n".join(
            f"The {agent_for(d)} looked into this and found:\n{a.answer}\n"
            f"It read {', '.join(a.citations) or 'nothing'}."
            for d, a in answers.items()
        )
        user = (
            f"User question: {query}\n\n"
            f"{reports}\n\n"
            f"Write the unified answer as plain prose for a colleague. Name no specialist and "
            f"no source in the answer text — the sources go in the citations field, nowhere else."
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

        return finalize_synthesis(result.answer, result.citations, citations)

    async def _decline(self, query: str) -> str:
        """A canned, non-hallucinated reply for a query that matched no domain.

        The REPLY text is fixed, never LLM-authored - the classification deciding which
        fixed reply to use is the only thing asked of the model, on the cheap SIMPLE
        tier. If even that fails, defaulting to the out-of-scope wording is always a
        true statement (a greeting genuinely isn't answerable either), so it degrades
        safely rather than surfacing an error for what is, from the user's side, a
        perfectly ordinary "hi".
        """
        try:
            check = await self._llm.structured(
                system=SMALL_TALK_SYSTEM,
                user=f"Question: {query}",
                schema=SmallTalkCheck,
                complexity=Complexity.SIMPLE,
            )
        except LLMError:
            return OUT_OF_SCOPE_REPLY
        return GREETING_REPLY if check.is_greeting else OUT_OF_SCOPE_REPLY

    async def ask(self, query: str) -> CopilotResponse:
        """The full lifecycle: route -> dispatch -> synthesise."""
        decision = await self.route(query)

        if not decision.domains:
            # Routing genuinely found nothing to dispatch to - stop here. No specialist
            # call, no synthesis call: an off-topic question should cost one cheap
            # classification call, not the full pipeline "thinking hard" about an answer
            # it was never going to ground in anything.
            return CopilotResponse(
                answer=await self._decline(query),
                citations=[],
                domains_used=[],
                routing_reasoning=decision.reasoning,
            )

        answers = await self.dispatch(query, decision.domains)

        if not answers:
            # Domains WERE matched; no specialist is registered for any of them. A
            # different, genuine problem from "nothing matched" above - a deployment
            # gap, not an out-of-scope question - so it keeps its own distinct message.
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
