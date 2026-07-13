# Runbook 12 — Schema Mismatch Recovery (Ingestion Pipeline)

Owner: Data Platform Team · Last updated: 2026-06-30

## Symptom

The `ingestion_raw_events` Databricks job (job 4822) terminates with
`SchemaMismatchException`. The message names the offending column, the expected type and
the type actually found in the source Parquet file. No rows are written to the bronze
layer, so every downstream job that reads `bronze.raw_events` will fail or produce a stale
result.

## Cause

An upstream producer changed a column type without going through the schema-contract
review. The most common offender is `customer_tier`, which must be `StringType`. When a
producer emits it as an integer code (1, 2, 3) instead of the label ("enterprise",
"mid-market"), ingestion rejects the whole batch.

## Recovery Steps

1. Identify the offending file from the exception message. It is the `part-*.parquet` path
   in the `s3://psiog-raw/events/<date>/` prefix.
2. Quarantine the bad partition: move it to `s3://psiog-raw/quarantine/<date>/`. Do not
   delete it — the producer team needs it for their root-cause analysis.
3. Re-run job 4822 (`ingestion_raw_events`) from the Databricks Jobs UI. It will skip the
   quarantined partition and ingest the remaining files.
4. Once 4822 succeeds, re-run job 4830 (`crm_sync`) manually. It does not retry on its own
   and will otherwise leave the CRM records stale until the next scheduled run at 04:00.
5. Notify the producer team so they can correct the emitter and re-publish the partition.

## Prevention

Enable the schema-contract test in the `deploy-ingestion` pipeline. The gate compares each
producer's declared schema against the bronze contract and fails the deployment before the
bad data ever reaches the platform.

## Escalation

If re-running 4822 fails a second time with the same exception, the contract itself may be
out of date. Escalate to the Data Platform on-call and page the schema owner. Do not
loosen the column type to unblock the pipeline — that corrupts the silver layer silently.
