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
| Q01 | Did yesterday's ETL pipeline for the sales data run successfully? | `data-platform` | ✅ succeeded | 106.8s | `exec_20261013_093038_bh89opg9` |
| Q02 | What was the error in the last failed Databricks job? | `data-platform` | ✅ succeeded | 84.9s | `exec_20261013_093236_hw2cf79a` |
| Q03 | Did the latest deployment of the payments service pass all quality gates? | `devops` | ✅ succeeded | 80.7s | `exec_20261013_093407_7n2zp0s9` |
| Q04 | What was the last deployment date for the auth service? | `devops` | ✅ succeeded | 79.9s | `exec_20261013_093537_v69s815p` |
| Q05 | What is the current deal status for Acme Corp? | `crm` | ✅ succeeded | 88.2s | `exec_20261013_093703_pet346s4` |
| Q06 | Who is the account owner for TechStart Ltd? | `crm` | ✅ succeeded | 83.7s | `exec_20261013_093840_gzezzfym` |
| Q07 | What is the runbook for when the ingestion pipeline throws a schema mismatch error? | `docs` | ✅ succeeded | 134.2s | `exec_20261013_094012_xcuwhxg0` |
| Q08 | What does the architecture doc say about the ingestion pipeline? | `docs` | ✅ succeeded | 105.7s | `exec_20261013_094238_kh7f0ki5` |
| Q09 | Did last night's pipeline failure affect any CRM customer sync? | `crm, data-platform` | ✅ succeeded | 397.4s | `exec_20261013_094433_uefpi8xb` |
| Q10 | The ingestion job failed - is there a fix in the runbooks? | `data-platform, docs` | ✅ succeeded | 218.9s | `exec_20261013_095146_emvif63h` |
| Q11 | What's the status of the latest deployment and are there any known issues? | `devops, docs` | ✅ succeeded | 377.9s | `exec_20261013_095545_hkow1b8j` |
| Q12 | Give me a full status update - pipeline, deployments, and any open incidents | `crm, data-platform, devops, docs` | ✅ succeeded | 554.7s | `exec_20261013_100238_uv6hnidw` |

## Answers as traced

### Q01 — Did yesterday's ETL pipeline for the sales data run successfully?

- **Execution ID:** `exec_20261013_093038_bh89opg9`
- **Run ID:** `run_20261013_093038_noumriq6`
- **Routed to:** `data-platform` (expected `data-platform`)

The sales_etl pipeline run #99102, which started on 2026-07-11T02:14:00Z, completed successfully. It returned 1279884 records written.

**Citations**

- Databricks Job #4821 (sales_etl) run #99102

### Q02 — What was the error in the last failed Databricks job?

- **Execution ID:** `exec_20261013_093236_hw2cf79a`
- **Run ID:** `run_20261013_093236_jfo55gmt`
- **Routed to:** `data-platform` (expected `data-platform`)

The last failed Databricks job was job #4822 (ingestion_raw_events) run #99150. The error message was ‘SchemaMismatchException: column ‘customer_tier’ expected StringType but found IntegerType in source file s3://psiog-raw/events/2026-07-12/part-0007.parquet’.

**Citations**

- Databricks Job #4822 (ingestion_raw_events) run #99150

### Q03 — Did the latest deployment of the payments service pass all quality gates?

- **Execution ID:** `exec_20261013_093407_7n2zp0s9`
- **Run ID:** `run_20261013_093407_0zd6tv1k`
- **Routed to:** `devops` (expected `devops`)

Yes, the latest deployment of the payments service, workflow-run #5512 (commit a1f9c34) passed all quality gates. The unit-tests, code-coverage, sonarqube, security-scan, and integration-tests all passed according to GitHub Actions run #5512.

**Citations**

- GitHub Actions run #5512 (deploy-payments, commit a1f9c34)

### Q04 — What was the last deployment date for the auth service?

- **Execution ID:** `exec_20261013_093537_v69s815p`
- **Run ID:** `run_20261013_093537_9hm0s20c`
- **Routed to:** `devops` (expected `devops`)

The last deployment date for the auth service was 2026-07-09T11:05:00Z. This deployment passed all quality gates, including unit-tests, code-coverage (83% threshold 80%), and the security-scan which found no high/critical CVEs.

**Citations**

- GitHub Actions run #5498 (deploy-auth, commit 7de2b10)

### Q05 — What is the current deal status for Acme Corp?

- **Execution ID:** `exec_20261013_093703_pet346s4`
- **Run ID:** `run_20261013_093703_wjyvn61x`
- **Routed to:** `crm` (expected `crm`)

The current deal status for Acme Corp is Negotiation, as indicated by DEAL-7781. The deal is owned by Divya Raman.

**Citations**

- CRM account ACC-1001 (Acme Corp)
- CRM deal DEAL-7781 (Acme Corp)

### Q06 — Who is the account owner for TechStart Ltd?

- **Execution ID:** `exec_20261013_093840_gzezzfym`
- **Run ID:** `run_20261013_093840_zo6th6i3`
- **Routed to:** `crm` (expected `crm`)

The account owner for TechStart Ltd is Karthik Rao. This information is available in CRM account ACC-1002.

**Citations**

- CRM account ACC-1002 (TechStart Ltd)

### Q07 — What is the runbook for when the ingestion pipeline throws a schema mismatch error?

- **Execution ID:** `exec_20261013_094012_xcuwhxg0`
- **Run ID:** `run_20261013_094012_vwym0lx2`
- **Routed to:** `docs` (expected `docs`)

If the `deploy-ingestion` pipeline fails its integration-test gate for a schema contract, check whether the corresponding ingestion job is also failing. The failure is often due to an upstream producer changing a column type without schema review, specifically with `customer_tier`. If re-running job 4822 fails a second time, escalate to the Data Platform on-call and page the schema owner.

**Citations**

- runbook-12-schema-mismatch.md § Cause
- runbook-05-deployment-quality-gates.md § When a Gate Fails
- runbook-12-schema-mismatch.md § Escalation

### Q08 — What does the architecture doc say about the ingestion pipeline?

- **Execution ID:** `exec_20261013_094238_kh7f0ki5`
- **Run ID:** `run_20261013_094238_zm7wto1i`
- **Routed to:** `docs` (expected `docs`)

The ingestion pipeline lands raw product and sales events into the Databricks lakehouse and promotes them through a three-layer medallion architecture. The pipeline includes the `deploy-ingestion` run 5530, which is subject to schema-contract testing. It has SLAs for bronze ingestion within 4 hours of file arrival and CRM sync complete by 04:30 daily.

**Citations**

- architecture-ingestion-pipeline.md § Overview
- runbook-12-schema-mismatch.md § Prevention
- architecture-ingestion-pipeline.md § SLAs

### Q09 — Did last night's pipeline failure affect any CRM customer sync?

- **Execution ID:** `exec_20261013_094433_uefpi8xb`
- **Run ID:** `run_20261013_094433_1n5lg1ip`
- **Routed to:** `crm, data-platform` (expected `crm, data-platform`)

Last night’s pipeline failure impacted CRM customer synchronization. The `crm_sync` job run #99163 failed due to an upstream dependency issue – the `bronze.raw_events` table was not refreshed by job 4822 (ingestion_raw_events), resulting in no data being synced to the CRM Citation. As a result, the sync status for accounts ACC-1001 (Acme Corp), ACC-1002 (TechStart Ltd) and ACC-1003 (Northwind Retail) is stale, with the last sync time recorded as 2026-07-11T04:02:00Z Citation.

**Citations**

- Databricks Job #4830 (crm_sync) run #99163
- CRM account ACC-1001 (Acme Corp)
- CRM account ACC-1002 (TechStart Ltd)
- CRM account ACC-1003 (Northwind Retail)

### Q10 — The ingestion job failed - is there a fix in the runbooks?

- **Execution ID:** `exec_20261013_095146_emvif63h`
- **Run ID:** `run_20261013_095146_axqbluya`
- **Routed to:** `data-platform, docs` (expected `data-platform, docs`)

The ingestion job `ingestion_raw_events` failed on 2026-07-12 due to a `SchemaMismatchException` in the `s3://psiog-raw/events/2026-07-12/part-0007.parquet` file. To resolve this, you should first quarantine the bad partition by moving it to `s3://psiog-raw/quarantine/<date>/` as outlined in the recovery steps. Following this, re-run job 4822 from the Databricks Jobs UI. After 4822 succeeds, manually re-run job 4830 (`crm_sync`) to refresh the CRM.

**Citations**

- Databricks Job #4822 (ingestion_raw_events) run #99150
- incident-2026-07-12-ingestion-failure.md § Actions
- runbook-12-schema-mismatch.md § Recovery Steps

### Q11 — What's the status of the latest deployment and are there any known issues?

- **Execution ID:** `exec_20261013_095545_hkow1b8j`
- **Run ID:** `run_20261013_095545_xi02izzt`
- **Routed to:** `devops, docs` (expected `devops, docs`)

The latest deployment attempt failed due to a code-coverage gate failure at 74%, falling short of the 80% threshold. Following this, a related issue arose with Job 4822 (`ingestion_raw_events`) on 2026-07-12, causing a `SchemaMismatchException` for the `customer_tier` column and subsequently impacting the CRM with stale account records as of 2026-07-11. The payments service deployment, run #5512, was successful, as was the auth service deployment, run #5498.

**Citations**

- GitHub Actions run #5512 (deploy-payments, commit a1f9c34)
- GitHub Actions run #5498 (deploy-auth, commit 7de2b10)
- runbook-05-deployment-quality-gates.md § The Gates
- incident-2026-07-12-ingestion-failure.md § Summary

### Q12 — Give me a full status update - pipeline, deployments, and any open incidents

- **Execution ID:** `exec_20261013_100238_uv6hnidw`
- **Run ID:** `run_20261013_100238_a3z7pbxf`
- **Routed to:** `crm, data-platform, devops, docs` (expected `crm, data-platform, devops, docs`)

The recent data pipeline activity shows the `sales_etl` job completed successfully twice on July 12th and 11th, processing significant volumes of records. However, the `crm_sync` job failed on July 12th due to a failure in the `ingestion_raw_events` job, specifically a `SchemaMismatchException`. Deployment of the ingestion service failed due to a code-coverage gate and integration test failures related to customer_tier schema contracts. The payments and auth services deployed successfully with passing quality gates. Furthermore, the `crm_sync` job does not automatically retry after upstream failures and requires manual re-runs, as detailed in the known issues.

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

