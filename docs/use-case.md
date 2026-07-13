# Use Case: GenAI-Powered Enterprise Copilot

## Who Is the Customer?

**L&D Team at Psiog** — acting as the internal customer representing the needs of Psiog's engineering, data, and operations teams.

---

## The End Goal

Build a single natural-language interface — a **chat copilot** — that any Psiog employee can open and ask operational questions in plain English. The copilot must:

1. Understand the intent of the question
2. Route it to the right internal system(s)
3. Pull live data from those systems
4. Return a grounded, cited answer — not a hallucinated one

**The success condition:** A new joiner on Day 1 can ask the copilot the same question a senior engineer would know by memory, and get a correct, cited answer — without needing to know which system to look in, what credentials to use, or how to navigate any of those platforms.

---

## Why This Matters (The Pain Being Solved)

Psiog's internal technology estate spans multiple disconnected systems:

| System | What Lives There |
|---|---|
| CRM | Customer records, deal status, contact history |
| Data Platform (Databricks) | Pipeline run history, job status, analytics data |
| DevOps (GitHub / Azure DevOps) | Deployments, build status, quality gate results |
| Internal Docs | Runbooks, architecture docs, incident records, SOPs |

Today, answering even a simple operational question requires opening 4-5 separate tools, using different credentials, and mentally stitching the results together. This creates three compounding problems:

- **Onboarding bottleneck** — new team members need months before they can independently navigate the estate
- **Senior engineer drain** — experienced engineers spend time answering questions an AI could handle
- **Decision lag** — cross-functional decisions are delayed because synthesizing multi-system data takes manual effort

---

## The Use Case, Precisely Defined

> **An employee types a question in plain English. The copilot identifies which system(s) hold the answer, dispatches specialist agents to retrieve live data, and responds with a cited, grounded answer — all within a single conversational interface.**

### Concrete Scenarios

**Scenario 1 — Data Platform Query**
> "Did yesterday's ETL pipeline for the sales data run successfully?"

- Coordinator identifies: data platform question
- Routes to: Data Platform Agent
- Agent queries: Databricks job run history
- Returns: run status, timestamp, any error logs — with source citation

**Scenario 2 — DevOps Query**
> "Did the latest deployment of the payments service pass all quality gates?"

- Coordinator identifies: DevOps question
- Routes to: DevOps Agent
- Agent queries: GitHub Actions / Azure DevOps pipeline results
- Returns: gate-by-gate status, commit SHA, deployment timestamp — with source citation

**Scenario 3 — CRM Query**
> "What is the current deal status for Acme Corp?"

- Coordinator identifies: CRM question
- Routes to: CRM Agent
- Agent queries: CRM system for account/deal records
- Returns: deal stage, owner, last activity — with source citation

**Scenario 4 — Documentation / Knowledge Query**
> "What is the runbook for when the ingestion pipeline throws a schema mismatch error?"

- Coordinator identifies: documentation question
- Routes to: Docs Agent
- Agent runs: semantic similarity search over indexed internal docs
- Returns: relevant runbook section, exact document name and section cited

**Scenario 5 — Cross-Domain Query**
> "The sales pipeline failed last night — is there a runbook for this, and did it affect yesterday's CRM sync?"

- Coordinator identifies: multi-domain question (data platform + docs + CRM)
- Routes to: Data Platform Agent + Docs Agent + CRM Agent in parallel
- Synthesizes: pipeline failure details + relevant runbook + CRM sync status
- Returns: unified, cross-cited answer

---

## System Architecture (Conceptual)

```
User (any employee)
        │
        │  "Did yesterday's pipeline run succeed?"
        ▼
┌─────────────────────────────────────┐
│         Coordinator Agent           │
│  - Understands query intent (LLM)   │
│  - Routes to appropriate specialist │
│  - Synthesizes multi-agent results  │
└─────────────────────────────────────┘
        │
   ┌────┴─────────────────────────────────────┐
   ▼           ▼              ▼               ▼
Data Agent  DevOps Agent   CRM Agent     Docs Agent
   │              │              │              │
Databricks   GitHub/Azure    CRM System    Vector
Job Runs      DevOps Runs     Records     Memory RAG
   │              │              │         (indexed
   └──────────────┴──────────────┴──────  internal docs)
                       │
              Grounded Response
         (live data + source citations)
                       │
                       ▼
              Employee sees answer
         "Yes, the pipeline ran at 02:14 AM
          and completed successfully.
          Source: Databricks Job #4821"
```

---

## What "Success" Looks Like (Measurable Outcomes)

| Outcome | Measurement |
|---|---|
| Correct routing | Coordinator sends each of the 10+ test queries to the right specialist agent — verified manually |
| Grounded responses | Every response cites the source system or document it pulled from |
| Hallucination rate | Measured across all 10+ test queries by comparing response claims to raw source data |
| Cross-domain coverage | At least one test query successfully spans 2+ system domains |
| New joiner utility | A non-technical person can get a correct answer without knowing which system to look in |

---

## What This Is NOT

- **Not a chatbot** that answers from training data — every response must be grounded in live system data or indexed internal docs
- **Not a single-LLM wrapper** — the architecture must have distinct specialist agents, not one agent with a long system prompt
- **Not a read-only demo** — the copilot must connect to real (or realistic mock) data sources and return real data
- **Not a keyword router** — routing decisions must use LLM-based intent understanding, not if/else on keywords

---

## Scope for This Capstone (Weeks 4–17)

| Phase | Scope |
|---|---|
| Week 4–9 | Architecture design, agent scaffolding, 2 specialist agents working, semantic search index populated |
| Week 10 (Checkpoint) | 2+ agents live, routing working, grounded responses with citations demonstrated |
| Week 10–16 | All 4 agents connected, cross-domain queries working, QA suite built |
| Week 17 (Final Demo) | Full copilot: 4 domains, 10+ validated test queries, hallucination rate documented, deployed on Azure |

---

## Technology Mapping (AgentField Approach)

| Requirement | Implementation |
|---|---|
| Coordinator + specialist agents | AgentField multi-agent orchestration (`app.call`, `@app.reasoner`) |
| Semantic search over internal docs | AgentField vector memory (`set_vector`, `similarity_search`) |
| LLM inference | Gemini 2.5 Flash or Llama 4 via OpenRouter (free tier) |
| Data platform queries | Databricks REST API wrapped in `@app.skill()` |
| DevOps queries | GitHub / Azure DevOps API wrapped in `@app.skill()` |
| CRM queries | CRM REST API wrapped in `@app.skill()` |
| Deployment | AgentField control plane via Docker Compose on Azure VM (free tier) |
| Session context | AgentField session-scoped memory (`app.memory.set("session", ...)`) |
