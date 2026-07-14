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

# A RECORD identifier, and nothing else: "#99163" (a job, run or build) or "ACC-1002" /
# "DEAL-7781" (a CRM record). Case-sensitive on the uppercase prefix, and that matters.
#
# An earlier version matched any token containing a digit, which quietly swept up document
# filenames — "runbook-12-schema-mismatch.md" looked like an identifier because of the "12".
# A citation with a key must be NAMED in the answer to survive, and prose never repeats a
# filename, so every docs citation was dropped: query 10 answered with the runbook's recovery
# steps and cited only the Databricks job. Half the answer, uncited — a grounding failure
# wearing a PASS.
#
# A document has no record id, so it can never be contradicted this way and is always kept.
# That is the bias this function is supposed to have.
_CITATION_KEY = re.compile(r"#\d+|\b[A-Z]{2,}-\d+\b")

# The same records as the ANSWER writes them, which is not how the citation writes them. The
# model drops the hash: a citation says "run #99163", the prose says "run 99163". Requiring
# the '#' on both sides made every such citation look CONTRADICTED — the answer named "other"
# records — and query 12 discussed crm_sync run 99163, deploy-ingestion run 5530 and deal
# DEAL-7781 while citing none of them.
#
# So the answer side matches bare digits too. The punctuation was never the fact; the number
# is. Three digits minimum, so a version or a count cannot masquerade as a record id.
_ANSWER_KEY = re.compile(r"#?\b\d{3,}\b|\b[A-Z]{2,}-\d+\b")


def _keys(text: str) -> set[str]:
    """The records a CITATION names."""
    return {k.lstrip("#").lower() for k in _CITATION_KEY.findall(text)}


def _spoken_keys(text: str) -> set[str]:
    """The records an ANSWER names, however it chose to punctuate them."""
    return {k.lstrip("#").lower() for k in _ANSWER_KEY.findall(text)}


def _named_in(answer: str, allowed: list[str]) -> list[str]:
    """Sources whose record the answer names outright.

    The CRM specialist wrote an answer about accounts ACC-1001, ACC-1002 and ACC-1003 and
    returned one citation. `finalize` only ever DROPPED a citation the answer contradicted;
    it had no way to ADD one the answer plainly used, so two of the three accounts went
    uncited — and the coordinator could not cite what the specialist never handed it.

    Naming ACC-1002 in the prose is as good as citing it: that record is where the claim
    came from. This only ever adds sources from `allowed`, so it cannot invent one.
    """
    spoken = _spoken_keys(answer)
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


# A clause that exists only to introduce a citation — "..., as detailed in [runbook-12.md]".
# Lift the citation out and the clause is left pointing at nothing: "...TechStart Ltd, as
# detailed in." It has no meaning without its object, so it goes with it.
_DANGLING_REFERENCE = re.compile(
    r"[,;]?\s*\b(?:as\s+(?:detailed|described|outlined|noted|shown|documented|per)\s+in"
    r"|as\s+(?:detailed|described|outlined|noted|shown|documented)"
    r"|according\s+to|see|per|from|in|documented\s+in)\s*(?=[.!?]\s*$|$)",
    re.IGNORECASE,
)


def _tidy(text: str) -> str:
    """Repair the punctuation left behind when a citation is lifted out of a sentence."""
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)  # empty brackets
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:])", r"\1", text)  # " ." -> "."
    # A citation set off with commas is a parenthetical; removing it must take both commas.
    text = re.sub(r",(?:\s*,)+", "", text)
    text = re.sub(r"([;:])(?:\s*[;:])+", r"\1", text)
    text = re.sub(r"[,;:]+\s*([.!?])", r"\1", text)
    text = _DANGLING_REFERENCE.sub("", text)  # "..., as detailed in." -> "..."
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"[,;:]+\s*([.!?])", r"\1", text)
    return text.strip()


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

    # A bracketed aside whose numbers belong to a source is a citation the model has
    # paraphrased ("[Nightly crm_sync run 99163]"), not something it is telling the reader.
    # Bare digits are used here, not _keys: the paraphrase drops the '#' that makes an id an
    # id, which is exactly what makes it a paraphrase.
    supplied_digits = {d for c in supplied for d in re.findall(r"\d{3,}", c)}

    def _is_reference(match: re.Match[str]) -> str:
        digits = set(re.findall(r"\d{3,}", match.group(1)))
        return " " if digits & supplied_digits else match.group(0)

    cleaned = re.sub(r"\s*\[([^\]]{3,120})\]", _is_reference, cleaned)
    cleaned = _tidy(cleaned)

    spoken = _spoken_keys(cleaned)  # every record the answer names, hash or no hash
    kept: list[str] = []

    for citation in supplied:
        keys = _keys(citation)

        if not keys:
            # A document. It has no record id, so the answer's identifiers can neither
            # confirm nor contradict it — and prose never repeats a filename. Always kept.
            kept.append(citation)
        elif keys & spoken or citation in inline:
            # The answer names this record, or wrote the citation into the prose.
            kept.append(citation)
        elif not spoken:
            # The answer asserts no record id at all, so there is nothing that could
            # contradict this source. The specialist was dispatched because the question
            # needed it and its report is the material this answer was built from, so it
            # stays. The bias is towards keeping — an uncited claim is the failure mode that
            # matters here, and a source the model merely forgot to name is still its source.
            kept.append(citation)
        # Otherwise: the answer names OTHER records and not this one. It is contradicted, and
        # it is dropped even if the model insisted on it — the guard that stops an answer
        # about job #4822 being served citing job #4830.

    # An invented citation never reaches this list: `supplied` is the only source of truth.
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

    But the anchor is *context, not a fact*, and the model will repeat it back as though it
    came from the records: "All five quality gates must pass ... as of 2026-07-14." That date
    is in no source. It is the anchor, laundered into a claim — a hallucination the deterministic
    fact check duly caught, and one this prompt created. So the anchor now says, in as many
    words, that it is not a fact and must not appear in the answer.
    """
    today = today or date.today()
    citation_block = "\n".join(f"- {c}" for c in citations)
    return (
        f"Today's date is {today.isoformat()} ({today.strftime('%A')}). "
        f"Resolve any relative date in the question against it — "
        f"'yesterday' means {(today - timedelta(days=1)).isoformat()}. "
        f"This date is context for reading the question. It is NOT a fact from the records: "
        f"never state it, or any part of it, in the answer.\n\n"
        f"{facts_label}\n"
        f"{facts}\n\n"
        f"You may cite only these sources, copied exactly. Never invent one:\n"
        f"{citation_block}\n\n"
        f"Question: {question}\n\n"
        f"Answer the question using only the records above. Pick the record whose timestamp "
        f"actually matches the question. Every date, id and number in your answer must appear "
        f"in the records above. Write the answer as plain prose for a colleague. "
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
