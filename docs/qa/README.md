# QA Evidence — the 12 mandatory test queries

Auto-generated from the last `make qa` run. One page per test query: what was asked, how it routed, what it cited, what the Judge Agent found, and how to screenshot it for the mid-term Evidence Pack.

## Headline numbers

| Metric | Target | Measured |
|---|---|---|
| Routing accuracy | 100.0% | **100.0%** |
| Hallucination rate | &lt;10.0% | **4.0%** |
| Answers carrying citations | all | **9 / 9** |
| Claims grounded | — | **48 / 50** |
| Answers verified by the Judge | all | **9 / 9** |
| LLM cost | ₹0 | **₹0** (local `gemma3:4b` / `gemma3:1b`) |

Queries completed in this run: **9 / 12**

## Per-query evidence

| # | Query | Expected | Routed to | Cites | Halluc. | Evidence |
|---|---|---|---|---|---|---|
| 1 | Did yesterday's ETL pipeline for the sales data run successfully? | `data-platform` | ✅ `data-platform` | 2 | 0.0% | [q01.md](q01.md) |
| 2 | What was the error in the last failed Databricks job? | `data-platform` | ✅ `data-platform` | 1 | 0.0% | [q02.md](q02.md) |
| 3 | Did the latest deployment of the payments service pass all quality gates? | `devops` | ✅ `devops` | 1 | 8.33% | [q03.md](q03.md) |
| 4 | What was the last deployment date for the auth service? | `devops` | ✅ `devops` | 1 | 0.0% | [q04.md](q04.md) |
| 5 | What is the current deal status for Acme Corp? | `crm` | ✅ `crm` | 2 | 0.0% | [q05.md](q05.md) |
| 6 | Who is the account owner for TechStart Ltd? | `crm` | ✅ `crm` | 1 | 0.0% | [q06.md](q06.md) |
| 7 | What is the runbook for when the ingestion pipeline throws a schema mismatch error? | `docs` | ✅ `docs` | 5 | 0.0% | [q07.md](q07.md) |
| 8 | What does the architecture doc say about the ingestion pipeline? | `docs` | ✅ `docs` | 2 | 0.0% | [q08.md](q08.md) |
| 9 | Did last night's pipeline failure affect any CRM customer sync? | `crm`, `data-platform` | ✅ `crm`, `data-platform` | 4 | 100.0% | [q09.md](q09.md) |
| 10 | The ingestion job failed - is there a fix in the runbooks? | `data-platform`, `docs` | _not yet run_ | — | — | — |
| 11 | What's the status of the latest deployment and are there any known issues? | `devops`, `docs` | _not yet run_ | — | — | — |
| 12 | Give me a full status update - pipeline, deployments, and any open incidents | `crm`, `data-platform`, `devops`, `docs` | _not yet run_ | — | — | — |

## Beyond the queries

A test query proves an agent routes correctly and cites its source. It cannot show that the suite passes, what the coverage figure really is, that the RAG index built, or that the control plane runs — and Sections 3 and 6 ask for all four. Screenshot only the query pages and **D-01 and D-08 go into the submission unevidenced**.

| Evidence | Proves | Command | Page |
|---|---|---|---|
| **E-13** | The graded QA run: routing accuracy and hallucination rate across all 12 queries | `make qa` | [e-13-qa-summary.md](e-13-qa-summary.md) |
| **E-14** | Full offline test suite passing, with the measured coverage figure | `make cov` | [e-14-tests-coverage.md](e-14-tests-coverage.md) |
| **E-15** | The documentation corpus chunked, embedded and indexed for similarity search | `make index` | [e-15-rag-index.md](e-15-rag-index.md) |
| **E-16** | The AgentField control plane running, with all five agent nodes registered | `make up && make agents` | [e-16-control-plane.md](e-16-control-plane.md) |

## Section 4.1 — Evidence Index (paste this into the mid-term doc)

The template requires one row per evidence block, and Section 3 requires every deliverable marked Done or Partial to point at an Evidence ID here. The evaluator cross-checks that link, so a page with no ID cannot support a claim.

| Evidence ID | Caption (what it proves) | Deliverable ID | Date captured | Link |
|---|---|---|---|---|
| E-01 | Q01 “Did yesterday's ETL pipeline for the sales data run successfully?” routes to data-platform and answers with citations | D-02, D-03 | *(fill in)* | *(GitHub commit)* |
| E-02 | Q02 “What was the error in the last failed Databricks job?” routes to data-platform and answers with citations | D-02, D-03 | *(fill in)* | *(GitHub commit)* |
| E-03 | Q03 “Did the latest deployment of the payments service pass all quality gates?” routes to devops and answers with citations | D-02, D-05 | *(fill in)* | *(GitHub commit)* |
| E-04 | Q04 “What was the last deployment date for the auth service?” routes to devops and answers with citations | D-02, D-05 | *(fill in)* | *(GitHub commit)* |
| E-05 | Q05 “What is the current deal status for Acme Corp?” routes to crm and answers with citations | D-02, D-06 | *(fill in)* | *(GitHub commit)* |
| E-06 | Q06 “Who is the account owner for TechStart Ltd?” routes to crm and answers with citations | D-02, D-06 | *(fill in)* | *(GitHub commit)* |
| E-07 | Q07 “What is the runbook for when the ingestion pipeline throws a schema mismatch error?” routes to docs and answers with citations | D-02, D-04 | *(fill in)* | *(GitHub commit)* |
| E-08 | Q08 “What does the architecture doc say about the ingestion pipeline?” routes to docs and answers with citations | D-02, D-04 | *(fill in)* | *(GitHub commit)* |
| E-09 | Q09 “Did last night's pipeline failure affect any CRM customer sync?” routes to crm, data-platform and answers with citations | D-02, D-06, D-03, D-07 | *(fill in)* | *(GitHub commit)* |
| E-13 | The graded QA run: routing accuracy and hallucination rate across all 12 queries | D-07 | *(fill in)* | *(GitHub commit)* |
| E-14 | Full offline test suite passing, with the measured coverage figure | D-08 | *(fill in)* | *(GitHub commit)* |
| E-15 | The documentation corpus chunked, embedded and indexed for similarity search | D-04 | *(fill in)* | *(GitHub commit)* |
| E-16 | The AgentField control plane running, with all five agent nodes registered | D-01 | *(fill in)* | *(GitHub commit)* |

> **D-01 is Partial, not Done.** The approved proposal committed to the control plane *plus* an Azure VM *plus* OpenRouter connected. OpenRouter is not provisioned — all inference is local at ₹0. Declare it Partial and record the deviation in Section 8; claiming it Done without evidence for those parts is exactly what the consistency check catches.

```bash
make qa && make evidence   # re-run the suite and regenerate this directory
```

