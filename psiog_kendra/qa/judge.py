"""The Judge Agent — automated grounding verification (AI-assisted QA).

For one answer it:
  1. takes the answer and the citations the copilot produced,
  2. fetches the raw content behind each citation,
  3. asks an LLM to check every claim in the answer against that raw content,
  4. reports the ungrounded claims.

    Hallucination Rate = (ungrounded claims / total claims) x 100

The judge deliberately re-fetches the sources itself rather than trusting the payload the
answering agent saw. A judge that grades against the agent's own context would never catch
a fabricated citation.
"""

from __future__ import annotations

import json
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.rag.chunker import chunk_corpus
from psiog_kendra.schemas import CopilotResponse, JudgeVerdict
from psiog_kendra.sources.base import load_mock

SYSTEM = """You are the grounding judge for an enterprise copilot. You detect hallucinations.

You are given an ANSWER and the RAW SOURCE CONTENT it cited.

Your job, step by step:

1. Split the ANSWER into individual factual claims. A claim is ONE checkable assertion:
   a status, a name, a number, a date, an ID, an error message, or a procedural step.
   Almost every sentence contains at least one claim. A sentence with several facts
   contains several claims - split it.

2. For EACH claim, check it against the RAW SOURCE CONTENT.
   - GROUNDED  = the source states it (rewording is fine, it is still grounded).
   - UNGROUNDED = the source does not state it, or contradicts it.

3. Return EVERY claim, quoted, in exactly one of the two lists:
   - "grounded_claims"   : the claims the source supports
   - "ungrounded_claims" : the claims it does not

CRITICAL: you must list every claim you found. Returning two empty lists means you did no
work, and an answer that asserts facts ALWAYS contains at least one claim. Never return
empty lists for a non-empty answer.

Be strict but fair. Different wording is not a hallucination. An invented number, name,
ID, date or status IS a hallucination.

Example shape (illustrative only):
  grounded_claims:   ["The sales_etl job succeeded", "It ran at 02:14 UTC"]
  ungrounded_claims: ["It processed 5 million rows"]
"""


def load_raw_sources() -> dict[str, Any]:
    """Everything the copilot could legitimately have cited.

    The judge grades against this, independent of what the agents actually retrieved.
    """
    return {
        "databricks": load_mock("databricks"),
        "devops": load_mock("devops"),
        "crm": load_mock("crm"),
        "documentation": [
            {"citation": c.citation, "text": c.text} for c in chunk_corpus(settings().docs_dir)
        ],
    }


def _relevant_sources(citations: list[str], raw: dict[str, Any]) -> dict[str, Any]:
    """Narrow the raw corpus to the systems the answer actually cited."""
    cited = " ".join(citations).lower()
    picked: dict[str, Any] = {}
    if "databricks" in cited:
        picked["databricks"] = raw["databricks"]
    if "github" in cited or "actions" in cited:
        picked["devops"] = raw["devops"]
    if "crm" in cited:
        picked["crm"] = raw["crm"]
    docs = [d for d in raw["documentation"] if d["citation"] in citations]
    if docs:
        picked["documentation"] = docs
    # An answer citing nothing we recognise still has to be judged - against everything.
    return picked or raw


class JudgeAgent:
    """The QA judge. Not part of the copilot; it grades the copilot.

    Its node id comes from NODE_JUDGE_AGENT.
    """

    def __init__(self, llm: LLMGateway, raw_sources: dict[str, Any] | None = None) -> None:
        cfg = settings()
        self.node_id = cfg.node_judge
        self._char_limit = cfg.judge_source_char_limit
        self._llm = llm
        self._raw = raw_sources if raw_sources is not None else load_raw_sources()

    async def verify(self, response: CopilotResponse) -> JudgeVerdict:
        """Grade one copilot answer for grounding."""
        if not response.answer.strip():
            return JudgeVerdict()  # nothing asserted, nothing to ground

        # An answer with no citation at all cannot be grounded, by definition.
        if not response.citations:
            return JudgeVerdict(
                ungrounded_claims=["Answer carries no citation, so no claim is verifiable."]
            )

        sources = _relevant_sources(response.citations, self._raw)
        raw_json = json.dumps(sources, indent=2)[: self._char_limit]
        base = (
            f"ANSWER:\n{response.answer}\n\n"
            f"CITATIONS CLAIMED:\n" + "\n".join(f"- {c}" for c in response.citations) + "\n\n"
            f"RAW SOURCE CONTENT:\n{raw_json}\n\n"
            "List EVERY factual claim in the answer, each in grounded_claims or "
            "ungrounded_claims."
        )

        for attempt in range(2):
            user = base
            if attempt:
                # The judge came back empty. That is not a clean answer — it is a judge
                # that skipped the work. Push it once, explicitly.
                user += (
                    "\n\nYou returned no claims at all. The answer above plainly asserts "
                    "facts. Re-read it, split it into individual claims, and list every one."
                )
            try:
                verdict = await self._llm.structured(
                    system=SYSTEM, user=user, schema=JudgeVerdict, complexity=Complexity.COMPLEX
                )
            except LLMError:
                break
            if verdict.is_measured:
                return verdict

        # Judge failed or refused to enumerate. Report the answer as UNVERIFIED rather than
        # certify it clean — a silent 0% would be the worst possible QA outcome.
        return JudgeVerdict(
            ungrounded_claims=[
                "Judge agent could not verify this answer (it enumerated no claims); "
                "grounding is UNVERIFIED, not confirmed."
            ]
        )
