'use client';

import { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Braces,
  CheckCircle2,
  CircleDot,
  ClipboardCheck,
  Cloud,
  Database,
  FileCheck2,
  FileSearch,
  Fingerprint,
  GitBranch,
  Globe2,
  HardDrive,
  Layers3,
  LockKeyhole,
  Network,
  PlayCircle,
  Radar,
  RefreshCcw,
  Search,
  Server,
  ShieldCheck,
  UserCheck,
  Waypoints,
  XCircle,
  Zap,
} from 'lucide-react';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  agents,
  apiEndpoints,
  boundaries,
  cliGroups,
  configFiles,
  evaluationMetrics,
  environmentSettings,
  failureSemantics,
  guardrails,
  marginBands,
  moatWeights,
  moduleMap,
  navItems,
  officialLinks,
  principles,
  proposalControls,
  riskWeights,
  runtimeDependencies,
  sourceRows,
  sourceTiers,
  tables,
  telemetry,
  userStories,
  valueChain,
  workflowSteps,
} from '@/lib/documentation';

const allSearchText = navItems.map(([, label]) => label).join(' ');

export function DocsPortal() {
  const [query, setQuery] = useState('');
  const normalizedQuery = query.trim().toLowerCase();
  const statusText = useMemo(
    () => normalizedQuery ? `Filtered by “${query.trim()}”` : 'Complete implementation reference',
    [normalizedQuery, query],
  );

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b border-border/80 bg-background/90 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-[1580px] items-center gap-4 px-4 py-3 lg:px-8">
          <a href="#overview" className="flex min-w-0 items-center gap-3" aria-label="Go to documentation overview">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-primary/30 bg-primary/10 text-primary">
              <Network size={18} />
            </span>
            <div className="min-w-0">
              <p className="truncate font-semibold tracking-tight">AI Factory Research Platform</p>
              <p className="truncate text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Implementation handbook · 2026.09</p>
            </div>
          </a>

          <div className="relative ml-auto hidden w-full max-w-md md:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={15} />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search architecture, agents, guardrails…"
              aria-label="Search implementation documentation"
              className="h-9 border-border bg-card/70 pl-9"
            />
          </div>

          <span className="status-pill hidden xl:inline-flex"><span className="status-dot" />29 tests passing</span>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1580px] lg:grid-cols-[270px_minmax(0,1fr)]">
        <aside className="sticky top-16 hidden h-[calc(100vh-4rem)] overflow-y-auto border-r border-border px-5 py-7 lg:block">
          <p className="nav-label">Contents</p>
          <nav className="mt-3 space-y-0.5" aria-label="Documentation sections">
            {navItems.map(([id, label], index) => (
              <a key={id} href={`#${id}`} className="nav-link">
                <span>{String(index + 1).padStart(2, '0')}</span>{label}
              </a>
            ))}
          </nav>
          <div className="mt-8 rounded-xl border border-amber-300/20 bg-amber-200/[0.04] p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-amber-200"><AlertTriangle size={14} />Scope boundary</div>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">The ranking measures fundamental AI-factory growth exposure. It is not valuation, a price target, or a trading signal.</p>
          </div>
          <p className="mt-5 text-[11px] leading-5 text-muted-foreground">{statusText}</p>
        </aside>

        <article className="min-w-0 px-4 py-8 sm:px-6 lg:px-12 lg:py-12 xl:px-16">
          <div className="relative mb-6 md:hidden">
            <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={15} />
            <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search documentation…" aria-label="Search implementation documentation" className="h-10 bg-card pl-9" />
          </div>

          <nav className="mb-8 flex gap-2 overflow-x-auto pb-2 lg:hidden" aria-label="Mobile documentation sections">
            {navItems.map(([id, label]) => <a key={id} href={`#${id}`} className="shrink-0 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">{label}</a>)}
          </nav>

          <DocSection id="overview" index="00" kicker="Executive orientation" title="A controlled research system from evidence to an auditable Top 20." intro="This portal documents the implemented architecture, data plane, agent responsibilities, deterministic scoring, storage, interfaces, controls and operational boundaries of the AI Factory Growth Research Platform." query={normalizedQuery} keywords={`overview objective ${allSearchText}`}>
            <div className="hero-grid">
              <div className="hero-copy">
                <div className="mb-5 flex flex-wrap gap-2">
                  <Badge className="bg-primary/15 text-primary">Point-in-time</Badge>
                  <Badge variant="outline">Evidence-first</Badge>
                  <Badge variant="outline">Human-authorized</Badge>
                  <Badge variant="outline">Model-assisted, code-scored</Badge>
                </div>
                <h1>From public evidence to a defensible <span>AI-factory growth ranking.</span></h1>
                <p>The platform maps compute, networking, power, cooling and construction spend; identifies public-company exposure; evaluates moat, operating margin, growth scenarios and risk; then publishes only reviewed results.</p>
              </div>
              <div className="system-snapshot" aria-label="System status summary">
                <SnapshotRow label="Reference deployment" value="Operational" tone="good" />
                <SnapshotRow label="Live connectors" value="3 / 10 catalogued" tone="good" />
                <SnapshotRow label="Workflow" value="9 bounded agents" tone="good" />
                <SnapshotRow label="Evidence claims" value="21 typed claim kinds" tone="good" />
                <SnapshotRow label="Persistent schema" value="13 tables" tone="good" />
                <SnapshotRow label="Horizontal scale" value="Planned boundary" tone="warn" />
              </div>
            </div>

            <div className="metric-grid">
              <Metric icon={<Database size={18} />} value="13" label="persistent tables" note="Lineage, runs, reviews and audit" />
              <Metric icon={<Activity size={18} />} value="9" label="workflow agents" note="Sequential typed company graph" />
              <Metric icon={<ShieldCheck size={18} />} value="12" label="control families" note="Network, evidence, model and release" />
              <Metric icon={<FileCheck2 size={18} />} value="29" label="automated tests" note="Unit, security and end-to-end" />
            </div>

            <Callout icon={<CircleDot size={17} />} title="The central design choice">
              Agents interpret approved evidence. Deterministic services own arithmetic, policy boundaries, rank ordering, release gates and audit persistence. This prevents an LLM from silently changing the investment methodology.
            </Callout>
          </DocSection>

          <DocSection id="problem" index="01" kicker="Problem definition" title="The assignment is an evidence-normalization and governance problem before it is an AI problem." intro="The system must explain why a public issuer is economically exposed to the AI-factory build-out, quantify the materiality, and make the conclusion reproducible at a historical cutoff." query={normalizedQuery} keywords="problem scope objective exclusions valuation public companies equity growth capex">
            <div className="two-col">
              <InfoCard icon={<BookOpen />} title="Question being answered">
                Which public companies have the strongest evidence-backed combination of AI-factory revenue exposure, durable differentiation, margin quality and three-year growth—after explicit risk adjustment?
              </InfoCard>
              <InfoCard icon={<XCircle />} title="Question not being answered" tone="warn">
                Which stock is cheapest, what will its price be, when should it be bought, or how rates and market multiples will move. Valuation and trading are Phase-1 exclusions.
              </InfoCard>
            </div>
            <h3>Required outputs</h3>
            <div className="card-grid three">
              <SmallCard title="Capital-stack map" text="Five monetization layers with versioned subsegments and reference spend assumptions." />
              <SmallCard title="Evidence dossier" text="Identity, documents, claims, exposure, moat, margin, scenarios, risk, citations and contradictions." />
              <SmallCard title="Ordered Top 20" text="Base rank with bear/bull rank range, confidence, analyst status and reproducibility manifest." />
            </div>
            <h3>Non-functional requirements embedded in the implementation</h3>
            <ul className="check-list">
              {['Quarterly repeatability and run-to-run comparison', 'Point-in-time evidence cutoffs and immutable history', 'Global-ready identity model without a hard-coded ticker universe', 'Source licensing and retention metadata', 'Prompt-injection, SSRF and credential protections', 'Human approval at claim and publication levels', 'Failure isolation, logs, metrics and persistent audit', 'Single-node pilot today with an explicit distributed migration path'].map((item) => <li key={item}><CheckCircle2 size={15} />{item}</li>)}
            </ul>
          </DocSection>

          <DocSection id="architecture" index="02" kicker="Architecture" title="A layered, fail-closed evidence pipeline." intro="The design separates acquisition, raw storage, normalization, judgment, calculation and authorization. Each boundary has a typed contract and a narrower authority than the layer before it." query={normalizedQuery} keywords="architecture components layers acquisition knowledge graph control runtime topology">
            <div className="architecture-stack">
              <ArchitectureLayer label="01 · Sources" icon={<Globe2 />} items={['SEC / GLEIF / GDELT', 'IR & filings', 'Project / power records', 'Technical standards', 'Licensed news / transcripts']} tone="source" />
              <ArchitectureArrow label="HTTPS · rate-limited · read-only" />
              <ArchitectureLayer label="02 · Acquisition" icon={<Radar />} items={['Source catalog', 'Allow-listed adapters', 'Safe HTTP client', 'Sync cursors', 'Raw snapshot store']} tone="acquire" />
              <ArchitectureArrow label="Hash · archive · normalize" />
              <ArchitectureLayer label="03 · Knowledge" icon={<Database />} items={['Security master', 'Document catalogue', 'Evidence ledger', 'Claim proposals', 'Taxonomy']} tone="knowledge" />
              <ArchitectureArrow label="As-of filter · role context" />
              <ArchitectureLayer label="04 · Research graph" icon={<Waypoints />} items={['Eligibility', 'Evidence', 'Exposure', 'Moat & margin', 'Growth & risk', 'Skeptic & narrative']} tone="agents" />
              <ArchitectureArrow label="Validated assessment" />
              <ArchitectureLayer label="05 · Control & release" icon={<ShieldCheck />} items={['Deterministic score', 'Scenario ranking', 'Quality evaluation', 'Analyst review', 'Report + manifest']} tone="control" />
            </div>

            <h3>Architectural principles</h3>
            <div className="principle-grid">
              {principles.map(([title, text], index) => <div key={title} className="principle"><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{title}</strong><p>{text}</p></div></div>)}
            </div>

            <div className="two-col">
              <InfoCard icon={<Server />} title="Reference topology · implemented">
                One API/worker process, SQLite in WAL mode, local content-addressed raw artifacts, LangGraph with local fallback, and a bounded thread pool across companies.
              </InfoCard>
              <InfoCard icon={<Cloud />} title="Distributed topology · migration target">
                API and worker replicas, PostgreSQL, S3/MinIO, Temporal, Redis coordination, OTLP export, SSO/RBAC, secret manager and egress policy. Dependencies are declared; adapters are not yet wired.
              </InfoCard>
            </div>
          </DocSection>

          <DocSection id="taxonomy" index="03" kicker="Market model" title="The AI-factory capital stack is versioned separately from company scoring." intro="The supplied Stargate graphic establishes seed spend hypotheses. These weights guide market mapping and candidate discovery; they are not multiplied into TAFGS because growth forecasts already reflect end-market opportunity." query={normalizedQuery} keywords="taxonomy compute servers networking power cooling construction spend weights stargate capital stack">
            <DataTable headers={['Layer', 'Reference spend', 'Seed share', 'Subsegments']} rows={valueChain.map((row) => [row.layer, row.spend, row.share, row.subsegments])} />
            <Callout icon={<AlertTriangle size={17} />} title="Assumption status" tone="warn">
              Total displayed reference spend is $68.445B. The taxonomy records `validated=false` until research owners corroborate the seed assumptions with primary or licensed market data.
            </Callout>
          </DocSection>

          <DocSection id="sources" index="04" kicker="Online data plane" title="Source definitions are configuration; connector authority remains in code." intro="`config/sources.json` contains URLs, endpoints, auth environment references, evidence tier, rate, timeout, response cap, licence notes and source-specific options. It cannot dynamically import or execute an adapter." query={normalizedQuery} keywords="data sources SEC GLEIF GDELT OpenFIGI Companies House XBRL EDINET EIA PatentsView USAspending auth rate limits">
            <div className="status-legend"><StatusBadge status="implemented" /><span>Live adapter</span><StatusBadge status="planned" /><span>Fail-closed catalog entry</span></div>
            <div className="source-table-wrap">
              <Table>
                <TableHeader><TableRow><TableHead>Source</TableHead><TableHead>Status</TableHead><TableHead>Tier</TableHead><TableHead>Authentication</TableHead><TableHead>Implemented role / boundary</TableHead></TableRow></TableHeader>
                <TableBody>{sourceRows.map((row) => <TableRow key={row.name}><TableCell className="align-top"><strong>{row.name}</strong><span className="table-sub">{row.category}</span></TableCell><TableCell className="align-top"><StatusBadge status={row.status} /><span className="table-sub max-w-52 whitespace-normal">{row.operational}</span></TableCell><TableCell className="align-top"><span className="tier-chip">T{row.tier}</span></TableCell><TableCell className="max-w-52 whitespace-normal align-top">{row.auth}</TableCell><TableCell className="min-w-80 whitespace-normal align-top text-muted-foreground">{row.role}</TableCell></TableRow>)}</TableBody>
              </Table>
            </div>

            <h3>Evidence tiers</h3>
            <div className="card-grid three">{sourceTiers.map(([name, weight, detail]) => <SmallCard key={name} title={name} eyebrow={`weight ${weight}`} text={detail} />)}</div>

            <h3>Source portfolio needed for institutional coverage</h3>
            <div className="card-grid two">
              <SmallCard title="Identity & corporate actions" text="Regulatory universes, GLEIF, OpenFIGI or a licensed global security master; preserve ADR, share-class, ticker and parent history." />
              <SmallCard title="Financials & exposure" text="Official XBRL plus annual reports, IR releases, presentations and licensed transcripts; distinguish revenue, orders, backlog and TAM." />
              <SmallCard title="Projects & demand" text="Hyperscaler capex, procurement portals, EIA/FERC/ISO/utility records, permits, tax incentives, construction awards and commissioning states." />
              <SmallCard title="Moat & risk" text="Standards bodies, reference architectures, patents, customer certifications, competitor evidence, filing risks, export controls and supply dependencies." />
            </div>

            <h3>Official references</h3>
            <div className="link-grid">{officialLinks.map(([label, href]) => <a key={href} href={href} target="_blank" rel="noreferrer">{label}<ArrowRight size={13} /></a>)}</div>
          </DocSection>

          <DocSection id="ingestion" index="05" kicker="Acquisition & lineage" title="Every source sync is bounded, archived and auditable before interpretation." intro="The connector service exposes only implemented and enabled adapters, derives a source/scope cursor, persists the attempt, then records a sanitized completion or failure." query={normalizedQuery} keywords="ingestion pipeline http raw snapshot content hash entity resolution CIK LEI sync cursor archive parser">
            <div className="step-track">
              {[
                ['Resolve', 'Validate source, enabled status, adapter and credential readiness.'],
                ['Scope', 'Build universe/company scope and load previous cursor.'],
                ['Fetch', 'HTTPS, DNS validation, manual safe redirects, rate limit, retries and size cap.'],
                ['Archive', 'SHA-256 raw bytes plus JSON manifest under date/hash path.'],
                ['Normalize', 'HTML text, official JSON, document metadata and injection flags.'],
                ['Resolve entity', 'CIK/ticker or legal-name/LEI mapping with confidence.'],
                ['Persist', 'Documents, identifiers, deterministic claims and next cursor.'],
                ['Audit', 'Counters/status/error saved to sync run and audit event.'],
              ].map(([title, text], index) => <div className="step" key={title}><span>{index + 1}</span><div><strong>{title}</strong><p>{text}</p></div></div>)}
            </div>

            <div className="two-col">
              <InfoCard icon={<HardDrive />} title="Raw snapshot layout">
                `artifacts/raw-sources/&lt;source&gt;/YYYY/MM/DD/&lt;hash-prefix&gt;/&lt;sha256&gt;.&lt;ext&gt;` with a sibling manifest recording source URL, external ID, content type, bytes, retrieval time, safe headers and metadata. Writes use temporary files and atomic rename; identical bytes are idempotent.
              </InfoCard>
              <InfoCard icon={<Fingerprint />} title="Document identity">
                Document UUID derives from source URL plus content hash. The database uniquely constrains URL + hash, so corrected content is preserved as a distinct version while duplicates collapse.
              </InfoCard>
            </div>

            <h3>Implemented adapter behavior</h3>
            <Accordion className="docs-accordion">
              <AccordionItem value="sec"><AccordionTrigger>SEC EDGAR · universe, filings and deterministic XBRL</AccordionTrigger><AccordionContent><p>Universe mode validates the exact regulator schema, groups multiple tickers/exchanges by zero-padded CIK, creates new issuers as unclassified/ineligible, preserves analyst classifications on refresh, and stores CIK/ticker identifiers. Company mode fetches submissions and Company Facts, updates identity, selects configured filing forms available by the cutoff, archives/normalizes filings, and computes annual revenue and operating margin from matching-period facts.</p><p>Revenue concepts are tried in order: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, then `SalesRevenueNet`. Margin uses `OperatingIncomeLoss / revenue × 100`; forms are limited to 10-K, 20-F and 40-F for annual XBRL selection.</p></AccordionContent></AccordionItem>
              <AccordionItem value="gleif"><AccordionTrigger>GLEIF · legal-entity resolution</AccordionTrigger><AccordionContent><p>Starts with the official legal-name filter. If empty, it requests a fuzzy completion and canonical LEI record. Names are normalized with configured legal suffixes and compared using SequenceMatcher; only a score at or above 0.82 persists the LEI. Unmatched searches remain documents and cursors, not silent merges.</p></AccordionContent></AccordionItem>
              <AccordionItem value="gdelt"><AccordionTrigger>GDELT · discovery only</AccordionTrigger><AccordionContent><p>Builds a quoted company alias/ticker query plus the configured AI-factory topic expression, clamps lookback to 1–365 days and results to 1–250, archives the response, and creates one metadata document per HTTPS article URL. Every record is marked `discovery_only=true`; article full text is not copied and no evidence claims are produced.</p></AccordionContent></AccordionItem>
            </Accordion>
          </DocSection>

          <DocSection id="extraction" index="06" kicker="Evidence proposals" title="The model may propose a claim; it cannot approve one." intro="Qualitative and forecast evidence uses retrieval plus structured generation, followed by deterministic validation and an explicit analyst decision. Reported SEC financials bypass the model." query={normalizedQuery} keywords="LLM extraction proposal exact quote human review OpenRouter Nemotron chunks confidence prompt schema">
            <div className="state-machine">
              <State label="Document" detail="normalized local text" />
              <ArrowRight />
              <State label="Relevant chunks" detail="keyword-scored top 8" />
              <ArrowRight />
              <State label="Model JSON" detail="zero temperature + schema" />
              <ArrowRight />
              <State label="Validation" detail="quote · unit · range · date" />
              <ArrowRight />
              <div className="state-split"><State label="Pending" detail="analyst review" tone="good" /><State label="Invalid" detail="audit only" tone="bad" /></div>
              <ArrowRight />
              <State label="Accepted claim" detail="or rejected proposal" tone="good" />
            </div>

            <DataTable headers={['Control', 'Implementation']} rows={proposalControls.map(([a, b]) => [a, b])} />

            <div className="two-col">
              <InfoCard icon={<Braces />} title="Model gateways">
                `offline` keeps all structured evidence/scoring available without an LLM. `openai_compatible` supports OpenRouter or another HTTPS chat-completions gateway. `ollama` supports loopback `/api/chat`. Responses must be one JSON object with required top-level keys.
              </InfoCard>
              <InfoCard icon={<LockKeyhole />} title="Prompt contract">
                The common prompt fixes role, cutoff, evidence policy, citation duty, disconfirming evidence and JSON-only output. The extraction prompt requires an exact quote, decimal ratios/CAGR, abstention and explicit separation of forecasts/judgments from reported facts.
              </InfoCard>
            </div>
            <Callout icon={<AlertTriangle size={17} />} title="Known parser boundary" tone="warn">Local text, JSON and HTML are supported. Files above 75 MB fail. PDF documents are deliberately rejected until a page-aware optional parser is implemented so the system does not invent page citations.</Callout>
          </DocSection>

          <DocSection id="agents" index="07" kicker="Agent network" title="Nine roles, one typed state, no free-form inter-agent debate." intro="An agent exists only where the task has a distinct judgment rubric or context boundary. Each agent deep-copies the assessment, writes its owned fields, and returns typed state to the supervisor." query={normalizedQuery} keywords="agents roles eligibility evidence exposure moat margin growth risk skeptic narrative">
            <div className="agent-sequence" aria-label="Agent execution order">{agents.map((agent, index) => <div key={agent.key}><span>{String(index + 1).padStart(2, '0')}</span><strong>{agent.name.replace(' Agent', '')}</strong></div>)}</div>
            <Accordion className="docs-accordion agent-accordion">
              {agents.map((agent) => <AccordionItem key={agent.key} value={agent.key}><AccordionTrigger><span className="agent-trigger"><code>{agent.key}</code>{agent.name}</span></AccordionTrigger><AccordionContent><div className="agent-detail"><Detail label="Owns" text={agent.owns} /><Detail label="Reads" text={agent.inputs} /><Detail label="Writes" text={agent.output} /><Detail label="Fail-closed behavior" text={agent.guard} /></div></AccordionContent></AccordionItem>)}
            </Accordion>
            <Callout icon={<Zap size={17} />} title="What is not an agent">Ranking, arithmetic, persistence, report rendering, publication authorization, configuration loading and network transport are deterministic services—not anthropomorphized agents.</Callout>
          </DocSection>

          <DocSection id="workflow" index="08" kicker="Orchestration" title="Parallel across companies; sequential inside each dossier." intro="The outer service fans out issuers with a bounded ThreadPoolExecutor. Each issuer runs the same ordered graph; the ranking fan-in happens only after every future has completed or been converted into a failed dossier." query={normalizedQuery} keywords="LangGraph workflow state fan out fan in ThreadPoolExecutor local graph run lifecycle failure">
            <div className="workflow-diagram">
              <div className="workflow-start">Frozen run<br /><small>as_of · config · universe</small></div>
              <ArrowRight />
              <div className="workflow-fan"><span>Company A graph</span><span>Company B graph</span><span>Company N graph</span></div>
              <ArrowRight />
              <div className="workflow-end">Deterministic fan-in<br /><small>score · rank · persist</small></div>
            </div>
            <div className="numbered-list">{workflowSteps.map(([title, text], index) => <div key={title}><span>{String(index + 1).padStart(2, '0')}</span><p><strong>{title}</strong>{text}</p></div>)}</div>
            <h3>Typed workflow state</h3>
            <CodeBlock>{`WorkflowState {
  run_id: string
  as_of_date: string
  company: security master record
  claims: EvidenceClaim[]  // already cutoff-filtered
  assessment: CompanyAssessment
  policy: versioned scoring policy
}`}</CodeBlock>
            <p className="body-copy">When LangGraph is importable, a compiled `StateGraph` links START through all nine nodes to END. The dependency-free local fallback executes the identical agent list in the identical order, which keeps local verification available without changing semantics.</p>
          </DocSection>

          <DocSection id="scoring" index="09" kicker="Deterministic methodology" title="TAFGS converts segment growth into issuer-level growth before risk adjustment." intro="This corrects the assignment’s raw formula for exposure materiality: a supplier with 5% AI exposure cannot be treated like a supplier with 80% exposure to the same end-market CAGR." query={normalizedQuery} keywords="TAFGS scoring formula margin CAGR exposure moat risk rank confidence scenarios">
            <div className="formula-card">
              <p className="formula-label">Company AI-driven CAGR</p>
              <code>((1 − exposure) + exposure × (1 + AI segment CAGR)³)^(1/3) − 1</code>
              <p>Non-AI revenue is held flat solely to isolate the AI-factory contribution.</p>
            </div>
            <div className="formula-card primary-formula">
              <p className="formula-label">Risk-adjusted TAFGS</p>
              <code>Moat × Margin Score × Company AI CAGR % × (1 − Risk Discount)</code>
              <p>Bear, base and bull are calculated independently; base determines the ordered Top 20.</p>
            </div>
            <div className="three-col">
              <div><h3>Margin rubric</h3><DataTable compact headers={['Operating margin', 'Score']} rows={marginBands.map(([a, b]) => [a, b])} /></div>
              <div><h3>Moat weights</h3><DataTable compact headers={['Component', 'Weight']} rows={moatWeights.map(([a, b]) => [a, b])} /></div>
              <div><h3>Risk weights</h3><DataTable compact headers={['Component', 'Weight']} rows={riskWeights.map(([a, b]) => [a, b])} /></div>
            </div>
            <div className="card-grid three">
              <SmallCard title="Risk discount" eyebrow="cap 35%" text="Weighted risk severity ÷ 5 × maximum discount. A severity of five across all components produces the 35% cap." />
              <SmallCard title="Rank stability" eyebrow="bear ↔ bull" text="1 − absolute bear/bull rank spread ÷ max(1, eligible count − 1), floored at zero." />
              <SmallCard title="Rank confidence" eyebrow="0–1" text="Evidence confidence × (0.65 + 0.35 × stability), clamped to [0,1]. It does not alter business quality." />
            </div>
            <Callout icon={<ShieldCheck size={17} />} title="Rankability gates">Complete identity; Tier-1 revenue and margin; exposure; three ordered scenarios; all six moat and six risk components; no unresolved contradiction; ≥0.65 evidence confidence; ≥0.85 citation coverage; finite in-range values.</Callout>
          </DocSection>

          <DocSection id="storage" index="10" kicker="Persistence & lineage" title="SQLite is the system of record for the single-node reference deployment." intro="The database runs in WAL mode with foreign keys enabled. Repository methods open short-lived managed connections; explicit transactions commit or roll back and close the handle." query={normalizedQuery} keywords="database SQLite WAL tables schema storage artifacts raw reports audit lineage manifest">
            <DataTable headers={['Table', 'Purpose']} rows={tables.map(([a, b]) => [a, b])} codeFirst />
            <h3>Filesystem artifacts</h3>
            <div className="card-grid three">
              <SmallCard title="artifacts/aifactory.db" eyebrow="SQLite / WAL" text="Security master, evidence, proposals, runs, assessments, ranks, reviews and audit events." />
              <SmallCard title="artifacts/raw-sources/" eyebrow="content addressed" text="Original provider bytes, safe response metadata, retrieval manifest and normalized filing text." />
              <SmallCard title="artifacts/reports/" eyebrow="release artifacts" text="Markdown report and JSON manifest containing versions, evidence IDs and report SHA-256." />
            </div>
            <h3>Atomic evidence contract</h3>
            <CodeBlock>{`EvidenceClaim {
  company_id · document_id · claim_type
  value_numeric | value_text · unit · period_end
  confidence · exact evidence_span · page_or_section
  source_tier · published_at · as_of_eligible
  contradiction · extraction_method
}`}</CodeBlock>
            <Callout icon={<Cloud size={17} />} title="Scale boundary" tone="warn">Before multiple writers, replace the repository with PostgreSQL migrations and the snapshot interface with versioned S3/MinIO. Local paths in historical records must become durable object keys; do not mount one SQLite file across replicas.</Callout>
          </DocSection>

          <DocSection id="interfaces" index="11" kicker="Interfaces" title="One application service powers the API, CLI and analyst workbench." intro="FastAPI request models validate bounds before delegating blocking work to a thread. All `/api/v1` endpoints use the reference `X-API-Key` dependency; liveness, readiness, metrics and the local workbench are public." query={normalizedQuery} keywords="API FastAPI endpoints CLI commands analyst workbench authentication health ready metrics">
            <h3>HTTP surface</h3>
            <div className="api-list">{apiEndpoints.map(([method, path, description]) => <div key={`${method}-${path}`}><span className={`method ${method.startsWith('GET') ? 'get' : 'post'}`}>{method}</span><code>{path}</code><p>{description}</p></div>)}</div>
            <h3>CLI surface</h3>
            <div className="card-grid three">{cliGroups.map(([title, commands]) => <SmallCard key={title} title={title} eyebrow="aifactory" text={commands} mono />)}</div>
            <CodeBlock>{`# Core analyst flow
aifactory source-list
aifactory source-sync sec_edgar --mode universe --limit 1000
aifactory source-sync sec_edgar --mode company --cik 1045810 \\
  --segment compute_servers --subsegment accelerators \\
  --as-of-date 2026-09-01 --limit 3
aifactory source-sync gleif --mode company --company-id COMPANY_ID
aifactory extract-evidence --company-id COMPANY_ID --as-of-date 2026-09-01
aifactory list-proposals --company-id COMPANY_ID --status pending
aifactory review-proposal PROPOSAL_ID --decision accepted \\
  --reviewer analyst@example.com --comment "Verified source and rubric"
aifactory run --as-of-date 2026-09-01 --generate-report
aifactory evaluate RUN_ID
aifactory review RUN_ID COMPANY_ID --decision approved \\
  --reviewer analyst@example.com --comment "Dossier reviewed"
aifactory publish RUN_ID --actor analyst@example.com`}</CodeBlock>
          </DocSection>

          <DocSection id="user-stories" index="12" kicker="Operating model" title="The user journey is a chain of accountable decisions, not a single “research” button." intro="Different roles own source approval, evidence judgment, methodology, operations, model risk and publication. Their actions are intentionally separated and persisted." query={normalizedQuery} keywords="user story analyst data steward methodology platform operator model risk auditor journey personas">
            <div className="story-grid">{userStories.map((story, index) => <div className="story" key={story.actor}><span>{String(index + 1).padStart(2, '0')}</span><div><strong>{story.actor}</strong><h4>{story.need}</h4><p>{story.journey}</p></div></div>)}</div>
            <h3>Quarterly research story</h3>
            <div className="journey-line">
              {['Freeze cutoff', 'Check source health', 'Sync changes', 'Review proposals', 'Run graph', 'Evaluate & diff', 'Approve Top 20', 'Publish manifest'].map((item, index) => <div key={item}><span>{index + 1}</span><p>{item}</p></div>)}
            </div>
          </DocSection>

          <DocSection id="guardrails" index="13" kicker="Security & governance" title="Guardrails exist at network, document, model, evidence, scoring and release boundaries." intro="The trust model assumes internet content is hostile, parser output may be wrong, model output is untrusted, and analyst overrides are privileged actions." query={normalizedQuery} keywords="guardrails security SSRF prompt injection secrets auth RBAC point in time human approval fail closed">
            <Accordion className="docs-accordion guardrail-accordion">
              {guardrails.map(([title, text], index) => <AccordionItem value={`guard-${index}`} key={title}><AccordionTrigger><span className="guard-title"><ShieldCheck size={15} />{title}</span></AccordionTrigger><AccordionContent><p>{text}</p></AccordionContent></AccordionItem>)}
            </Accordion>
            <h3>Trust boundaries</h3>
            <div className="trust-flow">
              {['Internet content', 'Parser output', 'Model proposal', 'Accepted claim', 'Ranked dossier', 'Published report'].map((item, index) => <div key={item}><span>{index < 3 ? 'untrusted' : index < 5 ? 'controlled' : 'authorized'}</span><strong>{item}</strong></div>)}
            </div>
            <Callout icon={<LockKeyhole size={17} />} title="Production authentication boundary" tone="warn">The current header API key is a reference control and comparison is not a complete institutional identity layer. A shared deployment needs SSO, RBAC, named analyst identities, secret manager, TLS termination, CSRF policy where applicable and network egress rules.</Callout>
          </DocSection>

          <DocSection id="telemetry" index="14" kicker="Observability" title="Operational signals are split between ephemeral metrics and durable audit history." intro="JSON logs and in-process Prometheus metrics answer “is it healthy now?” SQLite audit events answer “who did what, to which run/company, and when?”" query={normalizedQuery} keywords="telemetry logging JSON Prometheus metrics audit OpenTelemetry traces counters durations SLO alerts">
            <div className="telemetry-grid">{telemetry.map(([title, text], index) => <div key={title}><span>{['LOG', 'TIME', 'COUNT', 'PROM', 'AUDIT', 'BOUND'][index]}</span><strong>{title}</strong><p>{text}</p></div>)}</div>
            <h3>Recommended alerts</h3>
            <ul className="check-list warn-list">
              {['Any failed scheduled run', '>5% company-workflow failure rate', 'Source freshness above segment threshold', 'Citation coverage below 85%', 'Score reproducibility below 100%', 'Unexpected Top-20 churn without source changes', 'Model latency/cost above configured budget'].map((item) => <li key={item}><AlertTriangle size={15} />{item}</li>)}
            </ul>
            <h3>Initial SLOs</h3>
            <DataTable headers={['Measure', 'Target']} rows={[["Scheduled run completion", '99%'], ['Score reproducibility', '100%'], ['Required numeric citation coverage', '100%'], ['Mean dossier citation coverage', '≥95%'], ['Rankable workflow success', '≥95%'], ['API read availability', '99.5%'], ['RPO / RTO', '24h / 4h']]} />
          </DocSection>

          <DocSection id="evaluation" index="15" kicker="Quality system" title="Every run can be recomputed, gated and compared with the previous quarter." intro="Evaluation is deterministic. LLM-as-judge can supplement a future benchmark but may not replace exact calculations, citation checks or analyst labels." query={normalizedQuery} keywords="evaluation tests quality gates reproducibility citation benchmark red team comparison coverage">
            <DataTable headers={['Metric', 'What it verifies']} rows={evaluationMetrics.map(([a, b]) => [a, b])} />
            <div className="two-col">
              <InfoCard icon={<ClipboardCheck />} title="Research-ready gate">
                Score reproducibility is 100%, mean citation coverage and evidence confidence meet policy thresholds, and the rank output is nonempty.
              </InfoCard>
              <InfoCard icon={<UserCheck />} title="Publication-ready gate">
                Every research-ready gate passes and ranked approval coverage equals 100%.
              </InfoCard>
            </div>
            <h3>Test coverage implemented</h3>
            <div className="card-grid three">
              <SmallCard title="Scoring & config" text="Boundary bands, exposure conversion, risk, rank order, policy and environment parsing." />
              <SmallCard title="Ingestion & security" text="Package validation, XBRL selection, SSRF, prompt signatures, size caps and credential redaction." />
              <SmallCard title="Sources & extraction" text="Catalog safety, raw idempotency, cursors, identity, exact-quote proposal validation and human acceptance." />
              <SmallCard title="Model gateway" text="Endpoint rules, JSON parsing, required keys and bounded completion behavior." />
              <SmallCard title="End-to-end" text="Synthetic 20-company workflow, rankings, review, publication and report manifest." />
              <SmallCard title="Current result" text="29 tests pass; compile and dependency checks pass in the verified workspace." />
            </div>
            <Callout icon={<FileSearch size={17} />} title="Required benchmark before production model changes">Build a frozen, point-in-time analyst-labelled set spanning all five segments, ambiguous identities, units/currencies, restatements, contradictions, prompt injection and quarter-to-quarter walk-forward calibration.</Callout>
          </DocSection>

          <DocSection id="operations" index="16" kicker="Operations & deployment" title="Quarterly refresh is implemented; durable distributed orchestration is the next scale step." intro="The reference platform ships a CLI, FastAPI service, Docker image, Compose service and Kubernetes CronJob scheduled for 06:00 UTC on the fifth day of January, April, July and October." query={normalizedQuery} keywords="operations deployment Docker Compose Kubernetes CronJob quarterly refresh backup restore incident production PostgreSQL Temporal S3">
            <h3>Quarterly runbook</h3>
            <div className="numbered-list compact-list">{['Confirm source licences, credentials and connector health.', 'Freeze the research cutoff.', 'Sync filings, IR, project, technical and discovery evidence.', 'Review taxonomy/capital-weight assumptions.', 'Validate parser outputs and adjudicate claim proposals.', 'Execute the company graph and deterministic ranking.', 'Evaluate the run and compare with the previous quarter.', 'Resolve conflicts and review every provisional Top-20 dossier.', 'Publish the approved report and archive its manifest.'].map((text, index) => <div key={text}><span>{String(index + 1).padStart(2, '0')}</span><p>{text}</p></div>)}</div>
            <h3>Deployment progression</h3>
            <div className="deployment-line">
              <Deployment title="Developer / assignment" status="implemented" text="Python venv, SQLite, local artifacts, CLI/API, synthetic demo and live sources." />
              <Deployment title="Controlled pilot" status="implemented" text="One container/host, persistent volume, real secrets, approved sources, analyst process and backups." />
              <Deployment title="Institutional scale" status="planned" text="PostgreSQL, S3/MinIO, Temporal, worker replicas, Redis limits, OTLP, SSO/RBAC and private model gateway." />
            </div>
            <h3>Backup, restore and incident semantics</h3>
            <div className="card-grid three">
              <SmallCard title="Reference backup" text="Back up SQLite with a consistent snapshot plus raw-sources, reports and the exact config versions." />
              <SmallCard title="Production restore" text="PostgreSQL PITR, versioned object retention and a drill that verifies content hashes and score reproduction." />
              <SmallCard title="Incident response" text="Pause publication, preserve evidence/audit, revoke credentials, identify affected versions, correct with a new run—not history edits." />
            </div>
            <h3>Failure semantics</h3>
            <DataTable headers={['Failure boundary', 'Behavior']} rows={failureSemantics.map(([a, b]) => [a, b])} />
          </DocSection>

          <DocSection id="implementation" index="17" kicker="Code & configuration map" title="Each implementation concern has one primary module and one versioned contract." intro="The repository avoids hiding business logic inside orchestration prompts. Configuration owns policy; modules own bounded mechanisms; persisted manifests bind them together." query={normalizedQuery} keywords="implementation files modules config dependencies libraries repository map Python framework FastAPI LangGraph environment variables settings secrets">
            <h3>Python module ownership</h3>
            <DataTable headers={['Module', 'Responsibility']} rows={moduleMap.map(([a, b]) => [a, b])} codeFirst />
            <h3>Versioned configuration</h3>
            <DataTable headers={['File', 'Version', 'Owns']} rows={configFiles.map(([a, b, c]) => [a, b, c])} codeFirst />
            <h3>Libraries and infrastructure</h3>
            <DataTable headers={['Bundle', 'Components']} rows={runtimeDependencies.map(([a, b]) => [a, b])} />
            <h3>Runtime environment contract</h3>
            <p>Settings use the <code>AIFACTORY_</code> prefix unless an external provider requires a standard name. Values shown below are semantics or safe defaults—not the values installed on any host.</p>
            <DataTable headers={['Variable', 'Purpose', 'Default / handling']} rows={environmentSettings.map(([a, b, c]) => [a, b, c])} codeFirst />
            <div className="two-col">
              <InfoCard icon={<GitBranch />} title="Why LangGraph">
                It provides an explicit typed graph and inspection point while preserving a local fallback. The graph coordinates roles; it does not own investment arithmetic.
              </InfoCard>
              <InfoCard icon={<RefreshCcw />} title="Why not n8n in the decision path">
                n8n may trigger a refresh or notification, but the versioned graph, data contracts and deterministic scoring stay in tested code to prevent hidden workflow drift.
              </InfoCard>
            </div>
          </DocSection>

          <DocSection id="limitations" index="18" kicker="Honest boundaries" title="Implemented capability and production aspiration are deliberately labelled separately." intro="The platform is a real single-node evidence and ranking system. The items below are not silently implied by installed packages or configuration placeholders." query={normalizedQuery} keywords="limitations roadmap planned boundaries incomplete production migration PDF auth global coverage">
            <div className="boundary-grid">{boundaries.map(([title, text]) => <div key={title}><StatusBadge status="boundary" /><strong>{title}</strong><p>{text}</p></div>)}</div>
            <h3>Recommended next implementation order</h3>
            <div className="numbered-list">{[
              ['IR/PDF acquisition', 'Add RSS/sitemap discovery plus page-aware PDF extraction and rendered quote verification.'],
              ['Global regulatory coverage', 'Implement filings.xbrl.org, Companies House and EDINET for the selected universe.'],
              ['Security master', 'Implement OpenFIGI or procure point-in-time corporate actions and identifier history.'],
              ['Independent demand evidence', 'Implement EIA, ISO/utility, award, permit and project entities with lifecycle states.'],
              ['Licensed content', 'Procure transcript/news/project datasets only after machine-use and redistribution review.'],
              ['Distributed data plane', 'Migrate repositories to PostgreSQL, snapshots to S3/MinIO and outer jobs to Temporal.'],
              ['Institutional controls', 'Add SSO/RBAC, secret manager, OTLP, immutable retention, data rights and benchmark-driven model governance.'],
            ].map(([title, text], index) => <div key={title}><span>{String(index + 1).padStart(2, '0')}</span><p><strong>{title}</strong>{text}</p></div>)}</div>
            <div className="closing-card">
              <Layers3 size={24} />
              <div><strong>Definition of done for this implementation</strong><p>A source can be configured without embedding secrets, fetched within safety bounds, archived with lineage, converted into deterministic facts or human-gated proposals, evaluated through a typed graph, ranked by reproducible code, reviewed by an analyst and published with an immutable manifest.</p></div>
            </div>
          </DocSection>

          {normalizedQuery && !allSearchText.toLowerCase().includes(normalizedQuery) ? <p className="search-note">Sections are matched by subject keywords. Clear the search to restore the complete handbook.</p> : null}
          <footer><p>AI Factory Research Platform · Implementation Handbook</p><span>Methodology version 1.0.0 · taxonomy 2026.09.01</span></footer>
        </article>
      </div>
    </main>
  );
}

function DocSection({ id, index, kicker, title, intro, query, keywords, children }: { id: string; index: string; kicker: string; title: string; intro: string; query: string; keywords: string; children: React.ReactNode }) {
  const searchable = `${id} ${kicker} ${title} ${intro} ${keywords}`.toLowerCase();
  if (query && !searchable.includes(query)) return null;
  return <section id={id} className="doc-section scroll-mt-24"><div className="section-heading"><span>{index}</span><div><p>{kicker}</p><h2>{title}</h2><div className="section-intro">{intro}</div></div></div><div className="section-content">{children}</div></section>;
}

function Metric({ icon, value, label, note }: { icon: React.ReactNode; value: string; label: string; note: string }) {
  return <div className="metric-card"><div className="flex items-center justify-between text-primary">{icon}<span>{value}</span></div><p>{label}</p><small>{note}</small></div>;
}

function SnapshotRow({ label, value, tone }: { label: string; value: string; tone: 'good' | 'warn' }) {
  return <div><span>{label}</span><strong className={tone}>{value}</strong></div>;
}

function Callout({ icon, title, tone = 'default', children }: { icon: React.ReactNode; title: string; tone?: 'default' | 'warn'; children: React.ReactNode }) {
  return <div className={`callout ${tone}`}><span>{icon}</span><div><strong>{title}</strong><p>{children}</p></div></div>;
}

function InfoCard({ icon, title, tone = 'default', children }: { icon: React.ReactNode; title: string; tone?: 'default' | 'warn'; children: React.ReactNode }) {
  return <div className={`info-card ${tone}`}><span>{icon}</span><strong>{title}</strong><p>{children}</p></div>;
}

function SmallCard({ title, text, eyebrow, mono = false }: { title: string; text: string; eyebrow?: string; mono?: boolean }) {
  return <div className="small-card">{eyebrow ? <span>{eyebrow}</span> : null}<strong>{title}</strong><p className={mono ? 'font-mono' : ''}>{text}</p></div>;
}

function ArchitectureLayer({ label, icon, items, tone }: { label: string; icon: React.ReactNode; items: string[]; tone: string }) {
  return <div className={`architecture-layer ${tone}`}><div><span className="arch-icon">{icon}</span><strong>{label}</strong></div><div>{items.map((item) => <span key={item}>{item}</span>)}</div></div>;
}

function ArchitectureArrow({ label }: { label: string }) {
  return <div className="architecture-arrow"><ArrowRight size={16} /><span>{label}</span></div>;
}

function StatusBadge({ status }: { status: 'implemented' | 'planned' | 'boundary' }) {
  return <Badge variant="outline" className={`status-badge ${status}`}>{status === 'implemented' ? <CheckCircle2 /> : status === 'planned' ? <PlayCircle /> : <AlertTriangle />}{status}</Badge>;
}

function DataTable({ headers, rows, compact = false, codeFirst = false }: { headers: readonly string[]; rows: ReadonlyArray<readonly string[]>; compact?: boolean; codeFirst?: boolean }) {
  return <div className={`data-table ${compact ? 'compact' : ''}`}><Table><TableHeader><TableRow>{headers.map((header) => <TableHead key={header}>{header}</TableHead>)}</TableRow></TableHeader><TableBody>{rows.map((row, index) => <TableRow key={`${row[0]}-${index}`}>{row.map((cell, cellIndex) => <TableCell key={`${cell}-${cellIndex}`} className={`${cellIndex === 0 ? 'font-medium text-foreground' : 'text-muted-foreground'} ${codeFirst && cellIndex === 0 ? 'font-mono text-xs text-primary' : ''}`}>{cell}</TableCell>)}</TableRow>)}</TableBody></Table></div>;
}

function State({ label, detail, tone = 'default' }: { label: string; detail: string; tone?: 'default' | 'good' | 'bad' }) {
  return <div className={`state ${tone}`}><strong>{label}</strong><span>{detail}</span></div>;
}

function Detail({ label, text }: { label: string; text: string }) {
  return <div><span>{label}</span><p>{text}</p></div>;
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  return <div className="code-block"><div><CircleDot size={11} /><span>implementation contract</span></div><pre><code>{children}</code></pre></div>;
}

function Deployment({ title, status, text }: { title: string; status: 'implemented' | 'planned'; text: string }) {
  return <div><StatusBadge status={status} /><strong>{title}</strong><p>{text}</p></div>;
}
