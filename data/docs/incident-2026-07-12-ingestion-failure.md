# Incident INC-2043 — Ingestion Failure and CRM Sync Impact

Status: Open · Severity: SEV-2 · Opened: 2026-07-12 00:15 UTC
Owner: Data Platform on-call

## Summary

Job 4822 (`ingestion_raw_events`) failed at 00:04 UTC on 2026-07-12 with a
`SchemaMismatchException` on the `customer_tier` column: the source partition emitted
`IntegerType` where the bronze contract requires `StringType`.

Because `bronze.raw_events` was never refreshed, the downstream `crm_sync` job (4830)
failed at 04:00 UTC with `UpstreamDependencyFailed` and synced zero rows. Acme Corp and
TechStart Ltd account records in the CRM are therefore stale as of 2026-07-11.

## Known Issues

- The `deploy-ingestion` pipeline (run 5530) also failed its integration-test gate on the
  same schema contract for `customer_tier`, and its code-coverage gate at 74% (threshold
  80%). The failing deployment and the failing ingestion job share the same root cause.
- `crm_sync` does not auto-retry after an upstream failure. It must be re-run manually.

## Actions

1. Quarantine the bad partition and re-run job 4822 (see Runbook 12).
2. Manually re-run job 4830 once ingestion succeeds to refresh the CRM.
3. Producer team to fix the emitter and re-publish the partition.

## Impact

Two enterprise/mid-market accounts (Acme Corp, TechStart Ltd) are showing data one day
stale in the CRM. No customer-facing outage. Sales mart (job 4821) was unaffected and
completed successfully at 02:14 UTC.
