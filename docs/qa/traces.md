# Control-Plane Traces — one execution per test query

Each of the 12 test queries was run through `coordinator.ask` on the AgentField
control plane. The coordinator classifies intent with the LLM, dispatches to the
specialist agents with `app.call()` (recorded as a DAG), and synthesises one cited
answer — so a single trace evidences routing, the multi-agent architecture, and
grounding together.

Open **<http://localhost:8080/ui/>** and find the execution by its ID.

| Measured over these traces | Result |
|---|---|
| Executions succeeded | **12 / 12** |
| Routing accuracy (vs. the ground truth in `test_queries.py`) | **100.0%** (12/12) |
| Answers carrying at least one citation | **12 / 12** |

This is routing measured **through the live control plane**, agent to agent — not
the in-process path the offline suite exercises.

## 📸 How to take the screenshot

1. Open <http://localhost:8080/ui/> and select the execution ID for the query you want.
2. Stay on the **Inputs & Outputs** tab: the input query on the left, the
   `answer` / `citations` / `confidence` on the right. The citation is the proof
   the answer is grounded — make sure it is readable.
3. Capture the **whole browser window**, including the reasoner name, the
   `data-agent`/`coordinator` node badge, the green **Succeeded** status and the
   duration. Full-size, no crop, no collage.
4. For the cross-domain queries (Q9–Q12) also capture the **Debug**/DAG view: it
   shows the coordinator calling more than one specialist, which is the single
   clearest picture of the multi-agent design.

## Executions

| Q | Query | Routed to | Status | Time | Execution ID |
|---|---|---|---|---|---|
| Q01 | Did yesterday's ETL pipeline for the sales data run successfully? | `data-platform` | ✅ succeeded | 70.4s | `exec_20260714_141123_g9gremvx` |
| Q02 | What was the error in the last failed Databricks job? | `data-platform` | ✅ succeeded | 82.1s | `exec_20260714_141241_mqlvknj3` |
| Q03 | Did the latest deployment of the payments service pass all quality gates? | `devops` | ✅ succeeded | 77.1s | `exec_20260714_141414_omi6no7o` |
| Q04 | What was the last deployment date for the auth service? | `devops` | ✅ succeeded | 86.5s | `exec_20260714_141538_39ycscfa` |
| Q05 | What is the current deal status for Acme Corp? | `crm` | ✅ succeeded | 89.8s | `exec_20260714_141715_68sxegi6` |
| Q06 | Who is the account owner for TechStart Ltd? | `crm` | ✅ succeeded | 85.3s | `exec_20260714_141852_ebkaqo3h` |
| Q07 | What is the runbook for when the ingestion pipeline throws a schema mismatch error? | `docs` | ✅ succeeded | 123.8s | `exec_20260714_144630_ebji8tdr` |
| Q08 | What does the architecture doc say about the ingestion pipeline? | `docs` | ✅ succeeded | 115.2s | `exec_20260714_144845_mo16pl3y` |
| Q09 | Did last night's pipeline failure affect any CRM customer sync? | `crm, data-platform` | ✅ succeeded | 340.6s | `exec_20260714_142110_b9u0edtk` |
| Q10 | The ingestion job failed - is there a fix in the runbooks? | `data-platform, docs` | ✅ succeeded | 239.8s | `exec_20260714_145055_3hvpsfti` |
| Q11 | What's the status of the latest deployment and are there any known issues? | `devops, docs` | ✅ succeeded | 409.5s | `exec_20260714_145520_dxtvhyol` |
| Q12 | Give me a full status update - pipeline, deployments, and any open incidents | `crm, data-platform, devops, docs` | ✅ succeeded | 703.6s | `exec_20260714_150256_x4r81cqa` |

## Answers as traced

### Q01 — Did yesterday's ETL pipeline for the sales data run successfully?

- **Execution ID:** `exec_20260714_141123_g9gremvx`
- **Run ID:** `run_20260714_141123_cyc8nkb1`
- **Routed to:** `data-platform` (expected `data-platform`)

Yes, yesterday's sales ETL pipeline ran successfully. Run #99102 completed on 2026-07-11T02:14:00Z with a successful result and 1279884 records written.

**Citations**

- Databricks Job #4821 (sales_etl) run #99102

### Q02 — What was the error in the last failed Databricks job?

- **Execution ID:** `exec_20260714_141241_mqlvknj3`
- **Run ID:** `run_20260714_141241_v6ornsqg`
- **Routed to:** `data-platform` (expected `data-platform`)

The last failed Databricks job was job 4822, named ‘ingestion_raw_events’, run #99150. The error message indicates a ‘SchemaMismatchException’ due to a column having an unexpected IntegerType instead of StringType in the source file “s3://psiog-raw/events/2026-07-12/part-0007.parquet”.

**Citations**

- Databricks Job #4822 (ingestion_raw_events) run #99150

### Q03 — Did the latest deployment of the payments service pass all quality gates?

- **Execution ID:** `exec_20260714_141414_omi6no7o`
- **Run ID:** `run_20260714_141414_2tuh77rj`
- **Routed to:** `devops` (expected `devops`)

Yes, the latest deployment of the payments service passed all quality gates. The shows that the unit-tests, code-coverage, Sonarqube, security-scan, and integration-tests all passed.

**Citations**

- GitHub Actions run #5512 (deploy-payments, commit a1f9c34)

### Q04 — What was the last deployment date for the auth service?

- **Execution ID:** `exec_20260714_141538_39ycscfa`
- **Run ID:** `run_20260714_141538_k3btfwtn`
- **Routed to:** `devops` (expected `devops`)

The last deployment date for the auth service was 2026-07-09T11:05:00Z. All quality gates passed during this deployment, including unit tests, code coverage (83% against an 80% threshold), and the security scan which found no high/critical CVEs.

**Citations**

- GitHub Actions run #5498 (deploy-auth, commit 7de2b10)

### Q05 — What is the current deal status for Acme Corp?

- **Execution ID:** `exec_20260714_141715_68sxegi6`
- **Run ID:** `run_20260714_141715_6kn0k0f7`
- **Routed to:** `crm` (expected `crm`)

The current deal status for Acme Corp is Negotiation. The deal, DEAL-7781, is in the Negotiation stage and has an expected close date of 2026-08-30 [CRM deal DEAL-7781]. Divya Raman is the owner of this deal [CRM account ACC-1001].

**Citations**

- CRM account ACC-1001 (Acme Corp)
- CRM deal DEAL-7781 (Acme Corp)

### Q06 — Who is the account owner for TechStart Ltd?

- **Execution ID:** `exec_20260714_141852_ebkaqo3h`
- **Run ID:** `run_20260714_141852_5jq1gvy6`
- **Routed to:** `crm` (expected `crm`)

The account owner for TechStart Ltd is Karthik Rao. This information is available in the CRM account record for ACC-1002. The last sync time for this record was 2026-07-11T04:02:00Z, and the record is currently stale.

**Citations**

- CRM account ACC-1002 (TechStart Ltd)

### Q07 — What is the runbook for when the ingestion pipeline throws a schema mismatch error?

- **Execution ID:** `exec_20260714_144630_ebji8tdr`
- **Run ID:** `run_20260714_144630_1l16bvq9`
- **Routed to:** `docs` (expected `docs`)

If the `deploy-ingestion` pipeline fails its integration-test gate due to a schema contract mismatch, first check whether the corresponding ingestion job is also failing. If so, re-run the `deploy-ingestion` pipeline (run 5530) and investigate the cause, which is often an upstream producer changing a column type without schema review. If re-running fails a second time, escalate to the Data Platform on-call and page the schema owner. Do not loosen the column type to unblock the pipeline, as this corrupts the silver layer silently.

**Citations**

- incident-2026-07-12-ingestion-failure.md § Known Issues
- runbook-12-schema-mismatch.md § Cause
- runbook-05-deployment-quality-gates.md § When a Gate Fails
- runbook-12-schema-mismatch.md § Escalation

### Q08 — What does the architecture doc say about the ingestion pipeline?

- **Execution ID:** `exec_20260714_144845_mo16pl3y`
- **Run ID:** `run_20260714_144845_lyhajy1c`
- **Routed to:** `docs` (expected `docs`)

The ingestion pipeline lands raw product and sales events into the Databricks lakehouse and promotes them through a three-layer medallion architecture. It has SLAs for bronze ingestion within 4 hours of file arrival, sales mart (gold) available by 03:00 daily, and CRM sync complete by 04:30 daily. The pipeline uses a schema-contract test to prevent bad data from reaching the platform.

**Citations**

- architecture-ingestion-pipeline.md § Overview
- runbook-12-schema-mismatch.md § Prevention
- architecture-ingestion-pipeline.md § SLAs

### Q09 — Did last night's pipeline failure affect any CRM customer sync?

- **Execution ID:** `exec_20260714_142110_b9u0edtk`
- **Run ID:** `run_20260714_142110_pbdra5be`
- **Routed to:** `crm, data-platform` (expected `crm, data-platform`)

Last night’s pipeline failure, specifically run #99163 of the `crm_sync` job, resulted in a synchronization issue for CRM customer accounts. The `crm_sync` job failed because the source table `bronze.raw_events` hadn’t been refreshed by job #4822, leading to 0 rows being synced. Consequently, two CRM accounts, Acme Corp (ACC-1001) and TechStart Ltd (ACC-1002), experienced stale sync statuses.

**Citations**

- Databricks Job #4830 (crm_sync) run #99163
- CRM account ACC-1001 (Acme Corp)
- CRM account ACC-1002 (TechStart Ltd)

### Q10 — The ingestion job failed - is there a fix in the runbooks?

- **Execution ID:** `exec_20260714_145055_3hvpsfti`
- **Run ID:** `run_20260714_145055_vksib5t7`
- **Routed to:** `data-platform, docs` (expected `data-platform, docs`)

The ingestion job ‘ingestion_raw_events’ failed on 2026-07-12 due to a SchemaMismatchException related to an integer value in a source file. To resolve this, follow the steps outlined in Runbook 12, which involves identifying the problematic file in the `s3://psiog-raw/events/<date>/` prefix and moving it to the quarantine location `s3://psiog-raw/quarantine/<date>/`. After re-running job 4822 from the Databricks Jobs UI, which will skip the quarantined partition, manually re-run job 4830 to refresh the CRM, and notify the producer team to correct the emitter and re-publish the partition.

**Citations**

- Databricks Job #4822 (ingestion_raw_events) run #99150
- incident-2026-07-12-ingestion-failure.md § Actions
- runbook-12-schema-mismatch.md § Symptom
- runbook-12-schema-mismatch.md § Recovery Steps

### Q11 — What's the status of the latest deployment and are there any known issues?

- **Execution ID:** `exec_20260714_145520_dxtvhyol`
- **Run ID:** `run_20260714_145520_vrwcblzj`
- **Routed to:** `devops, docs` (expected `devops, docs`)

The latest deployment failed due to a code coverage gate failing at 74% and three schema contract test failures for the `customer_tier` field. Additionally, the `ingestion_raw_events` job failed on 2026-07-12 due to a `SchemaMismatchException` related to the `customer_tier` column, which triggered a failure in the `crm_sync` job and resulted in stale CRM records as of 2026-07-11. The payments and auth service deployments themselves were successful, with all quality gates passing. All five quality gates must pass for a service deployment to be promoted as of 2026-07-14.

**Citations**

- GitHub Actions run #5512 (deploy-payments, commit a1f9c34)
- GitHub Actions run #5498 (deploy-auth, commit 7de2b10)
- runbook-05-deployment-quality-gates.md § The Gates
- incident-2026-07-12-ingestion-failure.md § Summary

### Q12 — Give me a full status update - pipeline, deployments, and any open incidents

- **Execution ID:** `exec_20260714_150256_x4r81cqa`
- **Run ID:** `run_20260714_150256_ucqqco34`
- **Routed to:** `crm, data-platform, devops, docs` (expected `crm, data-platform, devops, docs`)

As of today, July 14, 2026, the `sales_etl` job (ID 4821) ran successfully twice, processing 1,284,502 and 1,279,884 records respectively. However, the `crm_sync` job (ID 4830) failed due to a dependency issue with the `ingestion_raw_events` job (ID 4822), stemming from a schema mismatch, and this job did not auto-retry. Furthermore, the `deploy-ingestion` workflow (run #5530) for the ingestion-service failed due to failing quality gates, specifically a low code-coverage score and integration test failures. The `deploy-payments` and `deploy-auth` workflows were successful and. Finally, deal DEAL-7781 within Acme Corp (ACC-1001) remains in the Negotiation stage.

**Citations**

- Databricks Job #4830 (crm_sync) run #99163
- Databricks Job #4821 (sales_etl) run #99141
- Databricks Job #4822 (ingestion_raw_events) run #99150
- Databricks Job #4821 (sales_etl) run #99102
- GitHub Actions run #5530 (deploy-ingestion, commit c40be71)
- GitHub Actions run #5512 (deploy-payments, commit a1f9c34)
- GitHub Actions run #5498 (deploy-auth, commit 7de2b10)
- CRM account ACC-1001 (Acme Corp)
- incident-2026-07-12-ingestion-failure.md § Known Issues

