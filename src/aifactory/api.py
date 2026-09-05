from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .config import get_settings
from .evaluation import compare_runs, evaluate_run
from .extraction import EvidenceExtractionError
from .models import ReviewStatus
from .service import PublicationGateError, ResearchService
from .sources import SourceSyncError
from .telemetry import METRICS


settings = get_settings()
service = ResearchService(settings)

app = FastAPI(
    title="AI Factory Research Platform",
    version="0.1.0",
    description="Auditable point-in-time research and ranking API",
)


class RunRequest(BaseModel):
    as_of_date: str
    company_ids: list[str] | None = None
    generate_report: bool = False


class ReviewRequest(BaseModel):
    reviewer: str = Field(min_length=2, max_length=120)
    decision: ReviewStatus
    comment: str = Field(default="", max_length=2000)
    overrides: dict[str, Any] = Field(default_factory=dict)


class PublishRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=120)


class SourceSyncRequest(BaseModel):
    mode: str = Field(default="company", pattern="^(company|universe)$")
    company_id: str | None = None
    cik: str | None = None
    as_of_date: str | None = None
    segment: str | None = None
    subsegment: str | None = None
    limit: int | None = Field(default=None, ge=1, le=10000)
    lookback_days: int | None = Field(default=None, ge=1, le=365)


class EvidenceExtractionRequest(BaseModel):
    company_id: str
    document_id: str | None = None
    as_of_date: str | None = None
    document_limit: int = Field(default=3, ge=1, le=20)


class ProposalReviewRequest(BaseModel):
    decision: str = Field(pattern="^(accepted|rejected)$")
    reviewer: str = Field(min_length=2, max_length=120)
    comment: str = Field(default="", max_length=2000)


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/", response_class=HTMLResponse)
def workbench() -> str:
    return (Path(__file__).parent / "web" / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aifactory-research"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    try:
        service.database.list_runs(limit=1)
        return {"status": "ready", "database": str(settings.db_path)}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=type(exc).__name__) from exc


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render_prometheus()


@app.get("/api/v1/config/segments", dependencies=[Depends(require_api_key)])
def segments() -> list[dict[str, Any]]:
    return service.database.list_market_segments()


@app.get("/api/v1/companies", dependencies=[Depends(require_api_key)])
def companies(eligible_only: bool = False) -> list[dict[str, Any]]:
    return service.database.list_companies(eligible_only=eligible_only)


@app.get("/api/v1/companies/{company_id}", dependencies=[Depends(require_api_key)])
def company(company_id: str) -> dict[str, Any]:
    item = service.database.get_company(company_id)
    if not item:
        raise HTTPException(status_code=404, detail="Company not found")
    item["documents"] = service.database.list_documents(company_id)
    item["identifiers"] = service.database.list_entity_identifiers(company_id)
    return item


@app.get("/api/v1/sources", dependencies=[Depends(require_api_key)])
def sources() -> dict[str, Any]:
    return {
        "catalog_version": service.source_catalog.version,
        "sources": service.source_service.list_sources(),
    }


@app.get("/api/v1/source-syncs", dependencies=[Depends(require_api_key)])
def source_syncs(
    source_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    return service.source_service.list_syncs(source_id, limit)


@app.post("/api/v1/sources/{source_id}/sync", dependencies=[Depends(require_api_key)])
async def source_sync(source_id: str, payload: SourceSyncRequest) -> dict[str, Any]:
    try:
        options = payload.model_dump(exclude_none=True)
        return await asyncio.to_thread(service.source_service.sync, source_id, **options)
    except SourceSyncError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/evidence/extract", dependencies=[Depends(require_api_key)])
async def extract_evidence(payload: EvidenceExtractionRequest) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            service.evidence_proposals.extract,
            payload.company_id,
            document_id=payload.document_id,
            as_of_date=payload.as_of_date,
            document_limit=payload.document_limit,
        )
    except EvidenceExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/evidence/proposals", dependencies=[Depends(require_api_key)])
def claim_proposals(
    company_id: str | None = None,
    status: str | None = Query(default=None, pattern="^(pending|accepted|rejected|invalid)$"),
    limit: int = Query(default=250, ge=1, le=1000),
) -> list[dict[str, Any]]:
    return service.database.list_claim_proposals(company_id, status, limit)


@app.post(
    "/api/v1/evidence/proposals/{proposal_id}/review",
    dependencies=[Depends(require_api_key)],
)
def review_claim_proposal(
    proposal_id: str, payload: ProposalReviewRequest
) -> dict[str, Any]:
    try:
        return service.evidence_proposals.review(
            proposal_id, payload.decision, payload.reviewer, payload.comment
        )
    except EvidenceExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/v1/demo/seed", dependencies=[Depends(require_api_key)])
def seed_demo() -> dict[str, int]:
    return service.seed_demo()


@app.post("/api/v1/runs", dependencies=[Depends(require_api_key)])
async def create_run(payload: RunRequest) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            service.run_research,
            payload.as_of_date,
            payload.company_ids,
            payload.generate_report,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/runs", dependencies=[Depends(require_api_key)])
def runs(limit: int = Query(default=50, ge=1, le=250)) -> list[dict[str, Any]]:
    return service.database.list_runs(limit=limit)


@app.get("/api/v1/runs/{run_id}", dependencies=[Depends(require_api_key)])
def run(run_id: str) -> dict[str, Any]:
    item = service.database.get_run(run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Run not found")
    return item


@app.get("/api/v1/runs/{run_id}/rankings", dependencies=[Depends(require_api_key)])
def rankings(run_id: str) -> list[dict[str, Any]]:
    return service.database.list_rankings(run_id)


@app.get("/api/v1/runs/{run_id}/assessments", dependencies=[Depends(require_api_key)])
def assessments(run_id: str) -> list[dict[str, Any]]:
    return service.database.list_assessments(run_id)


@app.get(
    "/api/v1/runs/{run_id}/assessments/{company_id}",
    dependencies=[Depends(require_api_key)],
)
def assessment(run_id: str, company_id: str) -> dict[str, Any]:
    item = service.database.get_assessment(run_id, company_id)
    if not item:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return item


@app.post(
    "/api/v1/runs/{run_id}/assessments/{company_id}/reviews",
    dependencies=[Depends(require_api_key)],
)
def review(run_id: str, company_id: str, payload: ReviewRequest) -> dict[str, str]:
    try:
        review_id = service.review(
            run_id,
            company_id,
            payload.reviewer,
            payload.decision,
            payload.comment,
            payload.overrides,
        )
        return {"review_id": review_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/runs/{run_id}/publish", dependencies=[Depends(require_api_key)])
def publish(run_id: str, payload: PublishRequest) -> dict[str, str]:
    try:
        return {"report": str(service.publish(run_id, payload.actor))}
    except PublicationGateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/runs/{run_id}/report", dependencies=[Depends(require_api_key)])
def generate_report(run_id: str) -> dict[str, str]:
    try:
        report_path, manifest_path = service.reporter.generate(run_id)
        return {"report": str(report_path), "manifest": str(manifest_path)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/runs/{run_id}/report", dependencies=[Depends(require_api_key)])
def download_report(run_id: str) -> FileResponse:
    path = settings.report_dir / f"{run_id}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report has not been generated")
    return FileResponse(path, media_type="text/markdown", filename=path.name)


@app.get("/api/v1/runs/{run_id}/audit", dependencies=[Depends(require_api_key)])
def audit(run_id: str, limit: int = Query(default=500, ge=1, le=2000)) -> list[dict[str, Any]]:
    return service.database.list_audit_events(run_id, limit=limit)


@app.get("/api/v1/runs/{run_id}/evaluation", dependencies=[Depends(require_api_key)])
def evaluation(run_id: str) -> dict[str, Any]:
    try:
        return evaluate_run(service.database, run_id, service.scoring_policy)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/runs/{previous_run_id}/compare/{current_run_id}", dependencies=[Depends(require_api_key)])
def comparison(previous_run_id: str, current_run_id: str) -> dict[str, Any]:
    try:
        return compare_runs(service.database, previous_run_id, current_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
