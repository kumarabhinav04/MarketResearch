export type Status = 'implemented' | 'planned' | 'boundary';

export const navItems = [
  ['overview', 'System overview'],
  ['problem', 'Problem & scope'],
  ['architecture', 'Architecture'],
  ['taxonomy', 'Capital-stack taxonomy'],
  ['sources', 'Data sources'],
  ['ingestion', 'Ingestion & lineage'],
  ['extraction', 'Evidence extraction'],
  ['agents', 'Agent network'],
  ['workflow', 'Workflow design'],
  ['scoring', 'Scoring & ranking'],
  ['storage', 'Storage model'],
  ['interfaces', 'API & CLI'],
  ['user-stories', 'User stories'],
  ['guardrails', 'Guardrails'],
  ['telemetry', 'Telemetry'],
  ['evaluation', 'Evaluation & testing'],
  ['operations', 'Operations & deployment'],
  ['implementation', 'Implementation map'],
  ['limitations', 'Boundaries & roadmap'],
] as const;

export const principles = [
  ['Point-in-time by construction', 'Every run freezes an as-of date. Later evidence is excluded rather than silently leaking into a historical result.'],
  ['Evidence before judgment', 'Agents see normalized, cited claims—not unrestricted browsing context or an unbounded research lake.'],
  ['Workflow before autonomy', 'A typed graph fixes the order, state, tool boundary, retry behavior, and stopping condition.'],
  ['Code owns numbers', 'Margins, exposure conversion, risk discounts, TAFGS, scenario ranks, confidence, and release gates are deterministic.'],
  ['Confidence is not quality', 'Source confidence controls evidence fitness; it never substitutes for moat, margin, growth, or risk.'],
  ['Retrieved text is untrusted', 'Documents are treated as data, scanned for prompt injection, and never allowed to issue instructions.'],
  ['Humans authorize evidence and release', 'Model extractions remain proposals and ranked dossiers remain unpublished until reviewed.'],
  ['Reproducibility over mutation', 'Each run and report has a configuration snapshot, version set, evidence IDs, and output hash.'],
] as const;

export const valueChain = [
  { id: 'compute_servers', layer: 'Compute & servers', spend: '$48.750B', share: '71.225%', subsegments: 'Accelerators, CPU, HBM, AI servers, storage' },
  { id: 'networking', layer: 'Networking', spend: '$8.385B', share: '12.251%', subsegments: 'Switches, NIC/DPU, InfiniBand, Ethernet, optics, cabling' },
  { id: 'power', layer: 'Power infrastructure', spend: '$6.630B', share: '9.686%', subsegments: 'Generation, transformers, switchgear, UPS, PDU/busway, generators, storage' },
  { id: 'construction', layer: 'Engineering & construction', spend: '$2.535B', share: '3.703%', subsegments: 'Design, general contracting, commissioning, modular construction' },
  { id: 'cooling', layer: 'Cooling systems', spend: '$2.145B', share: '3.134%', subsegments: 'Liquid cooling, CDU, chillers, cooling towers, CRAH, heat rejection' },
] as const;

export const sourceRows: Array<{ name: string; category: string; auth: string; tier: string; status: Status; role: string; operational: string }> = [
  { name: 'SEC EDGAR', category: 'Regulatory filings', auth: 'No key; declared contact User-Agent', tier: '1', status: 'implemented', role: 'Universe, CIK/ticker identity, submissions, filing HTML, Company Facts XBRL, deterministic revenue and margin.', operational: 'Live-verified; bounded to 8 req/s in catalog.' },
  { name: 'GLEIF Global LEI Index', category: 'Entity identity', auth: 'None', tier: '1', status: 'implemented', role: 'Exact legal-name search, fuzzy completion fallback, canonical record fetch, LEI persistence above 0.82 configured threshold.', operational: 'Live-verified with exact normalized-name match.' },
  { name: 'GDELT DOC 2.0', category: 'News discovery', auth: 'None', tier: '3', status: 'implemented', role: 'Topical company/news discovery; stores article metadata and URLs only. Never sole support for a material fact.', operational: 'Adapter works fail-closed; last host smoke returned invalid JSON/provider timeout.' },
  { name: 'USAspending.gov', category: 'Government awards', auth: 'None', tier: '1', status: 'planned', role: 'Contract and recipient discovery after public-parent resolution.', operational: 'Catalogued and disabled; connector not implemented.' },
  { name: 'OpenFIGI', category: 'Security identity', auth: 'Optional API key', tier: '2', status: 'planned', role: 'FIGI/security mapping and share-class normalization.', operational: 'Catalogued and disabled pending adapter and redistribution review.' },
  { name: 'UK Companies House', category: 'Regulatory filings', auth: 'API key', tier: '1', status: 'planned', role: 'UK legal entities, profiles, filing history and official documents.', operational: 'Catalogued and disabled.' },
  { name: 'filings.xbrl.org', category: 'ESEF/UKSEF index', auth: 'None', tier: '1', status: 'planned', role: 'European structured filing discovery with national OAM validation for material facts.', operational: 'Catalogued and disabled.' },
  { name: 'Japan EDINET v2', category: 'Regulatory filings', auth: 'Subscription key', tier: '1', status: 'planned', role: 'Official Japanese disclosure documents and structured reports.', operational: 'Catalogued and disabled.' },
  { name: 'U.S. EIA v2', category: 'Power market', auth: 'Free API key', tier: '1', status: 'planned', role: 'Electricity, generation, price, fuel and capacity context.', operational: 'Catalogued and disabled.' },
  { name: 'USPTO PatentsView', category: 'Patents', auth: 'API key', tier: '2', status: 'planned', role: 'Patent and assignee evidence; counts alone may not determine a moat.', operational: 'Catalogued and disabled.' },
];

export const sourceTiers = [
  ['Tier 1 · authoritative', '1.00', 'Regulator, company-primary, government or official project record. Required for reported financial metrics.'],
  ['Tier 2 · specialist', '0.80', 'Licensed transcript, standards body, technical document or utility record.'],
  ['Tier 3 · discovery', '0.45', 'Reputable news, industry publication or analyst discovery. Cannot be sole support for a material numeric claim.'],
] as const;

export const agents = [
  { name: 'Eligibility Agent', key: 'eligibility', owns: 'Public-security eligibility, segment assignment, security-master completeness.', inputs: 'Company/security master.', output: 'eligible flag and validation errors.', guard: 'Fails eligibility when exchange or security ID is absent.' },
  { name: 'Evidence Agent', key: 'evidence', owns: 'Evidence inventory, tier-weighted confidence, contradiction warning.', inputs: 'All as-of eligible claims.', output: 'claim IDs, mean evidence confidence, warnings.', guard: 'Adds a validation error when no eligible evidence exists.' },
  { name: 'Exposure Agent', key: 'exposure', owns: 'Current fraction of issuer revenue directly exposed to AI-factory spend.', inputs: 'Best non-contradictory ai_exposure claim.', output: 'Exposure ratio in [0,1].', guard: 'Does not infer missing exposure.' },
  { name: 'Moat Agent', key: 'moat', owns: 'Six independently evidenced defensibility components.', inputs: 'Six moat claim types and versioned weights.', output: 'Component map and weighted 0–5 moat score.', guard: 'Missing or out-of-range components make the assessment invalid.' },
  { name: 'Margin Agent', key: 'margin', owns: 'Reported operating margin and rubric bucket.', inputs: 'Best Tier-1 operating-margin claim.', output: 'Margin percent and score 1–5.', guard: 'Tier 1 is mandatory; negative margins are warned.' },
  { name: 'Growth Forecast Agent', key: 'growth_forecast', owns: 'Bear/base/bull exposed-business CAGR and company-wide conversion.', inputs: 'Exposure plus three scenario claims.', output: 'ScenarioForecast with segment and company CAGRs.', guard: 'Requires bear ≤ base ≤ bull and a complete three-scenario set.' },
  { name: 'Risk Agent', key: 'risk', owns: 'Six risk-severity components and capped discount.', inputs: 'Six risk claims and versioned weights.', output: 'Component map and 0–35% discount.', guard: 'Missing/out-of-range components fail scoring.' },
  { name: 'Skeptic Auditor', key: 'skeptic_auditor', owns: 'Falsification, required-claim coverage, conflict and threshold gates.', inputs: 'Full assessment, claims and policy.', output: 'Citation coverage, errors, rankable decision.', guard: 'Only this step calls final deterministic scoring, and only with no validation errors.' },
  { name: 'Narrative Agent', key: 'narrative', owns: 'Investor-readable role, catalysts, moat and risk narrative.', inputs: 'Approved dossier only.', output: 'Evidence template or structured model JSON.', guard: 'Model failure falls back to evidence template; it cannot change numeric scores.' },
] as const;

export const workflowSteps = [
  ['Bootstrap', 'Settings load `.env` without overriding process-level values; directories are created; SQLite schema and WAL are initialized.'],
  ['Freeze configuration', 'Taxonomy, scoring, source, extraction and prompt versions load; the run persists a scoring manifest and selected company IDs.'],
  ['Select universe', 'Only eligible companies participate; requested unknown or ineligible IDs stop the run.'],
  ['Create run', 'Run starts as created, then running; the as-of date cannot be in the future.'],
  ['Fan out', 'A bounded thread pool runs one company workflow per eligible issuer.'],
  ['Sequential company graph', 'Eligibility → evidence → exposure → moat → margin → growth → risk → skeptic → narrative.'],
  ['Isolate failures', 'A company exception creates a non-rankable assessment; other companies continue.'],
  ['Fan in and rank', 'Rankable assessments are sorted by risk-adjusted base TAFGS; bear/bull ranks and confidence are computed.'],
  ['Persist and evaluate', 'Assessments, rankings and audit events are stored; reproducibility and quality gates can be recomputed.'],
  ['Review and publish', 'Analysts review ranked dossiers. Publication fails until every ranked company is approved.'],
] as const;

export const moatWeights = [
  ['Architectural lock-in', '22%'], ['Switching costs', '18%'], ['Standards & IP', '18%'], ['Ecosystem & design wins', '18%'], ['Bottleneck scarcity', '14%'], ['Competitive defensibility', '10%'],
] as const;

export const riskWeights = [
  ['Customer concentration', '20%'], ['Cyclicality', '15%'], ['Execution', '20%'], ['Supply chain', '15%'], ['Geopolitical / regulatory', '15%'], ['Commoditization', '15%'],
] as const;

export const marginBands = [
  ['> 40%', '5'], ['30%–40%', '4'], ['20%–<30%', '3'], ['10%–<20%', '2'], ['< 10%', '1'],
] as const;

export const tables = [
  ['companies', 'Security universe, public-parent link, eligibility, segment/subsegment and metadata.'],
  ['market_segments', 'Versioned capital-stack taxonomy, reference spend, seed weight, assumptions and validation flag.'],
  ['source_documents', 'Publisher, source tier, URL, dates, SHA-256, raw path, licence, parser, injection flags and metadata.'],
  ['evidence_claims', 'Atomic fact/estimate with value, unit, period, exact span, section, confidence, contradiction and extraction method.'],
  ['entity_identifiers', 'CIK, ticker, LEI and future schemes with source, confidence and metadata.'],
  ['source_cursors', 'Incremental state per source and scope: ETag, Last-Modified, accession, last seen or last checked.'],
  ['source_sync_runs', 'Every connector attempt with status, cursor transition, counters, error, start and completion times.'],
  ['claim_proposals', 'Pending/invalid/accepted/rejected model proposals, validation errors, prompt/model versions and reviewer decision.'],
  ['research_runs', 'As-of date, lifecycle status, taxonomy/scoring/prompt/model versions and frozen configuration snapshot.'],
  ['company_assessments', 'Full structured dossier plus rankability, review status, confidence, coverage and scores.'],
  ['rankings', 'Base rank, bear rank, bull rank, risk-adjusted score and rank confidence.'],
  ['reviews', 'Analyst decision, comment, explicit overrides and timestamp per run/company.'],
  ['audit_events', 'Append-only actor, event type and JSON payload scoped to run/company.'],
] as const;

export const proposalControls = [
  ['Retrieval budget', '6,000-character chunks, 500-character overlap, top 8 keyword-relevant chunks.'],
  ['Generation budget', 'Maximum 8 proposals per document and 2,400 completion tokens for extraction.'],
  ['Allowed semantics', 'Only the 19 configured qualitative/forecast claim definitions; financial claims remain deterministic XBRL.'],
  ['Quote entailment proxy', '20–600 character exact contiguous substring from the cited chunk; unknown chunk IDs fail.'],
  ['Numeric contract', 'Finite numeric value, configured range, exact configured unit; narrative types forbid numeric values.'],
  ['Confidence', 'Finite value between 0 and 0.90; model certainty is intentionally capped.'],
  ['Time contract', 'Document must belong to the issuer and be published on/before cutoff; period end must be ISO date or null.'],
  ['Human gate', 'Valid proposals are pending, never claims. Acceptance creates a deterministic UUID claim and a permanent audit event.'],
] as const;

export const apiEndpoints = [
  ['GET', '/', 'Unprotected local analyst workbench HTML.'],
  ['GET', '/health', 'Liveness response.'],
  ['GET', '/ready', 'Database readiness; returns 503 on failure.'],
  ['GET', '/metrics', 'In-memory Prometheus text exposition.'],
  ['GET', '/api/v1/config/segments', 'Capital-stack segments.'],
  ['GET', '/api/v1/companies', 'Universe; optional eligible-only filter.'],
  ['GET', '/api/v1/companies/{company_id}', 'Company, source documents and entity identifiers.'],
  ['GET', '/api/v1/sources', 'Public connector capability and credential-readiness metadata—never credential values.'],
  ['GET', '/api/v1/source-syncs', 'Connector run history.'],
  ['POST', '/api/v1/sources/{source_id}/sync', 'Run allow-listed source sync in a worker thread.'],
  ['POST', '/api/v1/evidence/extract', 'Create review-only model proposals.'],
  ['GET', '/api/v1/evidence/proposals', 'Filter proposal ledger by company/status.'],
  ['POST', '/api/v1/evidence/proposals/{id}/review', 'Accept or reject one pending proposal.'],
  ['POST', '/api/v1/demo/seed', 'Load the clearly synthetic 20-company fixture.'],
  ['POST', '/api/v1/runs', 'Start a point-in-time research run.'],
  ['GET', '/api/v1/runs', 'List recent runs.'],
  ['GET', '/api/v1/runs/{run_id}', 'Run metadata and configuration snapshot.'],
  ['GET', '/api/v1/runs/{run_id}/rankings', 'Ordered ranking output.'],
  ['GET', '/api/v1/runs/{run_id}/assessments', 'All company dossiers for a run.'],
  ['GET', '/api/v1/runs/{run_id}/assessments/{company_id}', 'One dossier.'],
  ['POST', '/api/v1/runs/{run_id}/assessments/{company_id}/reviews', 'Record analyst review and optional override metadata.'],
  ['POST', '/api/v1/runs/{run_id}/publish', 'Apply release gate, mark published and regenerate report/manifest.'],
  ['POST / GET', '/api/v1/runs/{run_id}/report', 'Generate or download Markdown report.'],
  ['GET', '/api/v1/runs/{run_id}/audit', 'Persistent audit history.'],
  ['GET', '/api/v1/runs/{run_id}/evaluation', 'Deterministic quality and release gates.'],
  ['GET', '/api/v1/runs/{previous}/compare/{current}', 'Rank entry/exit, movement and score deltas.'],
] as const;

export const cliGroups = [
  ['Initialize & demo', 'init-db · seed-demo · reset-demo · approve-ranked-demo'],
  ['Sources', 'source-list · source-syncs · source-sync · ingest-sec'],
  ['Evidence', 'ingest · extract-evidence · list-proposals · review-proposal'],
  ['Research', 'run · quarterly-refresh · list-runs · list-companies · show-run'],
  ['Governance', 'review · evaluate · compare-runs · generate-report · publish'],
  ['Runtime', 'model-check · serve'],
] as const;

export const userStories = [
  { actor: 'Research analyst', need: 'Produce a defensible Top 20 at a chosen cutoff.', journey: 'Sync issuer evidence → inspect documents → run extraction → accept/reject proposals → execute run → review every ranked dossier → publish.' },
  { actor: 'Data steward', need: 'Onboard a source without leaking keys or weakening evidence standards.', journey: 'Add a disabled catalog entry → implement allow-listed adapter → archive raw response → add fixtures and lineage tests → complete legal/security review → enable.' },
  { actor: 'Methodology owner', need: 'Change weights or thresholds without silent rank drift.', journey: 'Version the policy → run frozen benchmark → generate rank diff → inspect sensitivity → approve configuration release.' },
  { actor: 'Platform operator', need: 'Know whether a quarterly run is healthy.', journey: 'Inspect sync history, JSON logs, counters, duration summaries and failed company dossiers; re-run creates new history rather than rewriting old results.' },
  { actor: 'Model-risk reviewer', need: 'Verify that the LLM cannot manufacture a score.', journey: 'Review prompt/schema version, exact-quote failures, invalid proposals and acceptance audit; confirm arithmetic and rank paths are model-free.' },
  { actor: 'Auditor', need: 'Reproduce a published result.', journey: 'Open report manifest → resolve run/config versions → inspect evidence claim IDs and source hashes → recompute scores → match report SHA-256.' },
] as const;

export const guardrails = [
  ['Network egress', 'HTTPS-only source URLs; DNS resolution rejects private, loopback, link-local and reserved addresses; every redirect is revalidated; maximum six redirects.'],
  ['Model endpoint', 'External gateways must use HTTPS. Plain HTTP is allowed only for localhost/loopback Ollama.'],
  ['Credentials', 'Environment variables only; `.env` does not override runtime variables; secret values do not enter workflow state, source metadata, raw manifests or audit events.'],
  ['Connector authority', 'Catalog values choose only from a code-owned adapter registry; disabled or unimplemented sources fail closed.'],
  ['Transport bounds', 'Per-source request rate, timeout, response-size limit, safe response-header allow list, retry/backoff and retry cap of eight.'],
  ['Prompt injection', 'Known patterns are flagged; system prompts explicitly treat filings/web pages as quoted untrusted data and forbid tool instructions.'],
  ['Evidence integrity', 'Exact quote, source tier, period, unit, numeric range, contradiction marker, document ownership and cutoff checks.'],
  ['Point-in-time', 'Future run dates are rejected; document and XBRL filing dates must be on/before the run cutoff.'],
  ['Financial authority', 'Reported revenue and operating margin require Tier-1 evidence; margin is calculated from matching-period XBRL facts.'],
  ['Scoring safety', 'Finite/range checks, complete component sets, ordered scenarios and deterministic calculations. Missing inputs make the issuer non-rankable.'],
  ['Human control', 'Model proposals require evidence-level acceptance; every ranked company requires dossier approval before publication.'],
  ['Operational isolation', 'One company failure cannot terminate the entire portfolio run; it is persisted as non-rankable with the exception type.'],
] as const;

export const telemetry = [
  ['JSON logs', 'timestamp, level, logger, message, run_id, company_id; optional event, agent, duration_ms, status and exception. Context variables propagate run/company correlation.'],
  ['Timed operations', 'Source fetch, complete research run and every agent invocation record duration and error counters. Agent step logs are debug; run/source events are info.'],
  ['Counters', 'Source fetch/retry, sync complete/fail, prompt-injection flags, per-agent executions, company workflow failures and research run complete/fail.'],
  ['Prometheus endpoint', '`GET /metrics` renders process-local counters and summary count/sum values with `aifactory_` names.'],
  ['Persistent audit', 'Source sync, ingestion, extraction, proposal review, run lifecycle, company assessment, analyst review and publication events survive process restart in SQLite.'],
  ['Current boundary', 'Metrics are in-memory and unlabelled; `AIFACTORY_OTEL_ENDPOINT` and optional packages are declared, but an OTLP exporter is not wired in this reference implementation.'],
] as const;

export const evaluationMetrics = [
  ['Assessment and ranked counts', 'Confirms breadth and nonempty output.'],
  ['Rankable rate', 'Share of assessed issuers that cleared all evidence and scoring gates.'],
  ['Evidence confidence', 'Mean tier-adjusted evidence confidence.'],
  ['Citation coverage', 'Mean coverage across required financial, exposure, scenario, moat and risk claim types.'],
  ['Score reproducibility', 'Recomputes stored risk-adjusted TAFGS and requires exact tolerance ≤ 1e-9.'],
  ['Unsupported required claims', 'Counts validation messages indicating missing/lacking evidence.'],
  ['Scenario rank stability', 'Measures bear-to-bull rank spread.'],
  ['Approval coverage', 'Share of ranked companies with approved dossier review.'],
] as const;

export const configFiles = [
  ['taxonomy.json', '2026.09.01', 'Capital-stack layers, reference spend, seed weights and subsegments.'],
  ['sources.json', '1.0.0', 'Source URLs, adapter IDs, status, auth references, rate/size/time limits, endpoints, licence notes and options.'],
  ['source_policy.json', '1.0.0', 'Evidence tiers, weights, financial authority, allowed schemes and blocked networks.'],
  ['scoring_policy.json', '1.0.0', 'Margin bands, moat/risk weights, 35% max discount, confidence/coverage gates and Top-20 size.'],
  ['extraction_policy.json', '1.0.0', 'Chunking, proposal budgets, quote/confidence limits, allowed claims, keywords, units and ranges.'],
  ['prompts/*.txt', '1.0.0 run field', 'Common untrusted-evidence contract and role-specific extraction/growth/moat/skeptic instructions.'],
] as const;

export const moduleMap = [
  ['config.py', 'Environment loading, typed settings, paths and JSON policy access.'],
  ['security.py', 'Prompt-injection signatures, HTTPS/DNS SSRF validation and redaction helper.'],
  ['telemetry.py', 'Context-correlated JSON logging, counters, durations and Prometheus rendering.'],
  ['models.py', 'Enums and typed evidence, forecast, assessment and ranking contracts.'],
  ['database.py', 'SQLite/WAL schema, transactions and repositories for all 13 tables.'],
  ['sources/catalog.py', 'Validated, versioned source definitions and secret-safe public capability view.'],
  ['sources/http.py', 'Bounded HTTPS transport, auth injection, redirects, retries, rate limiting and response caps.'],
  ['sources/storage.py', 'SHA-256 content-addressed raw snapshots, manifests and normalized text.'],
  ['sources/service.py', 'Allow-listed SEC, GLEIF and GDELT adapters, sync state, archival and audit.'],
  ['ingestion.py', 'Normalized evidence-package contract and legacy SEC/XBRL compatibility path.'],
  ['extraction.py', 'Chunk retrieval, structured model proposals, deterministic validation and analyst conversion to claims.'],
  ['llm.py', 'Offline, OpenAI-compatible and Ollama gateways; zero temperature, JSON contract and endpoint validation.'],
  ['agents/roles.py', 'Nine bounded research roles and fail-closed assessment gates.'],
  ['workflow.py', 'Typed sequential LangGraph and dependency-free local graph fallback.'],
  ['scoring.py', 'Exposure conversion, margins, weights, risk discount, TAFGS, ranks and stability.'],
  ['service.py', 'Composition root, parallel portfolio supervisor, review and publication gate.'],
  ['evaluation.py', 'Reproducibility/quality gates and run-to-run rank diff.'],
  ['reporting.py', 'Investor-style Markdown output and SHA-256 reproducibility manifest.'],
  ['api.py', 'FastAPI schemas, header-key reference auth, endpoints and background thread handoff.'],
  ['cli.py', 'Operational command surface and bounded argument validation.'],
  ['web/index.html', 'Dependency-free local analyst workbench.'],
  ['demo.py', 'Twenty-company synthetic evidence fixture; explicitly marked demo.'],
] as const;

export const runtimeDependencies = [
  ['Base runtime', 'FastAPI, Uvicorn, LangGraph, HTTPX, Certifi, BeautifulSoup, lxml, python-dateutil, Tenacity.'],
  ['Production extra', 'Psycopg, SQLAlchemy, Alembic, Boto3, Temporal, Redis, DuckDB, Polars and pgvector.'],
  ['Telemetry extra', 'OpenTelemetry API, SDK and OTLP HTTP exporter.'],
  ['Recommended parser additions', 'Arelle, pypdf/pdfplumber, Trafilatura, OpenPyXL, RapidFuzz, Playwright and OCRmyPDF/Tesseract—only when corresponding connectors are implemented.'],
] as const;

export const environmentSettings = [
  ['AIFACTORY_ENV', 'Runtime environment label used in logs and health context.', 'development'],
  ['AIFACTORY_DB_PATH', 'SQLite database path for the reference deployment.', 'data/aifactory.db'],
  ['AIFACTORY_CONFIG_DIR', 'Directory containing versioned taxonomy, source, scoring and extraction policies.', 'config'],
  ['AIFACTORY_REPORT_DIR', 'Generated reports and reproducibility manifests.', 'artifacts/reports'],
  ['AIFACTORY_RAW_SOURCE_DIR', 'Content-addressed raw, normalized and manifest snapshots.', 'artifacts/raw-sources'],
  ['AIFACTORY_API_KEY', 'Optional X-API-Key value for the reference API boundary.', 'Secret; no value is logged or persisted'],
  ['AIFACTORY_LOG_LEVEL', 'Structured application log threshold.', 'INFO'],
  ['AIFACTORY_MAX_WORKERS', 'Bounded portfolio-level company concurrency.', '4'],
  ['AIFACTORY_MIN_EVIDENCE_CONFIDENCE', 'Environment-level evidence threshold available to runtime policy.', '0.60'],
  ['AIFACTORY_MODEL_PROVIDER', 'Model gateway selection: offline, OpenAI-compatible or Ollama.', 'offline'],
  ['AIFACTORY_MODEL_NAME', 'Provider model identifier; the assignment can target an OpenRouter-hosted Nemotron model.', 'Provider-specific'],
  ['AIFACTORY_MODEL_BASE_URL', 'OpenAI-compatible gateway base URL or local Ollama endpoint.', 'Provider-specific'],
  ['AIFACTORY_MODEL_API_KEY', 'Gateway credential read only at request time.', 'Secret; environment only'],
  ['AIFACTORY_MODEL_TIMEOUT_SECONDS', 'Bounded model request timeout.', '60'],
  ['AIFACTORY_MODEL_MAX_COMPLETION_TOKENS', 'Hard completion ceiling used by the model gateway.', '2400'],
  ['AIFACTORY_MODEL_REASONING_EFFORT', 'Optional provider-supported reasoning effort.', 'Unset'],
  ['AIFACTORY_OTEL_ENDPOINT', 'Reserved collector endpoint for the planned OTLP exporter.', 'Unset; exporter not wired'],
  ['SEC_USER_AGENT', 'Required declared contact identity for SEC fair-access requests.', 'Operator-configured'],
  ['Source-specific key variables', 'Optional keys referenced by sources.json, such as OpenFIGI, EDINET, EIA or PatentsView.', 'Only required when its disabled adapter is implemented and enabled'],
] as const;

export const failureSemantics = [
  ['Source retrieval', 'Retry bounded failures; persist failed sync, unchanged cursor and sanitized error. Raw evidence is preserved if already archived.'],
  ['Parser / model', 'Fail the document proposal operation; invalid model output is retained as invalid and cannot be accepted.'],
  ['Company workflow', 'Persist a non-rankable assessment and continue other companies.'],
  ['Scoring', 'Fail closed for non-finite, out-of-range, missing or unordered inputs.'],
  ['Publication', 'Return conflict until every ranked company is approved.'],
  ['Rerun', 'Create a new immutable run; never rewrite a historical ranking to hide a correction.'],
] as const;

export const boundaries = [
  ['Valuation is absent', 'TAFGS ranks fundamental growth exposure, not expected equity return, fair value, entry point or trading signal.'],
  ['Global coverage is incomplete', 'SEC/GLEIF/GDELT are implemented. UK/EU/Japan, power, government-award and patent connectors remain disabled plans.'],
  ['PDF parsing is explicit opt-in', 'The extractor rejects PDFs until a page-aware parser is installed and implemented.'],
  ['Storage is single-node', 'SQLite/WAL and local raw artifacts are real and reproducible, but not safe for multiple concurrent writer replicas.'],
  ['Auth is a reference control', 'The API uses one X-API-Key; production requires SSO, RBAC, audit identity and secret-manager integration.'],
  ['Observability is local', 'Prometheus text and persistent audit exist; OTLP export, distributed traces and durable metric storage are not yet connected.'],
  ['Outer orchestration is not durable', 'ThreadPoolExecutor and CronJob are implemented; Temporal is declared for future retryable distributed jobs.'],
  ['Overrides are recorded, not recalculated', 'Review override JSON is auditable metadata; there is no separate deterministic override-recalculation engine.'],
] as const;

export const officialLinks = [
  ['SEC EDGAR APIs', 'https://www.sec.gov/search-filings/edgar-application-programming-interfaces'],
  ['SEC developer and fair-access resources', 'https://www.sec.gov/about/developer-resources'],
  ['GLEIF API', 'https://www.gleif.org/en/lei-data/gleif-api'],
  ['GDELT DOC 2.0', 'https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/'],
  ['USAspending endpoints', 'https://api.usaspending.gov/docs/endpoints'],
  ['OpenFIGI documentation', 'https://www.openfigi.com/api/documentation'],
  ['Companies House API', 'https://developer.company-information.service.gov.uk/'],
  ['filings.xbrl.org API', 'https://filings.xbrl.org/docs/api'],
  ['EIA API v2', 'https://www.eia.gov/opendata/documentation.php'],
  ['PatentsView API', 'https://search.patentsview.org/docs/docs/Search%20API/SearchAPIReference/'],
  ['OpenRouter API', 'https://openrouter.ai/docs/quickstart'],
] as const;
