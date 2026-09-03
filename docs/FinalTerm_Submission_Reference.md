# Final-Term Submission — Template Reference

Reference notes on `docs/pSiddhi3_0_FinalTerm_Submission_Template 1.docx` (IMPACT pSiddhi 3.0,
Psiog L&D). Captures the template's structure, rules, and every field to fill, plus how **Psiog
Kendra** maps onto it. **Not filled yet** — this is a scaffold for when we assemble evidence in
the Week 17 review window. Companion to [MidTerm_Submission_Reference.md](MidTerm_Submission_Reference.md),
which this document's numbering and carry-forward rules build directly on.

> **Purpose of the submission doc:** An **end-to-end record of the FULL programme, Week 4–17** —
> not a delta on the mid-term. It is evaluated **together with** the mid-term submission
> (`docs/S4-I-24_SridharVetrivel_MidTermDoc.docx`), so unchanged items may be **carried forward**
> by reference instead of re-documented; anything that changed must be updated to its current
> state.

## Key facts

| Item | Value |
|---|---|
| Covers | The **entire programme**, Week 4 through Week 17 |
| Final Review Window | Week 17 — *(L&D to confirm exact dates before circulation)* |
| Mid-Term document to pair | `S4-I-24_SridharVetrivel_MidTermDoc.docx` (already submitted; filename must match exactly) |
| Save filename as | `[TopicID]_[ParticipantName]_FinalTermDoc.docx` → `S4-I-24_SridharVetrivel_FinalTermDoc.docx` |
| Scored by | An **AI scoring engine** — structure must stay identical; cross-checked against the mid-term doc |

## Hard rules (from "READ BEFORE FILLING")

1. Record what is **actually built and verified across the full programme** (Week 4–17), against
   the **approved** proposal including any changes formally agreed with L&D during Phase 2. This
   is an end-to-end record, not a delta.
2. **Carry-forward is explicit, not implicit.** An item unchanged since mid-term is marked
   `Carried = Y` (Section 3) or "Carried from Mid-Term? Yes — EV-___" (Section 4) and briefly
   reconfirmed — not silently omitted, and not re-typed in full. Anything that changed must be
   updated to its **current** state, not left as the mid-term description.
3. **Every** deliverable the approved proposal committed to across the **full programme** must
   appear in Section 3 — including the ones already reported at mid-term. **Reuse mid-term D-IDs**
   for existing deliverables (`D-01`…`D-08`); **continue the sequence** (`D-09`, `D-10`, …) for
   anything new in Phase 2. Same rule for EV numbering: continue from mid-term's `EV-01`…`EV-18`.
4. Every deliverable marked **Done/Partial** in Section 3 must point to ≥1 Evidence ID — here, or
   (if carried) in the mid-term document. A claim with no evidence is scored **Not Started**.
5. Screenshots pasted **full-size and readable** directly in the doc (no collages/thumbnails);
   add a verifiable link (GitHub commit/PR, deployed URL, notebook, CI run) wherever possible.
6. **Do NOT rename, delete, renumber, or reorder sections.** Adding table rows / evidence blocks
   is fine.
7. Replace all grey italic instruction text with real content, then delete the instruction lines.
8. Status vocabulary is exactly: **Done / Partial / Not Started**.
9. Coverage % must be a **measured** figure from a coverage tool (attach as evidence), never an
   estimate.
10. **New this template:** a mandatory **Live Code Walkthrough plan** (§5.1) — name the module/
    flow ahead of time; the evaluator checks the stated file paths exist in the repo.
11. **New this template:** an **Enhancements & Additional Value-Adds** section (§9) — beyond-scope
    work, each with its own Evidence ID and cost impact (₹0 is a valid answer, but it must
    reconcile with §7's budget total).

## Section-by-section structure

### 1. Participant & Project Identification
Same fields as mid-term, plus two new ones. Copy exactly from the L&D Final Decision (Part D);
the mid-term filename here **must match** what was actually uploaded to Moodle at Week 10 (used
to pair the two documents for evaluation).

| Field | Our value |
|---|---|
| Topic ID | S4-I-24 |
| Topic Title | GenAI-Powered Enterprise Copilot |
| Participant Name | Sridhar Vetrivel |
| Employee ID | P394 *(as submitted at mid-term — confirm still current)* |
| Track | ☐ Custom ☐ Data ☐ Platform — *(tick exactly ONE; the mid-term doc ticked two, which is a defect flagged during its review — fix here)* |
| Semester & Category | Semester 4 — Integration Mastery (Capstone) |
| Participation Type | ☑ Regular *(as submitted at mid-term)* |
| Approved Budget Ceiling | ₹2,500 (fixed) |
| Mid-Term document filename | `S4-I-24_SridharVetrivel_MidTermDoc.docx` |
| Mid-Term result / feedback received | *(fill once L&D returns it — not yet known)* |
| Final Review Window | Week 17 — *(dates TBC by L&D)* |

### 2. Approved Proposal Recap
Same three sub-fields as mid-term (2.1 Problem Statement, 2.2 Solution Summary, 2.3 Core Tools).
**If unchanged from the mid-term recap, the template explicitly allows writing "No change from
Mid-Term recap"** under each heading — use that; do not rewrite. 2.2 should describe the
architecture **as finally implemented**; anything different from the originally approved design
goes in Section 8, not here.

> ⚠️ **The mid-term recap is still accurate.** Coordinator + 4 specialists on AgentField, LLM
> intent classification, grounded/cited responses — none of that changed in Phase 2. The one
> thing to add explicitly here: **local Ollama/Gemma 3 inference is now the permanent design**,
> not a temporary gap awaiting OpenRouter (see the Phase 2 scope decision, `Implementation.md`).

### 3. Progress Against Approved Plan (Week 4–17) — **the core section**
Table has **6 columns** now (mid-term had 5): **ID | Planned Deliverable | Planned Window |
Carried from Mid-Term? (Y/N) | Status | Evidence ID(s)**. Template pre-seeds rows `D-01`…`D-12`
— add more if needed, and **every** row from mid-term must reappear here (carried or updated).

Rows to carry forward from mid-term, reconfirmed at final status:

| ID | Planned Deliverable | Window | Carried? | Mid-term status | Final status |
|---|---|---|---|---|---|
| D-01 | AgentField control plane; Azure VM; OpenRouter connected | Week 4 | Y | Partial | **Partial → now a deliberate final scope decision, not a gap** — see Section 8 |
| D-02 | Coordinator Agent — LLM routing; Pydantic schemas | Week 5 | Y | Done | Done (unchanged) |
| D-03 | Data Platform Agent — Databricks REST; unit tests | Week 6 | Y | Done | Done (unchanged) |
| D-04 | Docs Agent + RAG index | Week 7 | Y | Done | Done (unchanged) |
| D-05 | DevOps Agent | Week 8 | Y | Done | Done (unchanged) |
| D-06 | CRM Agent | Week 9 | Y | Done | Done (unchanged) |
| D-07 | ≥6 of 12 queries grounded & cited (checkpoint) | Week 9–10 | Y | Done (12/12) | Done — **now verified through the live control plane**, not just in-process |
| D-08 | Unit tests passing; coverage ≥50% (checkpoint) | Week 9–10 | Y | Done (93%) | Done — **415 tests, 93.11%**, against the full-programme ≥80% target |

New Phase 2 deliverables (from the approved proposal's Weeks 11–17 plan / `Implementation.md` §8),
continuing the sequence — **fill in actual status, do not mark Done without evidence**:

| ID | Planned Deliverable (per approved proposal) | Window | Status *(fill honestly)* |
|---|---|---|---|
| D-09 | Cross-domain orchestration — parallel specialist dispatch, one synthesised & cross-cited answer | Week 11 | **Done** — all 4 cross-domain queries (Q9–Q12) route and synthesise correctly through the control plane; see `docs/qa/traces.md` |
| D-10 | Full 12-query test suite + Judge Agent (hallucination detection) | Week 12–13 | **Done** — routing 100%, hallucination 3.64% measured by the two-half Judge (`make qa-summary`) |
| D-11 | Azure B1s deployment | Week 14 | **Not Started / Descoped** — see Section 8; local Docker Compose is the final deployment target instead |
| D-12 | QA hardening (≥80% coverage) + demo prep | Week 15–16 | **Done** — 93.11% coverage; CI hardened (Python 3.11+3.12 matrix, coverage gate, opt-in live-model job); `docs/DEMO_RUNBOOK.md` is the demo script |

> ⚠️ **D-01 and D-11 need one consistent story, not two.** Both trace back to the same decision
> (OpenRouter/Azure not provisioned — see §8). Don't mark one "Partial" and the other "Not
> Started" without the same underlying explanation; the evaluator will read them together.

**3.1 Overall Final Self-Assessment** (Table 2, 4 rows): summarise the RFP's Week 17 definition of
done, give a defensible final %, **state the % reported at mid-term for comparison** (this is
new — mid-term didn't have to compare to anything), and tick the live-demonstrable state.

RFP / proposal Week 17 checkpoint = complete copilot live; all 12 test queries passing with
correct routing, grounded responses and citations; hallucination rate documented (**<10%**);
routing accuracy **100%**; QA coverage **≥80%**; Judge Agent reports; live demo; evidence on
Moodle. **Every one of these is already measured and met** on the local stack (see §6 below) —
the honest final % should reflect that the *technical* scope is complete, while stating plainly
that Azure hosting and OpenRouter were deliberately descoped, not missed.

### 4. Evidence Pack (Week 4–17)
- **4.1 Evidence Index** — same 5-column shape as mid-term, **plus a "Carried from Mid-Term?"
  column**. One row per block; captions must be specific. **Continue numbering from EV-19**
  (mid-term used EV-01…EV-18) for anything new.
- **4.2 Evidence Blocks** — same per-block header table as mid-term (What this proves |
  Deliverable ID | Date | Verifiable link), **plus a "Carried from Mid-Term?" checkbox**. If
  ticked Yes, **do not re-paste the screenshot** — just reference the original `EV-ID`. Template
  provides `EV-01`…`EV-10` blocks; copy-paste the block (heading + table + paste area) for more.

Evidence carried forward unchanged (tick Yes, reference the mid-term ID, no re-paste needed):
`EV-01`…`EV-06`, `EV-08`, `EV-11`, `EV-12`, `EV-13`✝, `EV-14`✝, `EV-15`, `EV-16`, `EV-17`, `EV-18`.
(`EV-11` was corrected during mid-term review — the pasted screenshot now shows the correct
`coordinator.ask` execution, `devops`+`docs` routing, citations from both systems — so it carries
cleanly.)

New/updated evidence needed for Phase 2 claims (continue from `EV-19`):

| New EV | Would evidence |
|---|---|
| EV-19 | Final `make cov` run — coverage figure as it stands at final submission (re-capture if it moved past 93.11%) |
| EV-20 | Final `make qa-summary` — routing % and hallucination % as measured at final submission |
| EV-21 | The hardened CI workflow actually running green on GitHub Actions (screenshot of the Actions tab, both Python versions) |
| EV-22 | `docs/DEMO_RUNBOOK.md` itself, or a screenshot of a live walkthrough following it, as evidence for D-12 |

✝ **EV-07, EV-09, EV-10 were flagged during the mid-term review as needing re-capture** (they
showed a pre-fix, zero-citation docs-agent run, or a single-specialist frame on a cross-domain
query). **Confirm those were fixed before ticking "Carried" on them** — if they were re-captured
after mid-term submission, they are *new* evidence for this document (a fresh EV-19+ number, not
a carry-forward), because the mid-term `.docx` itself is frozen and was not corrected.

### 5. Working Demo, Repository & Live Walkthrough Plan
Same repo-links table as mid-term, **plus a new mandatory `5.1 Live Code Walkthrough Plan`**
table: which module/flow to walk through (pick the most substantial AI component), the exact
repo path(s), the branch, and anything the panel should have open in advance.

| Field | Our value |
|---|---|
| Code repository URL | `https://github.com/Sridhar-Vetrivel/genAI-enterprise-agent` |
| Final commit ID + date | *(run `git log -1 --format='%h %ci'` at submission time)* |
| Deployed / hosted URL | N/A — local Docker Compose is the final deployment target (see §8); not hosted externally |
| Notebook / dashboard / other artefact links | `docs/qa/` (evidence pages), `docs/DEMO_RUNBOOK.md` (demo script), AgentField UI at `http://localhost:8080/ui/` during the live session |

**5.1 suggested walkthrough:** the **coordinator's cross-domain path** —
`agents/coordinator.py` (`RemoteSpecialist.answer()`, the `app.call()` fix) alongside
`psiog_kendra/coordinator.py` (`Coordinator.ask()` — routing → parallel dispatch → synthesis) and
`psiog_kendra/qa/judge.py` (the two-half Judge). This is the most substantial AI component and
the one place routing, multi-agent orchestration, and grounding all meet.

### 6. QA Progress (Full Programme)
Same shape as mid-term's Section 6, but now must report the **full-programme** total, not a
Week-9 interim. Coverage must be measured, attached as an Evidence ID.

| Test Type | Tests written/run | Coverage (measured) | Target | Evidence ID(s) |
|---|---|---|---|---|
| Unit tests | 415 passing, 4 skipped | 93.11% | ≥80% (full-programme target — the mid-term ≥50% was an interim only) | EV-14 / EV-19 |
| Routing accuracy (12 queries, live model, through the control plane) | 12/12 | **100%** | 100% | EV-01…EV-12, EV-18 |
| Hallucination rate (Judge Agent) | *(re-run `make qa` for a full 12/12 judged pass before final submission — mid-term reported 10/12)* | target **<10%**; mid-term measured **3.64%** on 10 queries | <10% | EV-13 / EV-20 |
| Integration tests (coordinator → specialists → synthesis, incl. the live control-plane path) | included in the 415 | — | — | EV-14 |

> ⚠️ **Close the 10-of-12 gap before final submission.** The mid-term hallucination figure was
> honestly scoped to 10 of 12 graded queries. For the final submission, run `make qa` (or
> `make qa-resume`) to get a genuine 12/12 judged figure — a full run is one command and roughly
> an hour on local CPU, and a 12/12 number is strictly stronger evidence at the review that
> ends the whole programme.

### 7. Tool & Budget Reconciliation (Full Programme)
Same shape as mid-term's Section 7, but **"Used in final solution?"** replaces "Used by Wk 9?",
and §7.1's Budget Summary now splits spend **before and after mid-term**.

Carry the mid-term table forward almost unchanged — nothing about the tool list changed in Phase
2, because the scope decision (§8) was to **stop** depending on OpenRouter/Azure, not to adopt a
new tool:

| Tool | Approved | Used in final? | Actual cost | Reason if changed |
|---|---|---|---|---|
| AgentField | Yes | Yes | ₹0 | As approved |
| OpenRouter | Yes (primary) | **No** | ₹0 | **Permanently descoped** — see §8 |
| Ollama (local fallback → now primary) | Yes (fallback) | Yes — carrying 100% of inference | ₹0 | Fallback promoted to sole/permanent inference path |
| Llama 4 Scout | Yes | No | ₹0 | Machine has Gemma 3 instead |
| nomic-embed-text | Not in approved list | Yes | ₹0 | Required — Gemma 3 cannot embed |
| Pydantic | Yes | Yes | ₹0 | As approved |
| Azure B1s VM | Yes | **No** | ₹0 | **Permanently descoped** — see §8 |
| Pytest + pytest-cov | Yes | Yes | ₹0 | As approved |
| GitHub Actions | Yes | Yes | ₹0 | As approved, **now hardened**: Python matrix, coverage gate, opt-in live job |
| Judge Agent | Yes | Yes | ₹0 | As approved |
| Docker / Docker Compose | Yes | Yes | ₹0 | As approved — **also the final hosting target**, not just local dev |

**7.1 Budget Summary:**

| Item | Amount |
|---|---|
| Approved ceiling | ₹2,500 |
| Actual spend till Mid-Term (Week 9) | ₹0 |
| Actual spend, Mid-Term → Final (Weeks 10–17) | ₹0 |
| Total actual spend (full programme) | **₹0** |
| Buffer remaining | **₹2,500 (100%)** |

### 8. Deviations from Approved Proposal (Full Programme)
Same 4-column shape as mid-term (**Item | Approved plan | Actual implementation | Reason for
change**). **Deviations already listed at mid-term must be carried forward here** — write
"Carried from Mid-Term" in the Reason column and confirm they still stand; do not omit them.

Carry every mid-term deviation forward (inference provider, local model swap, embedding model,
schema enum workaround, hosting, Judge Agent timing, orchestration framework restated, response
latency, mock data sources) — all still stand unchanged. **One mid-term deviation graduates to a
permanent decision, and that graduation is itself the one new deviation to add:**

| Item | Approved plan | Actual implementation | Reason for change |
|---|---|---|---|
| **OpenRouter provisioning** | Provision during Week 11 (per mid-term §9 plan) | **Will not be provisioned — a permanent scope decision**, not a delayed task | Local Ollama/Gemma 3 meets every graded target (routing 100%, hallucination 3.64%, coverage 93%) at ₹0; provisioning would add cost with no gap it needs to close for this POC |
| **Azure B1s hosting** | Provision during Week 11 (per mid-term §9 plan) | **Descoped — local Docker Compose is the final deployment target** | Same rationale; the stack runs identically under Compose, so nothing about the architecture is left unproven by staying local |

### 9. Enhancements & Additional Value-Adds — **new section, not in the mid-term template**
Work **beyond** the approved proposal's strict scope. Each entry needs an Evidence ID (if claimed
Done) and a cost impact (₹0 is valid, but must reconcile with §7's total). If genuinely none,
write "None" in row 1 — don't delete the section. Candidates from this build:

| ID | Enhancement | Why added | Status | Cost (₹) | Evidence |
|---|---|---|---|---|---|
| EN-01 | **Two-half Judge Agent** (LLM half + a deterministic fact-check half) | The LLM-only judge was caught marking a fabricated date as grounded — a judge that under-reports is the worst failure this system can have. The deterministic half can only ever *add* a finding, never remove one. | Done | ₹0 | EV-13 |
| EN-02 | **Live control-plane routing verification** (`scripts/trace_queries.py`, `docs/qa/traces.md`) | The proposal's own QA suite runs the coordinator in-process; the actual graded multi-agent path (`app.call()` through AgentField) was never exercised until this was built — and it caught a real, months-old 422 bug in that path. | Done | ₹0 | EV-18, `docs/qa/traces.md` |
| EN-03 | **Fleet health tooling** (`agents/health.py`, `make agents-status`) distinguishing *serving* from *routable* | A node can be alive-but-deregistered (heartbeat lapse) or registered-but-dead (port collision) — two different failures that look identical from one health signal each. Neither was previously detectable. | Done | ₹0 | `tests/unit/test_agent_runtime.py` |
| EN-04 | **CI hardening** — Python 3.11+3.12 matrix, concurrency cancellation, coverage-artifact upload, opt-in `live` job that installs Ollama and runs the real-model tests in CI | Goes beyond "a workflow that runs the suite" (the mid-term state) toward a CI pipeline that can reproduce the live-model integration path, not just the offline one. | Done | ₹0 | `.github/workflows/ci.yml`, EV-21 |

### 10. What Is NOT Completed + Future Scope
Same 4-column shape as mid-term's Section 9 (**Pending item | Why pending | Flagged at Mid-Term?
(Y/N) | Recommended future scope**), but **cross-checked against the mid-term doc too** now — a
"Done" here that mid-term called "pending" (or vice versa) must be explained, not silently
changed.

| Pending item | Why pending | Flagged at Mid-Term? | Recommended future scope |
|---|---|---|---|
| OpenRouter provisioning | Permanently descoped (§8) — not "not yet done", a decision | Y (as "Week 11" pending) | If ever revisited: pure config change, `AI_MODEL_COMPLEX=google/gemini-2.5-flash` |
| Azure B1s hosting | Permanently descoped (§8) | Y (as "Week 11" pending) | Deploy the existing Compose stack unmodified to a B1s VM if hosting is later required |
| Live REST source integration | Descoped by design — proposal's own mock-data-only rule (§7 of solution-proposal) | Y | Point the already-implemented, already-unit-tested REST clients at sandboxed real credentials |
| Full 12-of-12 judged hallucination figure | Mid-term reported 3.64% over 10/12 queries, scoped honestly rather than extrapolated | Y (explicitly, in the mid-term doc's §6) | Run `make qa` for the full 12; expected to land in the same low-single-digit band |

### 11. Risks & Blockers — Final Status
Same 4-column shape as before but relabelled: **Risk/Blocker | Final Status (Mitigated /
Realised / Accepted) | Mitigation taken | Final impact on delivered project**. This is a
**closure record** — carry every mid-term risk forward with its *final* outcome, not the
original plan.

| Risk / Blocker | Final Status | Mitigation taken | Final impact |
|---|---|---|---|
| OpenRouter not provisioned | **Accepted** (converted from "Open" to a permanent scope decision) | Zero-cost local model carries the whole build; env-var switch remains available | None — all graded targets met on the local model |
| Small local model writes prompt scaffolding into answers | **Mitigated** | Leak classes found and stripped, each with a regression test | None; would mostly disappear on a frontier model |
| LLM Judge under-reports hallucinations | **Mitigated** | Deterministic fact-check backstop added; can only add findings, never remove | None — is why the reported rate can be trusted |
| `gemma3:4b` needs ~4 GiB free RAM | **Accepted (environmental)** | Silent-never fallback to `gemma3:1b`, logged | None on hosted inference; still applies locally |
| Response latency (CPU inference) | **Accepted (environmental)** | Per-query hard stop; timed-out ≠ silently skipped | None architecturally; demo runbook plans around it |
| Cross-agent control-plane call path untested by the offline suite | **Realised, then fixed** | Found via manual verification: `app.call()` needs kwargs, not `input={...}`; fixed, and now covered by `docs/qa/traces.md` | Was a real months-old bug; now closed |
| Demo runs on synthetic data | **Accepted (by design)** | Per the proposal's own mock-data rule; live paths implemented + unit-tested | None |

### 12. Declaration & Pre-Submission Checklist
Same mechanics as mid-term's Section 11 (checkboxes + signature + date), but the checklist items
are final-programme-specific: mid-term filename matches exactly what was uploaded; every mid-term
D-ID/EV-ID/deviation is either carried-and-marked or updated, never silently dropped; §9
(Enhancements) reconciles with §7; §10 doesn't contradict §3/§4/the mid-term doc; repo walkthrough
paths in §5.1 actually exist in the repo.

## Consistency cross-checks the AI evaluator runs

- Section 3 Done/Partial ↔ must have Section 4 (or mid-term) Evidence IDs.
- **Section 3 Carried=Y rows ↔ must match the mid-term document's status for that D-ID** — a
  silent change without explanation reads as inconsistent.
- Section 1 Mid-Term filename ↔ must be the exact file uploaded to Moodle at Week 10.
- Section 6 coverage ↔ must be a measured EV, not an estimate.
- Section 7 ↔ every approved tool listed, including unused ones; ties to Section 8.
- **Section 9 (Enhancements) cost impact ↔ must reconcile with Section 7's total spend.**
- Section 10 pending list ↔ must not contradict Section 3, Section 4, or the mid-term document.
- Section 5.1 walkthrough file paths ↔ must exist in the stated repo/branch.
- Section 1 Topic ID ↔ L&D Final Decision (Part D) exactly.
- Section 3.1 final % ↔ defensible from the Section 3 table, and compared against the mid-term %.

## When we fill this (Week 17)

1. **Close the QA gap first**: run `make qa` (or `make qa-resume`) for a genuine 12/12 judged
   hallucination figure — the mid-term's honestly-scoped 10/12 should not carry forward
   unchanged if a full run is one command away.
2. Re-capture `make cov` and `make qa-summary` for final, current numbers (EV-19, EV-20).
3. Re-capture the three evidence blocks flagged as needing correction at mid-term review
   (EV-07, EV-09, EV-10 — the pre-fix docs-agent / single-specialist screenshots).
4. Confirm the CI workflow is green on GitHub (both Python versions) and screenshot it (EV-21).
5. Walk `docs/DEMO_RUNBOOK.md` once live end-to-end; that dry run is both the demo prep and the
   evidence for D-12 / EN-04.
6. Fill Section 3 (carry mid-term D-01…D-08, add D-09…D-12), Section 4 (carry EV-01…EV-18 by
   reference, add EV-19+), Section 9 (Enhancements — draft candidates above), then Sections 6,
   7, 8, 10, 11 in that order — each depends on the numbers settled in the step before it.
7. Work the Section 12 checklist last; save as `S4-I-24_SridharVetrivel_FinalTermDoc.docx`.
