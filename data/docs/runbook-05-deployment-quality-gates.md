# Runbook 05 — Deployment Quality Gates

Owner: DevOps Team · Last updated: 2026-06-12

## The Gates

Every service deployment runs five quality gates. A deployment is only promoted when all
five pass.

| Gate | Threshold | Blocking |
|---|---|---|
| unit-tests | 0 failures | Yes |
| code-coverage | ≥ 80% | Yes |
| sonarqube | 0 blocker issues | Yes |
| security-scan | no high/critical CVEs | Yes |
| integration-tests | 0 failures | Yes |

## When a Gate Fails

**code-coverage below threshold** — the deployment is blocked. Add tests for the uncovered
paths; do not lower the threshold. A waiver requires DevOps lead sign-off.

**integration-tests failing on a schema contract** — this usually means the service and the
data platform disagree about a column type. Do not re-run the pipeline hoping it passes.
Check whether the corresponding ingestion job is also failing (see Runbook 12), because the
two failures normally share one root cause.

**security-scan** — a high or critical CVE blocks release. Patch the dependency and re-run.

## Rollback

Re-run the previous successful workflow run for the service with the last known-good commit
SHA. Deployments are idempotent; rolling back does not require a database migration unless
the release included one.
