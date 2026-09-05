# Production data-source and connector plan

## What the platform must know

The system is not trying to predict a share price. For each public issuer, at a frozen research date, it must prove five things:

1. The security and public parent are correctly identified.
2. The issuer earns, or can plausibly earn, revenue from a defined layer of the AI-factory capital stack.
3. The claimed exposure, differentiation, margins, growth drivers, and risks are supported by dated evidence.
4. Calculations are reproducible from accepted claims and a versioned scoring policy.
5. An analyst can see the source, exact quote, period, unit, parser, model, and decision behind every material input.

No source supplies all five. The production design therefore uses a source portfolio, keeps discovery separate from evidence, and makes missing evidence visible instead of filling it with model guesses.

## Data flow implemented in this repository

```text
Versioned source catalog
        │
        ▼
bounded connector → immutable raw snapshot → normalized source document
        │                                           │
        ├── deterministic XBRL facts ───────────────┤
        │                                           ▼
        └── relevant text chunks → LLM proposals → analyst accept/reject
                                                    │
                                                    ▼
                                      approved evidence-claim ledger
                                                    │
                                                    ▼
                                 research graph → deterministic rank → review
```

URLs, endpoints, authentication references, rate limits, response limits, timeouts, source tier, and source-specific options live in `config/sources.json`. Secrets live only in environment variables. Company candidates come from source universes and entity resolution; they are not embedded in application code.

### Implemented now

| Source | Purpose | Authentication | What the connector stores | Scoring authority |
|---|---|---|---|---|
| SEC EDGAR | U.S. issuer universe, submissions, filings, XBRL company facts | None; declared contact `User-Agent` required | Raw responses, filing text, CIK/ticker identity, revenue and operating-margin facts | Tier 1 for reported U.S. financials |
| GLEIF Global LEI Index | Legal-entity identity and LEI mapping | None | Raw match response, normalized identity document, accepted LEI mapping above configured name threshold | Tier 1 for identity, not investment claims |
| GDELT DOC 2.0 | News and event discovery | None | Result metadata and URLs only | Tier 3 discovery; never sole support for material financial facts |

The live connector is selected from an allow-listed registry. A catalog entry cannot cause arbitrary code execution. External URLs must be HTTPS, DNS-resolve to public addresses, remain safe across redirects, respect configured size/rate/retry boundaries, and return only allow-listed response headers to the application. Credentials are applied just before transport and are not included in returned metadata, raw manifests, logs, or audit events.

### Catalogued but disabled until its connector and governance review are complete

| Source | Value | Key | Recommended use |
|---|---|---|---|
| USAspending.gov | U.S. federal awards and recipients | No | Contract discovery and corroboration; resolve recipient to public parent before use |
| OpenFIGI | FIGI/security mapping | Optional for low-rate public use; key for higher limits | Map listing identifiers after LEI/CIK resolution; review redistribution terms |
| UK Companies House | Company profiles and filing history | Yes | UK issuer identity and official filing discovery |
| filings.xbrl.org | ESEF/UKSEF filing index | No | European structured-filing discovery; validate material facts against national official records |
| Japan EDINET API v2 | Official Japanese disclosure documents | Yes | Japanese filings and structured reports |
| U.S. EIA API v2 | Electricity, generation, price, fuel, and capacity data | Yes, free | Power-market context; do not attribute a project to a company without project evidence |
| USPTO PatentsView PatentSearch | Patent records and assignees | Yes | Moat research input; patent counts alone never determine a moat score |

`implementation_status: planned` and `enabled: false` are deliberate fail-closed settings. Adding a URL to the catalog does not make a source production-ready.

## Recommended source portfolio by research question

### 1. Public universe and entity resolution

Use regulatory universes first, then map identifiers:

- SEC company ticker/exchange universe and CIK for U.S. reporting issuers.
- GLEIF for legal names, LEIs, headquarters jurisdiction, and parent relationships.
- OpenFIGI or an exchange/licensed security master for FIGI, ISIN, SEDOL, exchange ticker, share class, ADR, and primary-listing mapping.
- Companies House for UK legal entities; EDINET for Japan; ESEF/national Officially Appointed Mechanisms for Europe.
- A commercial global security master—LSEG, FactSet, S&P Capital IQ, Bloomberg, Morningstar, or ICE—when global point-in-time corporate actions and symbology are required.

Required controls are effective dates, public-parent mapping, share-class deduplication, ADR/primary-listing choice, ticker history, mergers/spin-offs, and analyst review of ambiguous matches. A fuzzy name match can propose an identifier; it cannot silently merge issuers.

### 2. Reported financials and margin quality

Preferred order:

1. Official XBRL facts and statements from the regulator.
2. The issuer's audited annual report when tag selection or segment interpretation is ambiguous.
3. Licensed normalized fundamentals for coverage/QA, reconciled back to the filing.

SEC Company Facts can support reported revenue and operating margin, but issuer-specific extension tags, restatements, fiscal calendars, acquisitions, discontinued operations, and GAAP/IFRS differences require validation. Production normalization should add Arelle for taxonomy-aware XBRL validation and a filing-period selection test suite.

Commercial normalization options include FactSet Fundamentals, LSEG Worldscope, S&P Capital IQ, Bloomberg, Morningstar, Intrinio, Financial Modeling Prep, and Financial Datasets. Provider licences must explicitly permit storage, derived values, user display, and report redistribution.

### 3. Direct AI-factory revenue exposure

There is usually no audited tag called “AI-factory revenue.” Build this as an evidence-backed interval from:

- Segment and geographic notes in annual/quarterly filings.
- Earnings releases, investor presentations, capital-markets-day decks, and product revenue disclosures.
- Earnings-call transcripts licensed for machine processing.
- Backlog/RPO, orders, book-to-bill, capacity, and design-win disclosures.
- Customer/project announcements corroborated by both sides where possible.
- Shipment, server, networking, optical, UPS, switchgear, turbine, and cooling market datasets.

Store reported facts separately from estimates. An analyst-approved estimate must preserve the method, low/base/high range, denominator, date, source evidence, and whether exposure is current revenue, orders, backlog, or addressable market. Never equate market share, total addressable market, or customer capex with issuer revenue.

Potential commercial sources include AlphaSense, Tegus, Quartr, FactSet CallStreet, LSEG transcripts, S&P Capital IQ transcripts, Dell'Oro, IDC, Omdia, Synergy Research, 650 Group, LightCounting, TrendForce, SemiAnalysis, and company-specific channel datasets. Their coverage and machine-use rights vary substantially.

### 4. Hyperscaler, sovereign-AI, and project pipeline

Use multiple evidence families:

- Hyperscaler filings and capex guidance from Microsoft, Alphabet, Amazon, Meta, Oracle, and other operators.
- Government procurement: USAspending, SAM.gov, EU TED, UK Contracts Finder, and national procurement portals.
- Power and interconnection: EIA, FERC, ISO/RTO interconnection queues, utility integrated-resource plans, rate cases, and public-service-commission dockets.
- Environmental/building permits, planning-board records, tax-incentive agreements, and municipal agendas.
- Construction awards and engineering-company backlog disclosures.
- Data-center operator announcements, land/power acquisitions, and commissioning milestones.

Project records need a normalized `project` entity with location, owner/operator, campus, power MW, IT MW where disclosed, phase, status, expected energization, suppliers, source dates, and confidence. Announced, permitted, financed, under construction, energized, and cancelled are different states. Avoid summing duplicate phases or marketing announcements.

Commercial project sources can include DC Byte, Structure Research, Baxtel, DatacenterHawk, Industrial Info Resources, ConstructConnect, Dodge Construction Network, Wood Mackenzie, Rystad, Enverus, and power-market specialists. Validate availability and licensing during procurement.

### 5. Moat and differentiation

Evidence should be component-specific:

- Architecture/ecosystem: reference architectures, supported platforms, SDK compatibility, certified designs, developer adoption, and documented installed base.
- Switching costs: qualification cycles, interoperability requirements, redesign effort, maintenance ecosystem, and long-lived installed assets.
- Standards/IP: standards-body contributions, essential patents where substantiated, protocol leadership, and product certification.
- Design wins: named deployments and multi-party confirmation, not anonymous pipeline commentary alone.
- Bottleneck/scarcity: qualified supply capacity, lead times, exclusive access, manufacturing constraints, and credible substitutes.
- Defensibility: competitor performance, price/performance, customer qualification, and loss/churn evidence.

Useful sources include official product documentation, NVIDIA/Microsoft/OCP reference architectures, PCI-SIG, IEEE, IETF, Ultra Ethernet Consortium, UALink Consortium, SNIA, DMTF, JEDEC, Uptime Institute, ASHRAE, patents, and customer/OEM compatibility lists. A model should synthesize these documents; it should not infer a moat from brand recognition.

### 6. Growth scenarios, catalysts, and risks

Construct bear/base/bull AI-segment growth from explicit drivers: unit demand, price/mix, capacity additions, shipment schedule, backlog conversion, project timing, and share assumptions. Record each driver and scenario formula.

Risk evidence comes primarily from filing risk factors, customer concentration notes, export restrictions, supply agreements, litigation/regulatory records, recalls, competitor launches, project cancellations, and historical order volatility. News and social data can trigger investigation but should not directly change a score.

## News, web, and investor-relations acquisition

GDELT is suitable for discovery, not full-text institutional evidence. For a durable system, add:

- RSS/Atom and sitemap discovery for issuer IR and regulator sites.
- A domain allow list, robots/terms review, crawl budgets, canonical URL handling, conditional requests, and content hashes.
- A licensed news/transcript provider for reliable historical retrieval and machine-processing rights.
- Playwright only for approved JavaScript sites when no API/feed exists; browser automation should be isolated from the scoring worker.
- Document parsers that retain page/section coordinates so quotes can be verified in the rendered source.

Do not bypass paywalls, CAPTCHAs, authentication controls, robots restrictions, or contractual prohibitions.

## Libraries and infrastructure

### Installed runtime dependencies

The base package installs:

- `httpx`, `certifi`: HTTPS transport and certificate validation.
- `beautifulsoup4`, `lxml`: controlled HTML/XML parsing.
- `python-dateutil`: dates from heterogeneous filings.
- `tenacity`: available for bounded adapter retry policies.
- `FastAPI`, `uvicorn`: API/workbench.
- `LangGraph`: bounded company workflow.

Install the current runtime with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Production extra already declared

```bash
python -m pip install -e ".[production,otel]"
```

This installs the intended migration stack, but installing it does not switch storage automatically:

| Component | Libraries | Role |
|---|---|---|
| PostgreSQL | `psycopg`, `SQLAlchemy`, `Alembic` | Multi-writer transactional system of record and schema migrations |
| Object storage | `boto3` with S3 or MinIO | Immutable raw documents, rendered pages, and report artifacts |
| Durable orchestration | `temporalio` | Retryable scheduled ingestion and quarterly workflows |
| Coordination/cache | `redis` | Distributed rate limits, locks, short-lived caches; never authoritative evidence |
| Analytics | `Polars`, `DuckDB` | Batch QA, benchmark analysis, and rank-diff exploration |
| Retrieval | PostgreSQL `pgvector` | Optional semantic candidate retrieval; exact citations and structured claims remain authoritative |
| Telemetry | OpenTelemetry packages | Traces/metrics export without prompt or credential leakage |

Before multiple API or worker replicas, implement the PostgreSQL repository adapter and migrations, the S3/MinIO snapshot adapter, and Temporal activities. SQLite/local files are production-real for one controlled node, not for horizontal writers.

### Recommended parser/evaluation extras to add with their connectors

- `arelle-release`: XBRL taxonomy validation and extension-tag handling.
- `pypdf` plus `pdfplumber`: PDF text, pages, and tables; render pages for quote verification.
- `trafilatura`: boilerplate-aware web extraction for approved IR pages.
- `openpyxl`: regulator/utility spreadsheets that must preserve tab/cell lineage.
- `rapidfuzz`: entity-match candidates; retain thresholds and manual ambiguity review.
- `playwright`: isolated rendering for approved JavaScript-only sources.
- `ocrmypdf`/Tesseract: scanned filings, with OCR confidence and rendered-page review.
- `respx`, `pytest`, and recorded fixtures: connector contract tests without hitting providers during CI.
- `pandera` or `pydantic`: explicit tabular and message contracts at adapter boundaries.

Do not install a large “document AI” framework merely for convenience. Add parsers per supported content type, pin versions, preserve raw bytes, and benchmark extraction quality on real filings.

## Configuration and secret setup

Copy `.env.example` to `.env` and set values locally or in a deployment secret manager. At minimum for SEC scheduled use:

```text
AIFACTORY_SEC_USER_AGENT=Your Organization research-contact@example.com
```

Optional connector credentials are referenced by name in `config/sources.json`:

```text
OPENFIGI_API_KEY=
COMPANIES_HOUSE_API_KEY=
EDINET_API_KEY=
EIA_API_KEY=
PATENTSVIEW_API_KEY=
```

Model credentials use `AIFACTORY_MODEL_API_KEY`. Never put a key in a prompt, source catalog, Python module, Docker image, report, or committed file. Use separate development and production keys, provider spend/rate limits, and immediate rotation after accidental disclosure.

## End-to-end live workflow

```bash
# Inspect connector capability and whether required secret variables are configured.
aifactory source-list

# Build a U.S. public-company universe from the regulator; no ticker list in code.
aifactory source-sync sec_edgar --mode universe --limit 1000

# Ingest one issuer, current filings, XBRL revenue/margin, and identity.
aifactory source-sync sec_edgar --mode company \
  --cik 1045810 \
  --segment compute_servers \
  --subsegment accelerators \
  --as-of-date 2026-09-01 \
  --limit 3

# Resolve a legal entity to a GLEIF LEI.
aifactory source-sync gleif --mode company --company-id COMPANY_ID

# Discover recent topical coverage. This creates source documents, not claims.
aifactory source-sync gdelt --mode company \
  --company-id COMPANY_ID --lookback-days 90 --limit 25

# Ask the configured model for cited, review-only proposals from normalized documents.
aifactory extract-evidence --company-id COMPANY_ID \
  --as-of-date 2026-09-01 --document-limit 3

# Inspect and explicitly accept or reject each proposal.
aifactory list-proposals --company-id COMPANY_ID --status pending
aifactory review-proposal PROPOSAL_ID \
  --decision accepted --reviewer analyst@example.com \
  --comment "Verified quote, period, unit, issuer, and rubric"

# Only accepted claims can participate in the research graph.
aifactory run --as-of-date 2026-09-01 \
  --company-id COMPANY_ID --generate-report
```

The same operations are exposed under `/api/v1/sources`, `/api/v1/source-syncs`, `/api/v1/evidence/*`, and `/api/v1/runs`. Protect the API with organization authentication/RBAC before shared use; the header API key is a reference control.

## How to add a source without hardwiring research data

1. Add a disabled catalog entry with official base URL, endpoint templates, auth environment reference, limits, source tier, licence notes, and options.
2. Define the connector output contract and point-in-time semantics.
3. Implement an allow-listed connector adapter; never dynamically import code from catalog values.
4. Store the unmodified response and manifest before parsing.
5. Add deterministic parser tests with provider fixtures, including corrections, pagination, rate limiting, malformed data, oversized responses, and credential redaction.
6. Add entity-resolution and duplicate-document tests.
7. Decide which outputs are deterministic claims, model proposals, or discovery-only documents.
8. Complete data-owner, legal/licensing, security, and model-processing review.
9. Run the frozen benchmark and rank-diff tests.
10. Change `implementation_status` and enable the source only after the connector passes those gates.

## Data quality and release gates

Every production batch should measure:

- Source availability, latency, HTTP status, retries, and freshness.
- Raw-to-normalized document count and parser failure rate.
- Entity match method, score, ambiguity, and analyst overrides.
- Duplicate/correction detection and document hash changes.
- Exact-quote validation, numeric range/unit/period validation, and proposal rejection reasons.
- Claim coverage by company, research dimension, source tier, and cutoff date.
- Source contradictions and unresolved restatements.
- Score reproducibility, rank sensitivity, analyst approval coverage, and quarter-to-quarter churn.

Fail a company closed when required evidence is absent. Fail publication closed when a ranked dossier is unapproved. Preserve unsuccessful syncs, invalid proposals, rejected claims, and superseded documents as audit records.

## Recommended implementation order

1. Harden the current SEC + GLEIF single-node pilot and replace the SEC placeholder contact with a real address.
2. Add issuer IR RSS/sitemap plus PDF/page-lineage parsing; this unlocks exposure, backlog, catalysts, and risks.
3. Add filings.xbrl.org, Companies House, and EDINET for the chosen global universe.
4. Add OpenFIGI/security-master mapping and corporate-action history.
5. Add EIA, utility/ISO, government-award, and project connectors for independent demand evidence.
6. Procure licensed transcript/news/market datasets after a coverage and machine-use evaluation.
7. Move the evidence ledger to PostgreSQL, raw bytes to S3/MinIO, and outer jobs to Temporal before horizontal scale.
8. Build a point-in-time analyst-labelled benchmark before letting model/provider changes affect production proposals.

Start with sources that change a research decision. More data does not improve the ranking if entity identity, dates, units, source rights, and evidence lineage are weak.

## Official API references

- [SEC EDGAR application programming interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) and [developer/fair-access resources](https://www.sec.gov/about/developer-resources)
- [GLEIF API](https://www.gleif.org/en/lei-data/gleif-api) and [LEI data access/use](https://www.gleif.org/en/lei-data/access-and-use-lei-data)
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- [USAspending API endpoints](https://api.usaspending.gov/docs/endpoints)
- [OpenFIGI API documentation](https://www.openfigi.com/api/documentation)
- [UK Companies House API](https://developer.company-information.service.gov.uk/) and [developer guidelines](https://developer.company-information.service.gov.uk/developer-guidelines/)
- [filings.xbrl.org API](https://filings.xbrl.org/docs/api) and [ESMA electronic reporting resources](https://www.esma.europa.eu/issuer-disclosure/electronic-reporting)
- [Japan EDINET API key/registration information](https://disclosure2.edinet-fsa.go.jp/week0020.aspx)
- [U.S. EIA API v2 documentation](https://www.eia.gov/opendata/documentation.php)
- [USPTO PatentsView PatentSearch API](https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/)
- [OpenRouter API quickstart](https://openrouter.ai/docs/quickstart) and [Nemotron 3.5 Lightning free model page](https://openrouter.ai/nvidia/nemotron-3.5-lightning:free)
