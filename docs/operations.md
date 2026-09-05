# Operations and quarterly refresh

## Standard quarterly runbook

1. Confirm source licences and connector health.
2. Freeze the research cutoff.
3. Ingest new filings, IR publications, project evidence, and technical sources.
4. Validate the market taxonomy and document any capital-weight changes.
5. Run parser and evidence-quality checks.
6. Execute the company research graph.
7. Evaluate the run.
8. Compare it with the previous quarter.
9. Resolve conflicts and review every provisional Top-20 company.
10. Publish the approved report and archive its manifest.

Commands:

```bash
aifactory quarterly-refresh --generate-report
aifactory evaluate CURRENT_RUN_ID
aifactory compare-runs PREVIOUS_RUN_ID CURRENT_RUN_ID
aifactory publish CURRENT_RUN_ID --actor analyst@example.com
```

The Kubernetes schedule in `deployment/quarterly-cronjob.yaml` runs at 06:00 UTC on the fifth day of January, April, July, and October. Use a filing-aware event trigger in addition to the quarter schedule if research freshness requires it.

## Logging

Logs are JSON and include timestamp, severity, logger, message, run ID, company ID, event, duration, and status. Agent-step completion logs use debug level; run-level events use info.

Never log:

- API keys or bearer tokens.
- Full licensed transcripts unless retention explicitly permits it.
- Hidden model reasoning.
- Unredacted personal data.

Store structured rationale, evidence IDs, tool observations, and deterministic outputs instead.

## Metrics

`GET /metrics` exposes Prometheus text metrics, including:

- Completed and failed research runs.
- Source fetches and retries.
- Source prompt-injection flags.
- Company workflow failures.
- Per-operation duration counts and totals.

Recommended production alerts:

- Any failed scheduled run.
- More than 5% company-workflow failures.
- Source freshness above the segment-specific threshold.
- Citation coverage below 85%.
- Score reproducibility below 100%.
- Unexpected Top-20 churn without material source changes.
- Model cost or latency above budget.

## Suggested SLOs

| SLO | Initial target |
|---|---:|
| Scheduled run completion | 99% |
| Score reproducibility | 100% |
| Required numeric claim citation coverage | 100% |
| Mean full-dossier citation coverage | ≥95% |
| Rankable workflow success | ≥95% |
| API read availability | 99.5% |
| Restore point objective | 24 hours |
| Restore time objective | 4 hours |

## Backup and restore

Reference deployment:

- Stop writes or use SQLite online backup.
- Back up the database, `artifacts/raw-sources`, reports, and config versions together.
- Test restoration quarterly.

Production:

- PostgreSQL point-in-time recovery.
- Versioned object-store retention.
- Immutable report manifests in separate storage.
- Restore drill that verifies document hashes and score reproducibility.

## Incident handling

1. Pause publication, not evidence acquisition.
2. Identify affected runs, sources, prompts, models, and parsers from manifests.
3. Preserve audit records and raw evidence.
4. Revoke compromised credentials or source connectors.
5. Correct by issuing a new run; do not rewrite historical results.
6. Record impact, remediation, and analyst communication.

## Scaling path

1. Keep one workflow process and SQLite until real load is measured.
2. Move to PostgreSQL before multiple writers.
3. Move raw sources to object storage.
4. Separate API and workers.
5. Add a durable outer orchestrator for long-running jobs.
6. Partition company workflows and bound provider concurrency.
7. Cache by document and prompt hash, never by ticker alone.
