from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database import Database, utc_now
from .models import EvidenceClaim
from .security import detect_prompt_injection, validate_external_url
from .telemetry import METRICS, timed_operation


LOGGER = logging.getLogger(__name__)


class IngestionError(RuntimeError):
    pass


class HttpSourceConnector:
    """Read-only HTTPS connector with rate limiting, retries, hashing, and SSRF checks."""

    def __init__(
        self,
        user_agent: str,
        minimum_interval_seconds: float = 0.12,
        timeout_seconds: float = 30.0,
    ):
        self.user_agent = user_agent
        self.minimum_interval_seconds = minimum_interval_seconds
        self.timeout_seconds = timeout_seconds
        self._last_request_at = 0.0

    def fetch(self, url: str, attempts: int = 3) -> tuple[bytes, dict[str, str]]:
        validate_external_url(url, resolve_dns=True)
        error: Exception | None = None
        for attempt in range(attempts):
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.minimum_interval_seconds:
                time.sleep(self.minimum_interval_seconds - elapsed)
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json,text/html,application/xhtml+xml,application/pdf",
                },
            )
            try:
                with timed_operation("source_fetch", LOGGER):
                    with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                        body = response.read()
                        headers = {key.lower(): value for key, value in response.headers.items()}
                self._last_request_at = time.monotonic()
                METRICS.increment("source_fetch_total")
                return body, headers
            except (urllib.error.URLError, TimeoutError) as exc:
                error = exc
                METRICS.increment("source_fetch_retry_total")
                if attempt + 1 < attempts:
                    time.sleep(2**attempt)
        raise IngestionError(f"Unable to retrieve {url}: {error}")


class SecEdgarConnector(HttpSourceConnector):
    BASE_URL = "https://data.sec.gov"

    def fetch_submissions(self, cik: str) -> dict[str, Any]:
        normalized = cik.strip().lstrip("0").zfill(10)
        body, _ = self.fetch(f"{self.BASE_URL}/submissions/CIK{normalized}.json")
        return json.loads(body.decode("utf-8"))

    def fetch_company_facts(self, cik: str) -> dict[str, Any]:
        normalized = cik.strip().lstrip("0").zfill(10)
        body, _ = self.fetch(f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{normalized}.json")
        return json.loads(body.decode("utf-8"))


def ingest_sec_company(
    database: Database,
    connector: SecEdgarConnector,
    cik: str,
    segment: str,
    subsegment: str,
    as_of_date: str,
    source_dir: Path,
) -> dict[str, Any]:
    """Ingest a US issuer identity and latest annual revenue/margin from SEC XBRL.

    This adapter intentionally stops at authoritative financial facts. Exposure,
    moat, forecasts, and risk require separately sourced evidence and remain gated.
    """
    normalized_cik = cik.strip().lstrip("0").zfill(10)
    submissions = connector.fetch_submissions(normalized_cik)
    facts = connector.fetch_company_facts(normalized_cik)
    company_id = f"sec-{normalized_cik}"
    tickers = submissions.get("tickers") or []
    exchanges = submissions.get("exchanges") or []
    database.upsert_company(
        {
            "id": company_id,
            "legal_name": submissions.get("name") or facts.get("entityName") or company_id,
            "ticker": tickers[0] if tickers else normalized_cik,
            "exchange": exchanges[0] if exchanges else "SEC",
            "security_id": f"CIK{normalized_cik}",
            "segment": segment,
            "subsegment": subsegment,
            "eligible": True,
            "demo": False,
            "metadata": {
                "cik": normalized_cik,
                "all_tickers": tickers,
                "all_exchanges": exchanges,
                "source": "SEC EDGAR",
            },
        }
    )

    source_dir.mkdir(parents=True, exist_ok=True)
    submissions_path = source_dir / f"CIK{normalized_cik}-submissions.json"
    facts_path = source_dir / f"CIK{normalized_cik}-companyfacts.json"
    submissions_text = json.dumps(submissions, indent=2, sort_keys=True)
    facts_text = json.dumps(facts, indent=2, sort_keys=True)
    submissions_path.write_text(submissions_text, encoding="utf-8")
    facts_path.write_text(facts_text, encoding="utf-8")

    submissions_doc = make_document(
        company_id,
        "regulatory_filing_index",
        "1",
        "U.S. Securities and Exchange Commission",
        "EDGAR submissions history",
        f"https://data.sec.gov/submissions/CIK{normalized_cik}.json",
        as_of_date,
        submissions_text,
    )
    submissions_doc["local_path"] = str(submissions_path)
    facts_doc = make_document(
        company_id,
        "xbrl_company_facts",
        "1",
        "U.S. Securities and Exchange Commission",
        "EDGAR XBRL company facts",
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{normalized_cik}.json",
        as_of_date,
        facts_text,
    )
    facts_doc["local_path"] = str(facts_path)
    database.upsert_document(submissions_doc)
    database.upsert_document(facts_doc)

    revenue_fact = _latest_annual_xbrl_fact(
        facts,
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        as_of_date,
    )
    operating_fact = _latest_annual_xbrl_fact(
        facts, ["OperatingIncomeLoss"], as_of_date, required_end=revenue_fact.get("end") if revenue_fact else None
    )
    claim_count = 0
    if revenue_fact:
        revenue_millions = float(revenue_fact["val"]) / 1_000_000.0
        database.upsert_claim(
            EvidenceClaim(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{facts_doc['id']}:revenue:{revenue_fact['end']}")),
                company_id=company_id,
                document_id=facts_doc["id"],
                claim_type="total_revenue",
                value_numeric=revenue_millions,
                value_text=None,
                unit="USD million",
                period_end=revenue_fact["end"],
                confidence=0.99,
                evidence_span=f"SEC XBRL annual revenue fact for period ending {revenue_fact['end']}.",
                page_or_section=f"us-gaap:{revenue_fact['_concept']}",
                source_tier="1",
                published_at=revenue_fact["filed"],
            ),
            extraction_method="sec_xbrl",
        )
        claim_count += 1
    if revenue_fact and operating_fact and float(revenue_fact["val"]) != 0:
        margin_pct = float(operating_fact["val"]) / float(revenue_fact["val"]) * 100.0
        database.upsert_claim(
            EvidenceClaim(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{facts_doc['id']}:margin:{operating_fact['end']}")),
                company_id=company_id,
                document_id=facts_doc["id"],
                claim_type="operating_margin",
                value_numeric=margin_pct,
                value_text=None,
                unit="percent",
                period_end=operating_fact["end"],
                confidence=0.98,
                evidence_span=(
                    f"Calculated from SEC XBRL OperatingIncomeLoss divided by annual revenue "
                    f"for period ending {operating_fact['end']}."
                ),
                page_or_section="calculation:OperatingIncomeLoss/revenue",
                source_tier="1",
                published_at=max(operating_fact["filed"], revenue_fact["filed"]),
            ),
            extraction_method="deterministic_sec_xbrl_calculation",
        )
        claim_count += 1
    return {
        "company_id": company_id,
        "documents": 2,
        "financial_claims": claim_count,
        "source_dir": str(source_dir),
        "warning": "Qualitative and forward-looking evidence is still required before ranking.",
    }


def _latest_annual_xbrl_fact(
    company_facts: dict[str, Any],
    concepts: list[str],
    as_of_date: str,
    required_end: str | None = None,
) -> dict[str, Any] | None:
    namespace = company_facts.get("facts", {}).get("us-gaap", {})
    candidates: list[dict[str, Any]] = []
    for concept in concepts:
        fact = namespace.get(concept, {})
        for item in fact.get("units", {}).get("USD", []):
            if item.get("form") not in {"10-K", "20-F", "40-F"}:
                continue
            if item.get("fp") not in {"FY", None}:
                continue
            if item.get("filed", "9999-99-99") > as_of_date:
                continue
            if required_end and item.get("end") != required_end:
                continue
            if "val" not in item or "end" not in item or "filed" not in item:
                continue
            candidate = dict(item)
            candidate["_concept"] = concept
            candidates.append(candidate)
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item["end"], item["filed"], item.get("accn", "")))


class EvidencePackageIngestor:
    """Validates and persists a normalized evidence package.

    Document parsing is deliberately separated from research judgment. Production
    parser adapters should emit this package contract before any agent sees content.
    """

    def __init__(self, database: Database):
        self.database = database

    def ingest(self, package: dict[str, Any]) -> dict[str, int]:
        required = {"companies", "documents", "claims"}
        missing = required.difference(package)
        if missing:
            raise IngestionError(f"Evidence package missing fields: {sorted(missing)}")

        for company in package["companies"]:
            self.database.upsert_company(company)

        for document in package["documents"]:
            injection_flags = detect_prompt_injection(document.get("text_preview", ""))
            item = dict(document)
            item["injection_flags"] = injection_flags
            if injection_flags:
                METRICS.increment("source_prompt_injection_flags_total")
            self.database.upsert_document(item)

        for raw in package["claims"]:
            claim_payload = dict(raw)
            extraction_method = claim_payload.pop("extraction_method", "structured")
            self.database.upsert_claim(EvidenceClaim(**claim_payload), extraction_method)

        return {
            "companies": len(package["companies"]),
            "documents": len(package["documents"]),
            "claims": len(package["claims"]),
        }

    def ingest_file(self, path: Path) -> dict[str, int]:
        with path.open("r", encoding="utf-8") as handle:
            return self.ingest(json.load(handle))


def make_document(
    company_id: str,
    source_type: str,
    source_tier: str,
    publisher: str,
    title: str,
    source_url: str,
    published_at: str,
    content: str,
    demo: bool = False,
) -> dict[str, Any]:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, source_url + content_hash)),
        "company_id": company_id,
        "source_type": source_type,
        "source_tier": source_tier,
        "publisher": publisher,
        "title": title,
        "source_url": source_url,
        "published_at": published_at,
        "retrieved_at": utc_now(),
        "content_hash": content_hash,
        "parser_version": "normalized-package-1.0",
        "licence_notes": "Synthetic demo source" if demo else "Review source terms",
        "text_preview": content[:2000],
        "metadata": {"demo": demo},
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
