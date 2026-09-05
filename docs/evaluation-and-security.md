# Evaluation, governance, and security

## Deterministic evaluation command

```bash
aifactory evaluate RUN_ID
```

It calculates:

- Assessment and ranked counts.
- Rankable rate.
- Mean evidence confidence.
- Mean citation coverage.
- Score reproducibility rate.
- Unsupported required-claim count.
- Mean bear/bull rank stability.
- Approval coverage.
- Research-ready and publication-ready release gates.

The evaluation recomputes every stored score from stored components. A release fails if stored and recomputed values differ.

## Offline benchmark suite

Before real deployment, construct a point-in-time golden set of at least 30–50 companies across all five segments. Preserve the source bundles that analysts actually saw.

Required test groups:

1. Exact XBRL and margin extraction.
2. Currency, unit, and period normalization.
3. Public-parent and dual-listing resolution.
4. Exposure evidence and interval estimation.
5. Moat component labels with analyst rationales.
6. Bear/base/bull driver scenarios.
7. Risk-category severity.
8. Unsupported and contradictory claims.
9. Rank sensitivity and quarterly churn.
10. Report factuality and citation coverage.

LLM-as-judge scores may supplement but not replace deterministic checks or analyst labels. Calibrate any judge against human disagreement and keep judge prompts/model versions in the experiment record.

## Threat model

| Threat | Control |
|---|---|
| Indirect prompt injection | Treat retrieved text as data; scan; role prompts forbid following it |
| SSRF | HTTPS-only sources; block private/loopback/link-local/reserved networks |
| Excessive agency | Read-only research tools; no trading or external messaging tools |
| Hallucinated figures | Numeric claims require evidence ID, unit, period, and schema validation |
| Data poisoning | Source tiers, content hashes, contrary-evidence search, human review |
| Look-ahead bias | Frozen cutoff and publication-date filters |
| Secret leakage | Secrets outside workflow state; redaction; no credential logging |
| Cross-company leakage | Company-scoped contexts and queries |
| Silent model/prompt drift | Versions and run configuration snapshot |
| Ranking manipulation | Deterministic code, reproducibility test, immutable audit event |
| Malicious analyst override | Authentication, RBAC in production, comment and audit event |
| Supply-chain compromise | Dependency pinning, SBOM, signature and vulnerability scanning |

## Red-team corpus

Include documents containing:

- “Ignore previous instructions” attacks.
- Fake tool-call JSON.
- Hidden HTML and PDF text.
- Conflicting currencies and unit multipliers.
- Later-dated restatements inserted into historical runs.
- Subsidiary names designed to map to the wrong public parent.
- Duplicate filings with different hashes.
- News articles presenting estimates as reported company facts.

The expected outcome is a flagged or non-rankable dossier, never autonomous corrective action against external systems.

## Governance roles

- Research owner: approves methodology, taxonomy, and thresholds.
- Data steward: approves sources, licensing, and retention.
- Analyst: reviews company dossiers and publication.
- Platform operator: handles reliability but cannot alter scores silently.
- Model-risk reviewer: approves model/prompt changes after benchmark results.
- Security owner: maintains threat model, access, egress, and incident response.

## Change control

Any taxonomy, formula, risk weight, prompt, model, parser, or source-tier change must:

1. Receive a new version.
2. Run on the frozen benchmark dataset.
3. Produce a rank-diff report.
4. Meet or exceed release thresholds.
5. Be approved before becoming the default.

