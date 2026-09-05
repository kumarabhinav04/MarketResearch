from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

from .models import CompanyAssessment, EvidenceClaim, RankingEntry, RunStatus


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    exchange TEXT NOT NULL,
    security_id TEXT NOT NULL,
    segment TEXT NOT NULL,
    subsegment TEXT NOT NULL,
    public_parent_id TEXT,
    eligible INTEGER NOT NULL DEFAULT 1,
    demo INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_company_security
ON companies(exchange, security_id);

CREATE TABLE IF NOT EXISTS market_segments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    reference_spend_usd_billions REAL NOT NULL,
    reference_weight REAL NOT NULL,
    validated INTEGER NOT NULL DEFAULT 0,
    assumptions_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_documents (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    source_type TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    publisher TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    local_path TEXT,
    licence_notes TEXT,
    parser_version TEXT,
    injection_flags_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE INDEX IF NOT EXISTS ix_documents_company ON source_documents(company_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_document_hash_url
ON source_documents(source_url, content_hash);

CREATE TABLE IF NOT EXISTS evidence_claims (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    value_numeric REAL,
    value_text TEXT,
    unit TEXT,
    period_end TEXT,
    confidence REAL NOT NULL,
    evidence_span TEXT NOT NULL,
    page_or_section TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    published_at TEXT NOT NULL,
    as_of_eligible INTEGER NOT NULL DEFAULT 1,
    contradiction INTEGER NOT NULL DEFAULT 0,
    extraction_method TEXT NOT NULL DEFAULT 'structured',
    created_at TEXT NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(document_id) REFERENCES source_documents(id)
);

CREATE INDEX IF NOT EXISTS ix_claims_company_type
ON evidence_claims(company_id, claim_type);

CREATE TABLE IF NOT EXISTS entity_identifiers (
    company_id TEXT NOT NULL,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    source_id TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(company_id, scheme, value),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE INDEX IF NOT EXISTS ix_identifiers_scheme_value
ON entity_identifiers(scheme, value);

CREATE TABLE IF NOT EXISTS source_cursors (
    source_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    cursor_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(source_id, scope)
);

CREATE TABLE IF NOT EXISTS source_sync_runs (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL,
    cursor_before_json TEXT NOT NULL DEFAULT '{}',
    cursor_after_json TEXT NOT NULL DEFAULT '{}',
    counters_json TEXT NOT NULL DEFAULT '{}',
    error TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_source_sync_runs_source_started
ON source_sync_runs(source_id, started_at DESC);

CREATE TABLE IF NOT EXISTS claim_proposals (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    reviewer TEXT,
    review_comment TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(company_id) REFERENCES companies(id),
    FOREIGN KEY(document_id) REFERENCES source_documents(id)
);

CREATE INDEX IF NOT EXISTS ix_claim_proposals_company_status
ON claim_proposals(company_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS research_runs (
    id TEXT PRIMARY KEY,
    as_of_date TEXT NOT NULL,
    status TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    scoring_version TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    config_snapshot_json TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    published_at TEXT,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_assessments (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    rankable INTEGER NOT NULL,
    review_required INTEGER NOT NULL,
    review_status TEXT NOT NULL,
    evidence_confidence REAL NOT NULL,
    citation_coverage REAL NOT NULL,
    base_tafgs REAL NOT NULL,
    risk_adjusted_tafgs REAL NOT NULL,
    assessment_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES research_runs(id),
    FOREIGN KEY(company_id) REFERENCES companies(id),
    UNIQUE(run_id, company_id)
);

CREATE TABLE IF NOT EXISTS rankings (
    run_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    bear_rank INTEGER NOT NULL,
    bull_rank INTEGER NOT NULL,
    risk_adjusted_tafgs REAL NOT NULL,
    rank_confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(run_id, company_id),
    FOREIGN KEY(run_id) REFERENCES research_runs(id),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL,
    comment TEXT NOT NULL,
    overrides_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES research_runs(id),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    company_id TEXT,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_run ON audit_events(run_id, created_at);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ManagedConnection(sqlite3.Connection):
    """SQLite connection whose context manager also closes the file handle."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, factory=ManagedConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def upsert_company(self, company: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO companies (
                    id, legal_name, ticker, exchange, security_id, segment, subsegment,
                    public_parent_id, eligible, demo, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    legal_name=excluded.legal_name,
                    ticker=excluded.ticker,
                    exchange=excluded.exchange,
                    security_id=excluded.security_id,
                    segment=excluded.segment,
                    subsegment=excluded.subsegment,
                    public_parent_id=excluded.public_parent_id,
                    eligible=excluded.eligible,
                    demo=excluded.demo,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    company["id"],
                    company["legal_name"],
                    company["ticker"],
                    company["exchange"],
                    company["security_id"],
                    company["segment"],
                    company.get("subsegment", ""),
                    company.get("public_parent_id"),
                    int(company.get("eligible", True)),
                    int(company.get("demo", False)),
                    json.dumps(company.get("metadata", {}), sort_keys=True),
                    now,
                    now,
                ),
            )

    def list_companies(self, eligible_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM companies"
        params: Sequence[Any] = ()
        if eligible_only:
            query += " WHERE eligible=1"
        query += " ORDER BY legal_name"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_dict(row, json_fields=("metadata_json",)) for row in rows]

    def get_company(self, company_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM companies WHERE id=?", (company_id,)
            ).fetchone()
        return _row_to_dict(row, json_fields=("metadata_json",)) if row else None

    def upsert_market_segment(self, segment: dict[str, Any], taxonomy_version: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO market_segments (
                    id, name, taxonomy_version, reference_spend_usd_billions,
                    reference_weight, validated, assumptions_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    taxonomy_version=excluded.taxonomy_version,
                    reference_spend_usd_billions=excluded.reference_spend_usd_billions,
                    reference_weight=excluded.reference_weight,
                    assumptions_json=excluded.assumptions_json,
                    updated_at=excluded.updated_at
                """,
                (
                    segment["id"],
                    segment["name"],
                    taxonomy_version,
                    segment["reference_spend_usd_billions"],
                    segment["reference_weight"],
                    int(segment.get("validated", False)),
                    json.dumps(
                        {
                            "subsegments": segment.get("subsegments", []),
                            "notes": segment.get("notes", ""),
                        },
                        sort_keys=True,
                    ),
                    utc_now(),
                ),
            )

    def list_market_segments(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM market_segments ORDER BY reference_weight DESC"
            ).fetchall()
        return [_row_to_dict(row, json_fields=("assumptions_json",)) for row in rows]

    def upsert_document(self, document: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO source_documents (
                    id, company_id, source_type, source_tier, publisher, title,
                    source_url, published_at, retrieved_at, content_hash, local_path,
                    licence_notes, parser_version, injection_flags_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    retrieved_at=excluded.retrieved_at,
                    parser_version=excluded.parser_version,
                    injection_flags_json=excluded.injection_flags_json,
                    metadata_json=excluded.metadata_json
                """,
                (
                    document["id"],
                    document.get("company_id"),
                    document["source_type"],
                    str(document["source_tier"]),
                    document["publisher"],
                    document["title"],
                    document["source_url"],
                    document["published_at"],
                    document.get("retrieved_at", utc_now()),
                    document["content_hash"],
                    document.get("local_path"),
                    document.get("licence_notes"),
                    document.get("parser_version", "1.0"),
                    json.dumps(document.get("injection_flags", []), sort_keys=True),
                    json.dumps(document.get("metadata", {}), sort_keys=True),
                ),
            )

    def upsert_claim(self, claim: EvidenceClaim, extraction_method: str = "structured") -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_claims (
                    id, company_id, document_id, claim_type, value_numeric, value_text,
                    unit, period_end, confidence, evidence_span, page_or_section,
                    source_tier, published_at, as_of_eligible, contradiction,
                    extraction_method, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value_numeric=excluded.value_numeric,
                    value_text=excluded.value_text,
                    confidence=excluded.confidence,
                    evidence_span=excluded.evidence_span,
                    contradiction=excluded.contradiction
                """,
                (
                    claim.id,
                    claim.company_id,
                    claim.document_id,
                    claim.claim_type,
                    claim.value_numeric,
                    claim.value_text,
                    claim.unit,
                    claim.period_end,
                    claim.confidence,
                    claim.evidence_span,
                    claim.page_or_section,
                    claim.source_tier,
                    claim.published_at,
                    int(claim.as_of_eligible),
                    int(claim.contradiction),
                    extraction_method,
                    utc_now(),
                ),
            )

    def list_documents(self, company_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM source_documents
                WHERE company_id=? ORDER BY published_at DESC
                """,
                (company_id,),
            ).fetchall()
        return [
            _row_to_dict(row, json_fields=("injection_flags_json", "metadata_json"))
            for row in rows
        ]

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM source_documents WHERE id=?", (document_id,)
            ).fetchone()
        return (
            _row_to_dict(row, json_fields=("injection_flags_json", "metadata_json"))
            if row
            else None
        )

    def list_extractable_documents(
        self, company_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM source_documents
                WHERE company_id=? AND source_type IN (
                    'regulatory_filing', 'company_ir', 'official_project_record',
                    'licensed_transcript', 'technical_document'
                )
                ORDER BY published_at DESC LIMIT ?
                """,
                (company_id, limit),
            ).fetchall()
        return [
            _row_to_dict(row, json_fields=("injection_flags_json", "metadata_json"))
            for row in rows
        ]

    def list_claims(self, company_id: str, as_of_date: str) -> list[EvidenceClaim]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM evidence_claims
                WHERE company_id=? AND as_of_eligible=1 AND substr(published_at, 1, 10) <= ?
                ORDER BY claim_type, confidence DESC, published_at DESC
                """,
                (company_id, as_of_date),
            ).fetchall()
        return [
            EvidenceClaim(
                id=row["id"],
                company_id=row["company_id"],
                document_id=row["document_id"],
                claim_type=row["claim_type"],
                value_numeric=row["value_numeric"],
                value_text=row["value_text"],
                unit=row["unit"],
                period_end=row["period_end"],
                confidence=row["confidence"],
                evidence_span=row["evidence_span"],
                page_or_section=row["page_or_section"],
                source_tier=row["source_tier"],
                published_at=row["published_at"],
                as_of_eligible=bool(row["as_of_eligible"]),
                contradiction=bool(row["contradiction"]),
            )
            for row in rows
        ]

    def upsert_entity_identifier(
        self,
        company_id: str,
        scheme: str,
        value: str,
        source_id: str,
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO entity_identifiers (
                    company_id, scheme, value, source_id, confidence,
                    metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id, scheme, value) DO UPDATE SET
                    source_id=excluded.source_id,
                    confidence=excluded.confidence,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    company_id,
                    scheme.upper(),
                    value,
                    source_id,
                    confidence,
                    json.dumps(metadata or {}, sort_keys=True),
                    now,
                    now,
                ),
            )

    def list_entity_identifiers(self, company_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM entity_identifiers
                WHERE company_id=? ORDER BY scheme, value
                """,
                (company_id,),
            ).fetchall()
        return [_row_to_dict(row, json_fields=("metadata_json",)) for row in rows]

    def get_source_cursor(self, source_id: str, scope: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT cursor_json FROM source_cursors WHERE source_id=? AND scope=?",
                (source_id, scope),
            ).fetchone()
        return json.loads(row["cursor_json"]) if row else {}

    def upsert_source_cursor(
        self, source_id: str, scope: str, cursor: dict[str, Any]
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO source_cursors (source_id, scope, cursor_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id, scope) DO UPDATE SET
                    cursor_json=excluded.cursor_json,
                    updated_at=excluded.updated_at
                """,
                (source_id, scope, json.dumps(cursor, sort_keys=True), utc_now()),
            )

    def create_source_sync(
        self, source_id: str, scope: str, cursor_before: dict[str, Any]
    ) -> str:
        sync_id = str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO source_sync_runs (
                    id, source_id, scope, status, cursor_before_json, started_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    sync_id,
                    source_id,
                    scope,
                    "running",
                    json.dumps(cursor_before, sort_keys=True),
                    utc_now(),
                ),
            )
        return sync_id

    def complete_source_sync(
        self,
        sync_id: str,
        status: str,
        counters: dict[str, Any] | None = None,
        cursor_after: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE source_sync_runs
                SET status=?, counters_json=?, cursor_after_json=?, error=?, completed_at=?
                WHERE id=?
                """,
                (
                    status,
                    json.dumps(counters or {}, sort_keys=True),
                    json.dumps(cursor_after or {}, sort_keys=True),
                    error,
                    utc_now(),
                    sync_id,
                ),
            )

    def list_source_syncs(
        self, source_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM source_sync_runs"
        params: list[Any] = []
        if source_id:
            query += " WHERE source_id=?"
            params.append(source_id)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            _row_to_dict(
                row,
                json_fields=(
                    "cursor_before_json",
                    "cursor_after_json",
                    "counters_json",
                ),
            )
            for row in rows
        ]

    def upsert_claim_proposal(self, proposal: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO claim_proposals (
                    id, company_id, document_id, claim_type, payload_json, status,
                    validation_errors_json, model_provider, model_name,
                    prompt_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    validation_errors_json=excluded.validation_errors_json,
                    model_provider=excluded.model_provider,
                    model_name=excluded.model_name,
                    prompt_version=excluded.prompt_version,
                    updated_at=excluded.updated_at
                """,
                (
                    proposal["id"],
                    proposal["company_id"],
                    proposal["document_id"],
                    proposal["claim_type"],
                    json.dumps(proposal["payload"], sort_keys=True),
                    proposal.get("status", "pending"),
                    json.dumps(proposal.get("validation_errors", []), sort_keys=True),
                    proposal["model_provider"],
                    proposal["model_name"],
                    proposal["prompt_version"],
                    now,
                    now,
                ),
            )

    def get_claim_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM claim_proposals WHERE id=?", (proposal_id,)
            ).fetchone()
        return (
            _row_to_dict(
                row, json_fields=("payload_json", "validation_errors_json")
            )
            if row
            else None
        )

    def list_claim_proposals(
        self,
        company_id: str | None = None,
        status: str | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if company_id:
            clauses.append("company_id=?")
            params.append(company_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        query = "SELECT * FROM claim_proposals"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            _row_to_dict(
                row, json_fields=("payload_json", "validation_errors_json")
            )
            for row in rows
        ]

    def review_claim_proposal(
        self,
        proposal_id: str,
        status: str,
        reviewer: str,
        comment: str,
    ) -> None:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE claim_proposals
                SET status=?, reviewer=?, review_comment=?, reviewed_at=?, updated_at=?
                WHERE id=?
                """,
                (status, reviewer, comment, utc_now(), utc_now(), proposal_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("Claim proposal not found")

    def create_run(self, payload: dict[str, Any]) -> str:
        run_id = payload.get("id") or str(uuid.uuid4())
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO research_runs (
                    id, as_of_date, status, taxonomy_version, scoring_version,
                    prompt_version, model_provider, model_name, config_snapshot_json,
                    started_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    payload["as_of_date"],
                    RunStatus.CREATED,
                    payload["taxonomy_version"],
                    payload["scoring_version"],
                    payload["prompt_version"],
                    payload["model_provider"],
                    payload.get("model_name", ""),
                    json.dumps(payload.get("config_snapshot", {}), sort_keys=True),
                    None,
                    utc_now(),
                ),
            )
        return run_id

    def update_run(self, run_id: str, status: str, error: str | None = None) -> None:
        now = utc_now()
        columns = ["status=?", "error=?"]
        values: list[Any] = [status, error]
        if status == RunStatus.RUNNING:
            columns.append("started_at=?")
            values.append(now)
        if status in {RunStatus.COMPLETED, RunStatus.FAILED}:
            columns.append("completed_at=?")
            values.append(now)
        if status == RunStatus.PUBLISHED:
            columns.append("published_at=?")
            values.append(now)
        values.append(run_id)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE research_runs SET {', '.join(columns)} WHERE id=?", values
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM research_runs WHERE id=?", (run_id,)
            ).fetchone()
        return _row_to_dict(row, json_fields=("config_snapshot_json",)) if row else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM research_runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_dict(row, json_fields=("config_snapshot_json",)) for row in rows]

    def save_assessment(self, assessment: CompanyAssessment) -> None:
        now = utc_now()
        payload = json.dumps(assessment.to_dict(), sort_keys=True)
        assessment_id = f"{assessment.run_id}:{assessment.company_id}"
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO company_assessments (
                    id, run_id, company_id, rankable, review_required, review_status,
                    evidence_confidence, citation_coverage, base_tafgs,
                    risk_adjusted_tafgs, assessment_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, company_id) DO UPDATE SET
                    rankable=excluded.rankable,
                    review_required=excluded.review_required,
                    review_status=excluded.review_status,
                    evidence_confidence=excluded.evidence_confidence,
                    citation_coverage=excluded.citation_coverage,
                    base_tafgs=excluded.base_tafgs,
                    risk_adjusted_tafgs=excluded.risk_adjusted_tafgs,
                    assessment_json=excluded.assessment_json,
                    updated_at=excluded.updated_at
                """,
                (
                    assessment_id,
                    assessment.run_id,
                    assessment.company_id,
                    int(assessment.rankable),
                    int(assessment.review_required),
                    assessment.review_status,
                    assessment.evidence_confidence,
                    assessment.citation_coverage,
                    assessment.base_tafgs,
                    assessment.risk_adjusted_tafgs,
                    payload,
                    now,
                    now,
                ),
            )

    def list_assessments(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT a.*, c.legal_name, c.ticker, c.exchange, c.segment, c.subsegment
                FROM company_assessments a
                JOIN companies c ON c.id=a.company_id
                WHERE a.run_id=?
                ORDER BY a.risk_adjusted_tafgs DESC
                """,
                (run_id,),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = _row_to_dict(row, json_fields=("assessment_json",))
            item["assessment"] = item.pop("assessment_json")
            results.append(item)
        return results

    def get_assessment(self, run_id: str, company_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT a.*, c.legal_name, c.ticker, c.exchange, c.segment, c.subsegment
                FROM company_assessments a
                JOIN companies c ON c.id=a.company_id
                WHERE a.run_id=? AND a.company_id=?
                """,
                (run_id, company_id),
            ).fetchone()
        if not row:
            return None
        item = _row_to_dict(row, json_fields=("assessment_json",))
        item["assessment"] = item.pop("assessment_json")
        return item

    def save_rankings(self, rankings: list[RankingEntry]) -> None:
        if not rankings:
            return
        run_id = rankings[0].run_id
        with self.transaction() as connection:
            connection.execute("DELETE FROM rankings WHERE run_id=?", (run_id,))
            now = utc_now()
            connection.executemany(
                """
                INSERT INTO rankings (
                    run_id, company_id, rank, bear_rank, bull_rank,
                    risk_adjusted_tafgs, rank_confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.run_id,
                        item.company_id,
                        item.rank,
                        item.bear_rank,
                        item.bull_rank,
                        item.risk_adjusted_tafgs,
                        item.rank_confidence,
                        now,
                    )
                    for item in rankings
                ],
            )

    def list_rankings(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*, c.legal_name, c.ticker, c.exchange, c.segment, c.subsegment,
                       a.review_status, a.evidence_confidence, a.assessment_json
                FROM rankings r
                JOIN companies c ON c.id=r.company_id
                JOIN company_assessments a
                  ON a.run_id=r.run_id AND a.company_id=r.company_id
                WHERE r.run_id=?
                ORDER BY r.rank
                """,
                (run_id,),
            ).fetchall()
        return [_row_to_dict(row, json_fields=("assessment_json",)) for row in rows]

    def record_review(
        self,
        run_id: str,
        company_id: str,
        reviewer: str,
        decision: str,
        comment: str,
        overrides: dict[str, Any] | None = None,
    ) -> str:
        review_id = str(uuid.uuid4())
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO reviews (
                    id, run_id, company_id, reviewer, decision, comment,
                    overrides_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    run_id,
                    company_id,
                    reviewer,
                    decision,
                    comment,
                    json.dumps(overrides or {}, sort_keys=True),
                    utc_now(),
                ),
            )
            connection.execute(
                """
                UPDATE company_assessments
                SET review_status=?, updated_at=?
                WHERE run_id=? AND company_id=?
                """,
                (decision, utc_now(), run_id, company_id),
            )
        return review_id

    def audit(
        self,
        actor: str,
        event_type: str,
        payload: dict[str, Any],
        run_id: str | None = None,
        company_id: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, run_id, company_id, actor, event_type, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    run_id,
                    company_id,
                    actor,
                    event_type,
                    json.dumps(payload, sort_keys=True),
                    utc_now(),
                ),
            )

    def list_audit_events(self, run_id: str, limit: int = 500) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_events WHERE run_id=?
                ORDER BY created_at DESC LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
        return [_row_to_dict(row, json_fields=("payload_json",)) for row in rows]

    def reset_demo(self) -> None:
        with self.transaction() as connection:
            demo_ids = [
                row["id"] for row in connection.execute("SELECT id FROM companies WHERE demo=1")
            ]
            if not demo_ids:
                return
            placeholders = ",".join("?" for _ in demo_ids)
            run_ids = [
                row["run_id"]
                for row in connection.execute(
                    f"SELECT DISTINCT run_id FROM company_assessments WHERE company_id IN ({placeholders})",
                    demo_ids,
                )
            ]
            if run_ids:
                run_placeholders = ",".join("?" for _ in run_ids)
                connection.execute(
                    f"DELETE FROM audit_events WHERE run_id IN ({run_placeholders})", run_ids
                )
                connection.execute(
                    f"DELETE FROM reviews WHERE run_id IN ({run_placeholders})", run_ids
                )
                connection.execute(
                    f"DELETE FROM rankings WHERE run_id IN ({run_placeholders})", run_ids
                )
                connection.execute(
                    f"DELETE FROM company_assessments WHERE run_id IN ({run_placeholders})",
                    run_ids,
                )
                connection.execute(
                    f"DELETE FROM research_runs WHERE id IN ({run_placeholders})", run_ids
                )
            connection.execute(
                f"DELETE FROM claim_proposals WHERE company_id IN ({placeholders})", demo_ids
            )
            connection.execute(
                f"DELETE FROM evidence_claims WHERE company_id IN ({placeholders})", demo_ids
            )
            connection.execute(
                f"DELETE FROM source_documents WHERE company_id IN ({placeholders})", demo_ids
            )
            connection.execute(f"DELETE FROM companies WHERE id IN ({placeholders})", demo_ids)


def _row_to_dict(
    row: sqlite3.Row, json_fields: tuple[str, ...] = ()
) -> dict[str, Any]:
    item = dict(row)
    for field in json_fields:
        if field in item:
            item[field] = json.loads(item[field] or "{}")
    for field in ("eligible", "demo", "validated", "rankable", "review_required"):
        if field in item:
            item[field] = bool(item[field])
    return item
