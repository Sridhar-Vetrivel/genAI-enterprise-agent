# Implementation.md — Build Blueprint

The concrete build plan for **Psiog Kendra**, the multi-agent Enterprise Copilot. This turns
the design in [docs/solution-proposal.md](docs/solution-proposal.md) and
[docs/use-case.md](docs/use-case.md) into a directory layout, agent contracts, schemas, and a
week-by-week execution plan.

> **Status: Weeks 4–10 are BUILT.** All 5 agents, the RAG index, the 12-query suite and the
> Judge Agent are implemented and running. Weeks 11–17 remain. Read [CLAUDE.md](CLAUDE.md) for
> the non-negotiable design rules and [docs/AGENTFIELD.md](docs/AGENTFIELD.md) for the SDK API.

## Build status (as of Week 10)

| Deliverable | Week | Status | Evidence |
|---|---|---|---|
| Control plane, scaffolding, config, schemas | 4 | Done | `deploy/docker-compose.yml`, `psiog_kendra/config.py`, `schemas.py` |
| Coordinator: LLM routing + synthesis | 5 | Done | `psiog_kendra/coordinator.py`, `agents/coordinator.py` |
| Data Platform agent (Databricks) | 6 | Done | `psiog_kendra/specialists/data_agent.py` |
| Docs agent + RAG index | 7 | Done | `rag/`, `index_docs.py` — 21 chunks, 0 orphans |
| DevOps agent (GitHub Actions) | 8 | Done | `psiog_kendra/specialists/devops_agent.py` |
| CRM agent | 9 | Done | `psiog_kendra/specialists/crm_agent.py` |
| 4 agents live + routing + cited answers | 10 | Done | `make ask`, `make qa` |
| Judge Agent (was Week 13 — pulled forward) | 10 | Done | `psiog_kendra/qa/judge.py` |
| QA evidence pack (one page per test query) | 10 | Done | `docs/qa/` — `make evidence` |

**Measured:** routing accuracy **100%** on all 12 queries (live `gemma3:4b`); test coverage
**93%** (target ≥80%); 329 tests passing offline; LLM cost **₹0**.

### What the Judge Agent actually caught

The Judge is a graded deliverable, but it also earned its keep as a debugging instrument.
Seven defects were found in the first end-to-end QA runs, and **every one was found by
reading a raw verdict against the fixture — not one was visible from a PASS line.** The
offline suite could not have caught any of them: they are all things only the live model
does. Worth stating plainly in the mid-term doc, because it is the argument for why an LLM
judge belongs in the QA layer at all:

| # | What was wrong | Why it mattered |
|---|---|---|
| 1 | An answer about job **#4822** was served citing job **#4830** | A citation that does not match its answer *looks* grounded and is not. The worst failure this system can have. |
| 2 | The agents had no clock — "yesterday" resolved to a run 2 days old | Nearly every operational question here carries a relative date. |
| 3 | Prompt scaffolding recited into the answer text | Corrupted the answer *and* defeated the judge's claim-splitting. |
| 4 | The judge scored its own **citation label** as a hallucination | Reported 16.67% on a perfectly grounded answer. |
| 5 | The judge enumerated **source fields the answer never made** | Padded the denominator with free passes — this one flattered the score, which is the direction nobody goes looking. |
| 6 | The judge filed one claim as **both grounded and ungrounded** | A self-contradiction, scored as a hallucination. |
| 7 | An answer naming 3 CRM accounts **cited only 1** | Two-thirds of the claims uncited, in the one place where citing across systems *is* the deliverable. |

### Latency: the cost of running the fallback as the primary

**Every number in this build was produced on the zero-cost fallback, not the approved
primary.** The proposal names OpenRouter (`google/gemini-2.5-flash`) as the inference
provider; it is not provisioned, so all inference runs on `gemma3:4b` under Ollama, on CPU,
with no GPU. The functional result is unaffected — routing, grounding and citations are all
correct — but the latency is not comparable:

| Query type | LLM calls | Measured (local `gemma3:4b`, CPU) |
|---|---|---|
| Single-domain (Q1–Q8) | ~3 (route → specialist → judge) | **2–4 min** |
| Cross-domain (Q9–Q12) | ~5–7 (route → 2–4 specialists → synthesis → judge) | **8–15+ min** |
| Full 12-query QA run | ~60 | **~1 hour** |

A cross-domain query is slow because the calls are inherently sequential — the coordinator
cannot synthesise until every specialist has answered, and the judge cannot grade until the
answer exists. On a hosted endpoint each of those calls is sub-second rather than minutes,
so **the same run would complete in single-digit minutes, and answer quality would improve
too**: `gemini-2.5-flash` would not need the leak-stripping and citation-repair scaffolding
that `gemma3:4b` requires (see the seven defects above — most are small-model artefacts, not
architectural flaws).

This is a **deployment constraint, not a design one**. `AI_MODEL_COMPLEX` is an env var: the
day OpenRouter is provisioned, the model swaps with no code change, and the architecture,
the routing logic and the grounding contract are all unchanged. Worth stating explicitly in
the mid-term § 8 so the demo's response time is not read as an architectural weakness.

**Deviations from the approved proposal** (record these in the mid-term doc, § 8):

1. **OpenRouter is not provisioned** — all inference runs on local Ollama at ₹0. This is the
   single biggest deviation, and it is what makes the demo slow (see the latency table
   above). Everything else follows from it.
2. **The local model is Gemma 3, not Llama 4 Scout** — `gemma3:4b` for hard cases (routing,
   synthesis, judging), `gemma3:1b` for simple ones. Embeddings need a separate model
   (`nomic-embed-text`, 768-dim) because Gemma 3 cannot embed.
3. **Ollama 0.23 rejects any JSON schema containing `enum`** (HTTP 500), so the routing
   schema uses `list[str]` and the 4-domain vocabulary is enforced by a Pydantic validator
   instead. Same guarantee, different mechanism.
4. **Data sources are synthetic fixtures**, per the proposal's mock-data-only rule
   (§ 7). The live REST paths are implemented and unit-tested against a mocked transport;
   flip `USE_MOCK_SOURCES=false` and supply credentials to go live.

---

## 1. Architecture recap

```
User (any employee)
   │  natural-language query
   ▼
Coordinator Agent ── LLM classifies intent → selects domain(s) → dispatches → synthesizes
   │
   ├──────────────┬──────────────┬──────────────┐
   ▼              ▼              ▼              ▼
data-agent    devops-agent   crm-agent      docs-agent
Databricks    GitHub/Azure   CRM REST       AgentField
REST API      DevOps API     (HubSpot/mock) vector memory (RAG)
   │              │              │              │
   └──────────────┴──────────────┴──────────────┘
                       │
            Grounded, cited response → User
```

- Single-domain queries → one specialist. Cross-domain queries → multiple specialists
  dispatched **in parallel**, then synthesized into one cross-cited answer.
- Every specialist returns an `AgentResponse` with a `citations` list. The coordinator never
  invents facts — it only synthesizes what specialists returned.

---

## 2. Proposed directory structure

```
.
├── agents/
│   ├── coordinator/
│   │   ├── agent.py            # Agent init + route_query reasoner
│   │   └── prompts.py          # System prompts for routing + synthesis
│   ├── data_agent/
│   │   ├── agent.py            # Reasoner: interpret Databricks JSON → AgentResponse
│   │   └── skills.py           # @app.skill() Databricks REST calls (jobs, runs, warehouses)
│   ├── devops_agent/
│   │   ├── agent.py
│   │   └── skills.py           # GitHub Actions / Azure DevOps REST calls
│   ├── crm_agent/
│   │   ├── agent.py
│   │   └── skills.py           # CRM REST calls (HubSpot free tier or mock)
│   └── docs_agent/
│       ├── agent.py            # Reasoner: RAG answer from retrieved chunks
│       └── indexer.py          # One-time chunk → embed → set_vector pipeline
├── schemas/
│   └── models.py               # Shared Pydantic schemas (extra="forbid")
├── qa/
│   ├── judge_agent.py          # LLM Judge: grounding / hallucination verification
│   ├── test_queries.py         # The 12 mandatory test queries + expected domains
│   └── report.py               # Emits routing accuracy + hallucination rate report
├── data/
│   ├── docs/                   # Runbooks, architecture docs, incident records (RAG corpus)
│   └── mock/                   # Synthetic CRM / Databricks / DevOps fixtures for the demo
├── tests/
│   ├── unit/                   # Per-skill tests with mocked API responses
│   ├── integration/            # Per-agent end-to-end (query in → cited response out)
│   └── routing/                # Coordinator routing-accuracy suite
├── deploy/
│   ├── docker-compose.yml      # AgentField control plane + agents
│   └── .env.example            # AGENTFIELD_SERVER, AI_MODEL, API keys, etc.
├── scripts/
│   └── build_proposal_docx.py  # (exists) regenerates the .docx proposal
├── docs/                       # (exists) RFP, proposal, SDK reference, diagrams
├── Makefile                    # fmt, lint, test, index, up/down
├── pyproject.toml              # deps + ruff config
├── CLAUDE.md                   # (exists) agent working guidance
├── Implementation.md           # this file
└── README.md                   # (exists) project overview
```

> Structure is a proposal — refine as the build reveals better boundaries, but keep the
> one-agent-per-directory, skills-vs-reasoner separation.

---

## 3. Shared schemas (`schemas/models.py`)

Every LLM call returns a typed, validated Pydantic model. Keep types basic; always forbid extras.

```python
from pydantic import BaseModel, ConfigDict
from typing import List

class RoutingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domains: List[str]          # e.g. ["data-platform", "docs"]
    reasoning: str              # why these domains were selected
    is_cross_domain: bool

class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    citations: List[str]        # source system or document name(s)
    confidence: str             # "high" | "medium" | "low"

class CopilotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str                 # final synthesized answer
    citations: List[str]        # union of all specialist citations
    domains_used: List[str]

class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grounded_claims: int
    total_claims: int
    ungrounded_claims: List[str]  # claims not supported by cited sources
    hallucination_rate: float     # (ungrounded / total) * 100
```

Domain labels are a fixed vocabulary: `data-platform`, `devops`, `crm`, `docs`.

---

## 4. Agent contracts

### Coordinator (`coordinator`)
- **Reasoner `route_query(query) -> CopilotResponse`:** LLM produces a `RoutingDecision`, then
  `app.call(...)` dispatches to each selected specialist (parallel for cross-domain), collects
  their `AgentResponse`es, and a second LLM call synthesizes them into a `CopilotResponse`.
- Persists conversation turns in `session` memory for multi-turn context.
- Must never answer from its own knowledge — only from specialist outputs.

### Data Platform (`data-agent`)
- **Skills:** `get_job_runs`, `get_pipeline_status`, `get_last_error` — wrap the Databricks
  Jobs / SQL Warehouses REST API.
- **Reasoner:** turns raw API JSON into a readable `AgentResponse` (does not dump JSON); cites
  the job/run id.

### DevOps (`devops-agent`)
- **Skills:** `get_build_status`, `get_deployment_history`, `get_quality_gates` — GitHub
  Actions / Azure DevOps REST API.
- **Reasoner:** explains *why* a build failed (summarizes logs), not just the status code;
  cites commit SHA + run.

### CRM (`crm-agent`)
- **Skills:** `get_deal_status`, `get_account_owner`, `get_contact_history` — CRM REST API
  (HubSpot free tier or mock).
- **Reasoner:** formats records into a contextual answer relevant to the question; cites the
  record.

### Docs (`docs-agent`)
- **`indexer.py`:** one-time pipeline — chunk each doc → embed → `set_vector(chunk_id,
  embedding, metadata={source, section, url})`.
- **Reasoner:** embed the query → `similarity_search(top_k=5)` → generate a cited answer from
  retrieved chunks; each citation is the exact document name + section.

---

## 5. RAG indexing pipeline (docs-agent)

```python
# Index once at setup (indexer.py)
await app.memory.set_vector(chunk_id, embedding_vector, metadata={
    "source": "runbook-12.md",
    "section": "Schema Mismatch Recovery",
    "url": "internal-docs/runbooks/runbook-12.md",
})

# At query time
results = await app.memory.similarity_search(query_embedding, top_k=5)
# each result → {key, score, text}; use metadata as the citation
```

Data-validation gate before the Week 10 checkpoint: all docs chunked and indexed, every chunk
has valid metadata, no orphan chunks, and similarity search returns relevant results for ≥5
representative queries.

---

## 6. The 12 mandatory test queries

| # | Query | Expected domain(s) |
|---|---|---|
| 1 | Did yesterday's ETL pipeline run successfully? | data-platform |
| 2 | What was the error in the last failed Databricks job? | data-platform |
| 3 | Did the payments service deployment pass all quality gates? | devops |
| 4 | What was the last deployment date for the auth service? | devops |
| 5 | What is the deal status for Acme Corp? | crm |
| 6 | Who is the account owner for TechStart Ltd? | crm |
| 7 | What is the runbook for a schema mismatch error? | docs |
| 8 | What does the architecture doc say about the ingestion pipeline? | docs |
| 9 | Did last night's pipeline failure affect any CRM customer sync? | data-platform + crm |
| 10 | The ingestion job failed — is there a fix in the runbooks? | data-platform + docs |
| 11 | Status of the latest deployment and any known issues? | devops + docs |
| 12 | Full status update — pipeline, deployments, and open incidents | all 4 |

The routing suite asserts `RoutingDecision.domains` equals the expected set for each. Target:
**100% routing accuracy**.

---

## 7. QA layers

| Layer | What it tests | How |
|---|---|---|
| Unit | Each `@app.skill()` in isolation | pytest + mocked API responses |
| Integration | Each specialist end-to-end (query → cited response) | pytest against live control plane |
| Routing | Coordinator routes all 12 queries correctly | automated actual-vs-expected suite |
| E2E | Full lifecycle, user input → final cited response | curl / harness against deployed system |

**Judge Agent** (`qa/judge_agent.py`): for each answer, fetch the cited raw source, verify each
claim against it, flag ungrounded claims, and emit `hallucination_rate = (ungrounded / total)
× 100`. Target **<10%** across all 12 queries. Also used as an LLM judge for routing decisions
and a 1–5 response-quality score.

Coverage target: **≥80%** overall.

---

## 8. Week-by-week execution plan (Weeks 4–17)

The build backbone. Each week lists the tasks, the files/artifacts it produces, and the QA
activity that must pass before moving on. Weeks map 1:1 to the proposal timeline
([docs/solution-proposal.md](docs/solution-proposal.md) § 8).

### Phase 1 — Foundation + Specialist Agents (Weeks 4–9)

#### Week 4 — Environment & scaffolding

- **Tasks:** Provision Azure B1s VM (free tier). Bring up the AgentField control plane via
  `deploy/docker-compose.yml`. Connect OpenRouter; verify a round-trip `app.ai(...)` call.
  Stand up the repo skeleton (`agents/`, `schemas/`, `qa/`, `tests/`, `data/`, `deploy/`).
- **Produces:** `deploy/docker-compose.yml`, `deploy/.env.example`, `pyproject.toml` (ruff +
  deps), `Makefile` (`fmt`/`lint`/`test`/`up`/`down`), `schemas/models.py` scaffold.
- **QA gate:** `make up` starts the control plane; a smoke test executes a trivial reasoner via
  `curl`; ruff formatting clean.

#### Week 5 — Coordinator Agent (routing)

- **Tasks:** Implement `agents/coordinator/agent.py` with `route_query`. LLM produces a
  `RoutingDecision` over the fixed vocabulary (`data-platform`, `devops`, `crm`, `docs`).
  Author routing/synthesis system prompts in `prompts.py`. Finalize all Pydantic schemas.
- **Produces:** `coordinator/agent.py`, `coordinator/prompts.py`, finalized `schemas/models.py`.
- **QA gate:** Routing unit tests on a starter subset of the 12 queries assert
  `RoutingDecision.domains` matches expected; schema validation rejects extra fields.

#### Week 6 — Data Platform Agent

- **Tasks:** Implement `data_agent/skills.py` (`get_job_runs`, `get_pipeline_status`,
  `get_last_error`) over the Databricks Jobs / SQL Warehouses REST API. Reasoner turns JSON
  into a cited `AgentResponse`. Add `data/mock/databricks_*.json` fixtures.
- **Produces:** `data_agent/agent.py`, `data_agent/skills.py`, mock fixtures.
- **QA gate:** Unit tests for each skill with mocked API responses (happy/edge/error);
  reasoner cites the job/run id and never dumps raw JSON.

#### Week 7 — Docs Agent + RAG index

- **Tasks:** Curate the doc corpus in `data/docs/` (runbooks, architecture docs, incident
  records). Build `docs_agent/indexer.py`: chunk → embed → `set_vector` with
  `{source, section, url}` metadata. Reasoner embeds query → `similarity_search(top_k=5)` →
  cited answer.
- **Produces:** `docs_agent/agent.py`, `docs_agent/indexer.py`, populated vector memory.
- **QA gate:** **Data-validation gate** — all docs chunked/indexed, every chunk has valid
  metadata, no orphan chunks, similarity search relevant for ≥5 representative queries.

#### Week 8 — DevOps Agent

- **Tasks:** Implement `devops_agent/skills.py` (`get_build_status`,
  `get_deployment_history`, `get_quality_gates`) over GitHub Actions / Azure DevOps REST API.
  Reasoner explains *why* a build failed (summarizes logs), cites commit SHA + run.
- **Produces:** `devops_agent/agent.py`, `devops_agent/skills.py`, mock fixtures.
- **QA gate:** Unit tests per skill; reasoner output explains failure cause, not just status.

#### Week 9 — CRM Agent

- **Tasks:** Implement `crm_agent/skills.py` (`get_deal_status`, `get_account_owner`,
  `get_contact_history`) over the CRM REST API (HubSpot free tier or `data/mock/crm_*.json`).
  Reasoner formats records into a contextual, cited answer.
- **Produces:** `crm_agent/agent.py`, `crm_agent/skills.py`, mock fixtures.
- **QA gate:** Unit tests per skill; integration test — query in → cited response out.

#### Week 10 — 🔵 CHECKPOINT (mid-term)

- **Tasks:** Wire the coordinator to all 4 specialists via `app.call(...)`. Run routing across
  every domain. Compile mid-term evidence.
- **Exit criteria:** 4 agents live; routing works across all domains; **≥6 of 12** queries
  return grounded, cited responses; unit coverage **≥50%**; mid-term docs on Moodle
  (architecture diagram, agent code, test results).

### Phase 2 — Cross-domain, QA & Deployment (Weeks 11–17)

#### Week 11 — Cross-domain orchestration

- **Tasks:** Coordinator dispatches multiple specialists **in parallel** and synthesizes one
  cross-cited `CopilotResponse`. Persist conversation turns in `session` memory for multi-turn.
- **Produces:** Parallel dispatch + synthesis logic in `coordinator/agent.py`.
- **QA gate:** Cross-domain queries (#9–#12) return a unified answer citing every domain used;
  a follow-up question resolves against session context.

#### Week 12 — Full test suite + routing accuracy

- **Tasks:** Implement all 12 queries in `qa/test_queries.py` and the `tests/routing/` suite.
  Measure routing accuracy; capture an initial hallucination-rate baseline.
- **Produces:** `qa/test_queries.py`, complete `tests/routing/` suite.
- **QA gate:** Routing accuracy measured and trending to **100%** on the 12 queries.

#### Week 13 — Judge Agent (AI-assisted QA)

- **Tasks:** Build `qa/judge_agent.py`: fetch cited raw source, verify each claim, flag
  ungrounded claims, emit `JudgeVerdict` with `hallucination_rate`. Also LLM-judge routing
  decisions and score response quality (1–5). Generate a per-run report in `qa/report.py`.
- **Produces:** `qa/judge_agent.py`, `qa/report.py`.
- **QA gate:** Judge produces an automated grounding report per run; hallucination rate
  computed across all 12 queries.

#### Week 14 — Azure deployment

- **Tasks:** Deploy the full system (control plane + all agents) on the Azure B1s VM via Docker
  Compose. Connect all agents end-to-end in the cloud environment.
- **Produces:** Deployed stack; documented deploy runbook in `deploy/`.
- **QA gate:** E2E test harness hits the deployed system and all 12 queries return cited answers.

#### Week 15 — QA hardening

- **Tasks:** Drive coverage to **≥80%** across routing, retrieval, integration, and response
  generation. Handle edge cases (empty results, API timeouts, ambiguous routing). Validate
  response quality across all 12 queries.
- **QA gate:** Coverage report ≥80%; full regression suite green in GitHub Actions CI.

#### Week 16 — Demo preparation

- **Tasks:** Write the demo script. Compile all evidence — routing logs, hallucination-rate
  report, coverage metrics, cost breakdown.
- **Produces:** Demo script + evidence bundle.
- **QA gate:** Dry-run of the full demo passes end-to-end.

#### Week 17 — 🔵 FINAL DEMO

- **Exit criteria:** Complete copilot live on Azure across 4 domains; **all 12** queries
  passing with correct routing, grounded responses, and citations; hallucination rate
  documented (**<10%**); routing accuracy **100%**; QA coverage **≥80%**; Judge Agent reports;
  recorded live demo; all evidence on Moodle.

### Critical path & dependencies

- Week 4 (control plane) blocks everything. Week 5 (coordinator + schemas) blocks all
  specialists. Week 7's RAG data-validation gate blocks the docs-agent’s reliability.
- Specialists (Weeks 6–9) are independent of each other and could be parallelized if capacity
  allows — but each depends on the Week 5 schema contract.
- Cross-domain (Week 11) depends on **all** specialists being live (Week 10). The Judge Agent
  (Week 13) depends on the full query suite (Week 12).

---

## 9. Deliverables checklist

**Week 10 checkpoint**
- [ ] All 4 specialist agents operational and routing correctly
- [ ] Vector memory indexed with runbooks + architecture docs
- [ ] NL routing working across all 4 domains
- [ ] ≥6 of 12 test queries returning grounded, cited responses
- [ ] Unit tests passing for all skill functions
- [ ] Mid-term documentation on Moodle

**Week 17 final**
- [ ] Complete copilot deployed on Azure
- [ ] All 12 queries passing: correct routing, grounded, cited
- [ ] Hallucination rate documented and measured (<10%)
- [ ] Routing accuracy 100% on the 12 queries
- [ ] QA suite ≥80% coverage
- [ ] Judge Agent producing automated grounding reports
- [ ] Live demo recorded; all evidence on Moodle

---

## 10. Environment variables

| Var | Purpose | Example |
|---|---|---|
| `AGENTFIELD_SERVER` | Control-plane URL | `http://localhost:8080` |
| `AI_MODEL` | LLM model (swap primary/fallback with no code change). **Use the local Ollama model now — OpenRouter is not yet provisioned.** | `ollama/gemma3:4b` (current default) · `ollama/gemma3:1b` (fast fallback) · `google/gemini-2.5-flash` (once OpenRouter is live) |
| `OLLAMA_HOST` | Local Ollama server (current inference path) | `http://localhost:11434` |
| `OPENROUTER_API_KEY` | OpenRouter inference — **not provisioned yet; leave unset until available** | — |
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN` | Databricks REST API | — |
| `GITHUB_TOKEN` / `AZDO_TOKEN` | DevOps REST API | — |
| `CRM_API_KEY` | CRM REST API (or unset → mock) | — |

Keep secrets out of git; commit only `deploy/.env.example`.
