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
import re
from typing import Any

from psiog_kendra.config import settings
from psiog_kendra.llm import Complexity, LLMError, LLMGateway
from psiog_kendra.rag.chunker import chunk_corpus
from psiog_kendra.schemas import CopilotResponse, JudgeVerdict
from psiog_kendra.sources.base import load_mock

SYSTEM = """You are the grounding judge for an enterprise copilot. You detect hallucinations.

You are given an ANSWER and the RAW SOURCE CONTENT it cited.

Your job, step by step:

1. Split the ANSWER PROSE into individual factual claims. A claim is ONE checkable assertion:
   a status, a name, a number, a date, an ID, an error message, or a procedural step.
   Almost every sentence contains at least one claim. A sentence with several facts
   contains several claims - split it.

   Take claims from the ANSWER ONLY. The CITATIONS CLAIMED block is NOT part of the answer:
   those strings are provenance labels naming where the answer came from, not assertions the
   answer makes. NEVER list a citation string as a claim. "GitHub Actions run #5498
   (deploy-auth, commit 7de2b10)" is a label, not a fact to check.

   Do NOT enumerate fields of the RAW SOURCE. A row of a record is not a claim. "The job id
   is 4822", "The run id is 99150", "The branch is main", "The actor is priya.n" — these are
   FIELDS, and you are reading them out of the very source you are checking against. The
   answer never wrote those sentences. You are grading the answer, not summarising the source.

   Never invent an identifier. If the answer does not mention job 4821 or run #99141, then
   "The job id is 4821" is not a claim the answer made — it is one you took from the source.
   Every id in every claim must appear in the ANSWER.

   Quote each claim as the answer phrased it, not as a field-value pair.

2. For EACH claim, check it against the RAW SOURCE CONTENT.
   - GROUNDED  = the source states it (rewording is fine, it is still grounded).
   - UNGROUNDED = the source does not state it, or contradicts it.

3. Return EVERY claim, quoted, in exactly one of the two lists:
   - "grounded_claims"   : the claims the source supports
   - "ungrounded_claims" : the claims it does not

   Each claim goes in EXACTLY ONE list, ONCE. Never put the same assertion in both lists,
   and never list it twice. "Yes, the deployment passed all gates" and "The deployment
   passed all gates" are the SAME claim - list it once.

CRITICAL: you must list every claim you found. Returning two empty lists means you did no
work, and an answer that asserts facts ALWAYS contains at least one claim. Never return
empty lists for a non-empty answer.

Be strict but fair. Different wording is not a hallucination. An invented number, name,
ID, date or status IS a hallucination.

Example shape (illustrative only):
  grounded_claims:   ["The sales_etl job succeeded", "It ran at 02:14 UTC"]
  ungrounded_claims: ["It processed 5 million rows"]
"""


def _normalise(text: str) -> str:
    """Reduce a string to comparable words, so punctuation and '#' cannot hide a match."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def strip_citation_echoes(claims: list[str], citations: list[str]) -> list[str]:
    """Drop 'claims' that are just the citation string parroted back.

    The judge kept enumerating the provenance label as though it were an assertion — it
    listed "GitHub Actions run #5498 (deploy-auth, commit 7de2b10)" as a claim and then
    marked it UNGROUNDED, in an answer whose every actual fact it had already confirmed.
    That is a phantom hallucination: it inflates the denominator, and lands in the numerator
    at random (the same echo scored GROUNDED on the previous query).

    A citation is where the answer came from, not something the answer asserts, so it is not
    a claim and must not be scored as one.

    The match is exact-after-normalisation, deliberately. A looser rule (substring) would eat
    real claims that happen to name their record — "The job failed on Databricks Job #4822
    (ingestion_raw_events) run #99150" is a genuine, checkable assertion. Under-filtering
    only keeps an extra real claim; over-filtering would hide a hallucination.
    """
    cited = {_normalise(c) for c in citations}
    return [c for c in claims if _normalise(c) and _normalise(c) not in cited]


# Words that carry no subject matter, so overlapping on them means nothing.
_STOPWORDS = frozenset(
    [
        "the",
        "a",
        "an",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "and",
        "or",
        "but",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "with",
        "from",
        "by",
        "as",
        "all",
        "any",
        "not",
        "no",
        "yes",
        "has",
        "have",
        "had",
        "there",
        "their",
        "which",
        "who",
    ]
)

# Tokens keep their internal dots, underscores and hyphens, so "priya.n", "sales_etl" and
# "unit-tests" survive as single identifiers rather than being shredded into fragments.
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._:\-]*")


def _content_words(text: str) -> list[str]:
    # Strip punctuation from the ENDS only. "records." must match "records", while the dots
    # and underscores INSIDE "priya.n" and "sales_etl" are part of the identifier and stay.
    words = (t.strip("._:-") for t in _TOKEN.findall(text.lower()))
    return [w for w in words if len(w) >= 3 and w not in _STOPWORDS]


# A bare restatement of a source field: "The job id is 4822", "The branch is main", "The
# actor is priya.n". These are not assertions the answer makes — they are rows of the record
# the judge is grading against, read back as though the answer had claimed them.
#
# Dropping them cannot hide a hallucination. If the answer really did fabricate an id, the
# substantive claim that carries it ("Job #9999 failed") is enumerated separately and still
# graded; only the redundant field-fragment goes.
_FIELD_RESTATEMENT = re.compile(
    r"^\s*(?:the\s+)?[\w\s]{0,24}?\b"
    r"(?:id|ids|sha|branch|actor|owner|status|conclusion|name|time|timestamp|state)\s+"
    r"(?:is|was|are|were)\s+[^.]{1,40}\.?\s*$",
    re.IGNORECASE,
)


def _identifiers(text: str) -> set[str]:
    """Job ids, run ids, account codes — the values a claim cannot invent by paraphrase."""
    return {t for t in re.findall(r"\b\d{3,}\b|\b[A-Z]{2,}-\d+\b", text)}


def claims_the_answer_actually_makes(
    claims: list[str], answer: str, *, min_overlap: float | None = None
) -> list[str]:
    """Drop 'claims' the judge read out of the source rather than out of the answer.

    Asked whether the payments deployment passed its gates, the judge listed "The branch is
    main", "The actor is priya.n", "The commit sha is a1f9c34" and "The workflow run id is
    5512" as claims — none of which the answer mentions. It had stopped grading the answer
    and started summarising the source.

    That is not a harmless quirk. Every such claim is trivially grounded — the judge copied it
    out of the very source it is checking against — so each one pads the denominator with a
    free pass and drags the hallucination rate DOWN. A metric that flatters us is worse than
    one that indicts us, because nobody goes looking for the bug.

    Three filters, because the first alone was not enough:

    1. **Word overlap.** At least `min_overlap` of the claim's content words must appear in
       the answer. "The branch is main" shares not one word with an answer about deployments.

    2. **Identifiers.** Every job id, run id or account code in the claim must appear in the
       answer. On query 10 the judge produced "The job id is 4821" and "The run id is 99141"
       for an answer that mentions neither — and marked them UNGROUNDED, scoring a flawless
       answer at 53.85%. Overlap alone passed them: "job" matched, so "The job id is 4821"
       scored exactly 0.5 and squeaked through. An id cannot be paraphrased; if the answer
       does not say 4821, the answer did not claim 4821.

    3. **Field restatements.** "The job id is 4822" is a row of the record, not an assertion,
       even when the answer does mention 4822 — the substantive claim about that job is
       enumerated separately and still graded.

    None of this can hide a real hallucination. A hallucination is by definition something
    the ANSWER asserted, so it is built from the answer's own words and its own identifiers.
    Only claims the answer never made fail these tests.
    """
    threshold = settings().judge_claim_overlap if min_overlap is None else min_overlap
    spoken = set(_content_words(answer))
    said_ids = _identifiers(answer)
    kept = []
    for claim in claims:
        if _FIELD_RESTATEMENT.match(claim):
            continue
        if not _identifiers(claim) <= said_ids:
            continue  # names an id the answer never uttered

        words = _content_words(claim)
        if not words:
            continue
        overlap = sum(1 for w in words if w in spoken) / len(words)
        if overlap >= threshold:
            kept.append(claim)
    return kept


def _claim_key(claim: str) -> str:
    """Identity of an assertion. A leading "yes"/"no" answers the question, it is not part
    of the claim, so "Yes, the deployment passed" and "The deployment passed" are one claim."""
    return re.sub(r"^(?:yes|no|indeed|correct)\b[,\s]*", "", _normalise(claim)).strip()


def resolve_contradictions(
    grounded: list[str], ungrounded: list[str]
) -> tuple[list[str], list[str], list[str]]:
    """De-duplicate a verdict and pull out the claims graded BOTH ways.

    On query 3 the judge returned "Yes, the latest deployment passed all quality gates" as
    grounded and "The latest deployment of the payments service passed all quality gates" as
    ungrounded — the same assertion, filed under both verdicts, in one breath. That single
    contradiction was the entire reported hallucination rate for a wholly grounded answer.

    A claim graded both ways has not been graded, and a self-contradicting verdict says
    nothing about the answer — it says the judge slipped. Scoring it either way is a thumb on
    the scale: call it ungrounded and a perfect answer reads 33%; call it grounded and we
    have taught ourselves to discard inconvenient findings.

    So they are returned separately, and the caller asks the judge to grade them again. Only
    a claim the judge contradicts itself on TWICE is finally set aside as ungraded.

    Returns (grounded, ungrounded, contradicted).
    """
    disputed = {_claim_key(c) for c in grounded} & {_claim_key(c) for c in ungrounded}

    def dedupe(claims: list[str]) -> list[str]:
        seen: set[str] = set()
        out = []
        for claim in claims:
            k = _claim_key(claim)
            if k in disputed or k in seen:
                continue
            seen.add(k)
            out.append(claim)
        return out

    contradicted = [c for c in grounded if _claim_key(c) in disputed]
    return dedupe(grounded), dedupe(ungrounded), contradicted


def scrub(
    verdict: JudgeVerdict, *, answer: str, citations: list[str]
) -> tuple[JudgeVerdict, list[str]]:
    """Clean a raw verdict before it is allowed to score anything.

    gemma3:4b is a capable grader and a sloppy bookkeeper. Left alone it will echo the
    citation label back as a claim, enumerate source fields the answer never mentioned, and
    file the same assertion under both verdicts at once. Each of those quietly corrupts the
    one number the RFP grades us on, so every verdict is scrubbed before it is counted.

    If scrubbing empties the verdict, the judge enumerated nothing real — the caller retries,
    and failing that reports UNVERIFIED. It must never read as a clean 0%.

    Returns (clean verdict, claims the judge graded both ways).
    """
    grounded = strip_citation_echoes(verdict.grounded_claims, citations)
    ungrounded = strip_citation_echoes(verdict.ungrounded_claims, citations)

    grounded = claims_the_answer_actually_makes(grounded, answer)
    ungrounded = claims_the_answer_actually_makes(ungrounded, answer)

    grounded, ungrounded, contradicted = resolve_contradictions(grounded, ungrounded)
    return (
        JudgeVerdict(grounded_claims=grounded, ungrounded_claims=ungrounded),
        contradicted,
    )


# A hard fact: something the answer cannot arrive at by rephrasing. A date, a job or run id,
# a record count, an account code. Percentages and 1-2 digit numbers are excluded — "83%",
# "3 accounts" and "two gates" are the kind of thing prose legitimately restates or counts.
_HARD_FACT = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{3,}\b|\b[A-Z]{2,}-\d+\b")


def unsupported_facts(answer: str, sources: dict[str, Any]) -> list[str]:
    """Hard facts the answer states that appear nowhere in the sources it cited.

    This is the deterministic half of the judge, and it exists because the LLM half missed a
    hallucination. On query 11 the answer said "Job 4822 failed on 2026-07-13". The fixture
    says 2026-07-12. gemma3:4b read that claim, checked it against the source, and marked it
    GROUNDED — a fabricated date waved through by the very agent whose job is to catch it.

    A judge that under-reports is the worst outcome this system has: the number looks good,
    so nobody investigates. And an LLM at this size cannot be relied on to notice a one-digit
    difference in a date.

    So dates, ids, record counts and account codes are checked by string search instead. They
    are the facts an answer cannot reach by paraphrase — either the source says 2026-07-12 or
    it does not — which is exactly why they are checkable without a model, and exactly where
    a small model is weakest.

    Deliberately NOT checked: percentages, and numbers under three digits. "74%", "three
    accounts", "both gates" are ordinary prose, and flagging them would drown a real finding
    in noise.
    """
    haystack = json.dumps(sources)
    stated = _HARD_FACT.findall(answer)
    missing = [fact for fact in dict.fromkeys(stated) if fact not in haystack]
    return missing


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
    """Narrow the raw corpus to the systems the answer actually cited.

    Every lookup is a `.get`: a caller may legitimately supply a partial corpus (a test with
    only Databricks records, a deployment where a source is unreachable), and a judge that
    raises KeyError there would take down the whole QA run over a missing key.
    """
    cited = " ".join(citations).lower()
    picked: dict[str, Any] = {}
    if "databricks" in cited and "databricks" in raw:
        picked["databricks"] = raw["databricks"]
    if ("github" in cited or "actions" in cited) and "devops" in raw:
        picked["devops"] = raw["devops"]
    if "crm" in cited and "crm" in raw:
        picked["crm"] = raw["crm"]
    docs = [d for d in raw.get("documentation", []) if d["citation"] in citations]
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

        # Never throw away a verdict that graded something. A first attempt that enumerated
        # ten claims and contradicted itself on one is still a real verdict on the other
        # nine — worth strictly more than the UNVERIFIED (100%) we fall back to. It was not:
        # on query 9 the first attempt contradicted itself, the retry came back empty, and a
        # flawless four-source cross-domain answer was reported as 100% ungrounded.
        best: JudgeVerdict | None = None
        nudge = ""

        for _ in range(2):
            try:
                raw = await self._llm.structured(
                    system=SYSTEM,
                    user=base + nudge,
                    schema=JudgeVerdict,
                    complexity=Complexity.COMPLEX,
                )
            except LLMError:
                break

            verdict, contradicted = scrub(raw, answer=response.answer, citations=response.citations)
            verdict = self._enforce_hard_facts(verdict, response, sources)

            if verdict.is_measured:
                best = verdict
                if not contradicted or nudge:
                    # Clean, or already retried once: take it, with any claim the judge
                    # contradicted itself on twice set aside as ungraded.
                    return verdict

            if nudge:
                break  # already pushed once; take whatever `best` holds

            if contradicted:
                # It filed the same claim as both grounded and ungrounded. That says nothing
                # about the answer — it says the judge slipped. Make it grade those claims
                # again rather than us scoring a coin-flip. This runs even when the disputed
                # pair was the WHOLE verdict, which scrubs to empty: the problem there is the
                # contradiction, not laziness, so it must not get the "you returned nothing"
                # push instead.
                disputed = "\n".join(f"- {c}" for c in contradicted)
                nudge = (
                    "\n\nYou listed these claims as BOTH grounded and ungrounded:\n"
                    f"{disputed}\n"
                    "A claim is grounded or it is not. Re-read the source, decide, and put "
                    "each claim in exactly one list."
                )
            else:
                # The judge came back empty. That is not a clean answer — it is a judge that
                # skipped the work. Push it once, explicitly.
                nudge = (
                    "\n\nYou returned no claims at all. The answer above plainly asserts "
                    "facts. Re-read it, split it into individual claims, and list every one."
                )

        if best is not None:
            return best

        # Judge failed or refused to enumerate. Report the answer as UNVERIFIED rather than
        # certify it clean — a silent 0% would be the worst possible QA outcome.
        return self._enforce_hard_facts(
            JudgeVerdict(
                ungrounded_claims=[
                    "Judge agent could not verify this answer (it enumerated no claims); "
                    "grounding is UNVERIFIED, not confirmed."
                ]
            ),
            response,
            sources,
        )

    def _enforce_hard_facts(
        self, verdict: JudgeVerdict, response: CopilotResponse, sources: dict[str, Any]
    ) -> JudgeVerdict:
        """Add any fabricated date, id or record count the LLM judge failed to notice.

        This runs on EVERY verdict, including a clean one, because the failure it guards is
        the judge saying an answer is fine when it is not. On query 11 the answer stated "Job
        4822 failed on 2026-07-13"; the source says 2026-07-12; gemma3:4b marked it grounded.
        A judge that under-reports is the worst outcome this system has — the number looks
        good, so nobody investigates.

        It can only ever ADD an ungrounded claim, never remove one. It cannot make an answer
        look cleaner than the LLM judge found it.
        """
        missing = unsupported_facts(response.answer, sources)
        if not missing:
            return verdict

        found = ", ".join(missing)
        return JudgeVerdict(
            grounded_claims=[
                c for c in verdict.grounded_claims if not any(m in c for m in missing)
            ],
            ungrounded_claims=[
                *verdict.ungrounded_claims,
                f"The answer states {found}, which appears nowhere in the sources it cited "
                f"(deterministic check, not the LLM judge).",
            ],
        )
