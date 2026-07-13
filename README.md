# Psiog Kendra — GenAI-Powered Enterprise Copilot

A multi-agent AI copilot that lets any Psiog employee ask an operational question in plain English and get a **grounded, cited answer** — pulled live from Databricks, GitHub/Azure DevOps, CRM, and internal documentation — without knowing which system to open or how to query it.

> Built in response to RFP **S4-I-24** (Impact pSiddhi — pSiddhi-2026-01, Semester 4 Capstone). Budget ceiling: ₹2,500 (fixed). Timeline: Weeks 4–17.

## The Problem

Psiog's engineering, data, and operations teams work across a fragmented technology estate — Databricks, GitHub/Azure DevOps, a CRM, and scattered runbooks/architecture docs. Answering even a simple question ("did yesterday's pipeline run succeed?") means opening 4–5 tools, using different credentials, and manually stitching results together. This creates an onboarding bottleneck, drains senior engineers as human routers, and slows cross-functional decisions.

## The Solution

**Psiog Kendra** is a **Coordinator Agent** + **4 Specialist Agents** built on [AgentField](docs/AGENTFIELD.md), an open-source multi-agent orchestration framework:

| Agent | Domain | Data Source |
|---|---|---|
| `coordinator` | Classifies intent, routes to specialist(s), synthesizes the final answer | LLM (local Ollama; OpenRouter once provisioned) |
| `data-agent` | Data platform | Databricks REST API (Jobs, SQL Warehouses) |
| `devops-agent` | CI/CD | GitHub Actions / Azure DevOps REST API |
| `crm-agent` | Customer data | CRM REST API (HubSpot free tier / mock) |
| `docs-agent` | Internal knowledge | AgentField vector memory (RAG over runbooks & architecture docs) |

Every response must cite its source (system or document) — this is not a chatbot answering from training data. Routing decisions are LLM-based intent classification, not keyword matching. See [docs/use-case.md](docs/use-case.md) for the full "what this is NOT" boundary.

```
User → Coordinator Agent (LLM routes intent) → one or more Specialist Agents (live data)
     → Grounded, cited response → User
```

For cross-domain questions (e.g. "did last night's pipeline failure affect any CRM sync?"), the Coordinator dispatches multiple specialists in parallel and synthesizes a single cross-cited answer.

## Quick Start

```bash
make install                    # venv + dependencies
cp deploy/.env.example .env     # every setting lives here; nothing is hardcoded
make index                      # chunk + embed the docs corpus into the vector index
make ask Q="Did yesterday's ETL pipeline run successfully?"
```

Prerequisites: Python 3.11+, [Ollama](https://ollama.com) running locally with
`gemma3:4b`, `gemma3:1b` and `nomic-embed-text` pulled. **gemma3:4b needs ~4 GiB of free
RAM**; if it will not fit, the gateway degrades to `gemma3:1b` and says so (routing quality
drops noticeably — free the RAM for real results).

```bash
make test      # offline suite: no LLM, no network        (206 tests)
make cov       # the same, with a coverage report          (94%)
make test-live # the tests that call the real local models
make qa        # 12 test queries + Judge Agent -> QA evidence report
make up        # AgentField control plane (Docker)
make agents    # register the 5 agents against it
```

## Repository Layout

```
.
├── psiog_kendra/            # the copilot (framework-free, unit-testable)
│   ├── config.py            # ALL settings, env-driven — nothing hardcoded anywhere
│   ├── schemas.py           # Pydantic contracts, every one extra="forbid"
│   ├── llm.py               # the single LLM gateway: 2 local model tiers + OOM fallback
│   ├── domains.py           # the 4-domain vocabulary and label normalisation
│   ├── coordinator.py       # LLM routing → parallel dispatch → cross-domain synthesis
│   ├── specialists/         # the 4 domain agents (skill + reasoner each)
│   ├── sources/             # Databricks / GitHub Actions / CRM clients (live + mock)
│   ├── rag/                 # chunk → embed → vector store → semantic retrieval
│   ├── qa/                  # 12 test queries, Judge Agent, QA report
│   ├── index_docs.py        # one-time RAG indexing + data-validation gate
│   └── cli.py               # chat interface
├── agents/                  # AgentField nodes: @app.skill / @app.reasoner / app.call
├── data/
│   ├── docs/                # the RAG corpus (runbooks, architecture, incidents)
│   └── mock/                # synthetic Databricks / DevOps / CRM fixtures
├── tests/                   # unit + integration + routing-accuracy suites
├── deploy/                  # docker-compose.yml + .env.example (every setting documented)
├── docs/                    # RFP, proposal, SDK reference, diagrams
├── CLAUDE.md                # working guidance for AI agents in this repo
├── Implementation.md        # the week-by-week build blueprint
└── README.md
```

**Current state:** the Weeks 4–10 build is complete — all 5 agents, the RAG index, the QA
suite and the Judge Agent are implemented and running. See [Implementation.md](Implementation.md)
for the week-by-week plan and what remains for Weeks 11–17.

### Measured results (local, gemma3:4b)

| Metric | Target | Measured |
|---|---|---|
| Routing accuracy (12 queries) | 100% | **100%** |
| Test coverage | ≥80% | **94%** |
| Answers carrying citations | all | all |
| LLM cost | ₹0 | **₹0** (fully local) |

## Tech Stack

- **Orchestration:** AgentField (Apache 2.0, self-hosted via Docker Compose) — coordinator/specialist agents, built-in vector memory, automatic call tracing as a DAG
- **LLM inference:** **Ollama, fully local, ₹0** — `gemma3:4b` for the hard calls (routing, synthesis, judging), `gemma3:1b` for the simple ones, `nomic-embed-text` for embeddings. OpenRouter (`google/gemini-2.5-flash`) is the intended primary but is **not yet provisioned**, so nothing in this build depends on it. Every model is swappable via env var, no code changes.
  - The approved proposal named **Llama 4 Scout** as the local model; the machine actually has **Gemma 3**. Recorded as a deviation in [Implementation.md](Implementation.md).
- **Structured output:** Pydantic schemas (`extra="forbid"`) for every LLM response — machine-verifiable for QA
- **Hosting:** Azure B1s VM (12-month free tier)
- **QA:** Pytest, GitHub Actions CI, an LLM Judge Agent for hallucination detection

Full cost breakdown and justification: [docs/solution-proposal.md § 6](docs/solution-proposal.md).

## QA & Success Criteria

- **Routing accuracy:** 100% on 12 mandatory test queries (single-domain and cross-domain)
- **Hallucination rate:** `(ungrounded claims / total claims) × 100`, measured by a dedicated Judge Agent, target <10%
- **Test coverage:** ≥80% across routing, retrieval, integration, and response generation

Full test query list and QA layers: [docs/solution-proposal.md § 5](docs/solution-proposal.md).

## Regenerating the Proposal Document

```bash
python scripts/build_proposal_docx.py
```

Rebuilds `docs/RFP_Solution_Proposal_Psiog_Kendra.docx` from the content in `docs/solution-proposal.md` and `docs/use-case.md`.
