"""Prompt construction and the scaffolding-leak guard.

These tests exist because of a real failure: asked "What was the error in the last failed
Databricks job?", gemma3:4b answered correctly and then recited the tail of its own prompt
into the answer field. The corrupted answer then defeated the grounding judge, which scored
the query 100% ungrounded.
"""

from __future__ import annotations

from datetime import date

import pytest

from psiog_kendra.prompting import (
    build_grounded_prompt,
    clean_answer,
    finalize,
    finalize_synthesis,
)

ALLOWED = [
    "Databricks Job #4822 (ingestion_raw_events) run #99150",
    "Databricks Job #4830 (crm_sync) run #99163",
]

# The exact answer gemma3:4b returned for test query 2. The tail is prompt scaffolding.
LEAKED = (
    "The last failed Databricks job was Databricks Job #4830 (crm_sync) run #99163. "
    "The error message indicates that the `ingestion_raw_events` job #4822 failed, "
    "specifically due to a `SchemaMismatchException` in the source data "
    "Citation strings you may use, verbatim: "
    "- Databricks Job #4830 (crm_sync) run #99163 "
    "- Databricks Job #4822 (ingestion_raw_events) run #99150."
)


class TestBuildGroundedPrompt:
    def test_carries_the_question_facts_and_citations(self) -> None:
        prompt = build_grounded_prompt(
            question="Did it run?",
            facts_label="Records:",
            facts='{"run_id": 1}',
            citations=["Databricks Job #1"],
        )
        assert "Did it run?" in prompt
        assert '{"run_id": 1}' in prompt
        assert "Databricks Job #1" in prompt

    def test_uses_plain_section_names_not_shouty_tokens(self) -> None:
        # An earlier version fenced the blocks with `<<<CITATIONS`, and gemma3 started
        # writing the token itself into the prose: "...part-0007.parquet [CITATIONS]."
        # Naming a section invites the model to reference it.
        prompt = build_grounded_prompt(question="q", facts_label="F:", facts="f", citations=["c"])
        assert "<<<" not in prompt
        assert "CITATIONS" not in prompt

    def test_puts_the_instruction_last(self) -> None:
        prompt = build_grounded_prompt(question="q", facts_label="F:", facts="f", citations=["c"])
        assert prompt.rstrip().endswith("into the answer text.")

    def test_tells_the_model_to_keep_citations_out_of_the_answer_text(self) -> None:
        prompt = build_grounded_prompt(question="q", facts_label="F:", facts="f", citations=["c"])
        assert "do not write" in prompt
        assert "citations field" in prompt

    def test_handles_an_empty_citation_list(self) -> None:
        assert build_grounded_prompt(question="q", facts_label="F:", facts="f", citations=[])

    def test_states_todays_date_so_yesterday_can_be_resolved(self) -> None:
        # An LLM has no clock. Asked "did yesterday's ETL pipeline run?", the model picked
        # a run from two days earlier because nothing told it what "yesterday" meant.
        prompt = build_grounded_prompt(
            question="Did yesterday's pipeline run?",
            facts_label="F:",
            facts="f",
            citations=["c"],
            today=date(2026, 7, 13),
        )
        assert "2026-07-13" in prompt
        assert "Monday" in prompt
        assert "'yesterday' means 2026-07-12" in prompt

    def test_tells_the_model_to_match_the_record_to_the_question(self) -> None:
        prompt = build_grounded_prompt(
            question="q", facts_label="F:", facts="f", citations=["c"], today=date(2026, 7, 13)
        )
        assert "timestamp actually matches the question" in prompt


class TestCleanAnswer:
    def test_strips_the_real_world_leak(self) -> None:
        cleaned = clean_answer(LEAKED)
        # The genuine answer survives ...
        assert "The last failed Databricks job was Databricks Job #4830" in cleaned
        assert "SchemaMismatchException" in cleaned
        # ... and the recited scaffolding does not.
        assert "Citation strings you may use" not in cleaned
        assert "verbatim" not in cleaned

    @pytest.mark.parametrize(
        "marker",
        [
            "Citation strings you may use",
            "FACTS (the only",
            "DOCUMENT EXCERPTS",
            "Answer the question from these",
            "Do not repeat these instructions",
        ],
    )
    def test_truncates_at_every_known_marker(self, marker: str) -> None:
        cleaned = clean_answer(f"Real answer here. {marker} blah blah")
        assert cleaned == "Real answer here."

    def test_drops_recited_citation_bullets(self) -> None:
        text = "The job failed.\n- Databricks Job #4830 (crm_sync) run #99163\n- Another one"
        cleaned = clean_answer(text)
        assert cleaned == "The job failed."

    def test_leaves_a_clean_answer_untouched_in_substance(self) -> None:
        text = "The sales_etl pipeline completed successfully at 02:14 UTC."
        assert clean_answer(text) == text

    def test_strips_a_bracketed_section_placeholder(self) -> None:
        # gemma3 wrote the section name into the prose instead of a citation:
        #   "...part-0007.parquet [CITATIONS]."
        cleaned = clean_answer("The job failed on part-0007.parquet [CITATIONS].")
        assert cleaned == "The job failed on part-0007.parquet."

    @pytest.mark.parametrize("token", ["[CITATIONS]", "[FACTS]", "<<<FACTS", "[SOURCES]"])
    def test_strips_every_placeholder_form(self, token: str) -> None:
        assert token.strip("[]<") not in clean_answer(f"An answer {token}.").upper()

    @pytest.mark.parametrize(
        "text",
        [
            "The failure affected two CRM records.",
            "Check the deployment facts before rerunning.",
            "The runbook lists three sources.",
        ],
    )
    def test_ordinary_prose_using_those_words_is_not_damaged(self, text: str) -> None:
        # The placeholder strip requires brackets precisely so this cannot happen.
        assert clean_answer(text) == text

    def test_unbalanced_smart_quotes_are_dropped(self) -> None:
        # Real output: '...1284502 records written.” ”Run #99102 also completed...'
        cleaned = clean_answer("Records written.” ”Run #99102 also completed.")
        assert "”" not in cleaned and "“" not in cleaned

    def test_balanced_quotes_are_preserved(self) -> None:
        # A properly quoted error message must survive — agents are told to quote them.
        text = "The job failed with “SchemaMismatchException” on customer_tier."
        assert clean_answer(text) == text

    def test_tidies_a_truncation_seam(self) -> None:
        assert not clean_answer("An answer -- Citation strings you may use: x").endswith("-")

    @pytest.mark.parametrize("text", ["", "   ", "\n\n"])
    def test_empty_input_is_empty_output(self, text: str) -> None:
        assert clean_answer(text) == ""

    def test_an_answer_that_is_pure_scaffolding_collapses_to_empty(self) -> None:
        assert clean_answer("Citation strings you may use, verbatim: - Job #1") == ""


class TestFinalize:
    def test_keeps_only_citations_we_supplied(self) -> None:
        _, citations = finalize("An answer.", ["Totally Invented Source"], ALLOWED)
        assert "Totally Invented Source" not in citations

    def test_lifts_an_inline_citation_out_of_the_prose(self) -> None:
        # gemma3 wrote the citation into the answer text instead of the citations field.
        answer, citations = finalize(
            f"The job failed on a schema mismatch [{ALLOWED[0]}].", [], ALLOWED
        )
        assert ALLOWED[0] not in answer
        assert answer == "The job failed on a schema mismatch."
        assert citations == [ALLOWED[0]]

    def test_does_not_attach_a_citation_that_contradicts_the_answer(self) -> None:
        # The bug this guards: an answer entirely about job #4822 was served with a
        # citation to job #4830, because the fallback blindly took the first allowed
        # source. A mismatched citation looks grounded and is not — the worst outcome.
        answer, citations = finalize(f"The failure was in job #4822 [{ALLOWED[0]}].", [], ALLOWED)
        assert citations == [ALLOWED[0]]
        assert ALLOWED[1] not in citations

    def test_model_citations_and_inline_citations_are_merged_without_duplicates(self) -> None:
        _, citations = finalize(f"Answer [{ALLOWED[0]}].", [ALLOWED[0], ALLOWED[1]], ALLOWED)
        assert citations == ALLOWED
        assert len(citations) == len(set(citations))

    def test_falls_back_only_when_nothing_can_be_established(self) -> None:
        _, citations = finalize("A bare answer with no citation anywhere.", [], ALLOWED)
        assert citations == ALLOWED[:1]

    def test_no_allowed_sources_yields_no_citations(self) -> None:
        answer, citations = finalize("An answer.", ["invented"], [])
        assert citations == []
        assert answer == "An answer."

    def test_removing_an_inline_citation_does_not_weld_the_sentences(self) -> None:
        # The bug this guards: deleting the citation outright produced
        # "...ran successfully.completed with a SUCCESS result state."
        answer, _ = finalize(
            f"The pipeline ran successfully. [{ALLOWED[0]}] completed with a SUCCESS state.",
            [],
            ALLOWED,
        )
        assert "successfully.completed" not in answer
        assert "successfully. completed" in answer

    def test_a_file_path_in_the_answer_is_not_mangled(self) -> None:
        # The naive repair for the weld above (".x" -> ". x") would corrupt exactly the
        # facts these answers exist to quote.
        text = "The job failed on s3://psiog-raw/events/2026-07-12/part-0007.parquet."
        answer, _ = finalize(text, [], ALLOWED)
        assert "part-0007.parquet" in answer
        assert "part-0007. parquet" not in answer

    def test_empty_brackets_left_by_the_strip_are_removed(self) -> None:
        answer, _ = finalize(f"The job failed [{ALLOWED[0]}].", [], ALLOWED)
        assert "[]" not in answer and "( )" not in answer
        assert answer == "The job failed."

    def test_a_citation_contradicted_by_the_answers_own_ids_is_replaced(self) -> None:
        # The real failure, from QA query 2. gemma3 answered entirely about job #4822
        # run #99150, then cited job #4830 — a genuine source, on the allow-list, that it
        # had not used. The allow-list check passed it. Only the answer's own record ids
        # catch this, and a mismatched citation is the worst outcome the system has.
        answer, citations = finalize(
            "The last failed Databricks job was job #4822 (ingestion_raw_events) run #99150. "
            "It failed with a SchemaMismatchException on customer_tier.",
            [ALLOWED[1]],  # the model's citation: job #4830, which it never used
            ALLOWED,
        )
        assert citations == [ALLOWED[0]]  # the #4822 source the answer actually describes
        assert ALLOWED[1] not in citations

    def test_an_inline_citation_contradicted_by_the_prose_is_not_trusted(self) -> None:
        # The real failure, caught live. gemma3 wrote the wrong citation INTO the sentence:
        #   "...found an IntegerType in the source file [Databricks Job #4830 (crm_sync)...]"
        # in an answer whose every fact came from job #4822. Lifting a citation out of the
        # prose proves the model MEANT to cite it — not that the citation is right. So the
        # lift is subject to the same corroboration check as everything else.
        answer, citations = finalize(
            "The last failed Databricks job was job #4822 (ingestion_raw_events) run #99150. "
            f"It failed on a SchemaMismatchException [{ALLOWED[1]}].",
            [],
            ALLOWED,
        )
        assert ALLOWED[1] not in answer  # still lifted out of the prose
        assert citations == [ALLOWED[0]]  # ... but corrected to the source actually used

    def test_a_citation_cannot_corroborate_itself(self) -> None:
        # The ids are read from the prose AFTER the inline citation is removed. Otherwise
        # "[Databricks Job #4830 ...]" would supply the very #4830 that vindicates it.
        _, citations = finalize(f"The job failed on job #4822 [{ALLOWED[1]}].", [], ALLOWED)
        assert citations == [ALLOWED[0]]

    def test_a_citation_with_no_record_ids_is_never_contradicted(self) -> None:
        # A doc section or CRM account carries no "#nnn" id, so it cannot be checked this
        # way — and absence of evidence is not evidence of mismatch. It must survive.
        docs = ["runbook-etl-failures.md § Rollback", "CRM Account: Acme Corp"]
        _, citations = finalize("Rollback is covered in the runbook for job #4822.", docs, docs)
        assert citations == docs

    def test_an_answer_with_no_record_ids_keeps_the_models_citation(self) -> None:
        # Prose answers ("the deployment passed all quality gates") assert no ids, so they
        # prove nothing about any citation. Every source stays eligible.
        _, citations = finalize("The deployment passed all quality gates.", [ALLOWED[1]], ALLOWED)
        assert citations == [ALLOWED[1]]

    def test_a_date_in_the_answer_is_not_mistaken_for_a_record_id(self) -> None:
        # The '#' in the id pattern is load-bearing: matching bare digits would let the
        # year in "2026-07-12" corroborate any citation that happened to contain "2026".
        _, citations = finalize("The run completed on 2026-07-12.", [ALLOWED[1]], ALLOWED)
        assert citations == [ALLOWED[1]]  # no ids asserted -> the model is still trusted

    def test_a_citation_set_off_with_commas_takes_both_commas_with_it(self) -> None:
        # From QA query 3. The model wrote "The deployment, [run #5512], completed" — the
        # citation is a parenthetical, so lifting it out must remove BOTH commas. Collapsing
        # the pair to one left the sentence limping: "The deployment, completed successfully."
        answer, _ = finalize(
            f"The deployment, [{ALLOWED[0]}], completed successfully.", [], ALLOWED
        )
        assert answer == "The deployment completed successfully."

    def test_a_comma_before_a_full_stop_is_removed(self) -> None:
        answer, _ = finalize(f"The job succeeded, [{ALLOWED[0]}].", [], ALLOWED)
        assert answer == "The job succeeded."

    def test_a_genuine_comma_is_not_eaten(self) -> None:
        # The parenthetical rule must not touch ordinary commas — only the empty pair its
        # own strip creates. Lists and subordinate clauses have to survive intact.
        text = "Unit-tests, code-coverage, and security-scan all passed, as the runbook requires."
        answer, _ = finalize(text, [], ALLOWED)
        assert answer == text

    def test_a_trailing_comma_before_the_full_stop_is_removed(self) -> None:
        answer, _ = finalize(f"The job succeeded, [{ALLOWED[0]}].", [], ALLOWED)
        assert answer == "The job succeeded."

    def test_scaffolding_and_inline_citation_are_both_removed(self) -> None:
        answer, citations = finalize(
            f"The job failed. [{ALLOWED[0]}] Citation strings you may use: blah",
            [],
            ALLOWED,
        )
        assert "Citation strings" not in answer
        assert ALLOWED[0] not in answer
        assert citations == [ALLOWED[0]]


class TestFinalizeSynthesis:
    """Cross-domain synthesis. None of this can happen in a single-domain answer — those
    bypass synthesis entirely — which is why it only surfaced on QA query 9."""

    SUPPLIED = [
        "Databricks Job #4830 (crm_sync) run #99163",
        "Databricks Job #4822 (ingestion_raw_events) run #99150",
        "CRM account ACC-1001 (Acme Corp)",
        "CRM account ACC-1002 (TechStart Ltd)",
        "CRM account ACC-1003 (Northwind Retail)",
    ]

    def test_the_specialists_name_tags_are_stripped_from_the_prose(self) -> None:
        # The coordinator labelled each report "[data-agent] ..." and gemma3 copied the tags
        # straight into the answer. A bracketed tag is an invitation to copy.
        answer, _ = finalize_synthesis(
            "Zero rows were synced to CRM [data-agent]. Three accounts were affected [crm-agent].",
            [],
            self.SUPPLIED,
        )
        assert "[data-agent]" not in answer
        assert "[crm-agent]" not in answer
        assert answer == "Zero rows were synced to CRM. Three accounts were affected."

    def test_a_source_the_answer_names_is_cited_even_if_the_model_forgot_it(self) -> None:
        # The real failure: the answer named ACC-1001, ACC-1002 and ACC-1003 and cited only
        # ACC-1001, leaving two-thirds of its claims uncited.
        answer = (
            "The crm_sync job (run #99163) failed, so accounts ACC-1001 (Acme Corp), "
            "ACC-1002 (TechStart Ltd) and ACC-1003 (Northwind Retail) were affected."
        )
        _, citations = finalize_synthesis(
            answer, ["CRM account ACC-1001 (Acme Corp)"], self.SUPPLIED
        )
        assert "CRM account ACC-1002 (TechStart Ltd)" in citations
        assert "CRM account ACC-1003 (Northwind Retail)" in citations
        assert "Databricks Job #4830 (crm_sync) run #99163" in citations

    def test_a_source_the_answer_never_touches_is_not_cited(self) -> None:
        # The bias is towards keeping, but not blindly: a specialist source that appears
        # nowhere in the synthesis and that the model never named is left out.
        answer = "Only account ACC-1001 (Acme Corp) was affected."
        _, citations = finalize_synthesis(answer, [], self.SUPPLIED)
        assert citations == ["CRM account ACC-1001 (Acme Corp)"]

    def test_a_citation_with_nothing_identifiable_is_always_kept(self) -> None:
        # A doc section carries no id, so it cannot be checked this way. Absence of evidence
        # is not evidence of absence — it stays.
        docs = ["runbook-12-schema-mismatch.md § Cause"]
        _, citations = finalize_synthesis("Re-run the job without loosening the type.", [], docs)
        assert citations == docs

    def test_scaffolding_leaks_are_still_stripped(self) -> None:
        answer, _ = finalize_synthesis(
            "The job failed. Citation strings you may use: blah", [], self.SUPPLIED
        )
        assert "Citation strings" not in answer

    def test_nothing_established_falls_back_to_every_specialist_source(self) -> None:
        # Better to over-cite the specialists that were actually dispatched than to serve a
        # cross-domain answer with no provenance at all.
        _, citations = finalize_synthesis("Several systems were affected.", [], self.SUPPLIED)
        assert citations == self.SUPPLIED

    def test_no_supplied_sources_yields_no_citations(self) -> None:
        answer, citations = finalize_synthesis("An answer.", ["invented"], [])
        assert citations == []
        assert answer == "An answer."


class TestNamedRecordsAreCited:
    """A record the answer NAMES is a record the answer used, whether or not the model
    remembered to cite it. finalize() only ever DROPPED a contradicted citation; it had no
    way to ADD one the answer plainly relied on, and CRM citations carry no '#id' so the
    whole corroboration path skipped them."""

    CRM = [
        "CRM account ACC-1001 (Acme Corp)",
        "CRM account ACC-1002 (TechStart Ltd)",
        "CRM account ACC-1003 (Northwind Retail)",
    ]

    def test_the_specialist_cites_every_account_its_answer_names(self) -> None:
        # The real failure: the CRM agent wrote about all three accounts and returned one
        # citation, leaving two-thirds of its own answer uncited — and the coordinator
        # cannot cite what the specialist never handed it.
        answer = (
            "Accounts ACC-1001 (Acme Corp), ACC-1002 (TechStart Ltd) and "
            "ACC-1003 (Northwind Retail) are all stale."
        )
        _, citations = finalize(answer, ["CRM account ACC-1001 (Acme Corp)"], self.CRM)
        assert citations == self.CRM

    def test_an_account_the_answer_never_names_is_not_cited(self) -> None:
        answer = "Only ACC-1001 (Acme Corp) is stale."
        _, citations = finalize(answer, [], self.CRM)
        assert citations == ["CRM account ACC-1001 (Acme Corp)"]

    def test_naming_a_record_cannot_invent_a_source(self) -> None:
        # _named_in only ever selects from `allowed`, so an id in the prose that belongs to
        # no supplied source adds nothing.
        _, citations = finalize("Account ACC-9999 is stale.", [], self.CRM)
        assert citations == ["CRM account ACC-1001 (Acme Corp)"]  # positional fallback only

    def test_a_contradicted_citation_is_still_dropped(self) -> None:
        # Adding named records must not resurrect the mismatched-citation bug: an answer
        # about job #4822 must never be served citing job #4830.
        answer, citations = finalize(
            "The failure was in job #4822 (ingestion_raw_events) run #99150.", [ALLOWED[1]], ALLOWED
        )
        assert citations == [ALLOWED[0]]


class TestSynthesisInlineCitations:
    SUPPLIED = [
        "Databricks Job #4830 (crm_sync) run #99163",
        "CRM account ACC-1001 (Acme Corp)",
        "CRM account ACC-1002 (TechStart Ltd)",
    ]

    def test_a_citation_written_into_the_prose_is_lifted_out(self) -> None:
        # With the [data-agent] tags gone the model simply moved the leak: it started
        # writing the citation STRINGS into the sentence instead.
        answer, citations = finalize_synthesis(
            "The crm_sync job failed [Databricks Job #4830 (crm_sync) run #99163].",
            [],
            self.SUPPLIED,
        )
        assert "[Databricks" not in answer
        assert answer == "The crm_sync job failed."
        assert "Databricks Job #4830 (crm_sync) run #99163" in citations

    def test_a_bracketed_paraphrase_of_a_source_is_lifted_out_too(self) -> None:
        # "[Nightly crm_sync run 99163]" is not a supplied citation verbatim, but its ids
        # belong to one — a bracketed aside naming a cited record is a reference, not prose.
        answer, _ = finalize_synthesis(
            "The nightly run failed on 2026-07-12 [Nightly crm_sync run 99163].",
            [],
            self.SUPPLIED,
        )
        assert "99163]" not in answer
        assert answer == "The nightly run failed on 2026-07-12."

    def test_a_bracketed_aside_that_is_not_a_reference_survives(self) -> None:
        # The rule keys on the source's identifiers, so ordinary bracketed prose is safe.
        text = "The job failed [see the runbook] before the sync."
        answer, _ = finalize_synthesis(text, [], self.SUPPLIED)
        assert answer == text
