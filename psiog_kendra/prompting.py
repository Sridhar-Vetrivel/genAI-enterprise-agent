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
_PLACEHOLDER = re.compile(
    r"\s*(?:\[\s*(?:CITATIONS?|FACTS?|SOURCES?|EXCERPTS?|RECORDS?)\s*\]"
    r"|<{2,}\s*(?:CITATIONS?|FACTS?|SOURCES?|EXCERPTS?|RECORDS?)\s*>{0,})",
    re.IGNORECASE,
)


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

    The last one is why a blind `or allowed[:1]` fallback was removed: it once attached
    "Databricks Job #4830 (crm_sync)" to an answer that was entirely about job #4822.
    A citation that does not match the answer is worse than no citation, because it
    looks grounded and is not. So the answer's own text is searched first, and the
    positional fallback only applies when nothing at all can be established.
    """
    cleaned = clean_answer(answer)

    # A citation the model wrote into the prose still tells us what it relied on.
    inline = [c for c in allowed if c in cleaned]
    for citation in inline:
        # Substitute a SPACE, not nothing. Deleting the citation outright welded the
        # surrounding words together: "...ran successfully. [Job #4821 run #99102]
        # completed with..." collapsed to "...ran successfully.completed with...".
        cleaned = re.sub(rf"\s*[\[(]?\s*{re.escape(citation)}\s*[\])]?", " ", cleaned)

    # No ".word" -> ". word" repair here on purpose: it would corrupt file paths and
    # error messages ("part-0007.parquet" -> "part-0007. parquet"), which are exactly the
    # facts these answers are supposed to quote. Substituting a space above prevents the
    # weld, so no repair is needed.
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned)  # empty brackets left behind
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)  # " ." -> "."

    valid = [c for c in model_citations if c in allowed]
    citations = list(dict.fromkeys(valid + inline))

    if not citations and allowed:
        # Nothing could be established from the model's output at all. Fall back to the
        # top-ranked source rather than serve an uncited answer, but this is a last resort.
        citations = allowed[:1]

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
