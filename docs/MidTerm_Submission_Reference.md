# Mid-Term Submission — Template Reference

Reference notes on `docs/pSiddhi3_0_MidTerm_Submission_Template.docx` (IMPACT pSiddhi 3.0,
Psiog L&D). Captures the template's structure, rules, and every field to fill, plus how **Psiog
Kendra** maps onto it. **Not filled yet** — this is a scaffold for when we assemble evidence in
the Week 10 review window.

> **Purpose of the submission doc:** Records what we have **ACTUALLY built and verified up to
> the end of Week 9**, measured against the L&D-approved proposal ([docs/solution-proposal.md](solution-proposal.md)).
> Do NOT include Week 10+ plans as progress.

## Key facts

| Item | Value |
|---|---|
| Submission deadline | End of Week 9 / start of Week 10 review window — **13-Jul-26** |
| Mid-Term review window | Week 10 (13-Jul-26 to 17-Jul-26) |
| Covers | Development up to **end of Week 9** |
| Save filename as | `[TopicID]_[ParticipantName]_MidTermDoc.docx` → `S4-I-24_SridharVetrivel_MidTermDoc.docx` |
| Scored by | An **AI scoring engine** — structure must stay identical |

## Hard rules (from "READ BEFORE FILLING")

1. Record only what is **actually built and verified** by end of Week 9, against the **approved**
   proposal (not the original draft). No Week 10+ plans as progress.
2. Evidence is one consolidated **Evidence Pack** (Section 4), IDs `EV-01, EV-02, …`. No
   week-by-week split.
3. Every deliverable marked **Done/Partial** in Section 3 MUST point to ≥1 Evidence ID. A claim
   with no evidence is scored **Not Started**.
4. Screenshots pasted **full-size and readable** directly in the doc (no collages/thumbnails);
   add a verifiable link (GitHub commit/PR, deployed URL, notebook, CI run) wherever possible.
5. **Do NOT rename, delete, renumber, or reorder sections.** Adding table rows / evidence blocks
   is fine.
6. Replace all grey italic instruction text with real content, then delete the instruction lines.
7. Status vocabulary is exactly: **Done / Partial / Not Started**.
8. Coverage % must be a **measured** figure from a coverage tool (attach as evidence), never an
   estimate.

## Section-by-section structure

### 1. Participant & Project Identification
Table — copy exactly from the L&D Final Decision (Part D); mismatched Topic ID delays evaluation.

| Field | Our value |
|---|---|
| Topic ID | S4-I-24 |
| Topic Title | GenAI-Powered Enterprise Copilot |
| Participant Name | Sridhar Vetrivel |
| Employee ID | *(fill)* |
| Track | ☐ Custom  ☐ Data  ☐ Platform — *(likely Custom; confirm)* |
| Semester & Category | Semester 4 — Integration Mastery (Capstone) |
| Participation Type | ☐ Regular  ☐ pSiddhi Lite — *(confirm)* |
| Approved Budget Ceiling | ₹2,500 (fixed) |
| Mid-Term Review Window | Week 10 (13-Jul-26 to 17-Jul-26) |

### 2. Approved Proposal Recap (3–5 sentences per field, summarised — not rewritten)
- **2.1 Problem Statement (as approved)** — fragmented estate, tribal knowledge, hallucination
  risk. Source: [docs/solution-proposal.md](solution-proposal.md) § 1.
- **2.2 Proposed Solution Summary (as approved)** — coordinator + 4 specialists on AgentField;
  core layers only, not implementation detail. Source: solution-proposal § 2–3.
- **2.3 Core Tools & AI Components (as approved)** — AgentField, OpenRouter (Gemini 2.5 Flash),
  Ollama/Llama 4 Scout fallback, Pydantic, Azure B1s, Pytest + Judge Agent. Full reconciliation
  goes in Section 7.

> ⚠️ **Actual LLM inference so far:** OpenRouter is **not yet provisioned**, so all LLM calls run
> on the **local Ollama** model (`gemma3:4b`, with `gemma3:1b` as a fast fallback) at ₹0. The
> approved proposal named **Llama 4 Scout** as the local model, but the machine has **Gemma 3**
> installed. Both facts are deviations — capture them in Section 7 (tool reconciliation) and
> Section 8 (deviations).

### 3. Progress Against Approved Plan (up to Week 9) — **the core section**
Table `D-01…D-08`: list **every** deliverable the approved proposal committed for **Weeks 4–9**
(copy from our timeline). Columns: **ID | Planned Deliverable | Planned Window | Status |
Evidence ID(s)**. Done/Partial require Evidence IDs.

Our Weeks 4–9 deliverables (from [../Implementation.md](../Implementation.md) § 8 / solution-proposal § 8) map to:

| ID | Planned Deliverable | Window |
|---|---|---|
| D-01 | AgentField control plane via Docker Compose; Azure VM provisioned; OpenRouter connected | Week 4 |
| D-02 | Coordinator Agent — intent classification + routing; Pydantic schemas defined | Week 5 |
| D-03 | Data Platform Agent — Databricks REST connected; job status/history; unit tests | Week 6 |
| D-04 | Docs Agent + RAG index — docs chunked/embedded/indexed; similarity search working | Week 7 |
| D-05 | DevOps Agent — GitHub/Azure DevOps connected; build status, deployments, quality gates | Week 8 |
| D-06 | CRM Agent — CRM/mock connected; contact/deal/account queries | Week 9 |
| D-07 | ≥6 of 12 test queries returning grounded, cited responses (checkpoint sub-goal) | Week 9–10 |
| D-08 | Unit tests passing for skill functions; coverage ≥50% (checkpoint sub-goal) | Week 9–10 |

**3.1 Overall Mid-Term Self-Assessment** (Table 2): summarise the RFP Week 10 checkpoint, give a
**defensible %** completed, and tick demonstrable-live state (☐ end-to-end / ☐ partially / ☐
screenshots only). RFP Week 10 checkpoint = 2+ specialist agents operational, semantic index
populated, routing across ≥2 domains, initial grounded/cited responses, unit tests passing,
mid-term docs on Moodle.

### 4. Evidence Pack (whole period)
- **4.1 Evidence Index** (Table): one row per block — **Evidence ID | Caption (what it proves) |
  Deliverable ID(s) | Verifiable link**. Captions must be specific ("routing correctly sends
  query #1 to data-agent with citation", not "screenshot of app").
- **4.2 Evidence Blocks** `EV-01…EV-06` provided (copy-paste for EV-07+). Each block has a
  one-line title, a header table (**What this proves | Deliverable ID | Date captured | Verifiable
  link**), and pasted full-size screenshot(s). Don't reuse a screenshot across two EV IDs.

### 5. Working Demo & Repository Links
Table — checked directly at evaluation. Repo must be accessible to L&D; deployed URLs live during
the Week 10 window. Use "N/A" where genuinely N/A, never blank.

| Field | Note |
|---|---|
| Code repository URL | *(GitHub repo — make L&D-accessible)* |
| Latest commit ID + date | *(as of submission)* |
| Deployed / hosted URL | *(Azure B1s, if live by Wk 9; else N/A)* |
| Demo video / recording link | optional |
| Notebook / dashboard / other artefact links | *(fill or N/A)* |

### 6. QA Progress (up to Week 9)
Table — **Test Type | Tests written/run | Coverage achieved (measured) | Target (per proposal) |
Evidence ID(s)**. Only QA actually executed. Coverage must be a real tool figure attached as an
EV block. Our targets: routing accuracy 100% on 12 queries, hallucination <10%, overall coverage
≥80% (mid-term interim: ≥50% unit).

### 7. Tool & Budget Reconciliation
- **Table 12** — every approved tool (**including ones not used**): Tool | Approved tier & cost |
  Used by Wk 9? (Yes/No/Partial) | Actual cost ₹ | Reason if changed/not used. Silent
  substitutions get flagged. Note: proposal already swaps the RFP's LangChain/MS Agent Framework
  → AgentField and Azure AI Search → AgentField vector memory (disclose here + Section 8).
- **7.1 Budget Summary** (Table 13): ceiling ₹2,500 | estimated spend at approval | actual spend
  till Wk 9 | buffer remaining | anticipated spend before Wk 17.

### 8. Deviations from Approved Proposal
Table — **Item | Approved plan | Actual implementation | Reason for change**. List ANY change
(scope, architecture, tool, timeline, descoping) and advisories considered. If none, write
"None" in row 1 — do not delete the section.

### 9. What Is NOT Completed Yet + Plan for Weeks 11–16
Table — **Pending item | Why pending | Plan to complete (target week)**. Cross-checked against
Sections 3 & 4 — a "Done" that also appears here (or vice versa) = inflated reporting.

### 10. Risks & Blockers
Table — **Risk/Blocker | Status (Open/Mitigated/Realised) | Mitigation taken so far | Impact /
support needed**. Carry forward proposal risks; add new ones; flag anything needing L&D support now.

### 11. Declaration & Pre-Submission Checklist
Checkboxes (all must be ticked) + participant signature/name + submission date. Confirms Section 1
matches Part D, every Done/Partial has evidence, coverage is measured, all tools listed,
deviations disclosed, instruction text deleted, sections not reordered, correct filename.

## Consistency cross-checks the AI evaluator runs

- Section 3 Done/Partial ↔ must have Section 4 Evidence IDs.
- Section 3 status ↔ Section 9 pending list must not contradict.
- Section 6 coverage ↔ must be a measured EV, not an estimate.
- Section 7 ↔ every approved tool listed, swaps explained; ties to Section 8 deviations.
- Section 1 Topic ID ↔ L&D Final Decision (Part D) exactly.
- Section 3.1 % ↔ defensible from the Section 3 table.

## When we fill this (Week 10)

1. Freeze what's genuinely Done/Partial by end of Week 9 — no aspirational statuses.
2. Capture evidence first (screenshots + commit links), assign EV IDs, then wire D-IDs → EV-IDs.
3. Run the coverage tool, screenshot the real number for Section 6.
4. Generate the filled `.docx` (can extend `scripts/build_proposal_docx.py` for this template),
   preserving section order/numbering exactly.
5. Work the Section 11 checklist last; save as `S4-I-24_SridharVetrivel_MidTermDoc.docx`.