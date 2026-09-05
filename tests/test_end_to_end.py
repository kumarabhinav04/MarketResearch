from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aifactory.config import Settings
from aifactory.evaluation import compare_runs, evaluate_run
from aifactory.models import ClaimType, ReviewStatus, RunStatus
from aifactory.service import PublicationGateError, ResearchService


ROOT = Path(__file__).resolve().parents[1]


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp.name)
        self.settings = Settings(
            environment="test",
            db_path=temp_path / "test.db",
            config_dir=ROOT / "config",
            report_dir=temp_path / "reports",
            raw_source_dir=temp_path / "raw-sources",
            api_key="test-key",
            log_level="CRITICAL",
            max_workers=4,
            min_evidence_confidence=0.65,
            model_provider="offline",
            model_name="",
            model_base_url="http://localhost:11434",
            model_api_key="",
            model_timeout_seconds=120,
            model_max_completion_tokens=800,
            model_reasoning_effort="",
            otel_endpoint="",
            sec_user_agent="AI-Factory-Test test@example.com",
        )
        self.service = ResearchService(self.settings)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_seed_run_rank_report_review_and_publish(self) -> None:
        seeded = self.service.seed_demo()
        self.assertEqual(seeded["companies"], 20)
        self.assertEqual(seeded["documents"], 60)
        self.assertEqual(seeded["claims"], 400)

        result = self.service.run_research("2026-09-01", generate_report=True)
        self.assertEqual(result["status"], RunStatus.COMPLETED)
        self.assertEqual(result["ranked_count"], 20)
        rankings = self.service.database.list_rankings(result["run_id"])
        self.assertEqual([item["rank"] for item in rankings], list(range(1, 21)))
        scores = [item["risk_adjusted_tafgs"] for item in rankings]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(Path(result["report"]).exists())
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["ranked_company_count"], 20)

        with self.assertRaises(PublicationGateError):
            self.service.publish(result["run_id"], "test-analyst")
        for item in rankings:
            self.service.review(
                result["run_id"],
                item["company_id"],
                "test-analyst",
                ReviewStatus.APPROVED,
                "Reviewed in test",
            )
        published_path = self.service.publish(result["run_id"], "test-analyst")
        self.assertTrue(published_path.exists())
        self.assertEqual(
            self.service.database.get_run(result["run_id"])["status"], RunStatus.PUBLISHED
        )
        evaluation = evaluate_run(
            self.service.database, result["run_id"], self.service.scoring_policy
        )
        self.assertTrue(evaluation["research_ready"])
        self.assertTrue(evaluation["publication_ready"])

        second = self.service.run_research("2026-09-01")
        comparison = compare_runs(
            self.service.database, result["run_id"], second["run_id"]
        )
        self.assertEqual(len(comparison["changes"]), 20)
        self.assertTrue(all(item["rank_change"] == 0 for item in comparison["changes"]))

    def test_missing_required_evidence_excludes_company(self) -> None:
        self.service.seed_demo()
        with self.service.database.connect() as connection:
            connection.execute(
                "DELETE FROM evidence_claims WHERE company_id=? AND claim_type=?",
                ("demo-001", ClaimType.OPERATING_MARGIN),
            )
        result = self.service.run_research("2026-09-01", company_ids=["demo-001"])
        self.assertEqual(result["ranked_count"], 0)
        assessment = self.service.database.get_assessment(result["run_id"], "demo-001")
        self.assertFalse(assessment["rankable"])
        self.assertTrue(
            any(
                "operating-margin" in message
                for message in assessment["assessment"]["validation_errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
