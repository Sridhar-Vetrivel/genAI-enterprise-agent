# QA Evidence — the 12 mandatory test queries

Auto-generated from the last `make qa` run. One page per test query: what was asked, how it routed, what it cited, what the Judge Agent found, and how to screenshot it for the mid-term Evidence Pack.

## Headline numbers

| Metric | Target | Measured |
|---|---|---|
| Routing accuracy | 100.0% | **100.0%** |
| Hallucination rate | &lt;10.0% | **2.7%** |
| Answers carrying citations | all | **5 / 5** |
| Claims grounded | — | **36 / 37** |
| Answers verified by the Judge | all | **5 / 5** |
| LLM cost | ₹0 | **₹0** (local `gemma3:4b` / `gemma3:1b`) |

Queries completed in this run: **5 / 12**

## Per-query evidence

| # | Query | Expected | Routed to | Cites | Halluc. | Evidence |
|---|---|---|---|---|---|---|
| 1 | Did yesterday's ETL pipeline for the sales data run successfully? | `data-platform` | ✅ `data-platform` | 2 | 0.0% | [q01.md](q01.md) |
| 2 | What was the error in the last failed Databricks job? | `data-platform` | ✅ `data-platform` | 1 | 0.0% | [q02.md](q02.md) |
| 3 | Did the latest deployment of the payments service pass all quality gates? | `devops` | ✅ `devops` | 1 | 8.33% | [q03.md](q03.md) |
| 4 | What was the last deployment date for the auth service? | `devops` | ✅ `devops` | 1 | 0.0% | [q04.md](q04.md) |
| 5 | What is the current deal status for Acme Corp? | `crm` | ✅ `crm` | 1 | 0.0% | [q05.md](q05.md) |
| 6 | Who is the account owner for TechStart Ltd? | `crm` | _not yet run_ | — | — | — |
| 7 | What is the runbook for when the ingestion pipeline throws a schema mismatch error? | `docs` | _not yet run_ | — | — | — |
| 8 | What does the architecture doc say about the ingestion pipeline? | `docs` | _not yet run_ | — | — | — |
| 9 | Did last night's pipeline failure affect any CRM customer sync? | `crm`, `data-platform` | _not yet run_ | — | — | — |
| 10 | The ingestion job failed - is there a fix in the runbooks? | `data-platform`, `docs` | _not yet run_ | — | — | — |
| 11 | What's the status of the latest deployment and are there any known issues? | `devops`, `docs` | _not yet run_ | — | — | — |
| 12 | Give me a full status update - pipeline, deployments, and any open incidents | `crm`, `data-platform`, `devops`, `docs` | _not yet run_ | — | — | — |

## How these map to the mid-term submission

Each page ends with screenshot instructions and a pre-filled Evidence-block header table. See [../MidTerm_Submission_Reference.md](../MidTerm_Submission_Reference.md) for the template's rules — every deliverable marked Done/Partial in Section 3 must point to at least one Evidence ID here.

```bash
make qa && make evidence   # re-run the suite and regenerate this directory
```

