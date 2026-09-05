from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .database import Database
from .demo import seed_demo
from .extraction import EvidenceProposalService
from .ingestion import EvidencePackageIngestor
from .llm import PromptRegistry, gateway_from_settings
from .models import CompanyAssessment, ReviewStatus, RunStatus
from .reporting import ReportGenerator
from .scoring import rank_assessments, scoring_manifest
from .sources import SourceCatalog, SourceIngestionService
from .sources.storage import RawSnapshotStore
from .telemetry import METRICS, configure_logging, run_id_context, timed_operation
from .workflow import CompanyResearchWorkflow


LOGGER = logging.getLogger(__name__)


class PublicationGateError(ValueError):
    pass


class ResearchService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        configure_logging(self.settings.log_level)
        self.database = Database(self.settings.db_path)
        self.database.initialize()
        self.taxonomy = self.settings.load_json("taxonomy.json")
        self.scoring_policy = self.settings.load_json("scoring_policy.json")
        self.source_policy = self.settings.load_json("source_policy.json")
        self.extraction_policy = self.settings.load_json("extraction_policy.json")
        self.source_catalog = SourceCatalog.load(self.settings.config_dir / "sources.json")
        self.source_service = SourceIngestionService(
            self.database,
            self.source_catalog,
            RawSnapshotStore(self.settings.raw_source_dir),
            self.settings.sec_user_agent,
        )
        self.gateway = gateway_from_settings(self.settings)
        self.prompt_registry = PromptRegistry(self.settings.config_dir / "prompts")
        self.evidence_proposals = EvidenceProposalService(
            self.database,
            self.gateway,
            self.prompt_registry,
            self.extraction_policy,
            self.settings.model_name,
        )
        self.workflow = CompanyResearchWorkflow(
            self.database,
            self.scoring_policy,
            self.gateway,
            self.prompt_registry,
        )
        self.reporter = ReportGenerator(self.database, self.settings.report_dir)

    def seed_demo(self) -> dict[str, int]:
        result = seed_demo(self.database, self.taxonomy)
        self.database.audit("system", "demo_seeded", result)
        return result

    def reset_demo(self) -> None:
        self.database.reset_demo()

    def ingest_evidence_package(self, package: dict[str, Any]) -> dict[str, int]:
        result = EvidencePackageIngestor(self.database).ingest(package)
        self.database.audit("ingestion_service", "evidence_package_ingested", result)
        return result

    def run_research(
        self,
        as_of_date: str,
        company_ids: list[str] | None = None,
        generate_report: bool = False,
    ) -> dict[str, Any]:
        _validate_as_of_date(as_of_date)
        for segment in self.taxonomy["segments"]:
            self.database.upsert_market_segment(segment, self.taxonomy["version"])
        companies = self.database.list_companies(eligible_only=True)
        if company_ids is not None:
            selected = set(company_ids)
            companies = [company for company in companies if company["id"] in selected]
            missing = selected.difference(company["id"] for company in companies)
            if missing:
                raise KeyError(f"Unknown or ineligible companies: {sorted(missing)}")
        if not companies:
            raise ValueError("No eligible companies are available; ingest evidence or seed demo data")

        run_id = self.database.create_run(
            {
                "as_of_date": as_of_date,
                "taxonomy_version": self.taxonomy["version"],
                "scoring_version": self.scoring_policy["version"],
                "prompt_version": "1.0.0",
                "model_provider": self.gateway.provider,
                "model_name": self.settings.model_name,
                "config_snapshot": {
                    "scoring": scoring_manifest(self.scoring_policy),
                    "source_policy_version": self.source_policy["version"],
                    "runtime": self.workflow.runtime_name,
                    "company_ids": [company["id"] for company in companies],
                },
            }
        )
        token = run_id_context.set(run_id)
        assessments: list[CompanyAssessment] = []
        try:
            self.database.update_run(run_id, RunStatus.RUNNING)
            self.database.audit(
                "workflow_supervisor",
                "run_started",
                {"company_count": len(companies), "runtime": self.workflow.runtime_name},
                run_id=run_id,
            )
            with timed_operation("research_run", LOGGER):
                with ThreadPoolExecutor(max_workers=self.settings.max_workers) as executor:
                    futures = {
                        executor.submit(
                            self.workflow.run, company["id"], run_id, as_of_date
                        ): company["id"]
                        for company in companies
                    }
                    for future in as_completed(futures):
                        company_id = futures[future]
                        try:
                            assessment = future.result()
                        except Exception as exc:
                            LOGGER.exception("Company workflow failed for %s", company_id)
                            assessment = CompanyAssessment(
                                company_id=company_id,
                                run_id=run_id,
                                rankable=False,
                                validation_errors=[f"Workflow failure: {type(exc).__name__}"],
                            )
                            METRICS.increment("company_workflow_failures_total")
                        assessments.append(assessment)
                        self.database.save_assessment(assessment)
                        self.database.audit(
                            "workflow_supervisor",
                            "company_assessed",
                            {
                                "rankable": assessment.rankable,
                                "score": assessment.risk_adjusted_tafgs,
                                "validation_errors": assessment.validation_errors,
                            },
                            run_id=run_id,
                            company_id=company_id,
                        )

                rankings = rank_assessments(
                    run_id,
                    assessments,
                    rank_size=int(self.scoring_policy["rank_size"]),
                )
                self.database.save_rankings(rankings)
            self.database.update_run(run_id, RunStatus.COMPLETED)
            self.database.audit(
                "ranking_service",
                "run_completed",
                {
                    "ranked_count": len(rankings),
                    "excluded_count": len(assessments) - len(rankings),
                },
                run_id=run_id,
            )
            paths: dict[str, str] = {}
            if generate_report and rankings:
                report_path, manifest_path = self.reporter.generate(run_id)
                paths = {"report": str(report_path), "manifest": str(manifest_path)}
            METRICS.increment("research_runs_completed_total")
            return {
                "run_id": run_id,
                "status": RunStatus.COMPLETED,
                "runtime": self.workflow.runtime_name,
                "company_count": len(companies),
                "ranked_count": len(rankings),
                "excluded_count": len(assessments) - len(rankings),
                **paths,
            }
        except Exception as exc:
            self.database.update_run(run_id, RunStatus.FAILED, error=str(exc))
            self.database.audit(
                "workflow_supervisor",
                "run_failed",
                {"error_type": type(exc).__name__, "error": str(exc)},
                run_id=run_id,
            )
            METRICS.increment("research_runs_failed_total")
            raise
        finally:
            run_id_context.reset(token)

    def review(
        self,
        run_id: str,
        company_id: str,
        reviewer: str,
        decision: str,
        comment: str,
        overrides: dict[str, Any] | None = None,
    ) -> str:
        if decision not in {item.value for item in ReviewStatus}:
            raise ValueError(f"Invalid review decision: {decision}")
        if not self.database.get_assessment(run_id, company_id):
            raise KeyError("Assessment not found")
        review_id = self.database.record_review(
            run_id, company_id, reviewer, decision, comment, overrides
        )
        self.database.audit(
            reviewer,
            "assessment_reviewed",
            {"decision": decision, "comment": comment, "overrides": overrides or {}},
            run_id=run_id,
            company_id=company_id,
        )
        return review_id

    def publish(self, run_id: str, actor: str) -> Path:
        run = self.database.get_run(run_id)
        if not run:
            raise KeyError("Run not found")
        if run["status"] not in {RunStatus.COMPLETED, RunStatus.PUBLISHED}:
            raise PublicationGateError("Only completed runs can be published")
        rankings = self.database.list_rankings(run_id)
        pending = [
            item["company_id"]
            for item in rankings
            if item["review_status"] != ReviewStatus.APPROVED
        ]
        if self.scoring_policy["publish_requires_top_rank_approval"] and pending:
            raise PublicationGateError(
                f"Ranked companies require approval before publication: {pending}"
            )
        self.database.update_run(run_id, RunStatus.PUBLISHED)
        report_path, manifest_path = self.reporter.generate(run_id)
        self.database.audit(
            actor,
            "run_published",
            {"report": str(report_path), "manifest": str(manifest_path)},
            run_id=run_id,
        )
        return report_path


def _validate_as_of_date(value: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("as_of_date must use YYYY-MM-DD") from exc
    if parsed > date.today():
        raise ValueError("as_of_date cannot be in the future")
