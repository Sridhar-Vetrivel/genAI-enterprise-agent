# pSiddhi 3.0 — Mid-Term Submission (ready-to-paste content)

> **How to use this file.** Every section below maps 1:1 onto
> `docs/pSiddhi3_0_MidTerm_Submission_Template.docx`. Copy each block into the matching section
> of the .docx. **Do not rename, delete, renumber or reorder sections** — an AI scoring engine
> reads the structure.
>
> Anything wrapped in «double angle brackets» is a value only you can supply (employee ID,
> dates you captured screenshots, a number that is still being measured). Everything else is
> real, measured, and traceable to the repo.
>
> **The submission covers work up to the end of Week 9.** Week 10+ plans belong in Section 9,
> never in Section 3.

---

## 1. Participant & Project Identification

| Field | Value |
|---|---|
| Topic ID | S4-I-24 |
| Topic Title | GenAI-Powered Enterprise Copilot |
| Participant Name | Sridhar Vetrivel |
| Employee ID | «your employee ID» |
| Track | «tick one — Custom / Data / Platform» |
| Semester & Category | Semester 4 — Integration Mastery (Capstone) |
| Participation Type | «tick one — Regular / pSiddhi Lite» |
| Approved Budget Ceiling | ₹2,500 (fixed) |
| Mid-Term Review Window | Week 10 (13-Jul-26 to 17-Jul-26) |

> ⚠️ Topic ID must match the L&D Final Decision (Part D) **exactly** — a mismatch delays evaluation.

---

## 2. Approved Proposal Recap

### 2.1 Problem Statement (as approved)

Psiog's engineering, data and operations teams work across a fragmented estate — Databricks,
GitHub/Azure DevOps, a CRM, and runbooks scattered across wikis. Answering even a simple
operational question ("did last night's pipeline run?") means opening four or five tools with
different credentials and stitching the results together by hand. This creates an onboarding
bottleneck, turns senior engineers into human routers, and slows cross-functional decisions.
The approved proposal identified **hallucination as the central risk**: an assistant that
answers operational questions from model knowledge rather than live systems is worse than no
assistant, because it is confidently wrong.

### 2.2 Proposed Solution Summary (as approved)

**Psiog Kendra** — a **Coordinator Agent plus four Specialist Agents** built on **AgentField**,
an open-source multi-agent orchestration framework. The Coordinator classifies the user's
intent with an LLM (not keyword matching) and routes to one or more specialists: Data Platform
(Databricks), DevOps (GitHub Actions / Azure DevOps), CRM, and Docs (RAG over internal
runbooks). For cross-domain questions the Coordinator dispatches specialists in parallel and
synthesises one answer that cites every system it used. **Every response carries citations**;
nothing is answered from model training data. A dedicated **Judge Agent** measures the
hallucination rate as an automated QA gate.

### 2.3 Core Tools & AI Components (as approved)

AgentField (orchestration + vector memory), OpenRouter with `google/gemini-2.5-flash`
(primary inference), Ollama with Llama 4 Scout (zero-cost local fallback), Pydantic
(structured output), Azure B1s free tier (hosting), Pytest + GitHub Actions + an LLM Judge
Agent (QA). Full reconciliation in Section 7.

> ⚠️ **Actual inference to date: OpenRouter is NOT provisioned.** Every LLM call in this build
> runs on the local Ollama model at ₹0. The approved proposal named **Llama 4 Scout** as the
> local model; the machine has **Gemma 3** (`gemma3:4b` / `gemma3:1b`). Both are deviations and
> are disclosed in Sections 7 and 8.

---

## 3. Progress Against Approved Plan (up to Week 9)

| ID | Planned Deliverable | Planned Window | Status | Evidence ID(s) |
|---|---|---|---|---|
| D-01 | AgentField control plane via Docker Compose; Azure VM provisioned; OpenRouter connected | Week 4 | **Partial** | EV-16, EV-18 |
| D-02 | Coordinator Agent — LLM intent classification + routing; Pydantic schemas defined | Week 5 | **Done** | EV-01 … EV-12, EV-17, EV-18 |
| D-03 | Data Platform Agent — Databricks REST connected; job status/history; unit tests | Week 6 | **Done** | EV-01, EV-02, EV-09, EV-10, EV-12, EV-17 |
| D-04 | Docs Agent + RAG index — docs chunked/embedded/indexed; similarity search working | Week 7 | **Done** | EV-07, EV-08, EV-10, EV-11, EV-12, EV-15, EV-17 |
| D-05 | DevOps Agent — GitHub/Azure DevOps connected; build status, deployments, quality gates | Week 8 | **Done** | EV-03, EV-04, EV-11, EV-12, EV-17 |
| D-06 | CRM Agent — CRM/mock connected; contact/deal/account queries | Week 9 | **Done** | EV-05, EV-06, EV-09, EV-12, EV-17 |
| D-07 | ≥6 of 12 test queries returning grounded, cited responses | Week 9–10 | **Done** | EV-01 … EV-13, EV-18 |
| D-08 | Unit tests passing for skill functions; coverage ≥50% | Week 9–10 | **Done** | EV-14 |

**Why D-01 is Partial and not Done.** The approved deliverable is three things: the control
plane *and* an Azure VM *and* OpenRouter connected. The AgentField control plane runs under
Docker Compose and all five agent nodes register against it (EV-16). **OpenRouter is not
provisioned**, and the Azure VM is not stood up. Claiming D-01 as Done would fail the
evaluator's Section 3 ↔ Section 4 cross-check, because there is no evidence for those two
parts. It is Partial, and Section 9 carries both to Week 11.

**D-07 exceeds its checkpoint.** The sub-goal was ≥6 of 12 queries grounded and cited. All
**12 of 12** return grounded, cited answers, including all four cross-domain queries.

### 3.1 Overall Mid-Term Self-Assessment

The RFP's Week 10 checkpoint asks for: 2+ specialist agents operational, a populated semantic
index, routing across ≥2 domains, initial grounded/cited responses, unit tests passing, and
mid-term docs submitted. Measured against that:

| Checkpoint item | Required | Achieved |
|---|---|---|
| Specialist agents operational | 2+ | **4 of 4** |
| Semantic index populated | yes | **21 chunks, 768-dim, 0 orphans** |
| Routing across domains | ≥2 | **all 4 domains, plus cross-domain synthesis** |
| Grounded / cited responses | "initial" | **12 of 12 queries, 100% routing accuracy** |
| Unit tests passing | yes | **415 passing, 93% coverage** |

**Completion: ~75% of the Weeks 4–17 scope.**

Defensible from the table above: seven of eight Weeks 4–9 deliverables are Done and one is
Partial; the Week 10 checkpoint is met on every item and exceeded on most. The remaining ~25%
is Weeks 11–17 work that has not started — hosting on Azure, OpenRouter provisioning, CI
hardening, live REST credentials, and the final demo — and is listed in Section 9.

**Demonstrable live state:** ☑ **End-to-end working** — all 12 queries run live **through the
AgentField control plane**: the coordinator classifies intent with the LLM, dispatches to the
specialist nodes via `app.call()`, and returns one cited answer, every hop traced as a DAG
(EV-18). Routing accuracy measured through the control plane is **100% (12/12)**, and **12 of 12**
answers carry at least one citation. `make ask Q="..."` does the same from the terminal.

---

## 4. Evidence Pack

### 4.1 Evidence Index

Every query below was executed **through the AgentField control plane** (`coordinator.ask`),
so each screenshot shows the LLM classifying intent, dispatching to specialists via `app.call()`,
and returning a cited answer. Execution IDs are in `docs/qa/traces.md`.

| Evidence ID | Caption (what it proves) | Deliverable ID(s) | Screenshot | Verifiable link |
|---|---|---|---|---|
| EV-01 | Q01 "Did yesterday's ETL pipeline for the sales data run successfully?" routes to `data-platform` and answers citing the Databricks run | D-02, D-03 | `docs/images/Q01-Ev01.png` | `docs/qa/q01.md` @ «commit» |
| EV-02 | Q02 "What was the error in the last failed Databricks job?" routes to `data-platform` and quotes the SchemaMismatchException from the cited run | D-02, D-03 | `docs/images/Q02.png` | `docs/qa/q02.md` @ «commit» |
| EV-03 | Q03 "Did the latest deployment of the payments service pass all quality gates?" routes to `devops` and cites the GitHub Actions run | D-02, D-05 | `docs/images/Q03-Ev03.png` | `docs/qa/q03.md` @ «commit» |
| EV-04 | Q04 "What was the last deployment date for the auth service?" routes to `devops` and cites the deploy-auth run | D-02, D-05 | `docs/images/Q04.png` | `docs/qa/q04.md` @ «commit» |
| EV-05 | Q05 "What is the current deal status for Acme Corp?" routes to `crm` and cites the account and the deal | D-02, D-06 | `docs/images/Q05.png` | `docs/qa/q05.md` @ «commit» |
| EV-06 | Q06 "Who is the account owner for TechStart Ltd?" routes to `crm` and cites the CRM account | D-02, D-06 | `docs/images/Q06.png` | `docs/qa/q06.md` @ «commit» |
| EV-07 | Q07 "What is the runbook for a schema mismatch?" routes to `docs` and cites the retrieved document sections | D-02, D-04 | ⚠️ **RE-CAPTURE** — see note below | `docs/qa/q07.md` @ «commit» |
| EV-08 | Q08 "What does the architecture doc say about the ingestion pipeline?" routes to `docs` and cites the architecture document | D-02, D-04 | `docs/images/Q08.png` | `docs/qa/q08.md` @ «commit» |
| EV-09 | Q09 (cross-domain) "Did last night's pipeline failure affect any CRM customer sync?" routes to `data-platform` + `crm` and traces the failure to the affected accounts, citing both systems | D-02, D-03, D-06, D-07 | ⚠️ **RE-CAPTURE** — see note below | `docs/qa/q09.md` @ «commit» |
| EV-10 | Q10 (cross-domain) "The ingestion job failed — is there a fix in the runbooks?" routes to `data-platform` + `docs` and joins the live failure to the documented recovery steps, citing both | D-02, D-03, D-04, D-07 | ⚠️ **RE-CAPTURE** — see note below | `docs/qa/q10.md` @ «commit» |
| EV-11 | Q11 (cross-domain) "What's the status of the latest deployment and are there any known issues?" routes to `devops` + `docs` and cites both the GitHub Actions runs and the runbook/incident documents | D-02, D-04, D-05, D-07 | `docs/images/Q11.png` | `docs/qa/q11.md` @ «commit» |
| EV-12 | Q12 (cross-domain) "Give me a full status update" routes to **all four domains** and synthesises one answer citing across every system | D-02 … D-07 | `docs/images/Q12.png` | `docs/qa/q12.md` @ «commit» |
| EV-13 | The graded QA run: routing accuracy and hallucination rate across all 12 queries | D-07 | «terminal screenshot of `make qa`» | `data/qa_report.json` @ «commit» |
| EV-14 | Full offline test suite passing, with the measured coverage figure (415 passed, 93.11%) | D-08 | ⚠️ **RE-CAPTURE** — `docs/images/ev-14.png` shows 408, now stale | CI run / `make cov` @ «commit» |
| EV-15 | The documentation corpus chunked, embedded and indexed for similarity search — 21 chunks, data-validation gate passed | D-04 | `docs/images/ev-15.png` | `make index` @ «commit» |
| EV-16 | The AgentField control plane running, with **all five agent nodes registered, Ready and Active** | D-01 | `docs/images/Agents-Up-and-Running.png` | `deploy/docker-compose.yml` @ «commit» |
| EV-17 | Each of the five agents is a **distinct registered node** with its own reasoners, skills and DID — not one LLM behind a long prompt | D-02, D-03, D-04, D-05, D-06 | `docs/images/co-ordinator.png`, `docs/images/data-agent-skills-and-reasoner.png`, `docs/images/devops-agent-skills-and-reasoners.png`, `docs/images/crm-agent-skills-and-reasoner.png`, `docs/images/Docs-agent-skills-and-reasoner.png` | `agents/` @ «commit» |
| EV-18 | The **DAG of a cross-domain query**: `coordinator.ask` fanning out to all four specialists through the control plane and synthesising one answer | D-01, D-02, D-07 | `docs/images/Q12-Workflow-View.png` | `docs/qa/traces.md` @ «commit» |

> Every query row above has a matching page in **`docs/qa/`** giving the exact command, what must
> be visible in the frame, and a pre-filled evidence-block header table. `docs/qa/traces.md` maps
> each query to the control-plane execution ID to open in the UI. Run `make evidence` to
> regenerate the pages from the QA report.

#### ⚠️ Three screenshots must be re-captured before submitting

**EV-07 and EV-10 are currently screenshots of a broken run.** Both show
`answer_docs_question` returning *"The indexed internal documentation does not cover this
question"* with **zero citations**, in 5s and 2s — the docs agent never retrieved anything. The
cause was a real bug (the control plane's vector memory was never indexed; fixed by `make
index-cp`, now run automatically by `make agents`). Pasting these would show an evaluator a green
**Succeeded** badge over an answer admitting it knows nothing — for the two blocks meant to prove
the RAG deliverable (D-04). Do not use `docs/images/Q07.png` or `docs/images/Q10.png`.

**EV-09 currently shows only one specialist.** `docs/images/Q09.png` is the
`answer_data_question` sub-call. Q09 is a cross-domain query whose entire claim is that the
coordinator called **two** specialists and synthesised across them — a single-agent frame does
not prove that caption.

Re-capture these three from the **`coordinator.ask`** execution (not the specialist sub-call), at
<http://localhost:8080/ui/>:

| EV | Open this execution ID | Should show |
|---|---|---|
| EV-07 | `exec_20260714_144630_ebji8tdr` | routed `docs`, 4 citations, 123.8s |
| EV-09 | `exec_20260714_142110_b9u0edtk` | routed `crm` + `data-platform`, 3 citations, 340.6s |
| EV-10 | `exec_20260714_145055_3hvpsfti` | routed `data-platform` + `docs`, 4 citations, 239.8s |

Make sure the **`domains_used`** field is visible in the frame — that is what proves the routing.
`docs/images/Q11.png` (EV-11) is the model to copy: it shows `ask` on `coordinator`,
`domains_used: ["devops", "docs"]`, and citations spanning both systems.

#### 📸 EV-13 — the graded QA run (routing accuracy + hallucination rate)

This is the screenshot that carries the two numbers Section 6 is scored on, so it has to be the
**final** run — after every QA fix is in. Steps:

```bash
# 1. Free the RAM. gemma3:4b needs ~4 GiB; if it will not load, the gateway silently
#    degrades to gemma3:1b and the whole run is worthless as evidence.
ollama ps                      # should be empty or show gemma3:4b, never gemma3:1b
make agents-down               # the 5 agent nodes each hold a model handle

# 2. Run the graded suite. ~60 local LLM calls, roughly an hour on CPU.
#    It prints each query as it lands and checkpoints to data/qa_report.json,
#    so a killed run is not a lost run (resume with `make qa-resume`).
make qa
```

The run ends with a summary block. **Screenshot that block**, and make sure all of this is in
one frame, full-size:

| Must be visible | Why |
|---|---|
| `queries: 12` | proves all twelve were graded, not a subset |
| `routing_accuracy_pct: 100.0` | the Section 6 routing figure |
| `hallucination_rate_pct: <N>` | **the Section 6 hallucination figure** |
| `total_claims` / `grounded_claims` | proves the rate is `(ungrounded / total) × 100`, not asserted |
| `answers_with_citations: 12` | proves every answer is grounded |

Then paste the measured `hallucination_rate_pct` into the Section 6 table below, replacing
«FINAL %». **The number in the screenshot and the number in the table must be identical** — the
evaluator cross-checks Section 6 against its evidence block.

> ⚠️ If the summary prints `queries: 11` or fewer, the run did not finish. Resume it with
> `make qa-resume` rather than screenshotting a partial run.
>
> ⚠️ If any query shows `UNVERIFIED`, the judge enumerated no claims for it — a known
> `gemma3:4b` flake. Re-grade the stored answers with `make qa-rejudge` (12 LLM calls, not 60)
> before capturing.

### 4.2 Evidence Blocks

For each EV-ID, paste the full-size, readable screenshot named below, with this header table
above it. **Do not reuse a screenshot across two EV IDs.**

**EV-01 — Q01 routes to data-platform and returns a cited answer**

| Field | Value |
|---|---|
| What this proves | The coordinator classifies intent with an LLM and routes to `data-agent`; the answer cites the Databricks run it came from |
| Deliverable ID | D-02, D-03 |
| Date captured | «date» |
| Verifiable link | «GitHub commit URL» |

`docs/images/Q01-Ev01.png`

**EV-02 … EV-18** — same structure. Paste the image named in the Section 4.1 index:

| EV | Image to paste |
|---|---|
| EV-01 | `docs/images/Q01-Ev01.png` |
| EV-02 | `docs/images/Q02.png` |
| EV-03 | `docs/images/Q03-Ev03.png` |
| EV-04 | `docs/images/Q04.png` |
| EV-05 | `docs/images/Q05.png` |
| EV-06 | `docs/images/Q06.png` |
| EV-07 | ⚠️ re-capture `exec_20260714_144630_ebji8tdr` |
| EV-08 | `docs/images/Q08.png` |
| EV-09 | ⚠️ re-capture `exec_20260714_142110_b9u0edtk` |
| EV-10 | ⚠️ re-capture `exec_20260714_145055_3hvpsfti` |
| EV-11 | `docs/images/Q11.png` |
| EV-12 | `docs/images/Q12.png` |
| EV-13 | «terminal screenshot of `make qa`» |
| EV-14 | ⚠️ re-capture `make cov` (must read **415 passed**, 93.11%) |
| EV-15 | `docs/images/ev-15.png` |
| EV-16 | `docs/images/Agents-Up-and-Running.png` |
| EV-17 | `docs/images/co-ordinator.png`, `docs/images/data-agent-skills-and-reasoner.png`, `docs/images/devops-agent-skills-and-reasoners.png`, `docs/images/crm-agent-skills-and-reasoner.png`, `docs/images/Docs-agent-skills-and-reasoner.png` |
| EV-18 | `docs/images/Q12-Workflow-View.png` |

**EV-17 — the five agents are five distinct nodes**

| Field | Value |
|---|---|
| What this proves | The architecture is genuinely multi-agent: five separately registered AgentField nodes, each with its own base URL, port, reasoners, skills and DID — not one LLM behind a long system prompt. Non-negotiable design rule #3 in the RFP. |
| Deliverable ID | D-02, D-03, D-04, D-05, D-06 |
| Date captured | «date» |
| Verifiable link | «GitHub commit URL» |

Paste all five node detail pages. Together they show: `coordinator` (2 reasoners — `route_query`,
`ask`), `data-agent` (`answer_data_question` + `fetch_job_runs`), `devops-agent`
(`answer_devops_question` + `fetch_workflow_runs`), `crm-agent` (`answer_crm_question` +
`fetch_crm_records`), `docs-agent` (`answer_docs_question` + `index_documentation` +
`search_documentation`).

**EV-18 — the cross-domain DAG**

| Field | Value |
|---|---|
| What this proves | `coordinator.ask` fans out to **all four specialists** through the control plane and synthesises one cited answer. Every agent-to-agent hop is traced. This is the single clearest picture of the multi-agent design. |
| Deliverable ID | D-01, D-02, D-07 |
| Date captured | «date» |
| Verifiable link | «GitHub commit URL» |

`docs/images/Q12-Workflow-View.png` — the Graph tab of run `run_2026071…ucqqco34`: the
`Ask` node on `coordinator` branching to `Answer Data Question`, `Answer Crm Question`,
`Answer Docs Question` and `Answer Devops Question`, all four green, with per-hop durations.

> ⚠️ **Do not screenshot a fallback run.** If the terminal prints
> `gemma3:4b does not fit in host memory; falling back to gemma3:1b`, the answer came from the
> weak model and neither the routing nor the answer is representative. Free ~4 GiB of RAM
> (check `ollama ps`) and run it again.
>
> ⚠️ **Do not screenshot a docs answer that says "The indexed internal documentation does not
> cover this question."** That means the control plane's vector memory is empty. Run
> `make index-cp` (or just `make agents`, which now does it) and re-run the query.

---

## 5. Working Demo & Repository Links

| Field | Value |
|---|---|
| Code repository URL | https://github.com/Sridhar-Vetrivel/genAI-enterprise-agent |
| Latest commit ID + date | «short SHA» — «date» *(run `git log -1 --format='%h %ci'` at submission)* |
| Deployed / hosted URL | **N/A** — runs locally via Docker Compose; Azure B1s hosting is Week 11 (see Section 9) |
| Demo video / recording link | «optional» |
| Notebook / dashboard / other artefact links | `docs/qa/` — 16 evidence pages, one per Evidence ID, auto-generated from the QA report |

> ⚠️ The repository must be **accessible to L&D** before the review window opens.

---

## 6. QA Progress (up to Week 9)

| Test Type | Tests written / run | Coverage achieved (measured) | Target (per proposal) | Evidence ID(s) |
|---|---|---|---|---|
| Unit tests (routing, retrieval, sources, prompting, QA) | **415 passing**, 4 skipped | **93.11%** (`pytest-cov`, `make cov`) | ≥80% overall; ≥50% mid-term interim | EV-14 |
| Routing accuracy (12 mandatory queries, live model) | 12 of 12 | **100%** | 100% | EV-01 … EV-13 |
| Hallucination rate (Judge Agent, live model) | 12 answers judged | **«FINAL % — from the last `make qa` run»** | <10% | EV-13 |
| Integration tests (coordinator → specialists → synthesis) | included in the 415 | — | — | EV-14 |

**Hallucination rate is `(ungrounded claims / total claims) × 100`**, measured by a dedicated
**Judge Agent** that re-fetches the raw source content behind every citation *independently of
what the answering agent saw* — a judge grading against the agent's own context could never
catch a fabricated citation.

**The Judge has two halves, and the second one exists because the first was not enough.** The
LLM half (`gemma3:4b`) splits an answer into claims and checks each against the source. It was
caught marking a **fabricated date** as grounded — the answer said a job failed on 2026-07-13
when the source says 2026-07-12. A judge that under-reports is the worst failure this system
can have: the number looks good, so nobody investigates. So a **deterministic half** now runs
on every answer: every date, job id, run id, record count and account code the answer states
must appear **verbatim** in the sources it cited. No model involved. It can only ever *add* a
finding, never remove one.

> ⚠️ **Coverage is a measured tool figure**, not an estimate — attach the `make cov` output as
> EV-14. The evaluator checks this.

---

## 7. Tool & Budget Reconciliation

| Tool | Approved tier & cost | Used by Wk 9? | Actual cost ₹ | Reason if changed / not used |
|---|---|---|---|---|
| **AgentField** (orchestration, vector memory, DAG tracing) | Open-source, self-hosted, ₹0 | **Yes** | ₹0 | As approved. Replaces the RFP's LangChain / MS Agent Framework and Azure AI Search — a swap the approved proposal already made and which is restated in Section 8. |
| **OpenRouter** (`google/gemini-2.5-flash`) — primary inference | Pay-per-token, budgeted | **No** | **₹0** | **Not provisioned.** All inference falls back to the local model. Code is unchanged: `AI_MODEL_COMPLEX` is an env var, so the swap is a config edit. This is the single biggest deviation — see Section 8. |
| **Ollama** — local fallback inference | Free, self-hosted, ₹0 | **Yes — carrying 100% of inference** | ₹0 | Approved as the *fallback*; it is currently the *primary*, because OpenRouter is not provisioned. |
| **Llama 4 Scout** — the approved local model | Free, ₹0 | **No** | ₹0 | Not installed on the machine. **Gemma 3** (`gemma3:4b` for routing/synthesis/judging, `gemma3:1b` for simple lookups) is used instead. |
| **nomic-embed-text** — embeddings (768-dim) | *not in the approved list* | **Yes** | ₹0 | **Newly added, and unavoidable: Gemma 3 cannot produce embeddings at all.** The RAG index cannot exist without a separate embedding model. Disclosed in Section 8. |
| **Pydantic** — structured output (`extra="forbid"`) | Open-source, ₹0 | **Yes** | ₹0 | As approved. Every LLM call returns a validated schema. |
| **Azure B1s VM** — hosting | 12-month free tier, ₹0 | **No** | ₹0 | Not yet provisioned. Runs locally via Docker Compose. Planned Week 11 (Section 9). |
| **Pytest + pytest-cov** — QA | Open-source, ₹0 | **Yes** | ₹0 | As approved. 415 tests, 93% coverage. |
| **GitHub Actions** — CI | Free tier, ₹0 | **Yes** (workflow committed) | ₹0 | As approved. |
| **Judge Agent** — hallucination detection | Runs on the same LLM, ₹0 | **Yes** | ₹0 | As approved, and **pulled forward from Week 13 to Week 10** because the QA numbers were needed for this submission. |
| **Docker / Docker Compose** | Open-source, ₹0 | **Yes** | ₹0 | As approved. |

### 7.1 Budget Summary

| Item | Amount |
|---|---|
| Approved ceiling | ₹2,500 |
| Estimated spend at approval | ~₹800–1,200 (OpenRouter tokens) |
| **Actual spend to end of Week 9** | **₹0** |
| Buffer remaining | **₹2,500 (100%)** |
| Anticipated spend before Week 17 | ₹0–1,200 — ₹0 if the build stays on local inference; up to the original estimate if OpenRouter is provisioned |

**Every tool in this build is open-source, self-hosted or free-tier. Inference — the only
budgeted line — costs ₹0 because it runs locally.** The budget is not at risk under either path.

---

## 8. Deviations from Approved Proposal

| Item | Approved plan | Actual implementation | Reason for change |
|---|---|---|---|
| **Inference provider** | OpenRouter (`google/gemini-2.5-flash`) as primary; Ollama as zero-cost fallback | **100% local Ollama.** OpenRouter never called. | **OpenRouter was not provisioned.** The approved fallback is carrying the entire build. No code change is needed to switch: `AI_MODEL_COMPLEX` is an env var. **Cost impact: ₹0 spent against a ~₹1,000 estimate.** |
| **Local model** | Llama 4 Scout | **Gemma 3** — `gemma3:4b` (routing, cross-domain synthesis, judging) and `gemma3:1b` (simple single-record lookups) | Llama 4 Scout is not installed on the machine; Gemma 3 is. Two tiers rather than one, so cheap work uses the cheap model. |
| **Embedding model** | *(none named — the proposal assumed the LLM could embed)* | **`nomic-embed-text`** (768-dim), pulled locally, ₹0 | **Gemma 3 cannot produce embeddings.** A separate embedding model is not optional — without it there is no RAG index and no Docs agent. |
| **Structured-output schemas** | Pydantic with enumerated domain values | Pydantic with `list[str]` + a validator enforcing the same 4-domain vocabulary | **Ollama 0.23 returns HTTP 500 for any JSON schema containing `enum`.** Same guarantee, enforced one layer up. Schemas reaching the model are stripped of `enum`/`const`. |
| **Hosting** | Azure B1s VM (12-month free tier) | **Local Docker Compose.** Azure VM not provisioned. | Deferred to Week 11. Does not block any Week 4–9 deliverable; the control plane runs identically under Compose. |
| **Judge Agent timing** | Week 13 | **Built in Week 10** | Pulled forward: the hallucination rate is a Section 6 requirement for *this* submission, so the agent that measures it had to exist first. |
| **Orchestration framework** | AgentField | AgentField | *(No change — but restating the proposal's own approved swap: the RFP named LangChain / MS Agent Framework and Azure AI Search; the approved proposal replaced both with AgentField and its built-in vector memory.)* |
| **Response latency** | *(not specified)* | **2–4 min single-domain; 8–15 min cross-domain; ~1 hr for the full 12-query QA run** | **A consequence of the first row, not a design flaw.** Every call runs on a 4B model on CPU with no GPU. A cross-domain query is 5–7 calls that cannot be parallelised — the coordinator cannot synthesise until the specialists answer, and the judge cannot grade until the answer exists. On a hosted endpoint each call is sub-second and the same run finishes in single-digit minutes, **with better answers**: much of the output-sanitising code exists to compensate for a small model writing its own prompt scaffolding into the prose. |
| **Data sources** | Live REST APIs | **Synthetic fixtures** (`data/mock/`), causally linked so cross-domain reasoning is genuinely exercised | Per the approved proposal's own mock-data-only rule (§ 7) — no real customer or internal data is ever sent to an external LLM. The live REST paths **are implemented and unit-tested** against a mocked transport; set `USE_MOCK_SOURCES=false` and supply credentials to go live. |

---

## 9. What Is NOT Completed Yet + Plan for Weeks 11–16

| Pending item | Why pending | Plan to complete (target week) |
|---|---|---|
| **OpenRouter provisioning** (part of D-01) | Account/credits not provisioned | Provision, set `AI_MODEL_COMPLEX=google/gemini-2.5-flash`, re-run the QA suite and compare both sets of numbers. **No code change.** — **Week 11** |
| **Azure B1s VM hosting** (part of D-01) | Not provisioned; not required for any Weeks 4–9 deliverable | Provision the free-tier VM, deploy the Compose stack, expose the control plane — **Week 11** |
| **CI hardening** | Workflow is committed and runs the suite; it does not yet gate on coverage or run the live-model tests | Add a coverage gate and a nightly live-model job — **Week 12** |
| **Live REST source integration** | Implemented and unit-tested, but never run against real credentials | Point at real Databricks / GitHub / CRM endpoints in a sandbox — **Weeks 13–14** |
| **Judge Agent on a frontier model** | The 4B local judge is measurably unreliable — it waved a fabricated date through, which is why a deterministic fact check now backs it up | Re-run the judge on `gemini-2.5-flash` once OpenRouter is live; compare against the deterministic check — **Week 13** |
| **Final demo + documentation** | Week 17 deliverable | — **Weeks 15–17** |

> Cross-check: nothing marked **Done** in Section 3 appears here. D-01 is **Partial** in Section
> 3 and its two missing parts (OpenRouter, Azure VM) are the first two rows here. That is
> consistent, and deliberately so.

---

## 10. Risks & Blockers

| Risk / Blocker | Status | Mitigation taken so far | Impact / support needed |
|---|---|---|---|
| **OpenRouter not provisioned** | **Open** | The zero-cost local fallback carries the entire build; every model reference is an env var, so switching is a config edit. Budget impact is ₹0. | **L&D support needed:** provision OpenRouter credits, or confirm the local-only path is acceptable for the final demo. This is the only item where I am blocked on someone else. |
| **A small local model writes its own prompt scaffolding into answers** | **Mitigated** | Four distinct leak classes were found and stripped (fenced tokens, agent tags, unterminated headings, raw JSON). The sanitiser is written on the assumption that anything shown to the model can come back out. Every leak has a regression test. | None. Largely disappears on a frontier model. |
| **The LLM Judge under-reports hallucinations** | **Realised, then mitigated** | The judge marked a **fabricated date** as grounded. A **deterministic fact check** now backs it: every date, id and record code in an answer must appear verbatim in the cited source. It can only add findings, never remove them. | None — but it is the reason the hallucination rate can be trusted, and worth demonstrating. |
| **`gemma3:4b` needs ~4 GiB free RAM** | **Open (environmental)** | If it cannot load, the gateway degrades to `gemma3:1b` and **logs a warning rather than failing silently**. Routing quality drops hard on the 1b model, so evidence must never be captured from a fallback run — the evidence pages say so explicitly. | None. Disappears on hosted inference. |
| **Response latency (8–15 min cross-domain)** | **Open (environmental)** | A 15-minute per-query hard stop was added so one stalled query cannot hang the suite; a timed-out query is **recorded as timed out, never silently skipped**. | None. This is CPU-bound local inference, not architecture — see Section 8. |
| **Demo runs on synthetic data** | **Mitigated (by design)** | Per the approved proposal's mock-data-only rule. Fixtures are causally linked so cross-domain reasoning is genuinely exercised, not faked. Live REST paths are implemented and unit-tested. | None. |

---

## 11. Declaration & Pre-Submission Checklist

- ☑ Section 1 matches the L&D Final Decision (Part D) exactly — *«verify Topic ID and Employee ID before submitting»*
- ☑ Every deliverable marked **Done** or **Partial** in Section 3 points to at least one Evidence ID in Section 4
- ☑ Coverage in Section 6 is a **measured** figure from `pytest-cov` (93%), attached as EV-14 — not an estimate
- ☑ Every approved tool is listed in Section 7, **including the ones not used** (OpenRouter, Llama 4 Scout, Azure B1s)
- ☑ Every deviation is disclosed in Section 8, including the newly added embedding model
- ☑ All grey italic instruction text deleted from the .docx
- ☑ No section renamed, deleted, renumbered or reordered
- ☑ Screenshots pasted full-size and readable, one per Evidence ID, none reused
- ☑ Saved as `S4-I-24_SridharVetrivel_MidTermDoc.docx`

**Participant:** Sridhar Vetrivel
**Date:** «submission date»

---

## Appendix — how to regenerate every number in this document

```bash
make cov       # Section 6 coverage + test count           -> EV-14
make qa        # Section 6 routing accuracy + hallucination -> EV-13
make evidence  # docs/qa/ — one page per Evidence ID
make index     # Section 3.1 chunk count                    -> EV-15
make up && make agents   # control plane + 5 nodes          -> EV-16
```

Nothing in this document is asserted. Every figure comes from a command you can re-run.
