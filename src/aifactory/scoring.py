from __future__ import annotations

import math
from typing import Any, Iterable

from .models import CompanyAssessment, RankingEntry, ScenarioForecast


class ScoringError(ValueError):
    pass


def operating_margin_score(margin_pct: float) -> int:
    """Assignment rubric with explicit boundary handling.

    Exactly 40% scores 4; exactly 30% scores 4; exactly 20% scores 3;
    exactly 10% scores 2. Negative margins remain score 1 and are flagged elsewhere.
    """
    if not math.isfinite(margin_pct):
        raise ScoringError("Operating margin must be finite")
    if margin_pct > 40.0:
        return 5
    if margin_pct >= 30.0:
        return 4
    if margin_pct >= 20.0:
        return 3
    if margin_pct >= 10.0:
        return 2
    return 1


def company_ai_driven_cagr(ai_exposure: float, ai_segment_cagr: float, years: int = 3) -> float:
    """Company-wide revenue CAGR attributable to AI, holding non-AI revenue flat."""
    if not 0.0 <= ai_exposure <= 1.0:
        raise ScoringError("AI exposure must be in [0, 1]")
    if ai_segment_cagr <= -1.0 or not math.isfinite(ai_segment_cagr):
        raise ScoringError("AI segment CAGR must be finite and greater than -100%")
    if years <= 0:
        raise ScoringError("Forecast years must be positive")
    future_total_ratio = (1.0 - ai_exposure) + ai_exposure * (1.0 + ai_segment_cagr) ** years
    return future_total_ratio ** (1.0 / years) - 1.0


def weighted_component_score(
    components: dict[str, float], weights: dict[str, float], scale_max: float = 5.0
) -> float:
    missing = set(weights).difference(components)
    if missing:
        raise ScoringError(f"Missing components: {sorted(missing)}")
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ScoringError("Component weights must sum to a positive value")
    for name, value in components.items():
        if name in weights and not 0.0 <= value <= scale_max:
            raise ScoringError(f"Component {name} must be in [0, {scale_max}]")
    return sum(components[name] * weight for name, weight in weights.items()) / total_weight


def risk_discount(
    risk_components: dict[str, float], risk_weights: dict[str, float], maximum_discount: float
) -> float:
    if not 0.0 <= maximum_discount <= 1.0:
        raise ScoringError("Maximum risk discount must be in [0, 1]")
    severity = weighted_component_score(risk_components, risk_weights, scale_max=5.0)
    return severity / 5.0 * maximum_discount


def calculate_assessment_scores(assessment: CompanyAssessment) -> CompanyAssessment:
    if assessment.forecast is None:
        raise ScoringError("Forecast is required")
    if not 0.0 <= assessment.moat_score <= 5.0:
        raise ScoringError("Moat score must be in [0, 5]")
    if not 0.0 <= assessment.risk_discount <= 1.0:
        raise ScoringError("Risk discount must be in [0, 1]")

    assessment.operating_margin_score = operating_margin_score(
        assessment.operating_margin_pct
    )
    assessment.base_tafgs = (
        assessment.moat_score
        * assessment.operating_margin_score
        * assessment.forecast.base_company_ai_cagr
        * 100.0
    )
    assessment.risk_adjusted_tafgs = assessment.base_tafgs * (
        1.0 - assessment.risk_discount
    )
    assessment.bear_risk_adjusted_tafgs = (
        assessment.moat_score
        * assessment.operating_margin_score
        * assessment.forecast.bear_company_ai_cagr
        * 100.0
        * (1.0 - assessment.risk_discount)
    )
    assessment.bull_risk_adjusted_tafgs = (
        assessment.moat_score
        * assessment.operating_margin_score
        * assessment.forecast.bull_company_ai_cagr
        * 100.0
        * (1.0 - assessment.risk_discount)
    )
    return assessment


def create_forecast(
    ai_exposure: float,
    bear_ai_segment_cagr: float,
    base_ai_segment_cagr: float,
    bull_ai_segment_cagr: float,
) -> ScenarioForecast:
    if not bear_ai_segment_cagr <= base_ai_segment_cagr <= bull_ai_segment_cagr:
        raise ScoringError("Forecast scenarios must satisfy bear <= base <= bull")
    return ScenarioForecast(
        bear_ai_segment_cagr=bear_ai_segment_cagr,
        base_ai_segment_cagr=base_ai_segment_cagr,
        bull_ai_segment_cagr=bull_ai_segment_cagr,
        bear_company_ai_cagr=company_ai_driven_cagr(ai_exposure, bear_ai_segment_cagr),
        base_company_ai_cagr=company_ai_driven_cagr(ai_exposure, base_ai_segment_cagr),
        bull_company_ai_cagr=company_ai_driven_cagr(ai_exposure, bull_ai_segment_cagr),
    )


def rank_assessments(
    run_id: str, assessments: Iterable[CompanyAssessment], rank_size: int = 20
) -> list[RankingEntry]:
    eligible = [item for item in assessments if item.rankable]
    base_sorted = sorted(
        eligible,
        key=lambda item: (-item.risk_adjusted_tafgs, item.company_id),
    )
    bear_sorted = sorted(
        eligible,
        key=lambda item: (-item.bear_risk_adjusted_tafgs, item.company_id),
    )
    bull_sorted = sorted(
        eligible,
        key=lambda item: (-item.bull_risk_adjusted_tafgs, item.company_id),
    )
    bear_ranks = {item.company_id: index for index, item in enumerate(bear_sorted, start=1)}
    bull_ranks = {item.company_id: index for index, item in enumerate(bull_sorted, start=1)}
    denominator = max(1, len(base_sorted) - 1)
    rankings: list[RankingEntry] = []
    for rank, assessment in enumerate(base_sorted[:rank_size], start=1):
        bear_rank = bear_ranks[assessment.company_id]
        bull_rank = bull_ranks[assessment.company_id]
        stability = max(0.0, 1.0 - abs(bear_rank - bull_rank) / denominator)
        rank_confidence = max(
            0.0,
            min(1.0, assessment.evidence_confidence * (0.65 + 0.35 * stability)),
        )
        rankings.append(
            RankingEntry(
                run_id=run_id,
                company_id=assessment.company_id,
                rank=rank,
                bear_rank=bear_rank,
                bull_rank=bull_rank,
                risk_adjusted_tafgs=round(assessment.risk_adjusted_tafgs, 6),
                rank_confidence=round(rank_confidence, 6),
            )
        )
    return rankings


def scoring_manifest(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "formula": "moat_score * margin_score * company_ai_cagr_pct * (1-risk_discount)",
        "company_ai_cagr": "((1-exposure)+exposure*(1+ai_segment_cagr)^3)^(1/3)-1",
        "policy_version": policy["version"],
        "margin_thresholds": policy["margin_thresholds"],
        "moat_weights": policy["moat_weights"],
        "risk_weights": policy["risk_weights"],
        "maximum_risk_discount": policy["maximum_risk_discount"],
    }

