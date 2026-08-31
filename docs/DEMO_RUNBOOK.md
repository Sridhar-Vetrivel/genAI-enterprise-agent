# Psiog Kendra — Execution & Demo Runbook

A step-by-step guide to running the copilot and demonstrating it end-to-end. Every command
here is real and copy-pasteable. Read the **⏱ timing** and **⚠️ gotcha** callouts — this build
runs on a **local 4B model on CPU with no GPU**, so responses take **minutes, not seconds**, and
that surprises everyone the first time.

> **What you are demonstrating.** A GenAI multi-agent Enterprise Copilot: one Coordinator agent
> classifies a plain-English question with an LLM and routes it to one or more of four specialist
> agents (Data Platform, DevOps, CRM, Docs). Every answer is **grounded and cited** — pulled from
> data, never from model memory. Cross-domain questions fan out to several specialists and are
> synthesised into one cited answer, with every hop traced as a DAG.

---

## 0. Two ways to run it — pick per audience

| Track | Command surface | Needs control plane? | Best for |
|---|---|---|---|
| **A — Quick CLI** | `make ask Q="…"` | **No** — runs in-process | A fast "it works, and it cites" moment |
| **B — Full architecture** | `make up && make agents`, then the UI at `http://localhost:8080/ui/` | **Yes** | Showing the 5 distinct agents, routing, and the cross-domain DAG |

Track B is the real showpiece — it proves the *multi-agent* claim. Track A is the fastest way to
show a grounded, cited answer without waiting on the control plane. **Do both**: A to warm up, B
for the architecture.

---

## 1. Prerequisites (one machine, all local)

| Requirement | Check | Notes |
|---|---|---|
| Python **3.11+** | `python3 --version` | 3.11 or 3.12 |
| **Docker** + Compose | `docker ps` | Runs the AgentField control plane |
| **Ollama** running | `curl -s localhost:11434/api/version` | Usually a background service — see ⚠️ below |
| Models pulled | `ollama list` | `gemma3:4b`, `gemma3:1b`, `nomic-embed-text` |
| **~4 GiB free RAM** | `free -h` | `gemma3:4b` will not load without it — see §7 |

⚠️ **Do not run `ollama serve` by hand.** Ollama typically runs as a background service already;
a second copy fails with `bind: address already in use`. Verify it's up with
`curl -s localhost:11434/api/version` (expect a version string). Only start it manually if that
returns nothing.

If a model is missing:

```bash
ollama pull gemma3:4b
ollama pull gemma3:1b
ollama pull nomic-embed-text
```

---

## 2. One-time setup

```bash
cd ~/genAI-Enterprise-Copilot

make install                 # create the venv, install the project + dev deps
cp deploy/.env.example .env  # every setting is here; defaults work out of the box
make index                   # chunk + embed the docs corpus into the LOCAL vector store
```

`make index` prints `indexed 21 chunks … data-validation gate passed`. This local index is what
the offline suite and the in-process CLI (Track A) read.

**Sanity-check the build offline (no LLM, no network, ~4 seconds):**

```bash
make cov
```

Expect **`415 passed`** and **`Total coverage: 93.11%`**. If this is green, the code is sound
before you involve any model.

---

## 3. Pre-demo checklist (run this right before presenting)

```bash
free -h                                  # confirm ~4 GiB free  (gemma3:4b needs it)
curl -s localhost:11434/api/version      # confirm Ollama is up
ollama ps                                # what's loaded now (empty is fine — loads on first call)
ollama list                              # gemma3:4b, gemma3:1b, nomic-embed-text all present
```

⚠️ **Close other memory-hungry apps.** If `gemma3:4b` cannot load, the gateway silently degrades
to `gemma3:1b`, which **over-selects domains and routes worse**. A degraded run is not a valid
demo. The gateway logs a warning when this happens — watch for
`falling back to gemma3:1b` and stop if you see it.

⚠️ **Do not run two model workloads at once.** `make ask` and the agent fleet both want the same
~4 GiB. Run one thing at a time.

---

## 4. Track A — Quick CLI demo (in-process, no control plane)

```bash
make ask Q="Did yesterday's ETL pipeline for the sales data run successfully?"
```

⏱ **~2 minutes** on CPU. You'll get a grounded answer plus a `citations:` line naming the exact
Databricks run. That citation is the whole point — the answer came from data, not model memory.

Try a cross-domain one (routes to two specialists, synthesised):

```bash
make ask Q="Did last night's pipeline failure affect any CRM customer sync?"
```

⏱ **~5–6 minutes.** It connects the failed `crm_sync` job to the specific CRM accounts affected,
citing both systems.

> Track A runs the coordinator with in-process specialists — it needs only Ollama and the local
> index from §2. No `make up`, no `make agents`.

---

## 5. Track B — Full multi-agent architecture demo

### 5.1 Bring up the control plane and the five agents

```bash
make up        # start the AgentField control plane (Docker)  ->  http://localhost:8080
make agents    # start all 5 agent nodes, health-check them, and index the control-plane store
```

`make agents` waits ~8s, then prints a health table. **Do not proceed until you see all five
`up` and the final line `all 5 nodes serving and routable`:**

```
  [     up     ] coordinator    :8001
  [     up     ] crm-agent      :8004
  [     up     ] data-agent     :8002
  [     up     ] devops-agent   :8003
  [     up     ] docs-agent     :8005

all 5 nodes serving and routable
indexed 21 chunks into the control plane
```

Re-check any time with:

```bash
make agents-status
```

### 5.2 Show the architecture in the UI

Open **`http://localhost:8080/ui/`** in a browser.

- **Agent Nodes** page → all **5 nodes**, `READY` / `Active`, each with its own reasoners,
  skills and DID. This is the direct proof it's *five distinct agents*, not one LLM behind a
  long prompt.
- Click a node (e.g. `data-agent`) to show its port, reasoner (`answer_data_question`) and skill
  (`fetch_job_runs`).

### 5.3 Run a query through the control plane

Every query goes through `coordinator.ask`, so the control plane records the whole flow — routing
→ specialist dispatch → synthesis — as a traceable execution.

```bash
curl -s -X POST http://localhost:8080/api/v1/execute/coordinator.ask \
  -H "Content-Type: application/json" \
  -d '{"input":{"query":"Did yesterday'\''s ETL pipeline for the sales data run successfully?"}}' \
  --max-time 900
```

⏱ **~2 min single-domain.** The JSON reply carries `answer`, `citations`, `domains_used`, and the
`execution_id` / `run_id` you can open in the UI.

**In the UI:** open the execution → **Inputs & Outputs** shows the question, the cited answer, and
`domains_used`. This is the per-query evidence.

### 5.4 The showpiece — a cross-domain DAG

```bash
curl -s -X POST http://localhost:8080/api/v1/execute/coordinator.ask \
  -H "Content-Type: application/json" \
  -d '{"input":{"query":"Give me a full status update - pipeline, deployments, and any open incidents"}}' \
  --max-time 1200
```

⏱ **~10–12 min** — this fans out to **all four specialists**. When it returns, open the run in the
UI and switch to the **Graph** tab: the `Ask` node on `coordinator` branching to
`Answer Data Question`, `Answer Crm Question`, `Answer Docs Question`, `Answer Devops Question`,
all green, with per-hop timings. **This single view is the clearest picture of the whole design.**

> ⏱ **Plan for latency.** Cross-domain queries are 5–7 sequential LLM calls (the coordinator
> can't synthesise until the specialists answer). Pre-run the slow ones *before* the audience is
> watching and show the saved trace in the UI, or run one live and talk through the architecture
> while it works.

---

## 6. Show the QA numbers (no re-run needed)

The graded QA run is already stored in `data/qa_report.json`. Render it instantly:

```bash
make qa-summary
```

```
  Routing accuracy        : 100.0%  ✅ PASS   (target 100%)
  Answers with citations  : 10/10
  HALLUCINATION RATE      : 3.64%  ✅ PASS   (target <10%)
    = (2 ungrounded / 55 claims) x 100
```

Three headline numbers, all measured:
- **Routing accuracy 100%** (12/12, verified through the live control plane — see
  `docs/qa/traces.md`)
- **Hallucination rate 3.64%** (target <10%)
- **Test coverage 93.11%** (`make cov`)

> To re-grade from scratch (~1 hour, ~60 local LLM calls): `make qa`. You do **not** need this for
> a demo — `make qa-summary` reads the numbers already produced. Re-running would produce slightly
> different numbers on a non-deterministic model.

---

## 7. The 12 demo queries

Q1–Q8 are single-domain; Q9–Q12 are cross-domain (the impressive ones for the DAG).

| # | Query | Routes to |
|---|---|---|
| 1 | Did yesterday's ETL pipeline for the sales data run successfully? | data-platform |
| 2 | What was the error in the last failed Databricks job? | data-platform |
| 3 | Did the latest deployment of the payments service pass all quality gates? | devops |
| 4 | What was the last deployment date for the auth service? | devops |
| 5 | What is the current deal status for Acme Corp? | crm |
| 6 | Who is the account owner for TechStart Ltd? | crm |
| 7 | What is the runbook for when the ingestion pipeline throws a schema mismatch error? | docs |
| 8 | What does the architecture doc say about the ingestion pipeline? | docs |
| 9 | Did last night's pipeline failure affect any CRM customer sync? | data-platform + crm |
| 10 | The ingestion job failed - is there a fix in the runbooks? | data-platform + docs |
| 11 | What's the status of the latest deployment and are there any known issues? | devops + docs |
| 12 | Give me a full status update - pipeline, deployments, and any open incidents | all four |

---

## 8. Troubleshooting (every gotcha we hit, with the fix)

| Symptom | Cause | Fix |
|---|---|---|
| `make agents` shows a node `DOWN` | Node failed to bind / crashed on startup | Check `data/agents/<node>.log`; re-run `make agents` |
| A node shows `UNREGISTERED` | It's serving but the control plane evicted it (heartbeat lapsed during a long inference) | Re-run `make agents`; confirm `make up` is running |
| Docs answers *"The indexed internal documentation does not cover this question"* | The control-plane vector store is empty (it's wiped when the container is recreated) | `make index-cp` (or just `make agents`, which now does it) |
| Answer came from `gemma3:1b` / routing looks wrong | `gemma3:4b` couldn't load — degraded to 1b | Free ~4 GiB RAM (`free -h`), stop other model workloads, retry. **Never demo a fallback run.** |
| `curl … coordinator.ask` returns `execution timeout` | A slow query exceeded the control-plane limit | Already raised to 20 min in `deploy/agentfield.yaml`; if you changed it, restart with `make down && make up` |
| `422 Missing required field: query` | Calling a reasoner with the wrong payload shape | Use `{"input":{"query":"…"}}` for the REST API exactly as shown in §5.3 |
| `ollama serve` → `address already in use` | Ollama is already running as a service | Don't start it manually; `curl localhost:11434/api/version` to confirm it's up |
| Everything is slow | Local 4B model on CPU, no GPU | Expected. Single-domain ~2–4 min, cross-domain ~8–15 min. This is a deployment property, not a bug — see `Implementation.md`. |

**Recover to a clean slate:**

```bash
make agents-down     # stop the 5 nodes
make down            # stop + remove the control plane
make up && make agents   # fresh start (re-indexes the control-plane store automatically)
```

---

## 9. Shutdown

```bash
make agents-down     # stop the 5 agent nodes
make down            # stop the control plane
```

Ollama is a system service — leave it running. Nothing else needs stopping.

---

## 10. Quick reference card

```text
SETUP (once)     make install ; cp deploy/.env.example .env ; make index
VERIFY OFFLINE   make cov                      # 415 passed, 93.11%
QUICK DEMO       make ask Q="…"                # in-process, ~2 min
FULL STACK       make up && make agents        # control plane + 5 nodes
  fleet health   make agents-status            # all 5 serving AND routable
  the UI         http://localhost:8080/ui/
  run a query    curl … /api/v1/execute/coordinator.ask  (see §5.3)
QA EVIDENCE      make qa-summary               # routing 100%, hallucination 3.64%
SHUTDOWN         make agents-down && make down
```

**Headline results:** routing **100%** · hallucination **3.64%** (target <10%) · coverage
**93.11%** · **5** distinct agents · **12/12** queries grounded and cited · cost **₹0** (fully
local). See `docs/qa/traces.md` for the per-query control-plane execution IDs.
