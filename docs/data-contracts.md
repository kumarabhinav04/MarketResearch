# Data contracts and lineage

## Normalized evidence package

Every parser or external data adapter must emit the same contract before research agents can consume it:

```json
{
  "companies": [
    {
      "id": "issuer-identifier",
      "legal_name": "Example Public Company",
      "ticker": "EXM",
      "exchange": "NYSE",
      "security_id": "US0000000000",
      "segment": "power",
      "subsegment": "switchgear",
      "eligible": true,
      "demo": false,
      "metadata": {"cik": "0000000000"}
    }
  ],
  "documents": [
    {
      "id": "stable-document-id",
      "company_id": "issuer-identifier",
      "source_type": "regulatory_filing",
      "source_tier": "1",
      "publisher": "Regulator",
      "title": "Annual report",
      "source_url": "https://example.org/filing",
      "published_at": "2026-02-15",
      "retrieved_at": "2026-03-01T12:00:00Z",
      "content_hash": "sha256",
      "parser_version": "parser-name-1.2.0"
    }
  ],
  "claims": [
    {
      "id": "stable-claim-id",
      "company_id": "issuer-identifier",
      "document_id": "stable-document-id",
      "claim_type": "operating_margin",
      "value_numeric": 24.8,
      "value_text": null,
      "unit": "percent",
      "period_end": "2025-12-31",
      "confidence": 0.99,
      "evidence_span": "Reported operating income and revenue...",
      "page_or_section": "Consolidated statements, page 72",
      "source_tier": "1",
      "published_at": "2026-02-15",
      "as_of_eligible": true,
      "contradiction": false
    }
  ]
}
```

## Company and security identity

Company and security are separate concepts even though the reference schema stores one selected security per company.

Production entity resolution must account for:

- Public parent versus private subsidiary.
- ADR, primary listing, and secondary listing deduplication.
- Name and ticker changes.
- Mergers, spin-offs, and discontinued operations.
- Different operating segments inside a diversified issuer.
- Eligibility as of the run date, not just today.

Use stable identifiers—CIK, LEI, ISIN, exchange security ID—rather than ticker as the primary key.

## Document lineage

Document identity is based on source URL and content hash. A new filing version or corrected document gets a new hash. Raw bytes should be retained in production object storage with immutable versioning.

Required lineage fields:

- Publisher and source tier.
- Publication and retrieval timestamps.
- Content hash.
- Parser name/version.
- Local/object-storage location.
- Licence and retention notes.
- Prompt-injection flags.
- Original currency, units, period, and accounting basis.

## Claim semantics

Claims are atomic. A claim should represent one fact or one explicitly labelled estimate—not an entire paragraph of mixed assertions.

Numeric claim types used by the scoring workflow:

- `total_revenue`
- `operating_margin`
- `ai_exposure`
- `ai_segment_cagr_bear`, `ai_segment_cagr_base`, `ai_segment_cagr_bull`
- Six `moat_*` components
- Six `risk_*` components

Narrative claim types:

- `role_narrative`
- `catalyst`
- `contrary_evidence`

## Source tiers

| Tier | Intended use | Weight |
|---|---|---:|
| 1 | Regulatory, company-primary, government, or official project record | 1.00 |
| 2 | Licensed transcript, standards body, technical or utility record | 0.80 |
| 3 | Reputable news, industry publication, analyst discovery source | 0.45 |

Tier 3 may discover a candidate or corroborate a thesis. It may not be the sole support for a financial metric or material contract value.

## Point-in-time rules

- `published_at <= run.as_of_date`.
- Restatements published after the cutoff are ineligible for the historical run.
- The latest value is selected by period and filing date, not by database insertion time.
- A current company name must not overwrite the identity shown in an old run manifest.
- Currency translation inputs must also be point-in-time versioned.

## Database tables

| Table | Purpose |
|---|---|
| `companies` | Security universe and eligibility |
| `market_segments` | Capital-stack taxonomy and seed assumptions |
| `source_documents` | Document provenance and hashes |
| `evidence_claims` | Atomic cited facts and estimates |
| `entity_identifiers` | Point-in-time CIK, LEI, ticker, and future identifier mappings |
| `source_cursors` | Conditional-fetch state and incremental connector cursors |
| `source_sync_runs` | Connector attempts, counters, failures, and cursor transitions |
| `claim_proposals` | Model-proposed claims awaiting explicit analyst acceptance |
| `research_runs` | Frozen run manifest |
| `company_assessments` | Structured agent and deterministic outputs |
| `rankings` | Base/bear/bull rank results |
| `reviews` | Human decisions and overrides |
| `audit_events` | Operational and governance history |
