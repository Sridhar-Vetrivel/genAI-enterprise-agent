# IMPACT pSiddhi 3.0

## REQUEST FOR PROPOSAL (RFP)

**Topic:** S4-I-24 — GenAI-Powered Enterprise Copilot  
**Program:** Semester 4 · Integration Mastery · pSiddhi-2026-01  
**Budget:** ₹2,500 (Fixed Ceiling) · QA Mandatory · AI Core

---

## RFP Issued By L&D (The Customer)

**Impact pSiddhi — pSiddhi-2026-01 · Semester 4 · Capstone**

| RFP Field            | Content                                                  |
|----------------------|----------------------------------------------------------|
| Program              | Impact pSiddhi — pSiddhi-2026-01                         |
| RFP Issued By        | L&D Team (acting as Customer)                            |
| Topic ID             | S4-I-24                                                  |
| Topic Title          | GenAI-Powered Enterprise Copilot                         |
| Semester & Category  | Semester 4 — Integration Mastery (Capstone)              |
| Budget Ceiling       | ₹2,500 per participant for the semester (FIXED — non-negotiable) |
| Timeline             | Weeks 4–17 (Development Phase 1 + Phase 2)               |
| Proposal Due Date    | End of Week 2                                            |

---

## Problem Statement

Psiog's engineering, data, and operations teams interact daily with a complex and growing technology estate — CRM systems, data platforms, DevOps pipelines, data workspaces, Azure infrastructure, internal documentation repositories, and analytics environments. Navigating this estate requires deep context that takes months to acquire, tribal knowledge that concentrates in senior engineers, and the ability to context-switch rapidly across platforms that do not share a common interface or query language.

An engineer who needs to know whether yesterday's pipeline run succeeded, find the relevant runbook for a failing service, understand what the latest cost report is showing, check whether a deployment passed its quality gates, or query a CRM record — must visit four or five separate systems, each requiring different credentials, different navigation patterns, and different mental models. This fragmentation is not just inefficient — it is a bottleneck on organizational velocity. New team members are productive in months rather than weeks because there is no intelligent interface that gives them access to the full technology estate through natural language. Senior engineers spend time answering questions that an AI-powered copilot could answer in seconds. Cross-functional decisions are delayed because synthesizing information from multiple systems requires manual effort that busy people defer. Psiog Digital requires a multi-agent enterprise copilot that orchestrates across CRM, data platforms, DevOps pipelines, and internal documentation — enabling any team member to interact with the full technology stack through natural language, with responses grounded in live system data and cited internal documentation.

### The Core Challenges

**Fragmented Technology Estate Requiring Multi-System Context**  
Accessing a complete answer to even a simple operational question — did this pipeline succeed, what does the relevant runbook say, what is the current cost trend — requires visiting multiple systems with different interfaces, different credentials, and different mental models. There is no unified natural-language interface that can assemble answers from across the estate.

**Tribal Knowledge Concentrated in Senior Engineers**  
Platform context, system-specific troubleshooting knowledge, and cross-system correlation skills concentrate in senior engineers who become query bottlenecks. When those engineers are unavailable, the team's operational capability degrades — and new team members face months of onboarding before they can independently navigate the estate.

**No Multi-Agent Orchestration Across System Domains**  
Different system domains — data platform, DevOps, CRM, documentation — require different specialized contexts to query effectively. There is no multi-agent architecture where specialist agents handle domain-specific queries and a coordinator routes incoming questions to the appropriate specialist.

**Ungrounded AI Responses in a Technical Context**  
Any AI assistant in a technical environment must ground its responses in live system data and cited documentation — not generate plausible-sounding but unverified answers from training data. Without a retrieval-augmented, citation-grounded multi-agent architecture, copilot responses risk guiding engineers to act on incorrect information.

---

## What L&D Requires

A multi-agent enterprise copilot with a natural-language interface that orchestrates across at least 4 system domains — data platform, DevOps, CRM, and documentation — using distinct specialist agents coordinated by a routing layer, with all responses grounded in live system data and cited internal documentation, and response quality measured including hallucination rate.

The solution must:

- Handle queries across at least 4 system domains: data platform, DevOps, CRM, and internal documentation.
- Implement a multi-agent architecture with distinct specialist agents per domain and a coordinator agent routing incoming queries to the appropriate specialist.
- Index internal documentation into a semantic search layer for context-aware, citation-grounded responses.
- Demonstrate correct multi-agent routing across at least 10 test queries spanning all domains, with response quality and hallucination rate measured and documented.
- Embed GenAI and multi-agent orchestration as the genuine core — semantic query understanding, agent routing, cross-system synthesis, and citation-grounded answer delivery are all AI-powered, not keyword-routed.
- Deploy on Azure infrastructure with all agent components connected end-to-end.
- Operate entirely within the ₹2,500 budget ceiling by maximizing free tiers and open-source tooling throughout.
- Include a comprehensive QA strategy covering agent routing accuracy, response grounding, hallucination rate, and cross-system query correctness.

---

## Requirements

- Solution must deliver a multi-agent enterprise copilot end-to-end — natural-language interface, multi-agent orchestration across CRM, data platform, DevOps, and documentation systems, semantic search for grounded retrieval, cross-system integration, serverless agent execution, and measured response quality.
- GenAI and multi-agent orchestration must be the core architecture — distinct specialist agents, a coordinator routing queries to the appropriate specialist, and responses citing source systems and documentation.
- A working POC/demo must be delivered by Week 17.
- All tools and costs must be justified and stay within ₹2,500.
- QA is mandatory — proposal must include a comprehensive QA strategy covering agent routing accuracy, response grounding, hallucination rate, and cross-system query correctness.
- Documentation and evidence must be submitted on Moodle at each checkpoint.

---

## Minimum Coverage Requirements

| Dimension                         | Minimum Target                                              |
|-----------------------------------|-------------------------------------------------------------|
| System domains handled            | At least 4 (data platform, DevOps, CRM, documentation)      |
| Specialist agents                 | One per domain, coordinated by a routing agent              |
| Test queries with measured quality| At least 10 spanning all domains                            |
| Citation grounding                | All responses cite source systems or documents              |
| Hallucination rate                | Documented and measured across all test queries             |
| QA test coverage                  | ≥80% across agent routing, retrieval, integration, and response generation |

---

## Suggested Tools

The following tools are recommended starting points. Participants may propose alternatives if justified within the budget ceiling.

### Platform Tools

| Tool                    | Purpose & Notes                                                                                                                                                  |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Azure AI Search Free Tier | Semantic search index for internal documentation, runbooks, architecture docs, and historical incident records enabling grounded copilot responses — free tier available. |
| Databricks Free Edition | Data platform query target for pipeline status, job run history, and analytics data retrieval by the data platform agent — zero cost within free tier limits.    |
| Apache Camel (OSS)      | Integration framework for connecting CRM, DevOps, and operational data sources to the multi-agent orchestration layer — open-source, zero cost.                  |
| Azure Functions Free Tier | Serverless execution environment for individual agent invocation, query routing, and response assembly — operates within free tier limits.                      |
| Power BI Desktop        | Analytics query target for business metrics and report data retrieval by the analytics agent.                                                                    |
| GitHub Copilot Free     | Accelerates multi-agent orchestration code, Azure Functions agent implementations, and integration connector development.                                         |

### AI Tools

| Tool                                       | Purpose & Notes                                                                                                                                                        |
|--------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Google AI Studio — Gemini 2.5 Flash (Free Tier) | Core GenAI engine for natural-language query understanding, agent response generation, cross-system synthesis, and citation-grounded answer delivery — primary AI inference layer. |
| Ollama + Llama 4 Scout (8B)                | Local LLM for offline agent development, routing logic testing, and cost-free inference during development.                                                            |
| LangChain v1.2.17                          | Open-source agent orchestration framework for multi-agent coordination, tool routing, and context management across system domains — zero cost.                         |
| Microsoft Agent Framework 1.0              | Enterprise agent coordination framework for defining specialist agents, handoff protocols, and multi-step reasoning chains across the technology estate — zero cost.    |

---

## Budget Guidance (₹2,500 Fixed Ceiling)

> ⚠️ The budget ceiling of ₹2,500 per participant per semester is FIXED. Proposals exceeding this ceiling will be automatically rejected. Design your solution to maximize free tiers and open-source tools. All platform and AI tools listed above are available at ₹0 within their free tier limits. Any paid usage must be explicitly justified with estimated costs.

---

## QA Mandate

> 🔴 QA is mandatory in every semester. Your proposal MUST include a QA Strategy section. Proposals without a QA strategy will be rejected as incomplete.

### Your QA Strategy must cover:

1. **Test approach:** How will you verify that the coordinator agent correctly routes queries to the appropriate specialist for all 4 system domains, that specialist agent responses are grounded in live system data and cited documentation, that the semantic search index retrieves relevant content, and that hallucination rate is measured and documented across all 10+ test queries?

2. **Test types:** Unit tests, integration tests, E2E tests — which apply to your agent routing logic, specialist agent implementations, semantic search retrieval, cross-system integration connectors, and response generation chain?

3. **AI-assisted QA:** How will you use AI to validate routing accuracy, improve grounding quality, identify hallucinated responses, or test the full pipeline from natural-language query through specialist agent invocation to final citation-grounded response output?

4. **Test coverage target:** What percentage of your agent routing logic, specialist agent implementations, semantic search integration, cross-system connectors, and response generation will be covered by automated tests?

5. **Data validation:** How will you ensure the semantic search index is complete and correctly indexed for all documentation domains — and that agent response outputs are grounded in retrieved system data, with hallucination rate measured, documented, and below an acceptable threshold across all test queries?

---

## Evaluation Criteria

| Criterion               | What We Look For                                                                                                                                                         | Weight |
|-------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|
| Problem Understanding   | Genuine grasp of fragmented multi-system context requirements, tribal knowledge concentration, absent multi-agent orchestration, and the hallucination risk of ungrounded AI responses in a technical environment — not just paraphrasing the RFP | 15%    |
| Solution Quality        | Sound multi-agent architecture with practical specialist agent design, clear routing flow from natural-language query through coordinator to specialist agent to citation-grounded response | 20%    |
| AI Integration Depth    | Multi-agent orchestration, semantic retrieval, and citation-grounded GenAI response generation are genuinely core — not a single LLM with system prompts relabeled as multi-agent | 20%    |
| QA Strategy             | Comprehensive testing approach covering agent routing accuracy, specialist agent response quality, semantic retrieval relevance, citation correctness, and hallucination rate measurement | 15%    |
| Budget & Cost Justification | Within ₹2,500 ceiling, free tiers maximized, every cost explicitly justified with estimates                                                                          | 15%    |
| Timeline Feasibility    | Realistic week-by-week plan with meaningful milestones tied to agent architecture design, specialist agent build, semantic index population, integration connector delivery, and quality measurement | 15%    |

---

## Deliverables Expected

| Checkpoint | Expected Deliverables |
|------------|-----------------------|
| Week 10    | • Multi-agent architecture operational with at least 2 specialist agents<br>• Semantic search index populated with internal documentation<br>• Natural-language query routing working across at least 2 system domains<br>• Initial grounded responses with citations demonstrated<br>• Unit tests passing<br>• Mid-term documentation submitted on Moodle |
| Week 17    | • Complete enterprise copilot: 4+ system domains, multi-agent orchestration via LangChain and Microsoft Agent Framework, grounded responses across 10+ test queries<br>• Hallucination rate documented and measured<br>• Agent routing accuracy validated<br>• Azure Functions deployment<br>• QA test suite with ≥80% coverage<br>• Live demo with all evidence submitted on Moodle |
