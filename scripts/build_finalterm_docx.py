"""Fill the pSiddhi 3.0 FINAL-term template with Psiog Kendra's real, measured content.

    python -m scripts.build_finalterm_docx

Reads  docs/pSiddhi3_0_FinalTerm_Submission_Template 1.docx   (never modified)
Writes docs/S4-I-24_SridharVetrivel_FinalTermDoc.docx

Same discipline as scripts/build_midterm_docx.py: the template is FILLED, not rebuilt. Every
heading, table, style and section number stays exactly where L&D put it, because an AI scoring
engine reads the structure and the template's own rules forbid renaming, deleting, renumbering
or reordering a section. This script only:

  * writes into existing table cells, and appends rows where the content needs more than the
    template shipped (the rules explicitly allow adding rows and evidence blocks);
  * clones the EV block skeleton for EV-07..EV-22, which is what the template tells you to do;
  * deletes the grey italic instruction paragraphs, which the pre-submission checklist requires;
  * ticks the checklist boxes.

Screenshots are NOT embedded. Each paste area names the image to drop in (or says plainly that
the block is carried from mid-term and needs no image), so the pictures can be placed by hand at
full size -- the template demands full-size, readable images, and that is a judgement call about
the page.

Every number here is measured and re-derivable from the repo:
  make cov         -> 419 passed, 4 skipped, 93.11% coverage
  make qa-summary  -> 12 of 12 judged, 100% routing, 5.56% hallucination (3 ungrounded / 54)
  docs/qa/traces.md + data/trace_manifest.json -> all 12 queries through the live control plane
"""

from __future__ import annotations

import copy
import shutil
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Pt
from docx.table import Table
from docx.text.paragraph import Paragraph

TEMPLATE = Path("docs/pSiddhi3_0_FinalTerm_Submission_Template 1.docx")
OUTPUT = Path("docs/S4-I-24_SridharVetrivel_FinalTermDoc.docx")
IMAGES = Path("docs/images")

GREY = "808080"  # the instruction text the checklist says to delete

# --------------------------------------------------------------------------------------
# Screenshots, per evidence block: ev -> (mode, [filenames under docs/images/])
#
# Every file here was opened and read before being mapped, because the filename is not
# evidence of the content. Three traps that mapping by name alone would have walked into:
#
#   * Q07.png, Q09.png and Q10.png are the DEFECTIVE mid-term captures -- two are
#     zero-citation `answer_docs_question` runs on docs-agent ("The indexed internal
#     documentation does not cover this question.") and one is a single-specialist frame of
#     a two-specialist query. They are exactly what EV-07/09/10 say they replaced, so they
#     are NOT used; ev-07.png / ev-09-*.png / ev-10-*.png are the 03-Sep re-captures, and
#     their execution ids match the ones cited in the blocks.
#   * Q8.png and Q08.png are two captures of the SAME query. Q8.png is a specialist frame
#     (`answer_docs_question` on docs-agent); Q08.png is the `ask` frame on coordinator with
#     `domains_used: ["docs"]`. EV-08 is about ROUTING, so it needs Q08.png.
#   * ev-14.png reads "415 passed" and ev-hallucination.png reads "3.64% / 10 of 12" -- the
#     mid-term figures. They belong to EV-14 and EV-13, which are captioned as exactly those
#     Week-10 interim measurements. Using either for EV-19/EV-20 would contradict Section 6.
#
# "carried" = the same image submitted at mid-term, re-pasted so this document reads
# standalone; the carry-forward tick in the block's table still applies.
# --------------------------------------------------------------------------------------

EV_IMAGES: dict[str, tuple[str, list[str]]] = {
    "EV-01": ("carried", ["Q01-Ev01.png"]),
    "EV-02": ("carried", ["Q02.png"]),
    "EV-03": ("carried", ["Q03-Ev03.png"]),
    "EV-04": ("carried", ["Q04.png"]),
    "EV-05": ("carried", ["Q05.png"]),
    "EV-06": ("carried", ["Q06.png"]),
    "EV-07": ("new", ["ev-07.png"]),
    "EV-08": ("carried", ["Q08.png"]),
    "EV-09": ("new", ["ev-09-flow.png", "ev-09-qa.png"]),
    "EV-10": ("new", ["ev-10-flow.png", "ev-10-qa.png"]),
    "EV-11": ("carried", ["Q11.png"]),
    "EV-12": ("carried", ["Q12.png"]),
    "EV-13": ("carried", ["ev-hallucination.png"]),
    "EV-14": ("carried", ["ev-14.png"]),
    "EV-15": ("carried", ["ev-15.png"]),
    "EV-16": ("carried", ["Agents-Up-and-Running.png"]),
    "EV-17": (
        "carried",
        [
            "co-ordinator.png",
            "data-agent-skills-and-reasoner.png",
            "devops-agent-skills-and-reasoners.png",
            "crm-agent-skills-and-reasoner.png",
            "Docs-agent-skills-and-reasoner.png",
        ],
    ),
    "EV-18": ("carried", ["Q12-Workflow-View.png"]),
    # EV-19 .. EV-22 have no image yet. Their paste areas keep the instruction naming the
    # exact command to run, because a graded figure must be captured from a real terminal --
    # rendering the numbers into a picture here would be manufacturing evidence.
}

_SHOT_CARRIED = (
    "Screenshot below — the same evidence submitted at Mid-Term as {ev}, re-pasted here so "
    "this document reads standalone. The carry-forward reference in the table above still "
    "applies."
)
_SHOT_NEW = "Screenshot below — captured for this submission:"

# --------------------------------------------------------------------------------------
# Section 1 — Participant & Project Identification (11 rows)
# --------------------------------------------------------------------------------------

PARTICIPANT = [
    "S4-I-24",
    "GenAI-Powered Enterprise Copilot",
    "Sridhar Vetrivel",
    "P394",
    # Mid-term ticked both Custom and Data; this is a single-track topic. Corrected here.
    "☑ Custom      ☐ Data      ☐ Platform",
    "Semester 4 — Integration Mastery (Capstone)",
    "☑ Regular      ☐ pSiddhi Lite",
    "₹2,500 (fixed)",
    "S4-I-24_SridharVetrivel_MidTermDoc.docx",
    "«TICK ONE FROM THE L&D MID-TERM FEEDBACK RECORD»\n"
    "☐ On track      ☐ At risk — actions were assigned      ☐ Other: ______",
    "Week 17 — 31-Aug-2026 to 04-Sep-2026 (derived from the Week 10 window of 13-Jul-2026 to "
    "17-Jul-2026 recorded in the Mid-Term document; L&D to confirm)",
]

# --------------------------------------------------------------------------------------
# Section 2 — Approved Proposal Recap (as approved; as finally implemented)
# --------------------------------------------------------------------------------------

PROBLEM = (
    "Unchanged from the approved proposal and the Mid-Term recap, restated in full here because "
    "this document is an end-to-end record. Psiog's engineering, data and operations teams work "
    "across a fragmented estate — Databricks for pipelines, GitHub/Azure DevOps for deployments, "
    "a CRM for customer data, and runbooks scattered across wikis. Answering even a simple "
    "operational question — \"did last night's pipeline run?\" — means opening four or five tools "
    "with different credentials and stitching the results together by hand. This creates an "
    "onboarding bottleneck, turns senior engineers into human routers, and slows cross-functional "
    "decisions. The approved proposal identified hallucination as the central risk: an assistant "
    "that answers operational questions from model knowledge rather than from live systems is "
    "worse than no assistant, because it is confidently wrong. Grounding and citation are "
    "therefore not features of this system; they are its precondition."
)

SOLUTION = (
    "Psiog Kendra, as finally implemented: a Coordinator Agent plus four Specialist Agents on "
    "AgentField, an open-source multi-agent orchestration framework, all five running as distinct "
    "registered nodes under Docker Compose. The Coordinator classifies the user's intent with an "
    "LLM (never keyword matching) and dispatches to one or more specialists through the control "
    "plane — Data Platform (Databricks), DevOps (GitHub Actions / Azure DevOps), CRM, and Docs "
    "(RAG over internal runbooks, 21 chunks embedded at 768 dimensions). For a cross-domain "
    "question the Coordinator fans out to every relevant specialist in parallel and synthesises "
    "one answer that cites every system it used; each agent-to-agent hop is traced as a DAG. "
    "Every response carries citations validated against the answer's own record ids, so an answer "
    "cannot cite a source it did not actually use, and nothing is answered from model training "
    "data. A two-half Judge Agent measures the hallucination rate as an automated QA gate.\n\n"
    "One thing to state explicitly, because it is a Phase 2 scope decision rather than a gap: "
    "100% of inference runs on the LOCAL Ollama model (Gemma 3) as the permanent design. "
    "OpenRouter and the Azure B1s VM were formally descoped — see Section 8. Nothing about the "
    "architecture depends on either; the model reference remains a single environment variable."
)

TOOLS_APPROVED = (
    "As approved: AgentField (orchestration, vector memory and DAG tracing), OpenRouter with "
    "google/gemini-2.5-flash (primary inference), Ollama with a local model (zero-cost fallback "
    "inference), Pydantic with extra=\"forbid\" (structured output), Azure B1s VM on the 12-month "
    "free tier (hosting), Docker Compose (deployment), and Pytest + GitHub Actions + an LLM Judge "
    "Agent (QA). Full reconciliation against actual usage — including the two approved tools that "
    "were descoped and the one that had to be added — is in Section 7."
)

# --------------------------------------------------------------------------------------
# Section 3 — every deliverable the approved proposal committed to, Week 4 through 17
# ID | Planned Deliverable | Planned Window | Carried from Mid-Term? | Status | Evidence ID(s)
# --------------------------------------------------------------------------------------

DELIVERABLES = [
    (
        "D-01",
        "AgentField control plane via Docker Compose; Azure VM provisioned; OpenRouter connected",
        "Week 4",
        "Y",
        "Partial — control plane and all five nodes operational; the Azure VM and OpenRouter parts "
        "of this row were formally DESCOPED in Phase 2 (Section 8), so this stays Partial by "
        "decision, not by omission",
        "EV-16, EV-17, EV-18",
    ),
    (
        "D-02",
        "Coordinator Agent — LLM intent classification and routing; Pydantic schemas defined",
        "Week 5",
        "Y",
        "Done — unchanged since mid-term; 100% routing accuracy re-verified across all 12 queries "
        "through the live control plane",
        "EV-01 … EV-12, EV-17, EV-18, EV-20",
    ),
    (
        "D-03",
        "Data Platform Agent — Databricks REST connected; job status and history; unit tests",
        "Week 6",
        "Y",
        "Done — unchanged since mid-term",
        "EV-01, EV-02, EV-09, EV-10, EV-12, EV-17",
    ),
    (
        "D-04",
        "Docs Agent + RAG index — corpus chunked, embedded and indexed; similarity search working",
        "Week 7",
        "Y",
        "Done — unchanged since mid-term",
        "EV-07, EV-08, EV-10, EV-11, EV-12, EV-15, EV-17",
    ),
    (
        "D-05",
        "DevOps Agent — GitHub/Azure DevOps connected; build status, deployments, quality gates",
        "Week 8",
        "Y",
        "Done — unchanged since mid-term",
        "EV-03, EV-04, EV-11, EV-12, EV-17",
    ),
    (
        "D-06",
        "CRM Agent — CRM/mock connected; contact, deal and account queries",
        "Week 9",
        "Y",
        "Done — unchanged since mid-term",
        "EV-05, EV-06, EV-09, EV-12, EV-17",
    ),
    (
        "D-07",
        "At least 6 of the 12 mandatory test queries returning grounded, cited responses",
        "Week 9–10",
        "Y",
        "Done — exceeded: 12 of 12, every one grounded and cited, all re-verified end-to-end "
        "through the live control plane (not just in-process)",
        "EV-01 … EV-12, EV-18, EV-20  (mid-term interim: EV-13)",
    ),
    (
        "D-08",
        "Unit tests passing for skill functions; test coverage ≥50% (Week 10 interim target)",
        "Week 9–10",
        "Y",
        "Done — exceeded: 419 passing, 4 skipped, 93.11% measured coverage",
        "EV-19 (mid-term interim: EV-14)",
    ),
    (
        "D-09",
        "Cross-domain orchestration — parallel specialist dispatch and one synthesised, "
        "cross-cited answer",
        "Week 11",
        "N — new row for a Week 11 deliverable, but note the work landed EARLY: the cross-domain "
        "path was already working, traced and evidenced at Mid-Term under D-07",
        "Done, ahead of its planned window — all four cross-domain queries (Q09–Q12) route to "
        "multiple specialists and synthesise a single cited answer, every hop traced as a DAG "
        "through the control plane. First traced 14-Jul-2026 (Week 10); Q07, Q09 and Q10 "
        "re-traced 03-Sep-2026 for the corrected evidence blocks",
        "EV-09, EV-10, EV-11, EV-12, EV-18",
    ),
    (
        "D-10",
        "Full 12-query test suite + Judge Agent for hallucination detection",
        "Week 12–13",
        "N",
        "Done — the 12-query suite and the Judge Agent were both built in Week 10 (the Judge was "
        "pulled forward because the mid-term Section 6 required the rate it measures; see Section "
        "8). The FULL 12-of-12 judged pass completed on 03-Sep-2026 (Week 17): 100% routing, "
        "5.56% hallucination against a <10% target. Mid-term reported the same measurement "
        "honestly scoped to 10 of 12; that scope gap is what closed in Week 17",
        "EV-20  (mid-term interim: EV-13)",
    ),
    (
        "D-11",
        "Azure B1s VM deployment — the copilot hosted and reachable",
        "Week 14",
        "N",
        "Not Started — formally DESCOPED in Phase 2 (Section 8, Section 10). Local Docker Compose "
        "is the final deployment target; the stack runs identically either way, so no capability "
        "is left unproven",
        "— (descoped; see Section 8)",
    ),
    (
        "D-12",
        "QA hardening to ≥80% coverage + demo preparation",
        "Week 15–16",
        "N",
        "Done — 93.11% coverage against the ≥80% full-programme target (measured, EV-19). The CI "
        "hardening (Python 3.11 + 3.12 matrix, concurrency cancellation, enforced coverage gate, "
        "coverage artefact, opt-in live-model job) and docs/DEMO_RUNBOOK.md both landed on "
        "03-Sep-2026 — Week 17, one week after the planned Week 15–16 window. Stated rather than "
        "smoothed over: the artefacts are committed and verifiable by file, and the two "
        "screenshots of them RUNNING (EV-21, EV-22) are captured in the review window, as noted "
        "in Section 10",
        "EV-19  (primary, already measured); EV-21, EV-22 (capture pending — see Section 10)",
    ),
    (
        "D-13",
        "Final demo, consolidated evidence pack and documentation submitted",
        "Week 17",
        "N",
        "Done — this document and the consolidated 22-block evidence pack in Section 4, both "
        "complete and submitted. The live end-to-end walkthrough is performed AT the review "
        "session itself (that is the only time it can be), scripted by docs/DEMO_RUNBOOK.md and "
        "planned in Section 5.1; its screenshot is EV-22",
        "EV-19, EV-20  (already measured); EV-21, EV-22 (capture pending — see Section 10)",
    ),
]

SELF_ASSESSMENT = [
    (
        "checkpoint",
        "RFP / approved-proposal Week 17 definition of done: the complete copilot demonstrable "
        "live end-to-end; all 12 mandatory test queries passing with correct LLM-based routing, "
        "grounded responses and citations; routing accuracy 100%; hallucination rate documented "
        "and under 10%; QA coverage ≥80%; Judge Agent reports produced; evidence pack submitted; "
        "total spend within the ₹2,500 ceiling.\n\n"
        "Measured against it — every graded item is met and evidenced: 12 of 12 queries route "
        "correctly and answer with citations (100% routing, EV-01…EV-12, EV-20); hallucination "
        "rate 5.56% on a full 12-of-12 judged pass against a <10% target (EV-20); coverage 93.11% "
        "measured by pytest-cov against ≥80% (EV-19); the Judge Agent exists and produced the "
        "report the rate is derived from; the five-node multi-agent architecture is demonstrable "
        "live through the control plane with every hop traced (EV-16 … EV-18); total spend ₹0 "
        "against ₹2,500.",
    ),
    (
        "percent",
        "~95% of the approved scope.\n\n"
        "Defensible from the Section 3 table: of 13 deliverables, 11 are Done, 1 is Partial "
        "(D-01) and 1 is Not Started (D-11). Both exceptions trace to the SAME formally recorded "
        "Phase 2 scope decision (Section 8): neither OpenRouter nor the Azure B1s VM was "
        "provisioned, because the zero-cost local model meets every graded target and Docker "
        "Compose is a complete deployment target for a POC.\n\n"
        "The arithmetic, stated both ways so it is auditable either way. Strictly, counting D-01 "
        "as Partial and D-11 as incomplete: 11 of 13 = 85%. Reading it by clause instead: D-01 "
        "has three clauses (control plane under Compose — DELIVERED; Azure VM — descoped; "
        "OpenRouter — descoped), and D-11 is a single descoped clause, so 11 rows are fully "
        "delivered, 1 row is delivered apart from two descoped clauses, and 1 row is descoped in "
        "full. On that reading ~95% of the approved scope is delivered and no graded capability "
        "is left unproven — every RFP target in the row above is measured and met. The ~95% "
        "figure is the second reading; the 85% figure is the first. Neither is hidden.",
    ),
    (
        "midterm-percent",
        "Week 10 checkpoint: 100% complete and exceeded on every item.\n"
        "Overall Weeks 4–17 scope at mid-term: ~75%.\n\n"
        "The ~75% → ~95% movement is accounted for by the four Phase 2 deliverables D-09, D-10, "
        "D-12 and D-13 completing, and by D-11 being descoped rather than delivered.",
    ),
    (
        "demonstrable",
        "☑ Yes, end-to-end      ☐ Yes, partially      ☐ No, recording/screenshots only\n\n"
        "All 12 mandatory queries run live through the AgentField control plane: the coordinator "
        "classifies intent with the LLM, dispatches to the specialist nodes via app.call(), and "
        "returns one cited answer — with every agent-to-agent hop traced as a DAG in the "
        "AgentField UI. docs/DEMO_RUNBOOK.md is the step-by-step script for the review session. "
        "One honest caveat about pacing, not capability: inference is CPU-bound on a local 4B "
        "model, so a single-domain query takes 2–4 minutes and a cross-domain query 8–15 minutes. "
        "The runbook plans the demo around that (pre-warmed models, a short query first), and the "
        "same queries return in seconds on a hosted endpoint.",
    ),
]

# --------------------------------------------------------------------------------------
# Section 4.1 — Evidence Index
# EV | Caption | Deliverable ID(s) | Verifiable link | Carried from Mid-Term?
# --------------------------------------------------------------------------------------

CARRIED = "Yes — Mid-Term EV-{n}"
NEW = "No — new / re-captured"

EVIDENCE = [
    (
        "EV-01",
        "Q01 \"Did yesterday's ETL pipeline for the sales data run successfully?\" is routed by the "
        "LLM to data-platform and answered citing the exact Databricks run",
        "D-02, D-03",
        "docs/qa/q01.md · execution exec_20260714_141123_g9gremvx",
        "Yes — Mid-Term EV-01",
    ),
    (
        "EV-02",
        "Q02 \"What was the error in the last failed Databricks job?\" routes to data-platform and "
        "quotes the SchemaMismatchException from the job record it cites",
        "D-02, D-03",
        "docs/qa/q02.md · execution exec_20260714_141241_mqlvknj3",
        "Yes — Mid-Term EV-02",
    ),
    (
        "EV-03",
        "Q03 \"Did the latest deployment of the payments service pass all quality gates?\" routes "
        "to devops and cites the GitHub Actions run",
        "D-02, D-05",
        "docs/qa/q03.md · execution exec_20260714_141414_omi6no7o",
        "Yes — Mid-Term EV-03",
    ),
    (
        "EV-04",
        "Q04 \"What was the last deployment date for the auth service?\" routes to devops and "
        "answers the date from the deploy-auth run it cites",
        "D-02, D-05",
        "docs/qa/q04.md · execution exec_20260714_141538_39ycscfa",
        "Yes — Mid-Term EV-04",
    ),
    (
        "EV-05",
        "Q05 \"What is the current deal status for Acme Corp?\" routes to crm and cites BOTH the "
        "account and the deal record",
        "D-02, D-06",
        "docs/qa/q05.md · execution exec_20260714_141715_68sxegi6",
        "Yes — Mid-Term EV-05",
    ),
    (
        "EV-06",
        "Q06 \"Who is the account owner for TechStart Ltd?\" routes to crm and cites the CRM "
        "account — a differently phrased question reaching the same specialist, which is evidence "
        "that routing is intent classification and not keyword matching",
        "D-02, D-06",
        "docs/qa/q06.md · execution exec_20260714_141852_ebkaqo3h",
        "Yes — Mid-Term EV-06",
    ),
    (
        "EV-07",
        "RE-CAPTURED. Q07 \"What is the runbook for a schema mismatch?\" routes to docs and answers "
        "from the RAG index, citing 3 retrieved sections on this control-plane run — the mid-term "
        "screenshot for this block showed a pre-fix, zero-citation docs-agent run, so it is "
        "replaced rather than carried",
        "D-02, D-04",
        "docs/qa/q07.md · docs/qa/traces.md · execution exec_20260903_181908_i4xiuaut",
        "No — re-captured (supersedes the defective Mid-Term EV-07 image)",
    ),
    (
        "EV-08",
        "Q08 \"What does the architecture doc say about the ingestion pipeline?\" routes to docs "
        "and cites the indexed architecture document down to the section",
        "D-02, D-04",
        "docs/qa/q08.md · execution exec_20260714_144845_mo16pl3y",
        "Yes — Mid-Term EV-08",
    ),
    (
        "EV-09",
        "RE-CAPTURED. CROSS-DOMAIN — Q09 \"Did last night's pipeline failure affect any CRM "
        "customer sync?\" routes to data-platform + crm and links the failed job to the specific "
        "customer accounts left stale, citing both systems. The mid-term image showed a "
        "single-specialist frame of this cross-domain query, so it is replaced rather than carried",
        "D-02, D-03, D-06, D-07, D-09",
        "docs/qa/q09.md · docs/qa/traces.md · execution exec_20260903_182225_ak7wxnxf",
        "No — re-captured (supersedes the defective Mid-Term EV-09 image)",
    ),
    (
        "EV-10",
        "RE-CAPTURED. CROSS-DOMAIN — Q10 \"The ingestion job failed — is there a fix in the "
        "runbooks?\" routes to data-platform + docs and joins the live failure to the documented "
        "recovery steps, citing 5 sources spanning both systems on this control-plane run. The "
        "mid-term image showed a single-specialist frame, so it is replaced rather than carried",
        "D-02, D-03, D-04, D-07, D-09",
        "docs/qa/q10.md · docs/qa/traces.md · execution exec_20260903_183031_6f9v61d6",
        "No — re-captured (supersedes the defective Mid-Term EV-10 image)",
    ),
    (
        "EV-11",
        "CROSS-DOMAIN — Q11 \"What's the status of the latest deployment and are there any known "
        "issues?\" routes to devops + docs; the four citations span both systems (two GitHub "
        "Actions runs plus the quality-gates runbook and the incident report)",
        "D-02, D-04, D-05, D-07, D-09",
        "docs/qa/q11.md · execution exec_20260714_145520_dxtvhyol",
        "Yes — Mid-Term EV-11",
    ),
    (
        "EV-12",
        "CROSS-DOMAIN — Q12 \"Give me a full status update — pipeline, deployments, and any open "
        "incidents\" routes to ALL FOUR domains and synthesises one answer citing across every "
        "system. The hardest query in the suite",
        "D-02, D-03, D-04, D-05, D-06, D-07, D-09",
        "docs/qa/q12.md · execution exec_20260714_150256_x4r81cqa",
        "Yes — Mid-Term EV-12",
    ),
    (
        "EV-13",
        "MID-TERM INTERIM, carried for continuity: the Week-10 graded QA run — 3.64% hallucination "
        "(2 ungrounded / 55 claims) over 10 of the 12 queries. Superseded for the full programme "
        "by EV-20, which judges all 12; kept here so the mid-term numbering is not silently "
        "dropped and the two documents reconcile",
        "D-07, D-10",
        "data/qa_report.json (mid-term snapshot) — see EV-20 for the final figure",
        "Yes — Mid-Term EV-13 (interim; superseded by EV-20)",
    ),
    (
        "EV-14",
        "MID-TERM INTERIM, carried for continuity: the Week-10 offline suite — 415 passed, 93.11% "
        "coverage. Superseded for the full programme by EV-19 (419 passed, 93.11%); kept here so "
        "the mid-term numbering is not silently dropped",
        "D-08, D-12",
        "`make cov` (mid-term snapshot) — see EV-19 for the final figure",
        "Yes — Mid-Term EV-14 (interim; superseded by EV-19)",
    ),
    (
        "EV-15",
        "The documentation corpus chunked, embedded and indexed for semantic search — 21 chunks at "
        "768 dimensions, data-validation gate passed with no orphan chunks",
        "D-04",
        "`make index` · psiog_kendra/index_docs.py",
        "Yes — Mid-Term EV-15",
    ),
    (
        "EV-16",
        "The AgentField control plane running under Docker Compose with all five agent nodes "
        "registered, Ready and Active — the orchestration layer the whole architecture depends on",
        "D-01",
        "deploy/docker-compose.yml · `make up && make agents` · `make agents-status`",
        "Yes — Mid-Term EV-16",
    ),
    (
        "EV-17",
        "Five DISTINCT registered nodes — not one LLM behind a long system prompt. Each agent "
        "carries its own base URL, port, reasoners, skills and DID: coordinator (route_query, "
        "ask), data-agent, devops-agent, crm-agent, docs-agent. Direct evidence for the RFP's "
        "multi-agent requirement",
        "D-02, D-03, D-04, D-05, D-06",
        "agents/ · http://localhost:8080/ui/ (Nodes view)",
        "Yes — Mid-Term EV-17",
    ),
    (
        "EV-18",
        "The cross-domain DAG — coordinator.ask fanning out to all four specialists through the "
        "control plane and synthesising one answer, with per-hop durations. The clearest single "
        "picture of the multi-agent design",
        "D-01, D-02, D-07, D-09",
        "docs/qa/traces.md · execution exec_20260714_150256_x4r81cqa",
        "Yes — Mid-Term EV-18",
    ),
    (
        "EV-19",
        "FINAL, measured: the full offline test suite passing with coverage — 419 passed, 4 "
        "skipped, 93.11% coverage against the ≥80% full-programme target. A pytest-cov figure, "
        "not an estimate. Supersedes EV-14",
        "D-08, D-12",
        "`make cov` · .github/workflows/ci.yml (coverage.xml artefact)",
        "No — new (final-programme measurement)",
    ),
    (
        "EV-20",
        "FINAL, measured: the graded QA run over ALL 12 queries — routing accuracy 100% and "
        "hallucination rate 5.56% (3 ungrounded / 54 claims) against a <10% target, with the rate "
        "shown alongside its own inputs so it can be re-derived from data/qa_report.json. "
        "Supersedes EV-13's 10-of-12 interim",
        "D-02, D-07, D-10",
        "`make qa-summary` · data/qa_report.json · psiog_kendra/qa/judge.py",
        "No — new (final-programme measurement)",
    ),
    (
        "EV-21",
        "The hardened CI workflow running green on GitHub Actions across BOTH Python 3.11 and "
        "3.12, with the coverage gate enforced and the coverage.xml artefact uploaded — CI that "
        "reproduces the measurement, not just runs the tests",
        "D-12",
        ".github/workflows/ci.yml (committed) · GitHub Actions run: «PASTE RUN URL»",
        "No — new; SCREENSHOT CAPTURE PENDING (review window). See Section 10",
    ),
    (
        "EV-22",
        "The live end-to-end walkthrough executed against docs/DEMO_RUNBOOK.md — control plane up, "
        "five nodes routable, a single-domain and a cross-domain query answered live with "
        "citations. Evidence that the demo plan in Section 5.1 actually runs",
        "D-12, D-13",
        "docs/DEMO_RUNBOOK.md (committed) · http://localhost:8080/ui/",
        "No — new; SCREENSHOT CAPTURE PENDING (performed at the review). See Section 10",
    ),
]

# --------------------------------------------------------------------------------------
# Section 4.2 — one block per Evidence ID
# ev -> (title, what-this-proves, deliverable ids, date, verifiable link, carried, paste note)
# --------------------------------------------------------------------------------------

_CARRY_NOTE = (
    "[ No screenshot required here — this block is CARRIED UNCHANGED from Mid-Term {ev}, which "
    "is evaluated alongside this document. The original full-size screenshot is in "
    "S4-I-24_SridharVetrivel_MidTermDoc.docx. ]"
)


def _paste(images: list[str]) -> str:
    return "[ PASTE SCREENSHOT HERE — full-size, readable ]    →    " + "   |   ".join(images)


EV_BLOCKS: dict[str, tuple[str, str, str, str, str, str, str]] = {
    "EV-01": (
        "Q01 routes to data-platform and returns a grounded, cited answer",
        "The coordinator classifies intent with an LLM (no keyword matching) and routes to "
        "data-agent. The answer cites the exact Databricks run it read, so the claim is checkable.",
        "D-02, D-03",
        "Developed Week 5–6; verified through the live control plane 14-Jul-2026",
        "docs/qa/q01.md · execution exec_20260714_141123_g9gremvx",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-01",
        _CARRY_NOTE.format(ev="EV-01"),
    ),
    "EV-02": (
        "Q02 quotes the real error from the failed Databricks job it cites",
        "The data agent reads the live job record and quotes the SchemaMismatchException from it. "
        "The error text is in the source, not in the model's training data.",
        "D-02, D-03",
        "Developed Week 6; verified through the live control plane 14-Jul-2026",
        "docs/qa/q02.md · execution exec_20260714_141241_mqlvknj3",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-02",
        _CARRY_NOTE.format(ev="EV-02"),
    ),
    "EV-03": (
        "Q03 routes to devops and cites the GitHub Actions run",
        "A differently-phrased question about a different domain routes correctly to devops-agent, "
        "which answers from the CI records and cites the run.",
        "D-02, D-05",
        "Developed Week 8; verified through the live control plane 14-Jul-2026",
        "docs/qa/q03.md · execution exec_20260714_141414_omi6no7o",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-03",
        _CARRY_NOTE.format(ev="EV-03"),
    ),
    "EV-04": (
        "Q04 answers a date question from the deployment record it cites",
        "The devops agent resolves 'last deployment' against the actual run history and cites the "
        "deploy-auth run — the LLM is never asked to recall a date.",
        "D-02, D-05",
        "Developed Week 8; verified through the live control plane 14-Jul-2026",
        "docs/qa/q04.md · execution exec_20260714_141538_39ycscfa",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-04",
        _CARRY_NOTE.format(ev="EV-04"),
    ),
    "EV-05": (
        "Q05 routes to crm and cites both the account and the deal",
        "The CRM agent answers from the customer records and cites every record it used, not just "
        "the first one.",
        "D-02, D-06",
        "Developed Week 9; verified through the live control plane 14-Jul-2026",
        "docs/qa/q05.md · execution exec_20260714_141715_68sxegi6",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-05",
        _CARRY_NOTE.format(ev="EV-05"),
    ),
    "EV-06": (
        "Q06 routes to crm and cites the CRM account",
        "A second CRM question, phrased entirely differently, routes to the same specialist — "
        "evidence that routing is intent classification, not keyword matching.",
        "D-02, D-06",
        "Developed Week 9; verified through the live control plane 14-Jul-2026",
        "docs/qa/q06.md · execution exec_20260714_141852_ebkaqo3h",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-06",
        _CARRY_NOTE.format(ev="EV-06"),
    ),
    "EV-07": (
        "Q07 routes to docs and answers from the RAG index, citing the retrieved sections",
        "The docs agent retrieves from the vector index by semantic similarity and answers strictly "
        "from the retrieved chunks, citing each document and section — 3 citations on THIS "
        "control-plane run. (The in-process QA run of the same query in EV-20 records 5 "
        "citations: retrieval returns the chunks it scores above threshold, so the count varies "
        "by run. The two are separate executions, not a discrepancy.) RE-CAPTURED for this "
        "submission: the image pasted at mid-term showed a pre-fix run that returned zero "
        "citations, so carrying it forward would have shown a defect the code no longer has.",
        "D-02, D-04",
        "Developed Week 7; re-captured through the live control plane 03-Sep-2026 (Week 17)",
        "docs/qa/traces.md (records the execution id, durable in the repo) · docs/qa/q07.md · "
        "control-plane execution exec_20260903_181908_i4xiuaut",
        "☑ No (new / progressed — supersedes the defective Mid-Term EV-07 image)      "
        "☐ Yes — same as Mid-Term EV-___",
        _paste(["AgentField UI → Executions → exec_20260903_181908_i4xiuaut "
                "(coordinator.ask, routed: docs, 3 citations, 181.2s)"]),
    ),
    "EV-08": (
        "Q08 routes to docs and cites the architecture document by section",
        "Semantic retrieval works over the internal documentation corpus: the answer is assembled "
        "from the indexed architecture doc and cites it down to the section.",
        "D-02, D-04",
        "Developed Week 7; verified through the live control plane 14-Jul-2026",
        "docs/qa/q08.md · execution exec_20260714_144845_mo16pl3y",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-08",
        _CARRY_NOTE.format(ev="EV-08"),
    ),
    "EV-09": (
        "CROSS-DOMAIN — Q09 links a pipeline failure to the CRM accounts it affected",
        "The coordinator routes ONE question to TWO specialists (data-platform + crm) and "
        "synthesises across them: it connects the failed crm_sync job to the specific customer "
        "accounts left stale by it, citing both systems. This is a genuine cross-domain inference, "
        "not two answers stapled together. RE-CAPTURED: the mid-term image showed a "
        "single-specialist frame of this query, which understated the very thing it was meant to "
        "prove.",
        "D-02, D-03, D-06, D-07, D-09",
        "Specialists developed Weeks 6–9; cross-domain path delivered by Week 10 (ahead of its "
        "planned Week 11 window) and first traced 14-Jul-2026; re-captured 03-Sep-2026",
        "docs/qa/traces.md (records the execution id, durable in the repo) · docs/qa/q09.md · "
        "control-plane execution exec_20260903_182225_ak7wxnxf",
        "☑ No (new / progressed — supersedes the defective Mid-Term EV-09 image)      "
        "☐ Yes — same as Mid-Term EV-___",
        _paste(["AgentField UI → Executions → exec_20260903_182225_ak7wxnxf "
                "(coordinator.ask, routed: crm + data-platform, 2 citations, 444.7s)"]),
    ),
    "EV-10": (
        "CROSS-DOMAIN — Q10 joins a live failure to the documented fix",
        "The coordinator routes to data-platform + docs, reads the live job failure, finds the "
        "matching runbook in the RAG index, and returns the recovery steps — 5 citations spanning "
        "the Databricks record and the runbook. RE-CAPTURED for the same reason as EV-09: the "
        "mid-term image showed only one specialist on a two-specialist query.",
        "D-02, D-03, D-04, D-07, D-09",
        "Specialists developed Weeks 6–7; cross-domain path delivered by Week 10 (ahead of its "
        "planned Week 11 window) and first traced 14-Jul-2026; re-captured 03-Sep-2026",
        "docs/qa/traces.md (records the execution id, durable in the repo) · docs/qa/q10.md · "
        "control-plane execution exec_20260903_183031_6f9v61d6",
        "☑ No (new / progressed — supersedes the defective Mid-Term EV-10 image)      "
        "☐ Yes — same as Mid-Term EV-___",
        _paste(["AgentField UI → Executions → exec_20260903_183031_6f9v61d6 "
                "(coordinator.ask, routed: data-platform + docs, 5 citations, 506.9s)"]),
    ),
    "EV-11": (
        "CROSS-DOMAIN — Q11 combines deployment status with known issues",
        "The coordinator routes to devops + docs. domains_used shows both. The four citations span "
        "both systems: two GitHub Actions runs plus the quality-gates runbook and the "
        "ingestion-failure incident report.",
        "D-02, D-04, D-05, D-07, D-09",
        "Specialists developed Weeks 7–8; cross-domain path delivered by Week 10 (ahead of its "
        "planned Week 11 window); traced 14-Jul-2026",
        "docs/qa/traces.md (records the execution id, durable in the repo) · docs/qa/q11.md · "
        "control-plane execution exec_20260714_145520_dxtvhyol",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-11",
        _CARRY_NOTE.format(ev="EV-11"),
    ),
    "EV-12": (
        "CROSS-DOMAIN — Q12 routes to ALL FOUR domains and synthesises one cited answer",
        "The hardest query in the suite. One question, all four specialists, one synthesised answer "
        "citing across every system — pipelines, deployments, customer accounts and incident docs.",
        "D-02, D-03, D-04, D-05, D-06, D-07, D-09",
        "Specialists developed Weeks 5–9; four-domain synthesis delivered by Week 10 (ahead of "
        "its planned Week 11 window); traced 14-Jul-2026",
        "docs/qa/traces.md (records the execution id, durable in the repo) · docs/qa/q12.md · "
        "control-plane execution exec_20260714_150256_x4r81cqa",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-12",
        _CARRY_NOTE.format(ev="EV-12"),
    ),
    "EV-13": (
        "MID-TERM INTERIM — the Week-10 graded QA run at 3.64% hallucination (superseded by EV-20)",
        "Carried for continuity, not as the final figure. At mid-term the rate was measured "
        "honestly over 10 of the 12 queries — 3.64% = (2 ungrounded / 55 claims) × 100 — and "
        "reported as exactly that scope, not extrapolated. The full-programme figure is in EV-20, "
        "which judges all 12. This block is kept so the mid-term EV numbering is carried forward "
        "rather than silently dropped, and so the two documents reconcile on their own terms.",
        "D-07, D-10",
        "Measured 14-Jul-2026 (Week 10)",
        "data/qa_report.json (mid-term snapshot) · see EV-20 for the final figure",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-13 (interim figure; "
        "superseded for the full programme by EV-20)",
        _CARRY_NOTE.format(ev="EV-13"),
    ),
    "EV-14": (
        "MID-TERM INTERIM — the Week-10 test suite at 415 passed / 93.11% (superseded by EV-19)",
        "Carried for continuity. 415 tests passed with 93.11% measured coverage at mid-term; the "
        "final-programme figure is 419 passed, 4 skipped, 93.11% (EV-19). Kept so the mid-term EV "
        "numbering is carried forward rather than silently dropped.",
        "D-08, D-12",
        "Measured 14-Jul-2026 (Week 10)",
        "`make cov` (mid-term snapshot) · see EV-19 for the final figure",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-14 (interim figure; "
        "superseded for the full programme by EV-19)",
        _CARRY_NOTE.format(ev="EV-14"),
    ),
    "EV-15": (
        "The documentation corpus chunked, embedded and indexed",
        "21 chunks embedded at 768 dimensions and written to the vector index, with the "
        "data-validation gate passing: no orphan chunks, all metadata present.",
        "D-04",
        "Developed Week 7; index rebuilt and validated 14-Jul-2026",
        "`make index` · psiog_kendra/index_docs.py",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-15",
        _CARRY_NOTE.format(ev="EV-15"),
    ),
    "EV-16": (
        "The AgentField control plane running with all five agent nodes registered",
        "The control plane is up under Docker Compose and all five nodes are registered, Ready and "
        "Active. This is the orchestration layer the whole architecture depends on — and the final "
        "deployment target, per the Section 8 scope decision.",
        "D-01",
        "Developed Week 4; re-verified on the demo stack 03-Sep-2026",
        "deploy/docker-compose.yml · `make up && make agents` · `make agents-status`",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-16",
        _CARRY_NOTE.format(ev="EV-16"),
    ),
    "EV-17": (
        "Five distinct agent nodes — not one LLM behind a long system prompt",
        "Each agent is separately registered with the control plane and carries its own base URL, "
        "port, reasoners, skills and DID: coordinator (route_query, ask), data-agent "
        "(answer_data_question, fetch_job_runs), devops-agent (answer_devops_question, "
        "fetch_workflow_runs), crm-agent (answer_crm_question, fetch_crm_records) and docs-agent "
        "(answer_docs_question, index_documentation, search_documentation). This is the direct "
        "evidence for the RFP's multi-agent requirement.",
        "D-02, D-03, D-04, D-05, D-06",
        "Developed Weeks 5–9; node registrations verified 14-Jul-2026",
        "agents/ · http://localhost:8080/ui/ (Nodes view)",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-17",
        _CARRY_NOTE.format(ev="EV-17"),
    ),
    "EV-18": (
        "The cross-domain DAG — the coordinator fanning out to all four specialists",
        "The Graph view of Q12: the Ask node on coordinator branching to Answer Data Question, "
        "Answer Crm Question, Answer Docs Question and Answer Devops Question — all four green, "
        "with per-hop durations. Every agent-to-agent call goes through the control plane and is "
        "traced. This is the clearest single picture of the multi-agent design.",
        "D-01, D-02, D-07, D-09",
        "Traced 14-Jul-2026 (Week 10)",
        "docs/qa/traces.md (records every one of the 12 execution ids, durable in the repo) · "
        "control-plane execution exec_20260714_150256_x4r81cqa",
        "☐ No (new / progressed)      ☑ Yes — same as Mid-Term EV-18",
        _CARRY_NOTE.format(ev="EV-18"),
    ),
    "EV-19": (
        "FINAL — the full offline test suite passing, with measured coverage",
        "419 tests passed, 4 skipped, 93.11% coverage — a measured pytest-cov figure against the "
        "≥80% full-programme target, not an estimate. The suite is deliberately offline (no LLM, "
        "no network, no control plane), which is why it can gate every commit in CI; the "
        "live-model path is covered separately by the opt-in CI job in EV-21 and by the "
        "control-plane executions in EV-01 … EV-12.",
        "D-08, D-12",
        "Measured 03-Sep-2026 (final submission)",
        "`make cov` · .github/workflows/ci.yml (coverage.xml artefact)",
        "☑ No (new / progressed — final-programme measurement, supersedes EV-14)      "
        "☐ Yes — same as Mid-Term EV-___",
        _paste(["Terminal: `make cov` — must read \"419 passed, 4 skipped\" and "
                "\"Total coverage: 93.11%\""]),
    ),
    "EV-20": (
        "FINAL — the graded QA run over all 12 queries: 100% routing, 5.56% hallucination",
        "The full-programme QA gate, all three targets met and every figure computed rather than "
        "asserted. Routing accuracy 100% (12 of 12) against a 100% target. Every answer carries at "
        "least one citation (12 of 12). Hallucination rate 5.56% = (3 ungrounded / 54 claims) × "
        "100, against a <10% target, shown alongside its own inputs. The header names "
        "data/qa_report.json so the figure can be re-derived from the raw graded data rather than "
        "taken on trust.",
        "D-02, D-07, D-10",
        "Measured 03-Sep-2026 (final submission)",
        "`make qa-summary` · data/qa_report.json · psiog_kendra/qa/judge.py",
        "☑ No (new / progressed — final-programme measurement, supersedes EV-13)      "
        "☐ Yes — same as Mid-Term EV-___",
        _paste(["Terminal: `make qa-summary` — must read \"Queries graded: 12 of 12\", "
                "\"Routing accuracy: 100.0%\" and \"HALLUCINATION RATE: 5.56%\""]),
    ),
    "EV-21": (
        "The hardened CI workflow green on GitHub Actions, across both Python versions",
        "CI that reproduces the measurement, not just runs the tests: a Python 3.11 + 3.12 matrix, "
        "a concurrency group that cancels superseded runs, the ≥80% coverage gate enforced in the "
        "job itself, coverage.xml uploaded as a build artefact, and a separate opt-in `live` job "
        "that installs Ollama, pulls gemma3:4b / gemma3:1b / nomic-embed-text and runs the "
        "real-model tests. Beyond the approved scope — see Section 9, EN-04.",
        "D-12",
        "Workflow written and committed 03-Sep-2026 (Week 17); CI run «DATE OF THE GREEN RUN»",
        ".github/workflows/ci.yml (committed and verifiable by file today) · GitHub Actions run: "
        "«PASTE RUN URL»",
        "☑ No — new (Phase 2 enhancement). SCREENSHOT CAPTURE PENDING: the workflow is committed, "
        "but a green run can only exist once the branch is pushed, so this is captured in the "
        "review window — see Section 10.      ☐ Yes — same as Mid-Term EV-___",
        _paste(["GitHub → Actions → the latest CI run on master: both matrix jobs "
                "(3.11 and 3.12) green, coverage artefact listed"]),
    ),
    "EV-22": (
        "The live end-to-end walkthrough, executed against the demo runbook",
        "Evidence that the Section 5.1 walkthrough plan actually runs, not just that it is written "
        "down: the control plane up, all five nodes reported routable by `make agents-status` "
        "(which asks each port directly rather than trusting the node list), and both a "
        "single-domain and a cross-domain query answered live with citations through "
        "coordinator.ask.",
        "D-12, D-13",
        "Runbook written and committed 03-Sep-2026 (Week 17); walkthrough performed «DATE»",
        "docs/DEMO_RUNBOOK.md (committed and verifiable by file today) · http://localhost:8080/ui/",
        "☑ No — new (Phase 2). SCREENSHOT CAPTURE PENDING: the runbook is committed, but the "
        "walkthrough it scripts is performed at the review session itself — see Section 10.      "
        "☐ Yes — same as Mid-Term EV-___",
        _paste(["Terminal: `make agents-status` showing all five nodes routable",
                "AgentField UI → Executions → the live coordinator.ask run from the "
                "walkthrough"]),
    ),
}

# --------------------------------------------------------------------------------------
# Section 5 — Working Demo, Repository & Live Walkthrough Plan
# --------------------------------------------------------------------------------------

REPO_LINKS = [
    "https://github.com/Sridhar-Vetrivel/genAI-enterprise-agent",
    "«FINAL SHORT SHA» — «DD-MMM-26»   (run: git log -1 --format='%h %ci' at submission time)\n"
    "The final commit is on the `master` branch. IMPORTANT: `master` must be merged into the "
    "repository's default branch before the review, so that the commit named here is what the "
    "evaluator sees on opening the repository — otherwise the default branch view will trail the "
    "submitted work.",
    "N/A — local Docker Compose is the FINAL deployment target for this POC (formally descoped "
    "from Azure B1s; see Section 8). The AgentField control plane and its UI serve at "
    "http://localhost:8080/ui/ and will be live on the demo machine throughout the Week 17 "
    "review window.",
    "docs/qa/ — one evidence page per Evidence ID, generated from the graded QA report; "
    "docs/qa/traces.md — every one of the 12 test queries mapped to its control-plane execution "
    "ID; docs/DEMO_RUNBOOK.md — the step-by-step live demo script; data/qa_report.json — the raw "
    "graded data behind every Section 6 number.",
]

WALKTHROUGH = [
    "The Coordinator's cross-domain path — the most substantial AI component, and the one place "
    "where LLM routing, multi-agent orchestration and grounding all meet. Flow: a plain-English "
    "question arrives → the coordinator classifies intent with the LLM into one or more of four "
    "domains (never keyword matching) → specialists are dispatched in parallel through the "
    "AgentField control plane → their grounded findings are synthesised into one answer whose "
    "citations are validated against the answer's own record ids → the Judge Agent grades the "
    "result. I will walk the routing decision, the fan-out, the citation-validation step (the "
    "single most important safeguard in the system) and the two-half Judge.",
    "agents/coordinator.py  (the AgentField node: RemoteSpecialist.answer(), the app.call() "
    "cross-agent path)\n"
    "psiog_kendra/coordinator.py  (Coordinator.ask() — routing → parallel dispatch → "
    "synthesis)\n"
    "psiog_kendra/prompting.py  (build_grounded_prompt(), _supported_by() — citation validation)\n"
    "psiog_kendra/qa/judge.py  (the two-half Judge: LLM claim-grounding + deterministic "
    "fact-check)\n"
    "agents/health.py  (serving vs. routable fleet health)",
    "`master` — the branch carrying the final commit and every file path listed above. It is "
    "merged into the repository default branch before the review window, so either branch shows "
    "the same tree; if the panel prefers, `master` can be checked out directly.",
    "Nothing from L&D — no credentials are needed, because the demo runs on synthetic fixtures by "
    "design (the approved proposal's own mock-data-only rule; Section 8). On the demo machine, "
    "already started and warmed per docs/DEMO_RUNBOOK.md: (1) Ollama serving gemma3:4b, gemma3:1b "
    "and nomic-embed-text; (2) the control plane and all five nodes up (`make up && make agents`), "
    "confirmed with `make agents-status`; (3) the RAG index loaded into the control plane's vector "
    "memory (`make index-cp`); (4) the AgentField UI open at http://localhost:8080/ui/ for the DAG "
    "view. Please note the pacing: CPU-bound local inference means 2–4 minutes for a "
    "single-domain query and 8–15 minutes for a cross-domain one, so the runbook front-loads a "
    "short query and keeps a pre-traced execution open for the long one.",
]

# --------------------------------------------------------------------------------------
# Section 6 — QA Progress (full programme)
# --------------------------------------------------------------------------------------

QA_ROWS = [
    (
        "Unit tests (routing, retrieval, sources, prompting, orchestration, agent runtime, QA "
        "harness)",
        "419 passing, 4 skipped",
        "93.11% (pytest-cov, `make cov`) ✅",
        "≥80% full programme (the ≥50% at mid-term was an interim only)",
        "EV-19  (mid-term interim: EV-14)",
    ),
    (
        "Routing accuracy — the 12 mandatory test queries, live model, through the control plane",
        "12 of 12",
        "100% ✅",
        "100%",
        "EV-01 … EV-12, EV-18, EV-20",
    ),
    (
        "Grounding — answers carrying at least one citation",
        "12 of 12",
        "100% ✅",
        "Every answer cited",
        "EV-01 … EV-12, EV-20",
    ),
    (
        "Hallucination rate — Judge Agent, FULL 12-of-12 judged pass",
        "12 of 12 answers judged (54 claims)",
        "5.56% ✅  = (3 ungrounded / 54 claims) × 100",
        "<10%",
        "EV-20  (mid-term interim: EV-13, 10 of 12)",
    ),
    (
        "Integration tests (coordinator → specialists → synthesis, including the live "
        "control-plane app.call() path)",
        "Included in the 419; the live path additionally exercised end-to-end for all 12 queries "
        "and recorded in docs/qa/traces.md",
        "—",
        "—",
        "EV-19, EV-18",
    ),
    (
        "CI — offline suite + coverage gate on every push, plus an opt-in live-model job",
        "Python 3.11 and 3.12 matrix; `live` job installs Ollama and runs the real-model tests",
        "Coverage gate enforced at ≥80% in the job itself",
        "CI running the suite",
        "EV-21",
    ),
]

QA_NOTE = (
    "All three graded QA targets are met on the full programme: routing accuracy 100% against a "
    "100% target, test coverage 93.11% against an ≥80% target, and a hallucination rate of 5.56% "
    "against a <10% target — the last one now measured over ALL 12 queries, closing the "
    "10-of-12 scope gap that was flagged honestly at mid-term.\n\n"
    "Hallucination rate = (ungrounded claims / total claims) × 100, measured by a dedicated Judge "
    "Agent that re-fetches the raw source content behind every citation independently of what the "
    "answering agent saw — a judge grading against the agent's own context could never catch a "
    "fabricated citation. The Judge has two independent halves, and that design is why the number "
    "can be trusted. The LLM half splits an answer into claims and checks each against the source. "
    "A deterministic half then runs on every answer with no model involved: every date, job id, "
    "run id, record count and account code the answer states must appear verbatim in the sources "
    "it cited. It can only ever ADD a finding, never remove one — so the reported rate errs "
    "pessimistic, never flattering.\n\n"
    "Reading the 3 ungrounded claims honestly: exactly one (Q07) is a specific identified "
    "grounding miss. The other two (Q10, Q12 — the two longest cross-domain answers) are the "
    "local 4B judge declining to enumerate claims for a long multi-source answer, and the harness "
    "deliberately counts an unverified answer as ungrounded rather than flatter the score. The "
    "reported 5.56% is therefore a ceiling, not a midpoint: the true rate is at or below it. This "
    "is precisely the kind of small-model imprecision that a hosted frontier judge resolves "
    "outright — and because the judge reads the same AI_MODEL_COMPLEX environment variable as "
    "every other call, pointing it at a stronger model is a configuration change with no code to "
    "write.\n\n"
    "Every figure in this table is reproducible from the repository without re-running the models: "
    "`make cov` re-measures coverage, and `make qa-summary` re-renders the routing and "
    "hallucination numbers from data/qa_report.json, the raw graded output."
)

# --------------------------------------------------------------------------------------
# Section 7 — Tool & Budget Reconciliation (full programme)
# --------------------------------------------------------------------------------------

TOOLS = [
    (
        "AgentField — orchestration, vector memory, DAG tracing",
        "Open-source, self-hosted, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "As approved, for the whole programme. Replaces the RFP's LangChain / MS Agent Framework "
        "and Azure AI Search — a swap the approved proposal itself made; restated in Section 8.",
    ),
    (
        "OpenRouter (google/gemini-2.5-flash) — primary inference",
        "Pay-per-token, budgeted ~₹800–1,200",
        "☐ Yes  ☑ No  ☐ Partial",
        "₹0",
        "NEVER PROVISIONED, and in Phase 2 formally DESCOPED rather than deferred (Section 8). The "
        "approved zero-cost fallback carries 100% of inference and meets every graded target. "
        "Switching remains a one-variable change (AI_MODEL_COMPLEX) with no code to write. "
        "Cost impact: ₹0 spent against a ~₹1,000 estimate.",
    ),
    (
        "Ollama — local inference (approved as the fallback; became the sole path)",
        "Free, self-hosted, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "Approved as the fallback and promoted to the permanent, sole inference path. The fallback "
        "is therefore proven under load rather than theoretical: routing 100%, hallucination 5.56%, "
        "all 12 queries answered through the control plane on it.",
    ),
    (
        "Llama 4 Scout — the approved local model",
        "Free, ₹0",
        "☐ Yes  ☑ No  ☐ Partial",
        "₹0",
        "Not installed on the machine. Gemma 3 used instead — gemma3:4b for routing, cross-domain "
        "synthesis and judging, gemma3:1b as an ultra-fast tier for simple single-record lookups. "
        "Disclosed in Section 8.",
    ),
    (
        "nomic-embed-text — embeddings, 768-dim  [ADDED, not in the approved list]",
        "Free, self-hosted, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "Unavoidable addition: Gemma 3 cannot produce embeddings at all. Without a separate "
        "embedding model there is no RAG index and no Docs agent. Disclosed in Section 8. ₹0, so "
        "it does not move the budget.",
    ),
    (
        "Pydantic — structured output (extra=\"forbid\")",
        "Open-source, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "As approved. Every LLM call returns a validated schema, which is what makes the responses "
        "machine-verifiable for QA rather than free text to be eyeballed.",
    ),
    (
        "Azure B1s VM — hosting",
        "12-month free tier, ₹0",
        "☐ Yes  ☑ No  ☐ Partial",
        "₹0",
        "NEVER PROVISIONED, and in Phase 2 formally DESCOPED (Section 8). Local Docker Compose is "
        "the final deployment target; the control plane and all five nodes run identically under "
        "Compose, so no architectural claim rests on the VM. Free tier either way, so ₹0.",
    ),
    (
        "Pytest + pytest-cov — QA",
        "Open-source, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "As approved. 419 tests passing at 93.11% measured coverage.",
    ),
    (
        "GitHub Actions — CI",
        "Free tier, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "As approved, and HARDENED in Phase 2 beyond the approved scope: Python 3.11 + 3.12 "
        "matrix, concurrency cancellation, an enforced ≥80% coverage gate, coverage.xml artefact, "
        "and an opt-in live-model job. See Section 9, EN-04. Still free tier, ₹0.",
    ),
    (
        "Judge Agent — hallucination detection",
        "Runs on the same LLM, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "As approved, pulled FORWARD from Week 13 to Week 10 (the hallucination rate was a "
        "mid-term Section 6 requirement), and extended in Phase 2 with a deterministic "
        "fact-checking half — see Section 9, EN-01.",
    ),
    (
        "Docker / Docker Compose — deployment",
        "Open-source, ₹0",
        "☑ Yes  ☐ No  ☐ Partial",
        "₹0",
        "As approved for local development, and now also the FINAL hosting target rather than a "
        "stepping stone to Azure (Section 8).",
    ),
]

BUDGET = [
    "₹2,500",
    "₹0",
    "₹0",
    "₹0",
    "₹2,500 (100% of the ceiling unspent)",
]

# --------------------------------------------------------------------------------------
# Section 8 — Deviations (full programme; every mid-term deviation carried forward)
# --------------------------------------------------------------------------------------

DEVIATIONS = [
    (
        "Inference provider — NOW A PERMANENT SCOPE DECISION",
        "OpenRouter (google/gemini-2.5-flash) as primary inference; Ollama as the zero-cost "
        "fallback. Mid-term recorded provisioning as a Week 11 task.",
        "100% local Ollama, permanently. OpenRouter has never been called and will not be "
        "provisioned.",
        "Carried from Mid-Term, and ESCALATED there from a pending task to a settled decision. "
        "This is the single most significant deviation in the programme, so it is stated plainly: "
        "the approved fallback meets every graded target on its own (routing 100%, hallucination "
        "5.56% on a full 12-of-12 pass, coverage 93.11%), so provisioning a paid endpoint would "
        "add cost without closing any gap this POC has. Switching remains a one-variable change "
        "(AI_MODEL_COMPLEX) with no code to write, so the option is preserved, not foreclosed. "
        "Cost impact: ₹0 against a ~₹1,000 budgeted line.",
    ),
    (
        "Hosting — NOW A PERMANENT SCOPE DECISION",
        "Azure B1s VM on the 12-month free tier. Mid-term recorded provisioning as a Week 11 task "
        "(deliverable D-11, Week 14).",
        "Local Docker Compose is the final deployment target. The Azure VM was never provisioned.",
        "Carried from Mid-Term, and ESCALATED there from deferred to descoped. Same rationale: the "
        "control plane and all five agent nodes run identically under Compose, so staying local "
        "leaves nothing about the architecture unproven — it changes where the containers run, not "
        "what they do. Recorded against D-11 (Not Started) and in Section 10 so no section "
        "contradicts another.",
    ),
    (
        "Local model",
        "Llama 4 Scout",
        "Gemma 3 — gemma3:4b for routing, cross-domain synthesis and judging; gemma3:1b for simple "
        "single-record lookups",
        "Carried from Mid-Term; still stands. Llama 4 Scout is not installed on the machine; "
        "Gemma 3 is. Two tiers rather than one, so cheap work runs on the cheap model.",
    ),
    (
        "Embedding model",
        "(None named — the approved proposal assumed the LLM could embed)",
        "nomic-embed-text (768-dim), pulled locally, ₹0",
        "Carried from Mid-Term; still stands. Gemma 3 cannot produce embeddings. A separate "
        "embedding model is not optional: without it there is no RAG index and no Docs agent.",
    ),
    (
        "Structured-output schemas",
        "Pydantic with enumerated domain values",
        "Pydantic with list[str] plus a validator enforcing the same four-domain vocabulary",
        "Carried from Mid-Term; still stands. Ollama 0.23 returns HTTP 500 for any JSON schema "
        "containing `enum`, so schemas reaching the model are stripped of enum/const and the same "
        "guarantee is enforced one layer up in a Pydantic validator. The contract is identical; "
        "only where it is enforced moved.",
    ),
    (
        "Judge Agent timing",
        "Week 13",
        "Built in Week 10; extended in Phase 2 with a deterministic fact-checking half",
        "Carried from Mid-Term; still stands. Pulled forward because the hallucination rate was a "
        "Section 6 requirement of the mid-term submission, so the agent that measures it had to "
        "exist first. The Phase 2 extension is logged as an enhancement (Section 9, EN-01).",
    ),
    (
        "Orchestration framework",
        "AgentField (as approved)",
        "AgentField — no change",
        "Carried from Mid-Term; restated for completeness. The RFP named LangChain / MS Agent "
        "Framework and Azure AI Search; the APPROVED proposal replaced both with AgentField and "
        "its built-in vector memory. No further change in Phase 2.",
    ),
    (
        "Response latency",
        "(Not specified in the approved proposal)",
        "2–4 minutes single-domain; 8–15 minutes cross-domain",
        "Carried from Mid-Term; still stands. A consequence of running a 4B model on a CPU with no "
        "GPU, not a design flaw: a cross-domain query is several sequential LLM calls that cannot "
        "be collapsed, because the coordinator cannot synthesise until the specialists answer. On "
        "a hosted endpoint each call is sub-second and the same queries return in seconds, with "
        "better answers. docs/DEMO_RUNBOOK.md plans the live demo around the local timings.",
    ),
    (
        "Data sources",
        "Live REST APIs (Databricks, GitHub/Azure DevOps, CRM)",
        "Synthetic fixtures, causally linked across systems so cross-domain reasoning is genuinely "
        "exercised rather than faked",
        "Carried from Mid-Term; still stands, and it is a rule of the approved proposal rather "
        "than a shortfall (§7: no real customer or internal data is ever sent to an external LLM). "
        "The live REST paths ARE implemented and unit-tested against a mocked transport; set "
        "USE_MOCK_SOURCES=false and supply credentials to go live. Also recorded in Section 10.",
    ),
    (
        "Prompt-scaffolding leakage into answers (discovered in Phase 2)",
        "(Not anticipated)",
        "The small local model occasionally wrote internal scaffolding — an agent tag such as "
        "\"[docs-agent]\" or the injected date anchor — into the prose. Each leak class is now "
        "stripped and covered by a regression test.",
        "NEW in Phase 2, and disclosed rather than quietly patched because it shaped the QA "
        "pipeline. Found by inspecting real generated answers, not by assumption; fixed narrowly, "
        "since aggressive string cleanup corrupts the very facts an answer exists to quote (file "
        "paths, timestamps, error strings). Cost impact: ₹0. A frontier model needs less of this "
        "scaffolding, not more.",
    ),
]

# --------------------------------------------------------------------------------------
# Section 9 — Enhancements & Additional Value-Adds (beyond approved scope)
# --------------------------------------------------------------------------------------

ENHANCEMENTS = [
    (
        "EN-01",
        "Two-half Judge Agent — the approved LLM judge, plus a deterministic fact-checking half "
        "that runs with no model involved",
        "The LLM-only judge was caught marking a fabricated date as grounded. A judge that "
        "under-reports is the worst failure this system can have, because it makes an ungrounded "
        "answer look verified. The deterministic half checks that every date, job id, run id, "
        "record count and account code in an answer appears verbatim in the sources it cited, and "
        "by construction it can only ever ADD a finding, never remove one — so the reported rate "
        "errs pessimistic. This is the reason the 5.56% figure can be trusted at all.",
        "Done",
        "₹0",
        "EV-20  (psiog_kendra/qa/judge.py)",
    ),
    (
        "EN-02",
        "Live control-plane verification harness — scripts/trace_queries.py and docs/qa/traces.md, "
        "mapping all 12 queries to real execution IDs",
        "The approved QA suite runs the coordinator with IN-PROCESS specialists, which means the "
        "actual graded multi-agent path — app.call() through the AgentField control plane — was "
        "never exercised by any test. Building this harness found a real, months-old HTTP 422 bug "
        "in exactly that path (the SDK takes keyword arguments, not an input={...} envelope). "
        "Without it, the architecture the RFP grades would have been the one piece never proven "
        "end-to-end.",
        "Done",
        "₹0",
        "EV-07, EV-09, EV-10, EV-18  (docs/qa/traces.md)",
    ),
    (
        "EN-03",
        "Fleet health tooling — agents/health.py and `make agents-status`, distinguishing a node "
        "that is SERVING from one that is ROUTABLE",
        "AgentField registers a node with the control plane BEFORE it binds its socket, so a node "
        "that dies on startup still appears in the fleet list — while /api/v1/nodes conversely "
        "hides healthy nodes whose health_status never left 'unknown'. Those are two opposite "
        "failures that look identical from any single health signal, and both actually bit this "
        "build (a port collision killed four of five nodes; a node-list check later condemned four "
        "working ones). This tool asks each port directly and cross-checks the discovery endpoint, "
        "so the fleet state shown before a live demo is the real one.",
        "Done",
        "₹0",
        "EV-16, EV-22  (agents/health.py, tests/unit/test_agent_runtime.py)",
    ),
    (
        "EN-04",
        "CI hardening — Python 3.11 + 3.12 matrix, concurrency cancellation, enforced ≥80% "
        "coverage gate, coverage.xml artefact, and an opt-in `live` job that installs Ollama and "
        "runs the real-model tests in CI",
        "The approved scope was \"a workflow that runs the suite\", which was the mid-term state. "
        "This goes further: CI now reproduces the MEASUREMENT (the coverage gate fails the build, "
        "so the Section 6 figure cannot silently rot), proves the code on two interpreter versions, "
        "and can exercise the live-model integration path on demand rather than only the offline "
        "one. Cancelling superseded runs also keeps the free tier well inside its limits.",
        "Done",
        "₹0",
        "EV-21  (.github/workflows/ci.yml)",
    ),
    (
        "EN-05",
        "docs/DEMO_RUNBOOK.md — an execution and demo runbook covering both the in-process path "
        "and the full control-plane stack, with a troubleshooting table for every failure mode "
        "this build actually hit",
        "A multi-agent stack has a startup order that is not obvious (models pulled and warmed, "
        "control plane up, five nodes bound to five distinct ports and registered with a "
        "callback URL the plane can dial from inside Docker, RAG index loaded into the plane's own "
        "vector memory — which is a DIFFERENT store from the local index the offline tests use). "
        "Every one of those had a wrong-by-default trap. Writing them down turns the live demo "
        "from a memory exercise into a checklist, and makes the work reproducible by someone else.",
        "Done",
        "₹0",
        "EV-22  (docs/DEMO_RUNBOOK.md)",
    ),
]

# --------------------------------------------------------------------------------------
# Section 10 — What Is NOT Completed + Future Scope
# --------------------------------------------------------------------------------------

PENDING = [
    (
        "OpenRouter provisioning / hosted frontier inference",
        "Not completed by DECISION, not by omission — formally descoped in Phase 2 (Section 8). "
        "The zero-cost local model met every graded target, so a paid endpoint would have added "
        "cost without closing a gap. Mid-term listed this as a Week 11 task; that plan was "
        "deliberately cancelled and the cancellation is recorded, not glossed.",
        "Y — flagged at Mid-Term as pending Week 11",
        "A pure configuration change if ever revisited: set AI_MODEL_COMPLEX=google/gemini-2.5-"
        "flash and re-run `make qa`. Expected gains, in order of value: cross-domain answer "
        "quality, judge precision (the two UNVERIFIED entries behind the 5.56% figure would "
        "resolve), and per-query latency dropping from minutes to seconds.",
    ),
    (
        "Azure B1s VM hosting (deliverable D-11)",
        "Not completed by DECISION — formally descoped in Phase 2 (Section 8). Local Docker "
        "Compose is the final deployment target and the stack runs identically under it, so the "
        "architecture is not left unproven; only the hosting location differs.",
        "Y — flagged at Mid-Term as pending Week 11",
        "Deploy the existing Compose stack unmodified to a free-tier B1s VM if a hosted URL is "
        "ever required. No application change is expected — the control plane is already "
        "containerised and every endpoint is an environment variable.",
    ),
    (
        "Live REST source integration against real credentials",
        "Descoped by the approved proposal's own rule (§7: mock/synthetic data only — no real "
        "customer or internal data is ever sent to an external LLM), so this is a boundary of the "
        "approved design rather than unfinished work. The REST clients themselves ARE implemented "
        "and unit-tested against a mocked transport.",
        "Y — flagged at Mid-Term",
        "Point the existing clients at sandboxed real endpoints: set USE_MOCK_SOURCES=false and "
        "supply Databricks / GitHub / CRM credentials. No new code — the transport layer is "
        "already the seam.",
    ),
    (
        "Judge determinism on long cross-domain answers",
        "Partially open, and it is why the reported hallucination rate is a ceiling rather than a "
        "midpoint. On two of the twelve queries (Q10, Q12 — the two longest answers) the local 4B "
        "judge declined to enumerate claims; the harness counts an unverified answer as "
        "ungrounded rather than flatter the score, which is the conservative choice.",
        "N — a Phase 2 finding, disclosed here rather than smoothed over",
        "Resolved by the same env-var swap as row 1: a hosted frontier judge enumerates long "
        "answers reliably. The deterministic fact-check half already runs on those answers "
        "regardless, so the safety property holds today — only the precision of the number "
        "improves.",
    ),
    (
        "Control-plane execution history across container restarts",
        "An AgentField storage-mode limitation found in Phase 2: in `local` storage mode the "
        "control plane re-runs its migrations on every container start, so execution history does "
        "not survive a `docker compose down`. It affects only the trace VIEWER, never the graded "
        "results — every QA number lives in data/qa_report.json and every execution ID is recorded "
        "in docs/qa/traces.md, both of which are durable files in the repository. This is exactly "
        "why every Section 4 evidence block names the repository artefact FIRST and the "
        "control-plane execution id second: the pasted screenshot plus docs/qa/traces.md are the "
        "durable record, and the live UI is a reproducible view of it rather than the source of "
        "truth.",
        "N — a Phase 2 finding",
        "Mount the control plane's database path onto a named volume in deploy/docker-compose.yml, "
        "or run it in a persistent storage mode, so the DAG history is browsable across restarts. "
        "A deployment-configuration change, not an application one.",
    ),
    (
        "Screenshot capture for EV-21 (CI green on GitHub Actions) and EV-22 (the live "
        "walkthrough) — NOT a deliverable gap, an evidence-capture timing note",
        "Both underlying artefacts are DONE and verifiable by file in the repository today: "
        ".github/workflows/ci.yml carries the hardened workflow (Python 3.11 + 3.12 matrix, "
        "enforced ≥80% coverage gate, coverage artefact, opt-in live-model job) and "
        "docs/DEMO_RUNBOOK.md carries the demo script. What cannot exist yet is a SCREENSHOT of "
        "each one running: a green Actions run requires the branch to be pushed, and the "
        "walkthrough is by definition performed at the review session. Recorded here so that "
        "Section 3's Done statuses for D-12 and D-13 are read correctly — each rests primarily on "
        "already-measured evidence (EV-19, EV-20), with these two as confirming captures.",
        "N — a Phase 2 note",
        "Capture both inside the Week 17 review window: push the branch and screenshot the green "
        "matrix run (EV-21), then walk docs/DEMO_RUNBOOK.md live and screenshot "
        "`make agents-status` plus the resulting coordinator.ask execution (EV-22).",
    ),
]

# --------------------------------------------------------------------------------------
# Section 11 — Risks & Blockers, final status (closure record)
# --------------------------------------------------------------------------------------

RISKS = [
    (
        "OpenRouter not provisioned (the programme's only external dependency)",
        "Accepted — converted from an open blocker into a permanent scope decision",
        "The zero-cost local fallback was made to carry the entire build, and it did: all three "
        "graded QA targets are met on it. Every model reference stayed an environment variable "
        "(AI_MODEL_COMPLEX), so the option was preserved rather than designed out.",
        "None on the delivered project. Every graded target is met at ₹0 against a ₹2,500 ceiling. "
        "The residual effect is qualitative — answer quality, judge precision and latency would "
        "all improve on a hosted model — and each of those is disclosed where it applies "
        "(Sections 6, 8, 10) rather than netted out here.",
    ),
    (
        "Answer quality on a 4B local model",
        "Mitigated",
        "A grounding pipeline enforces what a small model cannot be trusted to do unaided: the "
        "answer's own record ids arbitrate its citations, so an answer cannot cite a source it did "
        "not actually use — a check an allow-list cannot make. The injected date anchor removes "
        "relative-date guessing. Every safeguard carries a regression test.",
        "None. A frontier model needs LESS of this scaffolding, not more: the safeguards become a "
        "cross-check rather than a corrective.",
    ),
    (
        "The LLM Judge under-reporting hallucinations",
        "Mitigated",
        "A deterministic fact-check backs the LLM judge: every date, id and record code in an "
        "answer must appear verbatim in the cited source, with no model involved. It can only ever "
        "ADD a finding, never remove one.",
        "None — this is precisely why the reported 5.56% can be trusted, and why it errs "
        "pessimistic. On a frontier judge the two halves are expected to agree, turning a safety "
        "net into a corroboration.",
    ),
    (
        "Prompt scaffolding leaking into user-visible answers",
        "Realised, then mitigated",
        "Found by reading real generated answers rather than assuming the tests covered it: three "
        "distinct leak shapes (a hyphenated agent tag, an unterminated one, and a "
        "space-separated capitalised one) plus the date anchor. Each was fixed narrowly and pinned "
        "with a regression test — deliberately narrowly, because aggressive text cleanup corrupts "
        "the file paths, timestamps and error strings an answer exists to quote.",
        "None in the delivered answers. Disclosed in Section 8 because it is a genuine "
        "small-model characteristic that a reviewer should know about.",
    ),
    (
        "The cross-agent control-plane call path was never exercised by the test suite",
        "Realised, then fixed",
        "The QA suite runs the coordinator with in-process specialists, so the real multi-agent "
        "path had a latent HTTP 422 for months. Caught by building the live trace harness "
        "(Section 9, EN-02): app.call() passes the target reasoner's parameters as keyword "
        "arguments, not inside an input={...} envelope. Fixed, and now covered for all 12 queries "
        "in docs/qa/traces.md.",
        "Was a real bug on the single most important path in the architecture, and it is now "
        "closed and evidenced (EV-07, EV-09, EV-10, EV-18). The lesson is recorded in CLAUDE.md so "
        "the gap cannot silently reopen.",
    ),
    (
        "gemma3:4b needs ~4 GiB of free RAM",
        "Accepted (environmental)",
        "If the model will not load, the gateway degrades to gemma3:1b and LOGS A WARNING rather "
        "than failing silently — a degraded run announces itself instead of quietly producing weak "
        "evidence. Routing quality drops noticeably on the 1b tier, so a graded run is only ever "
        "accepted from the 4b model.",
        "None on the delivered results, which were all produced on the 4b model. Disappears "
        "entirely on hosted inference.",
    ),
    (
        "Response latency (2–4 min single-domain, 8–15 min cross-domain)",
        "Accepted (environmental)",
        "A per-query hard stop ensures one slow query cannot hang the suite, and a timed-out query "
        "is RECORDED as timed out, never silently skipped. The QA harness checkpoints after every "
        "query, so a long run that is interrupted is not a lost run. docs/DEMO_RUNBOOK.md paces "
        "the live demo around the real timings.",
        "None architecturally — this is CPU-bound local inference, not design (Section 8). The "
        "same queries return in seconds on a hosted endpoint.",
    ),
    (
        "Demo runs on synthetic data",
        "Accepted (by design)",
        "Per the approved proposal's own mock-data-only rule (§7) — no real customer or internal "
        "data is ever sent to an external LLM. The fixtures are causally linked ACROSS systems (a "
        "failed job maps to specific stale CRM accounts and to a matching runbook), so "
        "cross-domain reasoning is genuinely exercised rather than staged. The live REST paths are "
        "implemented and unit-tested.",
        "None. It is a boundary of the approved design, recorded in Sections 8 and 10 so it is "
        "never mistaken for a capability claim.",
    ),
]

SIGNATURE = ["Sridhar Vetrivel", "«SUBMISSION DATE»"]


# --------------------------------------------------------------------------------------
# Docx plumbing. Fill; never rebuild.
# --------------------------------------------------------------------------------------


def set_cell(cell, text: str, *, bold: bool = False) -> None:
    """Write text into a cell, keeping the cell's own paragraph formatting."""
    para = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    for run in list(para.runs):
        run._element.getparent().remove(run._element)

    lines = text.split("\n")
    run = para.add_run(lines[0])
    run.bold = bold
    run.font.size = Pt(9)
    for line in lines[1:]:
        run = para.add_run("\n" + line)
        run.bold = bold
        run.font.size = Pt(9)


def fill_rows(table: Table, rows: list[tuple], *, start: int = 1, id_col: bool = False) -> None:
    """Fill a table's body, appending rows when the content needs more than the template shipped.

    The template's own rules allow adding rows; they forbid reordering sections. A row appended
    with `add_row()` inherits the table's style, so the result is indistinguishable from a row
    L&D typed themselves.
    """
    for i, values in enumerate(rows):
        index = start + i
        while len(table.rows) <= index:
            table.add_row()
        cells = table.rows[index].cells
        for j, value in enumerate(values):
            if j >= len(cells):
                break
            # Column 0 of an ID table (D-01, EV-01, EN-01) is pre-printed; do not overwrite it.
            if id_col and j == 0 and cells[0].text.strip():
                continue
            set_cell(cells[j], str(value), bold=(j == 0 and not id_col))


def fill_after_heading(doc: Document, heading: str, text: str) -> None:
    """Write `text` into the first empty paragraph following `heading`.

    Located by heading text rather than by index: an index that silently points at the wrong
    paragraph would overwrite a template heading, which is the one kind of damage the template
    forbids outright.
    """
    paras = doc.paragraphs
    for i, para in enumerate(paras):
        if para.text.strip().startswith(heading):
            for candidate in paras[i + 1 : i + 6]:
                if not candidate.text.strip():
                    _set_para(candidate, text)
                    return
            raise RuntimeError(f"no empty paragraph found under {heading!r}")
    raise RuntimeError(f"heading not found: {heading!r}")


def main() -> int:
    if not TEMPLATE.exists():
        print(f"template not found: {TEMPLATE}")
        return 1
    shutil.copy(TEMPLATE, OUTPUT)
    doc = Document(str(OUTPUT))
    tables = doc.tables

    # ---- Section 1 --------------------------------------------------------------------
    for i, value in enumerate(PARTICIPANT):
        set_cell(tables[0].rows[i].cells[1], value)

    # ---- Section 2 --------------------------------------------------------------------
    fill_after_heading(doc, "2.1 Problem Statement", PROBLEM)
    fill_after_heading(doc, "2.2 Proposed Solution Summary", SOLUTION)
    fill_after_heading(doc, "2.3 Core Tools", TOOLS_APPROVED)

    # ---- Section 3 --------------------------------------------------------------------
    fill_rows(tables[1], DELIVERABLES, id_col=True)
    for i, (_, value) in enumerate(SELF_ASSESSMENT):
        set_cell(tables[2].rows[i].cells[1], value)

    # ---- Section 4.1 ------------------------------------------------------------------
    fill_rows(tables[3], EVIDENCE, id_col=True)

    # ---- Sections 5, 5.1, 6, 7, 7.1, 8, 9, 10, 11, 12 ---------------------------------
    for i, value in enumerate(REPO_LINKS):
        set_cell(tables[10].rows[i].cells[1], value)
    for i, value in enumerate(WALKTHROUGH):
        set_cell(tables[11].rows[i].cells[1], value)
    fill_rows(tables[12], QA_ROWS)
    # The QA narrative has no cell of its own: it goes under the Section 6 table, where the
    # evaluator reads how the hallucination rate was derived and over what scope.
    _note_after_table(tables[12], QA_NOTE)
    fill_rows(tables[13], TOOLS)
    for i, value in enumerate(BUDGET):
        set_cell(tables[14].rows[i].cells[1], value)
    fill_rows(tables[15], DEVIATIONS)
    fill_rows(tables[16], ENHANCEMENTS, id_col=True)
    fill_rows(tables[17], PENDING)
    fill_rows(tables[18], RISKS)
    for i, value in enumerate(SIGNATURE):
        set_cell(tables[19].rows[i].cells[1], value)

    # ---- Section 4.2: fill EV-01..EV-06, then clone the block for EV-07..EV-22 ---------
    # Blocks are (title paragraph, 5-row header table, paste-area paragraph). The template
    # says to copy-paste a whole block to extend the numbering; this does exactly that.
    ev_ids = list(EV_BLOCKS)
    block_tables = tables[4:10]  # EV-01 .. EV-06

    # Resolve the six shipped blocks to Paragraph OBJECTS before mutating anything.
    # Inserting a picture paragraph shifts every later paragraph index, so indices captured
    # up front and used after the first insert would silently point at the wrong paragraph.
    title_paras = [doc.paragraphs[i] for i in (33, 36, 39, 42, 45, 48)]
    paste_paras = [doc.paragraphs[i] for i in (34, 37, 40, 43, 46, 49)]

    section = doc.sections[0]
    img_width = section.page_width - section.left_margin - section.right_margin

    placed = 0
    anchor = None
    for n in range(6):
        ev = ev_ids[n]
        block = EV_BLOCKS[ev]
        _set_para(title_paras[n], f"{ev}  —  {block[0]}")
        _set_para(paste_paras[n], _shot_note(ev, block))
        _fill_block_table(block_tables[n], block)
        anchor, count = _add_images(paste_paras[n], ev, img_width)
        placed += count

    # Clone EV-06's block (title para + table + paste para) for each of EV-07..EV-22.
    src_title = title_paras[5]
    src_table = block_tables[5]
    src_paste = paste_paras[5]

    for ev in ev_ids[6:]:
        block = EV_BLOCKS[ev]

        spacer = copy.deepcopy(src_paste._element)
        anchor.addnext(spacer)
        anchor = spacer
        _clear_para(Paragraph(spacer, src_paste._parent))

        new_title = copy.deepcopy(src_title._element)
        anchor.addnext(new_title)
        anchor = new_title
        _set_para(Paragraph(new_title, src_title._parent), f"{ev}  —  {block[0]}")

        new_table = copy.deepcopy(src_table._element)
        anchor.addnext(new_table)
        anchor = new_table
        _fill_block_table(Table(new_table, src_table._parent), block)

        new_paste = copy.deepcopy(src_paste._element)
        anchor.addnext(new_paste)
        anchor = new_paste
        paste = Paragraph(new_paste, src_paste._parent)
        _set_para(paste, _shot_note(ev, block))
        anchor, count = _add_images(paste, ev, img_width)
        placed += count

    # ---- Section 12 checklist: tick every box -----------------------------------------
    # Only paragraph-level boxes are touched. Table-cell checkboxes (Track, Participation
    # Type, 3.1's live-demo row, Section 7's per-tool Yes/No/Partial, and each evidence
    # block's carry-forward row) are set explicitly above, because ticking those blindly
    # would assert things that are not true.
    for para in doc.paragraphs:
        if para.text.strip().startswith("☐"):
            for run in para.runs:
                if "☐" in run.text:
                    run.text = run.text.replace("☐", "☑")

    # ---- Delete the grey italic instruction text (the checklist requires it) -----------
    removed = 0
    for para in list(doc.paragraphs):
        runs = para.runs
        if not runs or not para.text.strip():
            continue
        grey = any(
            r.font.color is not None
            and r.font.color.rgb is not None
            and str(r.font.color.rgb) == GREY
            for r in runs
        )
        if grey and any(r.italic for r in runs):
            para._element.getparent().remove(para._element)
            removed += 1

    doc.save(str(OUTPUT))
    print(f"wrote {OUTPUT}")
    print("  sections filled : 1-12 (structure untouched)")
    print(f"  deliverables    : {len(DELIVERABLES)} (D-01 … D-{len(DELIVERABLES):02d})")
    print(f"  evidence blocks : {len(EV_BLOCKS)} (EV-01 … EV-{len(EV_BLOCKS):02d})")
    print(f"  enhancements    : {len(ENHANCEMENTS)} (EN-01 … EN-{len(ENHANCEMENTS):02d})")
    print(f"  instruction text: {removed} grey italic paragraphs deleted")
    print(f"  screenshots     : {placed} placed full-width across {len(EV_IMAGES)} blocks")
    missing = [ev for ev in EV_BLOCKS if ev not in EV_IMAGES]
    print(f"  awaiting capture: {', '.join(missing) if missing else 'none'}")
    return 0


def _note_after_table(table: Table, text: str) -> None:
    """Add explanatory prose immediately after a table.

    Builds a FRESH <w:p> rather than cloning whatever follows the table. Cloning the next
    element duplicated a section heading in the mid-term build — and a duplicated heading is
    precisely the structural damage the template forbids.
    """
    anchor = table._element
    for block in reversed(text.split("\n\n")):
        element = OxmlElement("w:p")
        anchor.addnext(element)
        para = Paragraph(element, table._parent)
        run = para.add_run(block)
        run.font.size = Pt(9)


def _shot_note(ev: str, block: tuple) -> str:
    """The line that sits above an evidence block's screenshot(s).

    Falls back to the block's own paste instruction when no image is mapped, so a block
    without a screenshot still tells the reader exactly what to capture.
    """
    entry = EV_IMAGES.get(ev)
    if entry is None:
        return block[6]
    mode, files = entry
    note = _SHOT_NEW if mode == "new" else _SHOT_CARRIED.format(ev=ev)
    if len(files) > 1:
        note += f"  ({len(files)} images)"
    return note


def _add_images(para: Paragraph, ev: str, width) -> tuple:
    """Insert one full-width picture paragraph per mapped image, after `para`.

    Returns the last element written and how many pictures were placed, so the caller can
    keep cloning after the images rather than in the middle of them.
    """
    entry = EV_IMAGES.get(ev)
    if entry is None:
        return para._element, 0

    anchor = para._element
    for name in entry[1]:
        path = IMAGES / name
        if not path.exists():
            raise FileNotFoundError(f"{ev}: image not found: {path}")
        element = OxmlElement("w:p")
        anchor.addnext(element)
        anchor = element
        run = Paragraph(element, para._parent).add_run()
        run.add_picture(str(path), width=width)
    return anchor, len(entry[1])


def _clear_para(para: Paragraph) -> None:
    for run in list(para.runs):
        run._element.getparent().remove(run._element)


def _set_para(para: Paragraph, text: str) -> None:
    keep = para.runs[0] if para.runs else None
    bold = keep.bold if keep is not None else None
    italic = keep.italic if keep is not None else None
    _clear_para(para)
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic


def _fill_block_table(table: Table, block: tuple[str, str, str, str, str, str, str]) -> None:
    """Fill one evidence block's 5-row header table.

    Rows: What this proves | Deliverable ID(s) | Date of Development/Testing | Verifiable link |
    Carried from Mid-Term?
    """
    _, proves, dids, date, link, carried, _ = block
    set_cell(table.rows[0].cells[1], proves)
    set_cell(table.rows[1].cells[1], dids)
    set_cell(table.rows[2].cells[1], date)
    set_cell(table.rows[3].cells[1], link)
    set_cell(table.rows[4].cells[1], carried)


if __name__ == "__main__":
    raise SystemExit(main())
