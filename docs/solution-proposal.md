# Solution Proposal
## RFP S4-I-24 — GenAI-Powered Enterprise Copilot
**Submitted by:** Sridhar Vetrivel 
**Program:** Impact pSiddhi — pSiddhi-2026-01 · Semester 4 · Capstone  
**Submitted to:** L&D Team (acting as Customer)  
**Proposal Date:** End of Week 2  
**Budget Ceiling:** ₹2,500 (Fixed)

---

## Table of Contents

1. [Problem Understanding](#1-problem-understanding)
2. [Proposed Solution](#2-proposed-solution)
3. [Architecture Design](#3-architecture-design)
4. [AI Integration Depth](#4-ai-integration-depth)
5. [QA Strategy](#5-qa-strategy)
6. [Budget & Cost Justification](#6-budget--cost-justification)
7. [Production Considerations: Data Privacy](#7-production-considerations-data-privacy)
8. [Timeline](#8-timeline)
9. [Deliverables](#9-deliverables)

---

## 1. Problem Understanding

### The Core Problem

Psiog's engineering, data, and operations teams work across a fragmented technology estate — Databricks for data pipelines, GitHub/Azure DevOps for deployments, a CRM system for customer data, and scattered internal documentation across runbooks and architecture docs. These systems are disconnected. They each require separate logins, separate navigation, and separate mental models.

This creates a bottleneck that affects everyone:

- **New joiners** cannot independently answer basic operational questions for months because the knowledge of which system to look in, and how to query it, is tribal — it lives in senior engineers' heads.
- **Senior engineers** become human routers, constantly interrupted to answer questions that are fundamentally lookups across these systems.
- **Operational decisions** are slowed because synthesizing a complete picture — did the pipeline succeed, is the runbook up to date, did it affect any customer — requires manually visiting multiple tools and stitching results together.

The problem is not a lack of data. Psiog has the data. The problem is that there is no unified, intelligent interface that can access all of it in response to a plain-English question.

### Why Existing Approaches Fall Short

| Approach | Why It Fails |
|---|---|
| Asking a senior engineer | Doesn't scale; blocks the expert; knowledge is lost when they leave |
| Separate dashboards per system | Still requires the user to know which dashboard, how to query it, and how to correlate results manually |
| A single-LLM chatbot | Answers from training data, not live system data — produces confident but unverifiable responses |
| Basic keyword-based search | Cannot understand intent, cannot cross-reference systems, cannot synthesize a unified answer |

### What Is Actually Needed

A multi-agent AI copilot that:
1. Understands the **intent** behind any natural-language question
2. Knows **which system** holds the relevant data
3. **Retrieves live data** from that system (not from an LLM's training memory)
4. Returns a **cited, grounded answer** — every claim traceable to a source

---

## 2. Proposed Solution

### Overview

We propose building **PsiogCopilot** — a multi-agent enterprise copilot with a natural-language interface that orchestrates across four system domains:

- **Data Platform** (Databricks) — pipeline runs, job history, analytics data
- **DevOps** (GitHub / Azure DevOps) — deployments, build status, quality gates
- **CRM** — customer records, deal status, contact history
- **Internal Documentation** — runbooks, architecture docs, incident records

The system uses a **Coordinator Agent** that receives every user query, determines intent, and routes it to one or more **Specialist Agents**. Each Specialist Agent is responsible for exactly one domain — it queries the live system, retrieves relevant data, and returns a cited response. The Coordinator synthesizes multi-agent results into a single, grounded reply.

### Why AgentField Instead of the Suggested Stack

The RFP suggests LangChain + Microsoft Agent Framework for orchestration, Azure AI Search for semantic search, and Azure Functions for serverless execution. We propose replacing this with **AgentField** — an open-source (Apache 2.0) AI backend framework — for the following reasons:

| Suggested Tool | AgentField Replacement | Reason |
|---|---|---|
| LangChain + MS Agent Framework | AgentField SDK orchestration | Single framework handles routing, tracing, and agent-to-agent calls natively — no glue code between two separate frameworks |
| Azure AI Search | AgentField vector memory fabric | Built-in semantic search (set_vector + similarity_search) — no external service, no cost |
| Azure Functions | AgentField control plane (Docker on Azure VM) | Simpler deployment, free tier VM sufficient for POC scale |

All specialist agents, the coordinator, and the semantic search index run within a single AgentField deployment. Every agent call is automatically traced and visualized as a DAG — providing built-in observability that would otherwise require additional tooling.

LLM inference will use **any llms** (via Openrouter) within the ₹2,500 budget ceiling, and **Llama 4 Scout via Ollama** locally during development at zero cost.

---

## 3. Architecture Design

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                       │
│     (Chat interface — any browser or terminal or UI)    │
└────────────────────────┬────────────────────────────────┘
                         │  Natural language query
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Coordinator Agent                       │
│                                                          │
│  1. Classifies query intent using LLM                    │
│  2. Identifies target domain(s)                          │
│  3. Dispatches to one or more specialist agents          │
│  4. Synthesizes results into a single grounded response  │
└────┬──────────────┬──────────────┬──────────────┬───────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐   ┌──────────┐  ┌──────────┐  ┌──────────────┐
│  DATA   │   │  DEVOPS  │  │   CRM    │  │     DOCS     │
│  AGENT  │   │  AGENT   │  │  AGENT   │  │    AGENT     │
│         │   │          │  │          │  │              │
│Databricks   │ GitHub / │  │  CRM     │  │  AgentField  │
│ REST API│   │ Azure    │  │  REST    │  │  Vector      │
│         │   │ DevOps   │  │  API     │  │  Memory RAG  │
└────┬────┘   └────┬─────┘  └────┬─────┘  └──────┬───────┘
     │              │              │               │
     └──────────────┴──────────────┴───────────────┘
                         │
              Grounded, cited response
                         │
                         ▼
              ┌─────────────────────┐
              │  User sees answer   │
              │  with source cited  │
              └─────────────────────┘
```

### Agent Definitions

#### Coordinator Agent (`coordinator`)
- **Role:** Query classifier and orchestrator
- **Responsibility:** Receives every user query, uses an LLM reasoner to determine which domain(s) are relevant, calls the appropriate specialist agent(s), and synthesizes the combined output into a final response
- **Key logic:** Can dispatch to multiple specialist agents in parallel for cross-domain queries

```python
app = Agent(
    node_id="coordinator",
    agentfield_server=os.getenv("AGENTFIELD_SERVER"),
    ai_config=AIConfig(model=os.getenv("AI_MODEL", "google/gemini-2.5-flash"))
)

@app.reasoner()
async def route_query(query: str) -> CopilotResponse:
    # LLM classifies intent and selects domain(s)
    routing = await app.ai(
        system="You are an enterprise copilot coordinator...",
        user=f"Query: {query}",
        schema=RoutingDecision
    )
    # Dispatch to specialists and synthesize
    ...
```

#### Data Platform Agent (`data-agent`)
- **Role:** Databricks specialist
- **Skills:** Query job run history, fetch pipeline status, retrieve analytics results
- **Data source:** Databricks REST API (Jobs API, SQL Warehouses API)

#### DevOps Agent (`devops-agent`)
- **Role:** Deployment and CI/CD specialist
- **Skills:** Fetch build status, check quality gate results, get deployment history
- **Data source:** GitHub Actions API / Azure DevOps REST API

#### CRM Agent (`crm-agent`)
- **Role:** Customer data specialist
- **Skills:** Look up contact records, deal status, account history
- **Data source:** CRM REST API (HubSpot Free or mock CRM)

#### Docs Agent (`docs-agent`)
- **Role:** Internal knowledge specialist
- **Skills:** Semantic search over indexed runbooks, architecture docs, incident records
- **Data source:** AgentField vector memory (pre-indexed internal documentation)

### State and Memory Design

| Scope | What Is Stored | Example |
|---|---|---|
| `session` | Conversation history for multi-turn queries | Previous questions in a session |
| `global` | Pre-indexed documentation embeddings | Runbook embeddings, doc chunks |
| `run` | Intermediate results within a single query | Partial responses from each specialist |

### Documentation Indexing (RAG Pipeline)

Internal documentation is indexed once at setup time:

```python
# Chunk document → generate embedding → store in AgentField vector memory
await app.memory.set_vector(chunk_id, embedding_vector, metadata={
    "source": "runbook-12.md",
    "section": "Schema Mismatch Recovery",
    "url": "internal-docs/runbooks/runbook-12.md"
})

# At query time — semantic search
results = await app.memory.similarity_search(query_embedding, top_k=5)
# Each result contains: key, score, text — used as citation in response
```

---

## 4. AI Integration Depth

AI is not a wrapper over this system — it is the core of every decision and every response.

### Where AI Is Used

| Component | AI Role | Not Keyword-Based |
|---|---|---|
| Query routing | LLM classifies intent and selects domain(s) | Same query phrased differently routes correctly |
| Data Platform Agent | LLM interprets raw API JSON into a readable response | Does not just dump JSON |
| DevOps Agent | LLM summarizes build logs and explains failures | Understands failure reason, not just status code |
| CRM Agent | LLM formats CRM records into a contextual answer | Knows what's relevant to the question |
| Docs Agent | Embedding model converts query to vector for similarity search; LLM generates cited answer from retrieved chunks | Pure semantic match, not keyword match |
| Response synthesis | Coordinator LLM synthesizes multi-agent outputs into one coherent response | Handles cross-domain answers naturally |

### LLM Configuration

```python
# Primary: Gemini 2.5 Flash via OpenRouter (free tier)
ai_config = AIConfig(model="google/gemini-2.5-flash")

# Development/fallback: Llama 4 Scout via Ollama (local, zero cost)
ai_config = AIConfig(model="ollama/llama4-scout")
```

OpenRouter is used as the unified inference gateway — model can be swapped with a single environment variable change, no code changes required.

### Structured Output (Pydantic Schemas)

All LLM responses are typed and validated — not free-form text:

```python
from pydantic import BaseModel, ConfigDict
from typing import List

class RoutingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domains: List[str]          # ["data-platform", "docs"]
    reasoning: str              # why these domains were selected
    is_cross_domain: bool

class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    citations: List[str]        # source system or document name
    confidence: str             # "high" | "medium" | "low"
```

This ensures every response is machine-verifiable — critical for QA and hallucination measurement.

---

## 5. QA Strategy

> QA is not an afterthought — it is built into the architecture from Week 1.

### Test Approach

We will verify the system across four layers:

| Layer | What We Test | How |
|---|---|---|
| Unit | Each `@app.skill()` function in isolation | pytest with mocked API responses |
| Integration | Each specialist agent end-to-end (query in → cited response out) | pytest hitting live AgentField control plane |
| Routing | Coordinator correctly routes each of the 10+ test queries | Automated suite comparing actual vs expected domain routing |
| E2E | Full query lifecycle from user input to final cited response | curl / test harness against deployed system |

### 10+ Mandatory Test Queries

| # | Query | Expected Domain(s) | Verified |
|---|---|---|---|
| 1 | "Did yesterday's ETL pipeline run successfully?" | Data Platform | — |
| 2 | "What was the error in the last failed Databricks job?" | Data Platform | — |
| 3 | "Did the payments service deployment pass all quality gates?" | DevOps | — |
| 4 | "What was the last deployment date for the auth service?" | DevOps | — |
| 5 | "What is the deal status for Acme Corp?" | CRM | — |
| 6 | "Who is the account owner for TechStart Ltd?" | CRM | — |
| 7 | "What is the runbook for a schema mismatch error?" | Docs | — |
| 8 | "What does the architecture doc say about the ingestion pipeline?" | Docs | — |
| 9 | "Did last night's pipeline failure affect any CRM customer sync?" | Data Platform + CRM | — |
| 10 | "The ingestion job failed — is there a fix in the runbooks?" | Data Platform + Docs | — |
| 11 | "What's the status of the latest deployment and are there known issues?" | DevOps + Docs | — |
| 12 | "Give me a full status update — pipeline, deployments, and any open incidents" | All 4 domains | — |

### Hallucination Rate Measurement

Every specialist agent returns a `citations` list (source system or document). A **Judge Agent** (a separate LLM reasoner) will:

1. Take the agent's `answer` and its `citations`
2. Fetch the raw source content that was cited
3. Verify each claim in the answer against the source
4. Flag any claim that cannot be grounded in the cited source as a hallucination

```
Hallucination Rate = (Ungrounded claims / Total claims) × 100
```

This will be measured across all 12 test queries and documented in the final submission.

### Agent Routing Accuracy

```
Routing Accuracy = (Correctly routed queries / Total test queries) × 100
Target: 100% on the 12 defined test queries
```

Each test query has a predefined expected domain. The test suite asserts that the coordinator's `RoutingDecision.domains` matches the expected domain(s).

### Test Coverage Target

| Component | Target Coverage | Test Type |
|---|---|---|
| Coordinator routing logic | 100% of 12 test queries | Routing accuracy suite |
| Each specialist agent (4 agents) | ≥80% code coverage | Unit + integration tests |
| Vector memory indexing and retrieval | ≥80% | Unit tests with test doc corpus |
| Cross-system synthesis | All cross-domain queries pass | E2E tests |
| **Overall** | **≥80%** | Combined |

### AI-Assisted QA

We will use a dedicated QA Reasoner (LLM-powered) to:
- **Evaluate routing decisions:** Given the query and the routing choice, is the routing correct? (LLM as judge)
- **Detect hallucinations:** Does the answer contain claims not supported by citations? (LLM as grounding verifier)
- **Assess response quality:** Is the answer complete, accurate, and clearly cited? (LLM scoring on 1–5 scale)

This produces a measurable QA report for every test run.

### Data Validation

Before the Week 10 checkpoint, we will verify:
- All runbooks and architecture docs are chunked and indexed in the vector memory
- Each indexed chunk has valid metadata (source file, section, last updated)
- Similarity search returns relevant results for at least 5 representative documentation queries
- No orphan chunks (chunks with missing or invalid metadata)

---

## 6. Budget & Cost Justification

> Total estimated spend: ₹2,500 — all components operate within free tiers except LLM inference, which utilizes the full ₹2,500 budget ceiling.

| Component | Tool | Cost | Justification |
|---|---|---|---|
| Agent orchestration | AgentField (Apache 2.0, self-hosted) | ₹0 | Open-source, no licensing fee |
| Vector memory / semantic search | AgentField built-in | ₹0 | Included in AgentField — no external service |
| LLM inference (primary) | any LLM models via OpenRouter | ₹2,500 | Budget ceiling allocated to LLM inference — the only paid component in the stack |
| LLM inference (development) | Llama 4 Scout via Ollama (local) | ₹0 | Runs locally on development machine, zero API cost |
| Data platform | Databricks Free Edition | ₹0 | Free tier covers development and demo workloads |
| DevOps data | GitHub API (Free) | ₹0 | Public API, free tier |
| CRM data | HubSpot Free CRM or mock data | ₹0 | HubSpot free tier or realistic mock for POC |
| Azure hosting | Azure B1s VM (free tier) | ₹0 | Azure 12-month free tier: 750 hrs/month B1s VM — runs Docker Compose |
| Development tooling | GitHub Copilot Free | ₹0 | Free tier for development acceleration |
| **Total** | | **₹2,500** | **₹2,500 ceiling fully utilized — LLM inference is the sole cost item** |

### Budget Risk Management

The ₹2,500 ceiling is treated as a hard limit. Every tool chosen is either:
- **Open-source and self-hosted** (AgentField, Ollama) — zero cost by design
- **Free-tier cloud service** (Gemini API, Databricks, Azure VM, GitHub) — usage stays within documented free limits

If any free tier limit is approached during development, Ollama + Llama 4 Scout provides a complete local fallback at ₹0.

---

## 7. Production Considerations: Data Privacy

> This section addresses a critical concern for any real enterprise deployment: the risk of sensitive internal data being exposed to external LLM providers.

### The Risk

Every call to an external LLM (Gemini via OpenRouter, Google AI Studio, etc.) sends the **full prompt** — including live data retrieved from Databricks, CRM records, pipeline logs, and runbook content — over the internet to a third-party server. In a real enterprise context this means:

- Customer names, deal values, and CRM records reach Google or OpenRouter servers
- Pipeline configurations and error logs leave the corporate network
- Data may be logged, retained, or subject to the laws of another jurisdiction
- A provider-side breach exposes internal operational data

No enterprise security policy accepts this for production systems containing sensitive business data.

### Three Mitigation Approaches

#### Option A: Fully Local LLM (Ollama — Zero Data Leaves the Network)

Run the LLM entirely inside the organisation's own infrastructure. No external API call is ever made.

```
┌──────────────────────────────────────────────────────┐
│             Your Server / Azure VM                    │
│                                                       │
│   AgentField Agents                                   │
│         │  prompt + live data                         │
│         ▼                                             │
│   ┌─────────────┐                                     │
│   │   Ollama    │  ← LLM runs here, on your machine   │
│   │ Llama 4     │    Data never leaves this host       │
│   │ Scout 8B    │                                     │
│   └─────────────┘                                     │
│         │  response                                   │
│         ▼                                             │
│   Agent synthesizes cited answer                      │
└──────────────────────────────────────────────────────┘
```

**Pros:** Zero data leakage, completely free, works air-gapped  
**Cons:** Requires a GPU for acceptable speed; Llama 4 Scout 8B is weaker than Gemini 2.5 Flash on complex multi-step reasoning

---

#### Option B: Azure OpenAI Service with Enterprise DPA

Microsoft's Azure OpenAI Service provides a contractual data privacy guarantee for enterprise customers:

- Prompts are **not logged** (configurable) and **not used for model training**
- Data stays within your **Azure region** (India, EU, etc.)
- Can be deployed behind a **Private Endpoint** — traffic never touches the public internet
- Covered by Microsoft's enterprise Data Processing Agreement (DPA)

```
┌──────────────────────────────────────────────────────────┐
│                 Your Azure Subscription                   │
│                                                           │
│   AgentField Agents (Azure VM)                            │
│         │  HTTPS (stays inside Azure backbone)            │
│         ▼                                                 │
│   ┌──────────────────────────────────────────────────┐   │
│   │       Azure OpenAI Service (Private Endpoint)    │   │
│   │   GPT-4o / GPT-4o-mini                           │   │
│   │   • No training on your data (contractual)       │   │
│   │   • Data stays in your Azure region              │   │
│   │   • Private Link — no public internet exposure   │   │
│   └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

**Pros:** Production-grade privacy guarantees, stronger model quality than local  
**Cons:** Costs money (GPT-4o-mini ~₹2–4 per 1,000 tokens) — must be budgeted carefully

---

#### Option C: Data Minimization Pattern (Recommended for Hybrid Deployments)

The LLM is only ever sent a **sanitized summary** of retrieved data — never raw records. PII and sensitive fields are stripped locally by the specialist agent before the LLM call, then rehydrated after.

```text
Step 1 — Specialist agent pulls raw data from source system (stays local):
  { job_id: 4821, customer: "Acme Corp", revenue: 4500000,
    pipeline: "sales_etl", status: "FAILED", error: "schema_mismatch",
    run_time: "2026-05-11T02:14:00Z" }

Step 2 — Agent strips sensitive fields before LLM call:
  { pipeline: "sales_etl", status: "FAILED",
    error_type: "schema_mismatch", run_time: "02:14 UTC" }
         ↓ only this reaches the external LLM

Step 3 — LLM generates a grounded narrative from the sanitized payload:
  "The sales_etl pipeline failed at 02:14 UTC with a schema_mismatch
   error. Relevant runbook: Schema Mismatch Recovery (runbook-12.md)"

Step 4 — Agent rehydrates response with real identifiers locally:
  "Job #4821 (Acme Corp) failed at 02:14 UTC..."
         ↑ substitution happens in your code, never in the LLM
```

**Pros:** Compatible with any LLM including free-tier external providers; sensitive fields never leave the network  
**Cons:** Requires defining a sanitization schema per domain; adds a preprocessing step to each specialist agent

---

### Decision for This Capstone

| Context | Approach Used |
|---|---|
| Development and testing | Ollama + Llama 4 Scout locally — zero cost, zero leakage |
| Capstone demo | Gemini 2.5 Flash via OpenRouter with **mock/synthetic data only** — no real business data is ever sent externally |
| Production deployment path | Data Minimization pattern + Azure OpenAI Private Endpoint |

All data sources used in the capstone demo are **mock or synthetic**. No real customer records, pipeline configurations, or internal documents containing sensitive information will be sent to any external LLM. This is stated explicitly so that evaluators understand the boundary between the capstone implementation and a production-grade deployment.

### Production Deployment Recommendation

A production version of this copilot should adopt all three layers together:

1. **Data Minimization** — strip PII and sensitive fields in every specialist agent before any LLM call
2. **Azure OpenAI Private Endpoint** — replace OpenRouter with Azure-hosted GPT-4o behind a Private Link
3. **Ollama fallback** — maintain a self-hosted Llama model as the fallback for queries flagged as high-sensitivity by the coordinator

This layered approach gives the enterprise both privacy guarantees and cost control, while keeping the multi-agent architecture unchanged.

---

## 8. Timeline

> Development spans Weeks 4–17. Proposal submitted end of Week 2.

| Week | Milestone | Deliverable |
|---|---|---|
| **2** | Proposal submitted | This document |
| **4** | Environment setup | AgentField control plane running locally via Docker Compose; Azure VM provisioned; OpenRouter API connected |
| **5** | Coordinator Agent built | Coordinator can classify query intent and route to named domains; Pydantic schemas defined |
| **6** | Data Platform Agent | Databricks REST API connected; job run status and history queries working; unit tests passing |
| **7** | Docs Agent + RAG index | Internal docs chunked, embedded, and indexed in AgentField vector memory; similarity search returning relevant results |
| **8** | DevOps Agent | GitHub/Azure DevOps API connected; build status, deployment history, quality gates working |
| **9** | CRM Agent | CRM API (or mock) connected; contact, deal, account queries working |
| **10** | **Week 10 Checkpoint** | 4 agents live; coordinator routing working across all domains; 6 of 12 test queries passing with citations; unit tests at ≥50%; mid-term docs on Moodle |
| **11** | Cross-domain queries | Coordinator handles multi-domain routing; parallel agent dispatch working; session memory preserving conversation context |
| **12** | Full test suite | All 12 test queries implemented; routing accuracy measured; initial hallucination rate documented |
| **13** | Judge Agent (AI QA) | Hallucination detection reasoner built; grounding verification automated; QA report generated per run |
| **14** | Azure deployment | Full system deployed on Azure B1s VM; all agents connected end-to-end in cloud environment |
| **15** | QA hardening | ≥80% test coverage achieved; edge cases handled; response quality validated across all 12 queries |
| **16** | Demo preparation | Demo script prepared; all evidence (routing logs, hallucination rates, test results) compiled |
| **17** | **Week 17 Final Demo** | Complete enterprise copilot live; all 12 test queries passing; hallucination rate documented; ≥80% QA coverage; all evidence on Moodle |

---

## 9. Deliverables

### Week 10 Checkpoint

- [ ] All 4 specialist agents operational and routing correctly
- [ ] AgentField vector memory indexed with internal documentation (runbooks, architecture docs)
- [ ] Natural-language routing working across all 4 system domains
- [ ] At least 6 of 12 test queries returning grounded, cited responses
- [ ] Unit tests passing for all agent skill functions
- [ ] Mid-term documentation submitted on Moodle (architecture diagram, agent code, test results)

### Week 17 Final Submission

- [ ] Complete enterprise copilot deployed on Azure
- [ ] All 12 test queries passing with correct routing, grounded responses, and citations
- [ ] Hallucination rate documented and measured (target: <10%)
- [ ] Routing accuracy: 100% on all 12 defined test queries
- [ ] QA test suite with ≥80% coverage across routing, retrieval, integration, and response generation
- [ ] Judge Agent (AI QA) producing automated grounding verification reports
- [ ] Live demo recorded and submitted
- [ ] All evidence (test logs, routing accuracy metrics, hallucination report, cost breakdown) submitted on Moodle

---

## Summary

| Evaluation Criterion | Our Approach | Weight |
|---|---|---|
| Problem Understanding | Addresses fragmentation, tribal knowledge, and hallucination risk — not just a paraphrase of the RFP | 15% |
| Solution Quality | 5-agent architecture (1 coordinator + 4 specialists), clear routing flow, structured cited responses | 20% |
| AI Integration Depth | LLM for routing, LLM per agent for response generation, embedding model for semantic search, LLM judge for QA — AI at every layer | 20% |
| QA Strategy | 12 test queries, routing accuracy measurement, hallucination rate measurement, Judge Agent, ≥80% coverage | 15% |
| Budget & Cost Justification | ₹0 of ₹2,500 used — all tools on free tiers, full buffer retained | 15% |
| Timeline Feasibility | Week-by-week milestones tied to specific agent builds, with clear checkpoints at Week 10 and Week 17 | 15% |
