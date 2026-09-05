from __future__ import annotations

import math
import unittest

from aifactory.models import CompanyAssessment
from aifactory.scoring import (
    ScoringError,
    calculate_assessment_scores,
    company_ai_driven_cagr,
    create_forecast,
    operating_margin_score,
    risk_discount,
    weighted_component_score,
)


class MarginScoreTests(unittest.TestCase):
    def test_boundaries_match_documented_policy(self) -> None:
        self.assertEqual(operating_margin_score(40.01), 5)
        self.assertEqual(operating_margin_score(40.0), 4)
        self.assertEqual(operating_margin_score(30.0), 4)
        self.assertEqual(operating_margin_score(29.99), 3)
        self.assertEqual(operating_margin_score(20.0), 3)
        self.assertEqual(operating_margin_score(10.0), 2)
        self.assertEqual(operating_margin_score(9.99), 1)
        self.assertEqual(operating_margin_score(-20.0), 1)

    def test_non_finite_margin_is_rejected(self) -> None:
        with self.assertRaises(ScoringError):
            operating_margin_score(math.nan)


class GrowthFormulaTests(unittest.TestCase):
    def test_zero_exposure_produces_zero_company_ai_growth(self) -> None:
        self.assertAlmostEqual(company_ai_driven_cagr(0.0, 0.5), 0.0)

    def test_full_exposure_equals_segment_growth(self) -> None:
        self.assertAlmostEqual(company_ai_driven_cagr(1.0, 0.35), 0.35)

    def test_exposure_materiality_is_embedded(self) -> None:
        low = company_ai_driven_cagr(0.1, 0.3)
        high = company_ai_driven_cagr(0.8, 0.3)
        self.assertGreater(high, low)

    def test_invalid_exposure_is_rejected(self) -> None:
        with self.assertRaises(ScoringError):
            company_ai_driven_cagr(1.2, 0.3)


class CompositeScoreTests(unittest.TestCase):
    def test_weighted_components_and_risk(self) -> None:
        weights = {"a": 0.25, "b": 0.75}
        self.assertAlmostEqual(weighted_component_score({"a": 1, "b": 5}, weights), 4.0)
        self.assertAlmostEqual(risk_discount({"a": 1, "b": 5}, weights, 0.35), 0.28)

    def test_score_is_deterministic(self) -> None:
        assessment = CompanyAssessment(
            company_id="example",
            run_id="run",
            moat_score=4.0,
            operating_margin_pct=35.0,
            risk_discount=0.2,
            forecast=create_forecast(0.5, 0.1, 0.2, 0.3),
        )
        calculate_assessment_scores(assessment)
        expected = 4.0 * 4 * assessment.forecast.base_company_ai_cagr * 100 * 0.8
        self.assertAlmostEqual(assessment.risk_adjusted_tafgs, expected)


if __name__ == "__main__":
    unittest.main()

