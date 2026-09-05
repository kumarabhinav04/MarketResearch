from __future__ import annotations

import json
import logging
import re
import uuid
import warnings
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Callable

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from ..database import Database, utc_now
from ..ingestion import _latest_annual_xbrl_fact, make_document
from ..models import EvidenceClaim
from ..security import detect_prompt_injection
from ..telemetry import METRICS
from .catalog import SourceCatalog, SourceCatalogError, SourceDefinition
from .http import FetchResponse, SourceHttpClient, SourceRequestError
from .storage import RawSnapshot, RawSnapshotStore


LOGGER = logging.getLogger(__name__)


class SourceSyncError(RuntimeError):
    pass


class SourceIngestionService:
    """Configuration-driven boundary between external data and the evidence ledger."""

    def __init__(
        self,
        database: Database,
        catalog: SourceCatalog,
        store: RawSnapshotStore,
        user_agent: str,
    ):
        self.database = database
        self.catalog = catalog
        self.store = store
        self.user_agent = user_agent
        self._connectors: dict[str, Callable[..., dict[str, Any]]] = {
            "sec_edgar": self._sync_sec_edgar,
            "gleif": self._sync_gleif,
            "gdelt": self._sync_gdelt,
        }

    def list_sources(self) -> list[dict[str, Any]]:
        return [source.public_dict() for source in self.catalog.list()]

    def list_syncs(
        self, source_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        return self.database.list_source_syncs(source_id, limit)

    def sync(self, source_id: str, **options: Any) -> dict[str, Any]:
        try:
            definition = self.catalog.get(source_id)
        except SourceCatalogError as exc:
            raise SourceSyncError(str(exc)) from exc
        if not definition.enabled:
            raise SourceSyncError(f"Source {source_id} is disabled in the source catalog")
        if definition.implementation_status != "implemented":
            raise SourceSyncError(f"Source {source_id} does not have an implemented adapter")
        if not definition.credential_configured:
            env_name = definition.auth.get("env", "required credential")
            raise SourceSyncError(f"Source {source_id} requires {env_name}")
        handler = self._connectors.get(definition.connector)
        if not handler:
            raise SourceSyncError(
                f"No connector is registered for {definition.connector}"
            )

        scope = _sync_scope(definition, options)
        cursor_before = self.database.get_source_cursor(source_id, scope)
        sync_id = self.database.create_source_sync(source_id, scope, cursor_before)
        try:
            with SourceHttpClient(definition, self.user_agent) as client:
                result = handler(definition, client, cursor_before, **options)
            status = str(result.pop("status", "completed"))
            cursor_after = dict(result.pop("cursor", cursor_before))
            if cursor_after != cursor_before:
                self.database.upsert_source_cursor(source_id, scope, cursor_after)
            self.database.complete_source_sync(
                sync_id,
                status,
                counters=result,
                cursor_after=cursor_after,
            )
            self.database.audit(
                "source_ingestion_service",
                "source_sync_completed",
                {
                    "sync_id": sync_id,
                    "source_id": source_id,
                    "scope": scope,
                    "status": status,
                    "counters": result,
                },
                company_id=options.get("company_id"),
            )
            METRICS.increment("source_sync_completed_total")
            return {
                "sync_id": sync_id,
                "source_id": source_id,
                "scope": scope,
                "status": status,
                **result,
            }
        except (SourceRequestError, SourceSyncError, ValueError, KeyError) as exc:
            safe_error = f"{type(exc).__name__}: {exc}"
            self.database.complete_source_sync(
                sync_id,
                "failed",
                error=safe_error,
                cursor_after=cursor_before,
            )
            self.database.audit(
                "source_ingestion_service",
                "source_sync_failed",
                {
                    "sync_id": sync_id,
                    "source_id": source_id,
                    "scope": scope,
                    "error_type": type(exc).__name__,
                },
                company_id=options.get("company_id"),
            )
            METRICS.increment("source_sync_failed_total")
            raise SourceSyncError(safe_error) from exc
        except Exception as exc:
            safe_error = f"Unexpected connector failure: {type(exc).__name__}"
            self.database.complete_source_sync(
                sync_id,
                "failed",
                error=safe_error,
                cursor_after=cursor_before,
            )
            METRICS.increment("source_sync_failed_total")
            raise SourceSyncError(safe_error) from exc
        except BaseException as exc:
            self.database.complete_source_sync(
                sync_id,
                "failed",
                error=f"Source sync interrupted: {type(exc).__name__}",
                cursor_after=cursor_before,
            )
            raise

    def _sync_sec_edgar(
        self,
        definition: SourceDefinition,
        client: SourceHttpClient,
        cursor: dict[str, Any],
        **options: Any,
    ) -> dict[str, Any]:
        mode = options.get("mode", "company")
        if mode == "universe":
            return self._sync_sec_universe(definition, client, cursor, options)
        if mode != "company":
            raise SourceSyncError("SEC mode must be company or universe")
        return self._sync_sec_company(definition, client, cursor, options)

    def _sync_sec_universe(
        self,
        definition: SourceDefinition,
        client: SourceHttpClient,
        cursor: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        response = client.request(
            "GET",
            definition.endpoints["universe"],
            conditional=cursor,
        )
        if response.not_modified:
            return {"status": "not_modified", "companies_seen": 0, "cursor": cursor}
        payload = response.json()
        fields = payload.get("fields", [])
        if fields != ["cik", "name", "ticker", "exchange"]:
            raise SourceSyncError("SEC universe schema changed")
        rows = payload.get("data", [])
        limit = int(options.get("limit") or 0)
        if limit:
            rows = rows[:limit]
        snapshot = self._archive_response(
            definition,
            response,
            external_id="company-tickers-exchange",
            metadata={"record_count": len(rows)},
        )
        document = _document_for_snapshot(
            definition,
            snapshot,
            company_id=None,
            source_type="security_universe",
            title="SEC company tickers and exchanges",
            source_url=definition.endpoints["universe"],
            published_at=date.today().isoformat(),
            content=response.body.decode("utf-8"),
            metadata={"record_count": len(rows)},
        )
        self.database.upsert_document(document)

        grouped: dict[str, dict[str, Any]] = {}
        for cik, name, ticker, exchange in rows:
            normalized = str(cik).zfill(10)
            item = grouped.setdefault(
                normalized,
                {"name": str(name), "tickers": [], "exchanges": []},
            )
            if ticker and ticker not in item["tickers"]:
                item["tickers"].append(str(ticker))
            if exchange and exchange not in item["exchanges"]:
                item["exchanges"].append(str(exchange))

        created = 0
        updated = 0
        for cik, item in grouped.items():
            company_id = f"sec-{cik}"
            existing = self.database.get_company(company_id)
            metadata = dict(existing.get("metadata_json", {}) if existing else {})
            metadata.update(
                {
                    "cik": cik,
                    "all_tickers": item["tickers"],
                    "all_exchanges": item["exchanges"],
                    "identity_source": definition.id,
                    "identity_retrieved_at": utc_now(),
                }
            )
            self.database.upsert_company(
                {
                    "id": company_id,
                    "legal_name": item["name"],
                    "ticker": item["tickers"][0] if item["tickers"] else cik,
                    "exchange": item["exchanges"][0] if item["exchanges"] else "SEC",
                    "security_id": f"CIK{cik}",
                    "segment": existing["segment"] if existing else "",
                    "subsegment": existing["subsegment"] if existing else "",
                    "public_parent_id": existing.get("public_parent_id") if existing else None,
                    "eligible": existing["eligible"] if existing else False,
                    "demo": False,
                    "metadata": metadata,
                }
            )
            self.database.upsert_entity_identifier(
                company_id, "CIK", cik, definition.id, metadata={"primary": True}
            )
            for ticker in item["tickers"]:
                self.database.upsert_entity_identifier(
                    company_id, "TICKER", ticker, definition.id
                )
            if existing:
                updated += 1
            else:
                created += 1
        return {
            "companies_seen": len(grouped),
            "companies_created": created,
            "companies_updated": updated,
            "documents": 1,
            "bytes_archived": snapshot.byte_count,
            "cursor": _cursor_from_response(response),
        }

    def _sync_sec_company(
        self,
        definition: SourceDefinition,
        client: SourceHttpClient,
        cursor: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        company_id = options.get("company_id")
        company = self.database.get_company(company_id) if company_id else None
        cik = str(options.get("cik") or _company_cik(company) or "")
        if not cik:
            raise SourceSyncError("SEC company sync requires cik or a company with a CIK")
        cik = cik.strip().lstrip("0").zfill(10)
        company_id = company_id or f"sec-{cik}"
        as_of_date = str(options.get("as_of_date") or date.today().isoformat())
        date.fromisoformat(as_of_date)
        submissions_url = definition.endpoints["submissions"].format(cik=cik)
        facts_url = definition.endpoints["company_facts"].format(cik=cik)
        submissions_response = client.request("GET", submissions_url)
        facts_response = client.request("GET", facts_url)
        submissions = submissions_response.json()
        facts = facts_response.json()
        submissions_snapshot = self._archive_response(
            definition,
            submissions_response,
            external_id=f"CIK{cik}-submissions",
            metadata={"cik": cik},
        )
        facts_snapshot = self._archive_response(
            definition,
            facts_response,
            external_id=f"CIK{cik}-companyfacts",
            metadata={"cik": cik},
        )

        tickers = [str(value) for value in submissions.get("tickers") or []]
        exchanges = [str(value) for value in submissions.get("exchanges") or []]
        existing = self.database.get_company(company_id)
        metadata = dict(existing.get("metadata_json", {}) if existing else {})
        metadata.update(
            {
                "cik": cik,
                "all_tickers": tickers,
                "all_exchanges": exchanges,
                "identity_source": definition.id,
                "identity_retrieved_at": utc_now(),
            }
        )
        segment = str(options.get("segment") or (existing or {}).get("segment") or "")
        subsegment = str(
            options.get("subsegment") or (existing or {}).get("subsegment") or ""
        )
        self.database.upsert_company(
            {
                "id": company_id,
                "legal_name": submissions.get("name") or facts.get("entityName") or company_id,
                "ticker": tickers[0] if tickers else (existing or {}).get("ticker", cik),
                "exchange": exchanges[0] if exchanges else (existing or {}).get("exchange", "SEC"),
                "security_id": f"CIK{cik}",
                "segment": segment,
                "subsegment": subsegment,
                "public_parent_id": (existing or {}).get("public_parent_id"),
                "eligible": bool(tickers and exchanges),
                "demo": False,
                "metadata": metadata,
            }
        )
        self.database.upsert_entity_identifier(company_id, "CIK", cik, definition.id)
        for ticker in tickers:
            self.database.upsert_entity_identifier(company_id, "TICKER", ticker, definition.id)

        submissions_document = _document_for_snapshot(
            definition,
            submissions_snapshot,
            company_id=company_id,
            source_type="regulatory_filing_index",
            title="EDGAR submissions history",
            source_url=_public_url(definition, submissions_url),
            published_at=as_of_date,
            content=submissions_response.body.decode("utf-8"),
            metadata={"cik": cik},
        )
        facts_document = _document_for_snapshot(
            definition,
            facts_snapshot,
            company_id=company_id,
            source_type="xbrl_company_facts",
            title="EDGAR XBRL company facts",
            source_url=_public_url(definition, facts_url),
            published_at=as_of_date,
            content=facts_response.body.decode("utf-8"),
            metadata={"cik": cik},
        )
        self.database.upsert_document(submissions_document)
        self.database.upsert_document(facts_document)
        financial_claims = _persist_sec_financial_claims(
            self.database,
            company_id,
            facts_document["id"],
            facts,
            as_of_date,
        )

        filing_limit = int(
            options.get("limit")
            or definition.options.get("default_filing_limit", 3)
        )
        filing_records = _recent_sec_filings(
            submissions,
            set(definition.options.get("forms", [])),
            as_of_date,
            filing_limit,
        )
        filing_documents = 0
        filing_bytes = 0
        latest_accession = cursor.get("latest_accession")
        for filing in filing_records:
            accession = filing["accessionNumber"]
            filing_url = definition.endpoints["filing"].format(
                cik_unpadded=str(int(cik)),
                accession_compact=accession.replace("-", ""),
                primary_document=filing["primaryDocument"],
            )
            filing_response = client.request("GET", filing_url)
            snapshot = self._archive_response(
                definition,
                filing_response,
                external_id=accession,
                metadata={"cik": cik, "form": filing["form"]},
            )
            normalized_text = _html_to_text(filing_response.body)
            normalized_path = self.store.put_normalized_text(snapshot, normalized_text)
            document = _document_for_snapshot(
                definition,
                snapshot,
                company_id=company_id,
                source_type="regulatory_filing",
                title=f"{filing['form']} filed {filing['filingDate']}",
                source_url=filing_url,
                published_at=filing["filingDate"],
                content=normalized_text,
                metadata={
                    **filing,
                    "cik": cik,
                    "normalized_text_path": str(normalized_path),
                },
            )
            document["injection_flags"] = detect_prompt_injection(normalized_text[:100_000])
            self.database.upsert_document(document)
            filing_documents += 1
            filing_bytes += snapshot.byte_count
            if not latest_accession:
                latest_accession = accession

        return {
            "company_id": company_id,
            "documents": 2 + filing_documents,
            "filings": filing_documents,
            "financial_claims": financial_claims,
            "bytes_archived": (
                submissions_snapshot.byte_count
                + facts_snapshot.byte_count
                + filing_bytes
            ),
            "cursor": {
                "latest_accession": latest_accession,
                "last_as_of_date": as_of_date,
            },
        }

    def _sync_gleif(
        self,
        definition: SourceDefinition,
        client: SourceHttpClient,
        cursor: dict[str, Any],
        **options: Any,
    ) -> dict[str, Any]:
        company_id = str(options.get("company_id") or "")
        company = self.database.get_company(company_id)
        if not company:
            raise SourceSyncError("GLEIF sync requires an existing company_id")
        legal_name = company["legal_name"]
        response = client.request(
            "GET",
            definition.endpoints["search"],
            params={
                "filter[entity.legalName]": legal_name,
                "page[size]": int(definition.options.get("result_limit", 10)),
            },
        )
        payload = response.json()
        search_mode = "legal_name_filter"
        archived_bytes = 0
        if not payload.get("data"):
            fuzzy_response = client.request(
                "GET",
                definition.endpoints["fuzzy"],
                params={"field": "entity.legalName", "q": legal_name},
            )
            fuzzy_payload = fuzzy_response.json()
            fuzzy_snapshot = self._archive_response(
                definition,
                fuzzy_response,
                external_id=f"fuzzy-name-search-{company_id}",
                metadata={"company_id": company_id, "legal_name": legal_name},
            )
            archived_bytes += fuzzy_snapshot.byte_count
            completion = next(iter(fuzzy_payload.get("data", [])), None)
            lei = (
                completion.get("relationships", {})
                .get("lei-records", {})
                .get("data", {})
                .get("id")
                if completion
                else None
            )
            if lei:
                response = client.request(
                    "GET", definition.endpoints["record"].format(lei=lei)
                )
                canonical_payload = response.json()
                canonical_item = canonical_payload.get("data")
                payload = {"data": [canonical_item] if canonical_item else []}
                search_mode = "fuzzy_completion"
        snapshot = self._archive_response(
            definition,
            response,
            external_id=f"name-search-{company_id}",
            metadata={"company_id": company_id, "legal_name": legal_name},
        )
        archived_bytes += snapshot.byte_count
        results = payload.get("data", [])
        best: tuple[float, dict[str, Any]] | None = None
        for item in results:
            candidate_name = (
                item.get("attributes", {})
                .get("entity", {})
                .get("legalName", {})
                .get("name", "")
            )
            score = _name_similarity(
                legal_name,
                candidate_name,
                set(definition.options.get("legal_suffixes", [])),
            )
            if best is None or score > best[0]:
                best = (score, item)
        threshold = float(definition.options.get("minimum_name_similarity", 0.82))
        matched = bool(best and best[0] >= threshold)
        metadata = {
            "query_name": legal_name,
            "candidate_count": len(results),
            "matched": matched,
            "match_score": round(best[0], 6) if best else 0.0,
            "search_mode": search_mode,
        }
        document = _document_for_snapshot(
            definition,
            snapshot,
            company_id=company_id,
            source_type="entity_identity_search",
            title=f"GLEIF identity search for {legal_name}",
            source_url=_public_url(definition, definition.endpoints["search"]),
            published_at=date.today().isoformat(),
            content=response.body.decode("utf-8"),
            metadata=metadata,
        )
        self.database.upsert_document(document)
        if not matched or best is None:
            return {
                "company_id": company_id,
                "matches": 0,
                "documents": 1,
                "bytes_archived": archived_bytes,
                "cursor": {"last_checked_at": utc_now()},
            }
        attributes = best[1].get("attributes", {})
        lei = str(attributes.get("lei") or best[1].get("id") or "")
        if not lei:
            raise SourceSyncError("GLEIF matched record did not contain an LEI")
        self.database.upsert_entity_identifier(
            company_id,
            "LEI",
            lei,
            definition.id,
            confidence=best[0],
            metadata={
                "registration_status": attributes.get("registration", {}).get("status"),
                "matched_legal_name": (
                    attributes.get("entity", {}).get("legalName", {}).get("name")
                ),
            },
        )
        company_metadata = dict(company.get("metadata_json", {}))
        company_metadata["lei"] = lei
        company_metadata["gleif_match_score"] = best[0]
        self.database.upsert_company(
            {
                "id": company["id"],
                "legal_name": company["legal_name"],
                "ticker": company["ticker"],
                "exchange": company["exchange"],
                "security_id": company["security_id"],
                "segment": company["segment"],
                "subsegment": company["subsegment"],
                "public_parent_id": company.get("public_parent_id"),
                "eligible": company["eligible"],
                "demo": company["demo"],
                "metadata": company_metadata,
            }
        )
        return {
            "company_id": company_id,
            "matches": 1,
            "lei": lei,
            "match_score": round(best[0], 6),
            "documents": 1,
            "bytes_archived": archived_bytes,
            "cursor": {"last_checked_at": utc_now(), "lei": lei},
        }

    def _sync_gdelt(
        self,
        definition: SourceDefinition,
        client: SourceHttpClient,
        cursor: dict[str, Any],
        **options: Any,
    ) -> dict[str, Any]:
        company_id = str(options.get("company_id") or "")
        company = self.database.get_company(company_id)
        if not company:
            raise SourceSyncError("GDELT sync requires an existing company_id")
        as_of_date = date.fromisoformat(
            str(options.get("as_of_date") or date.today().isoformat())
        )
        lookback_days = min(max(int(options.get("lookback_days") or 90), 1), 365)
        start_date = as_of_date - timedelta(days=lookback_days)
        limit = min(
            max(
                int(options.get("limit") or definition.options.get("default_result_limit", 25)),
                1,
            ),
            250,
        )
        aliases = _company_search_aliases(company, definition.options)
        identity_query = "(" + " OR ".join(f'"{item}"' for item in aliases) + ")"
        query = f'{identity_query} {definition.options["topic_query"]}'
        response = client.request(
            "GET",
            definition.endpoints["search"],
            params={
                "query": query,
                "mode": "ArtList",
                "maxrecords": limit,
                "format": "json",
                "sort": "HybridRel",
                "startdatetime": start_date.strftime("%Y%m%d000000"),
                "enddatetime": as_of_date.strftime("%Y%m%d235959"),
            },
        )
        payload = response.json()
        snapshot = self._archive_response(
            definition,
            response,
            external_id=f"company-search-{company_id}-{as_of_date.isoformat()}",
            metadata={"company_id": company_id, "query": query},
        )
        articles = payload.get("articles", [])
        document_count = 0
        latest_seen = cursor.get("latest_seen")
        for article in articles:
            article_url = str(article.get("url") or "")
            if not article_url.startswith("https://"):
                continue
            article_text = json.dumps(article, sort_keys=True)
            published_at = _gdelt_date(article.get("seendate"), as_of_date)
            document = make_document(
                company_id,
                "news_discovery",
                definition.source_tier,
                definition.publisher,
                str(article.get("title") or "Untitled discovery result"),
                article_url,
                published_at,
                article_text,
            )
            document["local_path"] = str(snapshot.content_path)
            document["licence_notes"] = definition.licence_notes
            document["parser_version"] = "gdelt-doc-2.0-metadata-1.0"
            document["injection_flags"] = detect_prompt_injection(
                str(article.get("title") or "")
            )
            document["metadata"] = {
                "source_id": definition.id,
                "domain": article.get("domain"),
                "language": article.get("language"),
                "source_country": article.get("sourcecountry"),
                "tone": article.get("tone"),
                "discovery_only": True,
            }
            self.database.upsert_document(document)
            document_count += 1
            seen = str(article.get("seendate") or "")
            if seen and (not latest_seen or seen > latest_seen):
                latest_seen = seen
        return {
            "company_id": company_id,
            "articles_seen": len(articles),
            "documents": document_count,
            "bytes_archived": snapshot.byte_count,
            "cursor": {"latest_seen": latest_seen, "last_checked_at": utc_now()},
        }

    def _archive_response(
        self,
        definition: SourceDefinition,
        response: FetchResponse,
        *,
        external_id: str,
        metadata: dict[str, Any],
    ) -> RawSnapshot:
        return self.store.put(
            definition.id,
            response.body,
            source_url=response.url,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            external_id=external_id,
            headers=response.headers,
            metadata=metadata,
        )


def _sync_scope(definition: SourceDefinition, options: dict[str, Any]) -> str:
    if definition.connector == "sec_edgar" and options.get("mode") == "universe":
        limit = int(options.get("limit") or 0)
        return f"universe:{limit or 'all'}"
    company_id = options.get("company_id")
    cik = options.get("cik")
    return f"company:{company_id or cik or 'unspecified'}"


def _company_cik(company: dict[str, Any] | None) -> str | None:
    if not company:
        return None
    metadata = company.get("metadata_json", {})
    return metadata.get("cik")


def _public_url(definition: SourceDefinition, endpoint: str) -> str:
    if endpoint.startswith("https://"):
        return endpoint
    return f"{definition.base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def _cursor_from_response(response: FetchResponse) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "etag": response.headers.get("etag"),
            "last_modified": response.headers.get("last-modified"),
            "last_checked_at": utc_now(),
        }.items()
        if value
    }


def _document_for_snapshot(
    definition: SourceDefinition,
    snapshot: RawSnapshot,
    *,
    company_id: str | None,
    source_type: str,
    title: str,
    source_url: str,
    published_at: str,
    content: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    document = make_document(
        company_id,  # type: ignore[arg-type]
        source_type,
        definition.source_tier,
        definition.publisher,
        title,
        source_url,
        published_at,
        content,
    )
    document["content_hash"] = snapshot.content_hash
    document["local_path"] = str(snapshot.content_path)
    document["licence_notes"] = definition.licence_notes
    document["parser_version"] = "source-platform-1.0"
    document["metadata"] = {"source_id": definition.id, **metadata}
    return document


def _persist_sec_financial_claims(
    database: Database,
    company_id: str,
    document_id: str,
    facts: dict[str, Any],
    as_of_date: str,
) -> int:
    revenue = _latest_annual_xbrl_fact(
        facts,
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        as_of_date,
    )
    operating = _latest_annual_xbrl_fact(
        facts,
        ["OperatingIncomeLoss"],
        as_of_date,
        required_end=revenue.get("end") if revenue else None,
    )
    count = 0
    if revenue:
        database.upsert_claim(
            EvidenceClaim(
                id=str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{document_id}:revenue:{revenue['end']}",
                    )
                ),
                company_id=company_id,
                document_id=document_id,
                claim_type="total_revenue",
                value_numeric=float(revenue["val"]) / 1_000_000.0,
                value_text=None,
                unit="USD million",
                period_end=revenue["end"],
                confidence=0.99,
                evidence_span=(
                    f"SEC XBRL annual revenue fact for period ending {revenue['end']}."
                ),
                page_or_section=f"us-gaap:{revenue['_concept']}",
                source_tier="1",
                published_at=revenue["filed"],
            ),
            extraction_method="sec_xbrl",
        )
        count += 1
    if revenue and operating and float(revenue["val"]):
        margin_pct = float(operating["val"]) / float(revenue["val"]) * 100.0
        database.upsert_claim(
            EvidenceClaim(
                id=str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{document_id}:margin:{operating['end']}",
                    )
                ),
                company_id=company_id,
                document_id=document_id,
                claim_type="operating_margin",
                value_numeric=margin_pct,
                value_text=None,
                unit="percent",
                period_end=operating["end"],
                confidence=0.98,
                evidence_span=(
                    "Calculated from SEC XBRL OperatingIncomeLoss divided by annual "
                    f"revenue for period ending {operating['end']}."
                ),
                page_or_section="calculation:OperatingIncomeLoss/revenue",
                source_tier="1",
                published_at=max(operating["filed"], revenue["filed"]),
            ),
            extraction_method="deterministic_sec_xbrl_calculation",
        )
        count += 1
    return count


def _recent_sec_filings(
    submissions: dict[str, Any],
    forms: set[str],
    as_of_date: str,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    recent = submissions.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", [])
    records: list[dict[str, Any]] = []
    for index, accession in enumerate(accessions):
        record = {
            key: values[index]
            for key, values in recent.items()
            if isinstance(values, list) and index < len(values)
        }
        if record.get("form") not in forms:
            continue
        if str(record.get("filingDate", "9999-99-99")) > as_of_date:
            continue
        if not accession or not record.get("primaryDocument"):
            continue
        records.append(record)
        if len(records) >= max(limit, 0):
            break
    return records


def _html_to_text(body: bytes) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(body, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _name_similarity(left: str, right: str, legal_suffixes: set[str]) -> float:
    def normalize(value: str) -> str:
        tokens = re.sub(r"[^a-z0-9]+", " ", value.casefold()).split()
        return " ".join(token for token in tokens if token not in legal_suffixes)

    return SequenceMatcher(None, normalize(left), normalize(right)).ratio()


def _company_search_aliases(
    company: dict[str, Any], options: dict[str, Any]
) -> list[str]:
    suffixes = set(options.get("legal_suffixes", []))
    tokens = re.sub(
        r"[^A-Za-z0-9]+", " ", str(company["legal_name"])
    ).split()
    base_name = " ".join(token for token in tokens if token.casefold() not in suffixes)
    aliases = [base_name or str(company["legal_name"])]
    ticker = str(company.get("ticker") or "").strip()
    if options.get("include_ticker") and len(ticker) >= 3 and ticker not in aliases:
        aliases.append(ticker)
    return aliases


def _gdelt_date(value: Any, fallback: date) -> str:
    text = str(value or "")
    for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return fallback.isoformat()
