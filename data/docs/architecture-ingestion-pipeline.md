# Architecture — Ingestion Pipeline

Owner: Data Platform Team · Last updated: 2026-05-18

## Overview

The ingestion pipeline lands raw product and sales events into the Databricks lakehouse and
promotes them through a three-layer medallion architecture.

## Layers

- **Bronze (`bronze.raw_events`)** — raw, append-only landing zone. Job 4822
  (`ingestion_raw_events`) reads Parquet files from `s3://psiog-raw/events/` every four
  hours and writes them unchanged apart from schema validation.
- **Silver (`silver.events_curated`)** — deduplicated, type-conformed, joined to the
  customer dimension. This is the layer analysts query.
- **Gold (`gold.sales_mart`)** — business aggregates. Job 4821 (`sales_etl`) builds the
  sales data mart nightly at 02:00 from the silver layer.

## Schema Contract

Every column landing in bronze is governed by a schema contract checked at ingestion time.
`customer_tier` is contractually a `StringType` and carries the labels `enterprise`,
`mid-market` or `smb`. A producer that emits an integer code violates the contract and the
batch is rejected — see Runbook 12 for recovery.

## Downstream Dependencies

`crm_sync` (job 4830) reads the curated customer table and pushes account records to the
CRM at 04:00 daily. It depends on job 4822 having refreshed `bronze.raw_events` earlier in
the night. If 4822 fails, 4830 fails with `UpstreamDependencyFailed` and CRM account
records remain stale until the next successful sync.

## SLAs

- Bronze ingestion: within 4 hours of file arrival.
- Sales mart (gold): available by 03:00 daily.
- CRM sync: complete by 04:30 daily.
