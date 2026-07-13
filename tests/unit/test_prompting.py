"""Prompt construction and the scaffolding-leak guard.

These tests exist because of a real failure: asked "What was the error in the last failed
Databricks job?", gemma3:4b answered correctly and then recited the tail of its own prompt
into the answer field. The corrupted answer then defeated the grounding judge, which scored
the query 100% ungrounded.
"""

from __future__ import annotations

from datetime import date

import pytest

from psiog_kendra.prompting import build_grounded_prompt, clean_answer, finalize

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

    def test_scaffolding_and_inline_citation_are_both_removed(self) -> None:
        answer, citations = finalize(
            f"The job failed. [{ALLOWED[0]}] Citation strings you may use: blah",
            [],
            ALLOWED,
        )
        assert "Citation strings" not in answer
        assert ALLOWED[0] not in answer
        assert citations == [ALLOWED[0]]
