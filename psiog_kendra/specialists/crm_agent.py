"""CRM specialist — accounts, deals and contact history.

Skill (deterministic): pull the account/deal/contact records for the named customer.
Reasoner (LLM): answer the specific question asked, not a record dump.

Deal lookups are a single-record read, so this agent runs on the SIMPLE model tier
(gemma3:1b) unless the record carries a sync warning, which needs the stronger model to
reason about staleness.
"""

from __future__ import annotations

import json
import re
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.domains import CRM
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.prompting import build_grounded_prompt, finalize
from psiog_kendra.schemas import AgentResponse
from psiog_kendra.sources.crm import CRMClient

SYSTEM = """You are the CRM specialist for the Psiog enterprise copilot.
You answer questions about customer accounts, deals, deal stages, owners and contacts.

Rules you must not break:
- Use ONLY the CRM records given to you. They are the single source of truth.
- Never invent an account, deal stage, amount, owner or date.
- Answer the exact question asked. If asked for the owner, lead with the owner's name.
- If a record carries a sync warning, say the data may be stale and give the last sync time.
- Every citation must be one of the citation strings supplied to you, copied verbatim.
- Be concise: 2-4 sentences.
"""

# Sentence-initial and question words that are capitalised but are not customer names.
_STOPWORDS = frozenset(
    {
        "the",
        "for",
        "what",
        "who",
        "is",
        "of",
        "status",
        "deal",
        "account",
        "owner",
        "give",
        "did",
        "does",
        "show",
        "and",
        "any",
        "current",
        "crm",
    }
)


def infer_account(query: str, known_accounts: list[str]) -> str | None:
    """Which customer is this query about?

    Candidates come from the CRM records themselves. A capitalised-token fallback keeps
    an account we have never seen from being silently ignored. This only narrows the
    lookup; it never decides the answer.
    """
    q = query.lower()
    for account in known_accounts:
        name = account.lower()
        if not name:
            continue
        if name in q:
            return account
        # "Acme Corp" should be found by a query that only says "Acme".
        for word in name.split():
            if len(word) > 3 and word in q:
                return account

    caps = [w for w in re.findall(r"\b[A-Z][A-Za-z]{2,}\b", query) if w.lower() not in _STOPWORDS]
    return caps[0] if caps else None


class CRMAgent:
    """The CRM specialist. Its node id comes from NODE_CRM_AGENT."""

    domain = CRM

    def __init__(self, llm: LLMGateway, client: CRMClient | None = None) -> None:
        self.node_id = settings().node_crm
        self._llm = llm
        self._client = client or CRMClient()

    async def fetch_records(self, query: str) -> tuple[dict[str, Any], list[str]]:
        """Skill: pull the CRM records relevant to this query."""
        all_records, all_citations = await self._client.fetch(None)
        account = infer_account(
            query, [str(a.get("name", "")) for a in all_records.get("accounts", [])]
        )

        if account:
            narrowed, narrowed_citations = await self._client.fetch(account)
            if narrowed_citations:
                return narrowed, narrowed_citations
        return all_records, all_citations

    @staticmethod
    def _is_stale(records: dict[str, Any]) -> bool:
        return any(a.get("sync_status") == "stale" for a in records.get("accounts", []))

    async def answer(self, query: str) -> AgentResponse:
        """Reasoner: produce a grounded, cited answer."""
        records, citations = await self.fetch_records(query)
        if not citations:
            return AgentResponse(
                answer="No CRM records matched this question.", citations=[], confidence="low"
            )

        # Staleness reasoning is the hard case; a plain field lookup is not.
        complexity = Complexity.COMPLEX if self._is_stale(records) else Complexity.SIMPLE

        user = build_grounded_prompt(
            question=query,
            facts_label="CRM account, deal and contact records:",
            facts=json.dumps(records, indent=2),
            citations=citations,
        )
        try:
            response = await self._llm.structured(
                system=SYSTEM, user=user, schema=AgentResponse, complexity=complexity
            )
        except LLMError:
            deals = records.get("deals") or []
            accounts = records.get("accounts") or []
            if deals:
                d = deals[0]
                text = (
                    f"{d['account_name']}: deal {d['deal_id']} is at stage "
                    f"{d['stage']}, owned by {d['owner']}."
                )
            elif accounts:
                a = accounts[0]
                text = f"{a['name']} is owned by {a['owner']}."
            else:
                text = "No CRM records matched this question."
            return AgentResponse(answer=text, citations=citations[:1], confidence="low")
        # Strip recited scaffolding, lift any inline citation out of the prose, and keep
        # only citations we actually supplied. See prompting.finalize.
        response.answer, response.citations = finalize(
            response.answer, response.citations, citations
        )
        return response
