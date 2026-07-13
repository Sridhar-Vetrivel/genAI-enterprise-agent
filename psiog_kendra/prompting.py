"""Shared prompt construction for the specialist agents.

All four specialists ask the same shape of question: "here are the records, here are the
citation strings you may use, now answer". Building that in one place matters for a reason
found the hard way — gemma3 will happily copy the tail of the prompt into its answer:

    "The last failed job was ... Citation strings you may use, verbatim:
     - Databricks Job #4830 (crm_sync) run #99163"

That scaffolding leak corrupts the answer, defeats the grounding judge, and is invisible
in unit tests that stub the LLM. So the prompt is structured to discourage it (delimited
blocks, the instruction last, an explicit "do not repeat this") and the reply is sanitised
afterwards regardless — belt and braces, because prompt discipline alone is not reliable
at this model size.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

# Markers that only ever appear in the prompt. If one shows up in an answer, the model has
# started reciting its instructions and everything from there on is scaffolding, not answer.
_LEAK_MARKERS = (
    "Citation strings you may use",
    "You may cite only these sources",
    "FACTS (the only",
    "DOCUMENT EXCERPTS",
    "the only facts you may use",
    "Answer the question from these",
    "Answer the question using only",
    "Do not repeat these instructions",
    "do not write them",
)

# Section-name placeholders the model sometimes emits in place of a real citation, e.g.
# "...part-0007.parquet [CITATIONS]." The brackets are required: a bare word like "records"
# is ordinary prose ("...affecting CRM records.") and must never be stripped.
# The closing bracket is OPTIONAL, and that is the whole point. gemma3 wrote an UNTERMINATED
# one into the prose — "...a mismatch in the `customer_tier` column type [Sources. To resolve
# this..." — which sailed straight through a pattern that demanded a matching "]", and took
# the grounding judge's claim-splitting down with it. The section word must follow the bracket
# immediately, so ordinary prose ("[see the runbook]") is untouched.
_PLACEHOLDER = re.compile(
    r"\s*(?:\[\s*(?:CITATIONS?|FACTS?|SOURCES?|EXCERPTS?|RECORDS?)\s*\]?"
    r"|<{2,}\s*(?:CITATIONS?|FACTS?|SOURCES?|EXCERPTS?|RECORDS?)\s*>{0,})",
    re.IGNORECASE,
)

# Record identifiers — job ids, run ids, build numbers. Every system in scope writes them
# with a leading '#', in the citation strings AND in the prose ("run #99150"), which is what
# makes them usable as a cross-check. The '#' is load-bearing: matching bare digits would
# make the year in "2026-07-12" collide with a job id.
_RECORD_ID = re.compile(r"#(\d+)")


def _record_ids(text: str) -> set[str]:
    return set(_RECORD_ID.findall(text))


# The specialist's own name, as the coordinator labels its report. gemma3 copies the tag
# straight into the synthesised prose — "...zero rows synced to CRM [data-agent]." — which
# is prompt scaffolding reaching the user, and it derails the grounding judge's claim
# splitting on top.
_AGENT_TAG = re.compile(r"\s*[\[(]\s*[a-z][a-z0-9-]*-agent\s*[\])]", re.IGNORECASE)

# Anything in a citation that could identify the record it names: "#99163", "ACC-1002",
# "2026-07-11T04:02:00Z". Unlike _record_ids this does not require a '#', because a CRM
# account is cited as "ACC-1002" with no hash. It is only ever matched WHOLE, so the year
# in a date cannot masquerade as an id.
_CITATION_KEY = re.compile(r"[a-z0-9][a-z0-9:._-]*[0-9][a-z0-9:._-]*", re.IGNORECASE)


def _keys(text: str) -> set[str]:
    return {k.lower() for k in _CITATION_KEY.findall(text)}


def _named_in(answer: str, allowed: list[str]) -> list[str]:
    """Sources whose record the answer names outright.

    The CRM specialist wrote an answer about accounts ACC-1001, ACC-1002 and ACC-1003 and
    returned one citation. `finalize` only ever DROPPED a citation the answer contradicted;
    it had no way to ADD one the answer plainly used, so two of the three accounts went
    uncited — and the coordinator could not cite what the specialist never handed it.

    Naming ACC-1002 in the prose is as good as citing it: that record is where the claim
    came from. This only ever adds sources from `allowed`, so it cannot invent one.
    """
    spoken = _keys(answer)
    return [c for c in allowed if _keys(c) and (_keys(c) & spoken)]


def _lift_inline(cleaned: str, allowed: list[str]) -> tuple[str, list[str]]:
    """Pull citation strings the model wrote into the prose back out of it.

    Substitutes a SPACE, never nothing: deleting outright welds the surrounding words
    together ("...ran successfully.completed with...").
    """
    inline = [c for c in allowed if c in cleaned]
    for citation in inline:
        cleaned = re.sub(rf"\s*[\[(]?\s*{re.escape(citation)}\s*[\])]?", " ", cleaned)
    return cleaned, inline


def _tidy(text: str) -> str:
    """Repair the punctuation left behind when a citation is lifted out of a sentence."""
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)  # empty brackets
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:])", r"\1", text)  # " ." -> "."
    # A citation set off with commas is a parenthetical; removing it must take both commas.
    text = re.sub(r",(?:\s*,)+", "", text)
    text = re.sub(r"([;:])(?:\s*[;:])+", r"\1", text)
    text = re.sub(r"[,;:]+\s*([.!?])", r"\1", text)
    return text


def finalize_synthesis(
    answer: str, model_citations: list[str], supplied: list[str]
) -> tuple[str, list[str]]:
    """Clean a cross-domain synthesis and settle which specialist sources it may cite.

    Two things went wrong on the first cross-domain query, and neither can happen in a
    single-domain answer (those bypass synthesis entirely):

    * The coordinator labelled each specialist report "[data-agent] ...", and gemma3 wrote
      the labels into the answer. Bracketed tags are an invitation to copy.
    * The synthesis named accounts ACC-1001, ACC-1002 and ACC-1003, and cited only ACC-1001.
      Keeping just the citations the model echoed back silently dropped sources the answer
      demonstrably used, leaving two-thirds of the claims uncited.

    So a specialist's citation is kept when the model names it OR when the record it points
    at is named in the answer. A citation with nothing identifiable in it (a doc section) is
    kept regardless — it cannot be checked this way, and absence of evidence is not evidence
    of absence. The specialists were dispatched because the question needed them and their
    answers are the sole material here, so the bias is deliberately towards keeping.

    Once the tags were gone the model simply moved the leak: it began writing the citation
    STRINGS into the prose instead — "...refresh of the bronze.raw_events table by job #4822
    [Databricks Job #4830 (crm_sync) run #99163]". Those are lifted out, exactly as they are
    for a specialist's answer, and so are any bracketed leftovers that merely paraphrase a
    source ("[Nightly crm_sync run 99163]") — a bracketed aside naming a cited record is a
    reference, not prose.
    """
    cleaned = _AGENT_TAG.sub("", clean_answer(answer))
    cleaned, inline = _lift_inline(cleaned, supplied)

    # A bracketed aside whose identifiers belong to a source is a citation the model has
    # paraphrased ("[Nightly crm_sync run 99163]"), not something it is telling the reader.
    supplied_keys = {k for c in supplied for k in _keys(c)}

    def _is_reference(match: re.Match[str]) -> str:
        return " " if _keys(match.group(1)) & supplied_keys else match.group(0)

    cleaned = re.sub(r"\s*\[([^\]]{3,120})\]", _is_reference, cleaned)
    cleaned = _tidy(cleaned)

    named = [c for c in model_citations if c in supplied]
    spoken = _named_in(cleaned, supplied)
    unidentifiable = [c for c in supplied if not _keys(c)]  # doc sections: cannot be checked

    kept = [c for c in supplied if c in inline or c in named or c in spoken or c in unidentifiable]
    return cleaned, kept or supplied


def _supported_by(answer: str, allowed: list[str]) -> list[str]:
    """The sources an answer's own identifiers entitle it to cite.

    The model cannot be trusted to report which record it used. It returned an answer wholly
    about job #4822 run #99150 and cited "Databricks Job #4830 (crm_sync) run #99163" — a real
    source, from the right system, that had nothing to do with what it had just written.

    So the answer's text is the arbiter. A citation whose record ids appear nowhere in the
    prose is contradicted by it, and is dropped. Two deliberate exemptions:

    * A citation carrying no ids at all (a doc section, a CRM account) cannot be contradicted
      this way, so it is always kept — absence of evidence is not evidence of mismatch.
    * An answer citing no ids at all (a prose summary, a runbook answer) proves nothing about
      any citation, so every source stays eligible.
    """
    answer_ids = _record_ids(answer)
    if not answer_ids:
        return list(allowed)
    return [c for c in allowed if not _record_ids(c) or (_record_ids(c) & answer_ids)]


def build_grounded_prompt(
    *,
    question: str,
    facts_label: str,
    facts: str,
    citations: list[str],
    today: date | None = None,
) -> str:
    """The one prompt shape every specialist uses to turn records into a cited answer.

    The delimiters are deliberately plain. An earlier version fenced the blocks with
    shouty tokens (`<<<CITATIONS`), and gemma3 started writing the token itself into the
    prose — "...part-0007.parquet [CITATIONS]." Naming a section invites the model to
    reference it, so the sections are named as blandly as possible.

    Today's date is stated explicitly because an LLM has no clock. Asked "did yesterday's
    ETL pipeline run successfully?", the model picked a run from two days earlier — it had
    no way to know which record "yesterday" pointed at. Every operational question here is
    full of relative dates ("yesterday", "last night", "the latest"), so the anchor matters.
    """
    today = today or date.today()
    citation_block = "\n".join(f"- {c}" for c in citations)
    return (
        f"Today's date is {today.isoformat()} ({today.strftime('%A')}). "
        f"Resolve any relative date in the question against it — "
        f"'yesterday' means {(today - timedelta(days=1)).isoformat()}.\n\n"
        f"{facts_label}\n"
        f"{facts}\n\n"
        f"You may cite only these sources, copied exactly. Never invent one:\n"
        f"{citation_block}\n\n"
        f"Question: {question}\n\n"
        f"Answer the question using only the records above. Pick the record whose timestamp "
        f"actually matches the question. Write the answer as plain prose for a colleague. "
        f"Put the sources you used in the citations field — do not write them, or any part "
        f"of these instructions, into the answer text."
    )


def finalize(answer: str, model_citations: list[str], allowed: list[str]) -> tuple[str, list[str]]:
    """Sanitise an answer and settle on the citations it is actually entitled to.

    Three things go wrong at this model size, and all three are handled here:

    * The model recites prompt scaffolding into the answer -> stripped.
    * The model writes the citation string inline, "...expected a StringType
      [Databricks Job #4822 ...]" -> lifted out of the prose and counted as a citation.
    * The model returns a citation that is not one we supplied -> dropped.

    The third is the dangerous one, and an allow-list alone does not catch it: the model
    returned an answer entirely about job #4822 run #99150 and cited "Databricks Job #4830
    (crm_sync) run #99163" — a source that was on the allow-list, and had nothing to do with
    what it had just written. A citation that does not match the answer is worse than no
    citation, because it looks grounded and is not. So the answer's own record ids are
    checked against each citation (see `_supported_by`), and the model's claim is only
    trusted where the text corroborates it.
    """
    cleaned = clean_answer(answer)

    # A citation the model wrote into the prose still tells us what it relied on. The lift
    # substitutes a SPACE, never nothing: deleting outright welded the surrounding words
    # together ("...ran successfully.completed with a SUCCESS state"). And no ".word" ->
    # ". word" repair, ever: it would corrupt file paths and error messages
    # ("part-0007.parquet" -> "part-0007. parquet"), the very facts the answer exists to quote.
    cleaned, inline = _lift_inline(cleaned, allowed)
    cleaned = _tidy(cleaned)

    # Only sources the answer's own identifiers do not contradict are eligible. Note this is
    # measured on the prose AFTER the inline citations are lifted out, so a citation cannot
    # corroborate itself — and an inline citation is checked like any other. The model has
    # been seen writing a contradicting citation directly into the sentence:
    #   "...found an IntegerType in the source file [Databricks Job #4830 (crm_sync) ...]."
    # in an answer whose every fact came from job #4822. Lifting a citation out of the prose
    # tells us the model MEANT to cite it; it does not make the citation correct.
    supported = _supported_by(cleaned, allowed)

    # A record the answer NAMES is a record the answer used, whether or not the model
    # remembered to cite it. The CRM specialist wrote about accounts ACC-1001, ACC-1002 and
    # ACC-1003 and returned one citation, leaving two-thirds of its own answer uncited —
    # and the coordinator cannot cite what the specialist never handed it. Dropping a
    # contradicted citation was only half the job.
    claimed = list(
        dict.fromkeys(
            inline + [c for c in model_citations if c in allowed] + _named_in(cleaned, allowed)
        )
    )
    citations = [c for c in claimed if c in supported]

    if not citations and supported:
        # The model named nothing usable — every citation it offered was invented, or
        # contradicted by the text it had just written. Prefer a source the answer actually
        # points at over the model's word; fall back positionally only if it points nowhere.
        citations = supported[:1]

    return cleaned, citations


def clean_answer(text: str) -> str:
    """Strip prompt scaffolding the model may have recited back into its answer.

    Truncates at the first leak marker, then removes any trailing citation bullets, so a
    leaked answer degrades to its genuine prefix instead of being served as-is.
    """
    if not text:
        return ""

    cut = len(text)
    for marker in _LEAK_MARKERS:
        found = text.lower().find(marker.lower())
        if found != -1:
            cut = min(cut, found)

    # A brace is never prose. gemma3 ran off the end of a cross-domain answer straight into
    # the structure of its own JSON reply:
    #   "...record last refreshed 2026-07-11.}]K. 1003 (Northwind Retail)."
    # Everything from there on is wreckage — and the grounding judge could not split claims
    # out of it, so a correct four-source answer came back UNVERIFIED (100%).
    #
    # Cutting at the first brace is safe HERE, and only because it was checked: not one
    # string value in any fixture — no error message, no file path, no CRM note — contains a
    # brace. If a source ever legitimately quotes one, this truncates a real answer, so the
    # test that pins it asserts on the fixtures, not on the rule.
    brace = min((text.find(c) for c in "{}" if c in text), default=-1)
    if brace != -1:
        cut = min(cut, brace)

    cleaned = text[:cut]

    # Drop trailing bullet lines that are just recited citations.
    lines = [ln for ln in cleaned.splitlines() if not re.match(r"^\s*[-*]\s+\S", ln)]
    cleaned = "\n".join(lines)

    # Remove any bracketed section-name placeholder the model wrote into the prose.
    cleaned = _PLACEHOLDER.sub("", cleaned)

    # gemma3 sprinkles unpaired smart quotes into prose it has stitched together
    # ('...records written.” ”Run #99102 also...'). If they do not balance, none of them
    # are meaningful, so drop them all rather than serve visibly broken text.
    if cleaned.count("“") != cleaned.count("”"):
        cleaned = cleaned.replace("“", "").replace("”", "")
    if cleaned.count('"') % 2:
        cleaned = cleaned.replace('"', "")

    # Tidy the seam left by truncating mid-sentence.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.rstrip("-–—:,;").strip()
    return cleaned
