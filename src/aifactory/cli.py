from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .config import get_settings
from .extraction import EvidenceExtractionError
from .models import ReviewStatus
from .evaluation import compare_runs, evaluate_run
from .llm import ModelGatewayError, OfflineModelGateway
from .service import PublicationGateError, ResearchService
from .sources import SourceSyncError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aifactory",
        description="Auditable AI Factory growth-equity research platform",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Initialize the evidence database")
    subparsers.add_parser("seed-demo", help="Load 20 clearly synthetic demo companies")
    subparsers.add_parser("reset-demo", help="Remove only synthetic demo data and its runs")

    run = subparsers.add_parser("run", help="Execute a point-in-time research run")
    run.add_argument("--as-of-date", required=True, help="Research cutoff in YYYY-MM-DD")
    run.add_argument("--company-id", action="append", dest="company_ids")
    run.add_argument("--generate-report", action="store_true")

    refresh = subparsers.add_parser(
        "quarterly-refresh", help="Run a refresh using today's date as the research cutoff"
    )
    refresh.add_argument("--generate-report", action="store_true")

    subparsers.add_parser("list-runs", help="List recent research runs")
    subparsers.add_parser("list-companies", help="List the security universe")
    subparsers.add_parser(
        "model-check", help="Verify the configured model without exposing credentials"
    )
    subparsers.add_parser("source-list", help="List configured online data sources")
    source_syncs = subparsers.add_parser(
        "source-syncs", help="List recent online-source synchronization runs"
    )
    source_syncs.add_argument("--source-id")
    source_syncs.add_argument("--limit", type=int, default=100)

    source_sync = subparsers.add_parser(
        "source-sync", help="Synchronize one configured online source"
    )
    source_sync.add_argument("source_id")
    source_sync.add_argument("--mode", choices=["company", "universe"], default="company")
    source_sync.add_argument("--company-id")
    source_sync.add_argument("--cik")
    source_sync.add_argument("--as-of-date")
    source_sync.add_argument("--segment")
    source_sync.add_argument("--subsegment")
    source_sync.add_argument("--limit", type=int)
    source_sync.add_argument("--lookback-days", type=int)

    extract = subparsers.add_parser(
        "extract-evidence",
        help="Create review-only evidence proposals from normalized source documents",
    )
    extract.add_argument("--company-id", required=True)
    extract.add_argument("--document-id")
    extract.add_argument("--as-of-date")
    extract.add_argument("--document-limit", type=int, default=3)

    proposals = subparsers.add_parser(
        "list-proposals", help="List pending, accepted, rejected, or invalid claim proposals"
    )
    proposals.add_argument("--company-id")
    proposals.add_argument(
        "--status", choices=["pending", "accepted", "rejected", "invalid"]
    )
    proposals.add_argument("--limit", type=int, default=250)

    proposal_review = subparsers.add_parser(
        "review-proposal", help="Accept or reject a validated evidence proposal"
    )
    proposal_review.add_argument("proposal_id")
    proposal_review.add_argument(
        "--decision", choices=["accepted", "rejected"], required=True
    )
    proposal_review.add_argument("--reviewer", required=True)
    proposal_review.add_argument("--comment", default="")

    show = subparsers.add_parser("show-run", help="Show run metadata and rankings")
    show.add_argument("run_id")

    review = subparsers.add_parser("review", help="Record an analyst review")
    review.add_argument("run_id")
    review.add_argument("company_id")
    review.add_argument(
        "--decision",
        choices=[item.value for item in ReviewStatus],
        required=True,
    )
    review.add_argument("--reviewer", required=True)
    review.add_argument("--comment", default="")

    approve_top = subparsers.add_parser(
        "approve-ranked-demo", help="Approve every ranked company in a synthetic demo run"
    )
    approve_top.add_argument("run_id")
    approve_top.add_argument("--reviewer", default="demo-reviewer")

    publish = subparsers.add_parser("publish", help="Publish an analyst-approved run")
    publish.add_argument("run_id")
    publish.add_argument("--actor", required=True)

    report = subparsers.add_parser("generate-report", help="Generate a provisional report")
    report.add_argument("run_id")

    evaluate = subparsers.add_parser("evaluate", help="Run deterministic quality gates")
    evaluate.add_argument("run_id")

    compare = subparsers.add_parser("compare-runs", help="Explain ranking changes between runs")
    compare.add_argument("previous_run_id")
    compare.add_argument("current_run_id")

    ingest = subparsers.add_parser("ingest", help="Ingest a normalized JSON evidence package")
    ingest.add_argument("path", type=Path)

    sec = subparsers.add_parser(
        "ingest-sec", help="Ingest SEC identity and latest annual XBRL revenue/margin"
    )
    sec.add_argument("--cik", required=True)
    sec.add_argument("--segment", required=True)
    sec.add_argument("--subsegment", required=True)
    sec.add_argument("--as-of-date", required=True)

    serve = subparsers.add_parser("serve", help="Run the API and analyst workbench")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        service = ResearchService(get_settings())
        result = dispatch(service, args)
        if result is not None:
            _print_json(result)
        return 0
    except (
        ValueError,
        KeyError,
        EvidenceExtractionError,
        ModelGatewayError,
        PublicationGateError,
        SourceSyncError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def dispatch(service: ResearchService, args: argparse.Namespace) -> Any:
    if args.command == "init-db":
        return {"status": "initialized", "database": str(service.settings.db_path)}
    if args.command == "seed-demo":
        return service.seed_demo()
    if args.command == "reset-demo":
        service.reset_demo()
        return {"status": "demo data removed"}
    if args.command == "run":
        return service.run_research(
            args.as_of_date,
            company_ids=args.company_ids,
            generate_report=args.generate_report,
        )
    if args.command == "quarterly-refresh":
        return service.run_research(
            date.today().isoformat(), generate_report=args.generate_report
        )
    if args.command == "list-runs":
        return service.database.list_runs()
    if args.command == "list-companies":
        return service.database.list_companies()
    if args.command == "model-check":
        if isinstance(service.gateway, OfflineModelGateway):
            raise ValueError("Configure a model provider before running model-check")
        response = service.gateway.complete_json(
            "You are a connectivity check. Return only valid JSON and no explanation.",
            'Return exactly this object: {"status":"ok"}',
            {"type": "object", "required": ["status"]},
        )
        if response.get("status") != "ok":
            raise ModelGatewayError("Model returned an unexpected connectivity response")
        return {
            "status": "ok",
            "provider": service.gateway.provider,
            "model": service.settings.model_name,
        }
    if args.command == "source-list":
        return {
            "catalog_version": service.source_catalog.version,
            "sources": service.source_service.list_sources(),
        }
    if args.command == "source-syncs":
        if args.limit < 1 or args.limit > 1000:
            raise ValueError("--limit must be between 1 and 1000")
        return service.source_service.list_syncs(args.source_id, args.limit)
    if args.command == "source-sync":
        options = {
            "mode": args.mode,
            "company_id": args.company_id,
            "cik": args.cik,
            "as_of_date": args.as_of_date,
            "segment": args.segment,
            "subsegment": args.subsegment,
            "limit": args.limit,
            "lookback_days": args.lookback_days,
        }
        return service.source_service.sync(
            args.source_id,
            **{key: value for key, value in options.items() if value is not None},
        )
    if args.command == "extract-evidence":
        if args.document_limit < 1 or args.document_limit > 20:
            raise ValueError("--document-limit must be between 1 and 20")
        return service.evidence_proposals.extract(
            args.company_id,
            document_id=args.document_id,
            as_of_date=args.as_of_date,
            document_limit=args.document_limit,
        )
    if args.command == "list-proposals":
        if args.limit < 1 or args.limit > 1000:
            raise ValueError("--limit must be between 1 and 1000")
        return service.database.list_claim_proposals(
            args.company_id, args.status, args.limit
        )
    if args.command == "review-proposal":
        return service.evidence_proposals.review(
            args.proposal_id,
            args.decision,
            args.reviewer,
            args.comment,
        )
    if args.command == "show-run":
        return {
            "run": service.database.get_run(args.run_id),
            "rankings": service.database.list_rankings(args.run_id),
            "audit": service.database.list_audit_events(args.run_id),
        }
    if args.command == "review":
        return {
            "review_id": service.review(
                args.run_id,
                args.company_id,
                args.reviewer,
                args.decision,
                args.comment,
            )
        }
    if args.command == "approve-ranked-demo":
        rankings = service.database.list_rankings(args.run_id)
        for item in rankings:
            company = service.database.get_company(item["company_id"])
            if not company or not company["demo"]:
                raise ValueError("approve-ranked-demo may only approve synthetic companies")
            service.review(
                args.run_id,
                item["company_id"],
                args.reviewer,
                ReviewStatus.APPROVED,
                "Synthetic demonstration approval",
            )
        return {"approved": len(rankings)}
    if args.command == "publish":
        return {"report": str(service.publish(args.run_id, args.actor))}
    if args.command == "generate-report":
        report_path, manifest_path = service.reporter.generate(args.run_id)
        return {"report": str(report_path), "manifest": str(manifest_path)}
    if args.command == "evaluate":
        return evaluate_run(service.database, args.run_id, service.scoring_policy)
    if args.command == "compare-runs":
        return compare_runs(
            service.database, args.previous_run_id, args.current_run_id
        )
    if args.command == "ingest":
        with args.path.open("r", encoding="utf-8") as handle:
            package = json.load(handle)
        return service.ingest_evidence_package(package)
    if args.command == "ingest-sec":
        return service.source_service.sync(
            "sec_edgar",
            mode="company",
            cik=args.cik,
            segment=args.segment,
            subsegment=args.subsegment,
            as_of_date=args.as_of_date,
        )
    if args.command == "serve":
        try:
            import uvicorn
        except ImportError as exc:
            raise ValueError("Install project dependencies before using serve") from exc
        uvicorn.run("aifactory.api:app", host=args.host, port=args.port, reload=False)
        return None
    raise ValueError(f"Unknown command: {args.command}")


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, default=str, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
