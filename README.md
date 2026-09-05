# AI Factory Growth Research Platform

An end-to-end reference implementation for producing an auditable, point-in-time ranking of public companies with fundamental growth exposure to AI-factory and hyperscale data-center build-outs.

The platform ranks **fundamental AI-factory beneficiaries**. Valuation is out of scope, so its output is not a stock-price forecast, trading signal, or investment recommendation.

## What is implemented

- Versioned AI-factory taxonomy and capital-stack seed weights.
- Company/security master with public-company eligibility controls.
- Immutable source-document metadata, hashes, local raw-source paths, and an evidence-claim ledger.
- Versioned online-source catalog with secret references, rate/size/timeout policies, sync cursors, and audit history.
- Live SEC EDGAR universe/filing/XBRL, GLEIF identity, and GDELT discovery connectors.
- Read-only HTTPS ingestion controls, DNS/redirect SSRF defenses, credential redaction, and prompt-injection flagging.
- Review-only model extraction with exact-quote, type, range, unit, period, and confidence validation.
- Specialized eligibility, evidence, exposure, moat, margin, growth, risk, skeptic, and narrative agents.
- LangGraph runtime when installed, plus a dependency-free graph runner for offline verification.
- Deterministic exposure-aware TAFGS, risk adjustment, bear/base/bull scenarios, and rank stability.
- Human review and publication gates.
- FastAPI service and a dependency-free analyst workbench.
- Markdown investment-research-style reports with reproducibility manifests.
- JSON logs, metrics endpoint, audit events, run evaluation, and run-to-run comparison.
- CLI, Docker image, Compose file, and quarterly Kubernetes CronJob.
- A 20-company synthetic evidence set. It tests the entire workflow without presenting invented figures as real research.

## Quick start

The core pipeline and tests use the Python standard library and run before installing web dependencies:

```bash
make test
make seed
make run
```

The generated report and manifest are written under `artifacts/reports/`.

For the API and LangGraph runtime:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
aifactory seed-demo
aifactory serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. The development API key is `local-development-key`; change it through `AIFACTORY_API_KEY` before any shared deployment.

Docker alternative:

```bash
export AIFACTORY_API_KEY='replace-with-a-secret'
export AIFACTORY_SEC_USER_AGENT='Your Organization research-contact@example.com'
docker compose up --build
```

## Common workflows

```bash
# Initialize and load safe synthetic data
aifactory init-db
aifactory seed-demo

# Point-in-time run
aifactory run --as-of-date 2026-09-01 --generate-report

# Inspect and evaluate
aifactory list-runs
aifactory show-run RUN_ID
aifactory evaluate RUN_ID

# Record a review
aifactory review RUN_ID COMPANY_ID \
  --decision approved \
  --reviewer analyst@example.com \
  --comment "Primary evidence and assumptions reviewed"

# Publish only after every Top-20 company is approved
aifactory publish RUN_ID --actor analyst@example.com

# Compare quarterly results
aifactory compare-runs PREVIOUS_RUN_ID CURRENT_RUN_ID

# Inspect the config-driven source registry
aifactory source-list

# Build the universe from an online regulator, not a code-owned ticker list
aifactory source-sync sec_edgar --mode universe --limit 1000

# Ingest SEC identity, filings, and annual XBRL revenue/margin
aifactory source-sync sec_edgar --mode company \
  --cik 0000320193 \
  --segment compute_servers \
  --subsegment ai_servers \
  --as-of-date 2026-09-01 \
  --limit 3

# Create human-gated evidence proposals from normalized documents
aifactory extract-evidence --company-id COMPANY_ID --as-of-date 2026-09-01
aifactory list-proposals --company-id COMPANY_ID --status pending
aifactory review-proposal PROPOSAL_ID \
  --decision accepted \
  --reviewer analyst@example.com \
  --comment "Verified source, quote, period, unit, and rubric"

# Scheduled command used by the CronJob
aifactory quarterly-refresh --generate-report
```

SEC ingestion only creates authoritative identity, revenue, and margin evidence. Model extraction creates proposals, never approved claims. The company remains excluded until an analyst accepts independently sourced exposure, moat, scenario, and risk claims and all evidence gates pass. See the [production data-source plan](docs/production-data-sources.md) for provider choices, licences, libraries, and the connector roadmap.

## Architecture

```text
Regulatory / IR / project sources
              │
              ▼
Safe acquisition → raw snapshots → normalized evidence package
              │                         │
              ▼                         ▼
Security master                 Evidence ledger
              └──────────────┬──────────┘
                             ▼
              Typed company research graph
    eligibility → evidence → exposure → moat → margin
          → scenarios → risk → skeptic → narrative
                             │
                             ▼
           deterministic score + sensitivity ranking
                             │
                             ▼
             analyst review → publication → diff
```

Agents interpret evidence. Code performs calculations, boundaries, quality gates, ranking, publication authorization, and audit persistence.

## Repository map

```text
config/                     Versioned taxonomy, policies, prompts
deployment/                 Quarterly CronJob and deployment notes
docs/                       Architecture and operating specifications
src/aifactory/agents/       Specialized agent contracts
src/aifactory/web/          Analyst review workbench
src/aifactory/api.py        FastAPI application
src/aifactory/database.py   Evidence ledger and audit database
src/aifactory/ingestion.py  Safe source and SEC ingestion
src/aifactory/scoring.py    Deterministic TAFGS engine
src/aifactory/service.py    End-to-end application service
src/aifactory/workflow.py   LangGraph/local state graph
tests/                      Unit, security, and end-to-end tests
```

## Documentation

- [Architecture](docs/architecture.md)
- [Production data sources and connector plan](docs/production-data-sources.md)
- [Data contracts](docs/data-contracts.md)
- [Scoring methodology](docs/scoring-methodology.md)
- [Agent and prompt design](docs/agents-and-prompts.md)
- [Evaluation and security](docs/evaluation-and-security.md)
- [Operations and quarterly refresh](docs/operations.md)
- [Deployment notes](deployment/README.md)

## Production boundaries

SQLite is intentionally used for a reproducible single-node deployment. The real connectors, raw snapshots, lineage, model proposal gate, and scoring workflow operate locally today. Move checkpoints, evidence, reviews, and rankings to PostgreSQL before horizontally scaling API replicas. Store raw documents in versioned object storage, put long-running runs behind Temporal, integrate organisation SSO/RBAC, and complete legal review for every licensed data source.

The bundled UI/API is a complete reference surface, not a claim of institutional investment-compliance certification.
