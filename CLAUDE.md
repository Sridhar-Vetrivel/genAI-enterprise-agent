# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repository.

## What this project is

**Psiog Kendra** — a GenAI-powered, multi-agent **Enterprise Copilot**. Any Psiog
employee asks an operational question in plain English and gets a **grounded, cited
answer** pulled live from Databricks, GitHub/Azure DevOps, a CRM, and internal docs —
without knowing which system to open or how to query it.

Built as the **Semester 4 Capstone** in response to RFP **S4-I-24** (Impact pSiddhi —
pSiddhi-2026-01). Budget ceiling: **₹2,500 (fixed, non-negotiable)**. Timeline: Weeks 4–17.

The architecture is **1 Coordinator Agent + 4 Specialist Agents**, built on
[AgentField](docs/AGENTFIELD.md), an open-source (Apache 2.0) multi-agent orchestration
framework:

| Agent | Domain | Data Source |
|---|---|---|
| `coordinator` | LLM intent classification, routing, cross-domain synthesis | LLM via OpenRouter |
| `data-agent` | Data platform | Databricks REST API (Jobs, SQL Warehouses) |
| `devops-agent` | CI/CD | GitHub Actions / Azure DevOps REST API |
| `crm-agent` | Customer data | CRM REST API (HubSpot free tier / mock) |
| `docs-agent` | Internal knowledge | AgentField vector memory (RAG over runbooks/docs) |

## Current state — READ THIS FIRST

**Weeks 4–10 are built and running.** All 5 agents, the RAG index, the 12-query suite and the
Judge Agent are implemented. Weeks 11–17 remain (see [Implementation.md](Implementation.md) § 8).

Background reading:

- [docs/use-case.md](docs/use-case.md) — precise use case, 5 scenarios, success criteria, hard boundaries
- [docs/solution-proposal.md](docs/solution-proposal.md) — full architecture, schemas, QA, budget, timeline
- [docs/AGENTFIELD.md](docs/AGENTFIELD.md) — the AgentField SDK reference (the only orchestration API to use)
- [docs/RFP-DOC-S4-I-24.md](docs/RFP-DOC-S4-I-24.md) — the customer's original requirements
- [Implementation.md](Implementation.md) — the build blueprint + current build status

### Where the code lives

- `psiog_kendra/` — the copilot itself, deliberately **framework-free** so it is unit-testable
  without a running control plane. `coordinator.py`, `specialists/`, `sources/`, `rag/`, `qa/`.
- `agents/` — thin **AgentField nodes** (`@app.skill()`, `@app.reasoner()`, `app.call()`) that
  delegate to `psiog_kendra`. This split is why the suite hits 94% coverage offline.
- `psiog_kendra/config.py` + `deploy/.env.example` — **every** setting. Nothing is hardcoded:
  no URL, endpoint path, model name, agent node id, file path, limit or threshold. If you need
  a new constant, it goes in `config.py` and is documented in `.env.example`.

### Hard-won constraints — do not rediscover these

- **Ollama 0.23 returns HTTP 500 for any JSON schema containing `enum`.** Schemas sent to the
  model are stripped by `llm.strip_unsupported()`; the 4-domain vocabulary is enforced by a
  Pydantic validator (`domains.normalize_domains`) instead. Never put a `Literal`/`Enum` in a
  schema that reaches the LLM.
- **`gemma3:4b` needs ~4 GiB of free RAM.** If it will not load, the gateway degrades to
  `gemma3:1b` and logs a warning. Routing quality drops hard on 1b (it over-selects domains) —
  a 100% routing run needs the 4b model.
- **Gemma 3 cannot produce embeddings.** RAG uses `nomic-embed-text` (768-dim), pulled locally.
- **Routing is prompt-sensitive.** The coordinator's system prompt teaches *minimal* domain
  selection with worked examples that are deliberately **not** the 12 graded queries. Do not
  paste the test queries into the prompt — that would be teaching to the test.
- **The model cannot be trusted to say which record it used.** It will answer entirely about
  job #4822 and cite job #4830 — a real source, on the allow-list, from the right system, that
  it never touched. An allow-list check does not catch this. `prompting._supported_by()` makes
  the answer's own record ids (`#4822`, `#99150`) the arbiter and drops any citation the prose
  contradicts. This applies to citations the model writes *inline* too: lifting one out of the
  prose proves it *meant* to cite it, not that the citation is right. **A mismatched citation
  is the worst bug this system can have — it looks grounded and is not.**
- **The LLM has no clock.** Asked about "yesterday", it picks whichever record it likes.
  `build_grounded_prompt()` states today's date and what "yesterday" resolves to. Almost every
  operational question here carries a relative date, so never drop the anchor.
- **Sanitising the answer is string surgery on facts.** `finalize()` deletes citation strings
  from the prose; the obvious repairs corrupt the very facts the answer exists to quote. Never
  add a `".x"` → `". x"` rule — it turns `part-0007.parquet` into `part-0007. parquet`. Test
  any cleanup against file paths, error messages and timestamps before shipping it.

## Non-negotiable design rules

These come from the RFP and the use case. Do not violate them — they are the grading criteria.

1. **Every response must be grounded and cited.** No answer from LLM training data. Each
   response carries a `citations` list naming the source system or document. This is not a
   chatbot.
2. **Routing is LLM-based intent classification, not keyword matching.** No `if/else` on
   keywords. The same question phrased differently must route correctly.
3. **Distinct specialist agents — not one LLM with a long system prompt.** The multi-agent
   architecture is the point.
4. **Structured output everywhere.** Every LLM call returns a Pydantic model with
   `model_config = ConfigDict(extra="forbid")`. Responses must be machine-verifiable for QA.
5. **Live (or realistic mock) data only.** No read-only demo faking results.
6. **Stay within ₹2,500.** Every tool is open-source/self-hosted or free-tier. LLM inference
   via OpenRouter is the sole budgeted cost; Ollama + Llama 4 Scout is the zero-cost local fallback.
7. **Capstone demo uses mock/synthetic data only** — no real customer records or internal
   data is ever sent to an external LLM. (See solution-proposal.md § 7.)

## Tech stack

- **Orchestration:** AgentField (self-hosted via Docker Compose) — agents, vector memory, DAG tracing
- **LLM inference:** **Currently OpenRouter is NOT provisioned — use the zero-cost local Ollama model for every LLM call.** The available local model is `ollama/gemma3:4b` (default; `ollama/gemma3:1b` as an ultra-fast fallback), served on `http://localhost:11434`. OpenRouter (`google/gemini-2.5-flash`) remains the intended primary once provisioned. Model is swappable via the `AI_MODEL` env var — no code changes.
  - ⚠️ Note: the approved proposal named **Llama 4 Scout** as the local model, but the machine actually has **Gemma 3** (`gemma3:4b`, `gemma3:1b`) installed — record this as a deviation in the mid-term doc (Section 8).
- **Structured output:** Pydantic (`extra="forbid"`)
- **Hosting:** Azure B1s VM (12-month free tier), Docker Compose
- **QA:** Pytest, GitHub Actions CI, and an LLM Judge Agent for hallucination detection
- **Language:** Python 3.11+, async/await for all I/O

## AgentField patterns (the only orchestration API)

Use the primitives from [docs/AGENTFIELD.md](docs/AGENTFIELD.md) — do not reach for LangChain
or the Microsoft Agent Framework (the proposal deliberately replaced them with AgentField).

- `Agent(node_id=..., agentfield_server=..., ai_config=AIConfig(model=...))` — agent init
- `@app.skill()` — deterministic functions (API calls, data manipulation)
- `@app.reasoner()` — non-deterministic, LLM-driven logic
- `await app.ai(system=..., user=..., schema=PydanticModel)` — structured LLM call
- `await app.call("node_id.reasoner_name", input={...})` — agent-to-agent call via control plane (traced as a DAG)
- `await app.memory.set(scope, key, obj)` / `.get(scope, key)` — scopes: `global`, `agent`, `session`, `run`
- `await app.memory.set_vector(chunk_id, embedding, metadata=...)` — vector storage
- `await app.memory.similarity_search(query_embedding, top_k=...)` — semantic search (returns key/score/text)
- `@app.on_change(pattern)` — memory event listeners

Test a reasoner:
```bash
curl -X POST http://[control_plane_url]/api/v1/execute/[node_id].[reasoner_name] \
  -H "Content-Type: application/json" \
  -d '{"input": { /* JSON payload */ }}'
```

## Commands

```bash
make install    # venv + deps
make index      # chunk + embed the docs corpus (run after changing data/docs/)
make test       # offline suite — no LLM, no network, no control plane
make cov        # the same, with coverage (must stay >=80%)
make test-live  # the tests that call the real local models (needs ~4 GiB free RAM)
make qa         # 12 test queries + Judge Agent -> data/qa_report.json
make ask Q="did the sales etl run?"
make up && make agents   # AgentField control plane + register the 5 nodes
```

A full `make qa` is ~60 local LLM calls and takes a long time on CPU. It prints each query
as it lands and checkpoints to `data/qa_report.json`, so a killed run is not a lost run.

## Code style

- **Ruff** for linting and formatting (`make fmt` runs `ruff format`)
- Type hints required on public APIs
- Async/await for all I/O
- Follow PEP 8 and the SOLID, YAGNI, DRY, KISS principles
- Keep Pydantic schemas simple (basic types), always `ConfigDict(extra="forbid")`

## Testing

Write tests that cover: (1) happy path, (2) edge cases (empty/null/boundary), (3) error cases
(invalid input, network failure, timeout), (4) integration points (verify mocks are called).

Quality bar — a test must:
- Actually fail when the code is broken
- Have clear assertions, not just "runs without error"
- Cover edge and error paths, not just the happy path
- Be independent and order-agnostic

QA targets from the proposal (see [docs/solution-proposal.md](docs/solution-proposal.md) § 5):
- **Routing accuracy:** 100% on the 12 mandatory test queries
- **Hallucination rate:** `(ungrounded claims / total claims) × 100`, target **<10%**, measured by the Judge Agent
- **Test coverage:** **≥80%** across routing, retrieval, integration, and response generation

## Regenerating the proposal document

```bash
python scripts/build_proposal_docx.py
```

Rebuilds `docs/RFP_Solution_Proposal_Psiog_Kendra.docx` from `docs/solution-proposal.md` and
`docs/use-case.md`. Keep the markdown as the source of truth; regenerate the `.docx` — do not
hand-edit it.

## Commit attribution

**Do not add a `Co-Authored-By` trailer.** Commits are authored under the repository owner's
name only. Write the message body to explain *why* the change was made.

## Things to avoid

- Don't hand-edit `docs/*.docx` or `docs/*.pptx` — regenerate from the markdown sources.
- Don't introduce LangChain / MS Agent Framework — the design uses AgentField exclusively.
- Don't add paid dependencies. If a free tier is at risk, fall back to Ollama (₹0).
- Don't route on keywords or answer from model knowledge — grounding and LLM routing are graded.
