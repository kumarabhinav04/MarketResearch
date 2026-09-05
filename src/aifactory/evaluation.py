from __future__ import annotations

from statistics import fmean
from typing import Any

from .database import Database


def evaluate_run(database: Database, run_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    run = database.get_run(run_id)
    if not run:
        raise KeyError("Run not found")
    assessments = database.list_assessments(run_id)
    rankings = database.list_rankings(run_id)
    if not assessments:
        raise ValueError("Run contains no assessments")

    reproducible = 0
    citation_values: list[float] = []
    confidence_values: list[float] = []
    unsupported = 0
    rankable = 0
    for item in assessments:
        assessment = item["assessment"]
        citation_values.append(float(assessment["citation_coverage"]))
        confidence_values.append(float(assessment["evidence_confidence"]))
        expected = (
            float(assessment["moat_score"])
            * int(assessment["operating_margin_score"])
            * float((assessment.get("forecast") or {}).get("base_company_ai_cagr", 0.0))
            * 100.0
            * (1.0 - float(assessment["risk_discount"]))
        )
        if abs(expected - float(assessment["risk_adjusted_tafgs"])) <= 1e-9:
            reproducible += 1
        if assessment["rankable"]:
            rankable += 1
        unsupported += sum(
            1
            for message in assessment["validation_errors"]
            if "missing" in message.lower() or "lack" in message.lower()
        )

    denominator = max(1, len(rankings) - 1)
    stability_values = [
        max(0.0, 1.0 - abs(item["bear_rank"] - item["bull_rank"]) / denominator)
        for item in rankings
    ]
    approval_coverage = (
        sum(1 for item in rankings if item["review_status"] == "approved") / len(rankings)
        if rankings
        else 0.0
    )
    metrics = {
        "assessment_count": len(assessments),
        "ranked_count": len(rankings),
        "rankable_rate": rankable / len(assessments),
        "mean_evidence_confidence": fmean(confidence_values),
        "mean_citation_coverage": fmean(citation_values),
        "score_reproducibility_rate": reproducible / len(assessments),
        "unsupported_required_claim_count": unsupported,
        "mean_scenario_rank_stability": fmean(stability_values) if stability_values else 0.0,
        "ranked_approval_coverage": approval_coverage,
    }
    gates = {
        "score_reproducibility": metrics["score_reproducibility_rate"] == 1.0,
        "citation_coverage": metrics["mean_citation_coverage"]
        >= policy["minimum_citation_coverage"],
        "evidence_confidence": metrics["mean_evidence_confidence"]
        >= policy["minimum_evidence_confidence"],
        "rank_output_nonempty": metrics["ranked_count"] > 0,
        "publication_approval": approval_coverage == 1.0,
    }
    return {
        "run_id": run_id,
        "status": run["status"],
        "metrics": metrics,
        "gates": gates,
        "research_ready": all(
            gates[name]
            for name in (
                "score_reproducibility",
                "citation_coverage",
                "evidence_confidence",
                "rank_output_nonempty",
            )
        ),
        "publication_ready": all(gates.values()),
    }


def compare_runs(database: Database, previous_run_id: str, current_run_id: str) -> dict[str, Any]:
    previous = {item["company_id"]: item for item in database.list_rankings(previous_run_id)}
    current = {item["company_id"]: item for item in database.list_rankings(current_run_id)}
    if not previous:
        raise ValueError("Previous run has no rankings")
    if not current:
        raise ValueError("Current run has no rankings")
    changes: list[dict[str, Any]] = []
    for company_id in sorted(set(previous) | set(current)):
        old = previous.get(company_id)
        new = current.get(company_id)
        if old and new:
            status = "retained"
            rank_change = old["rank"] - new["rank"]
            score_change = new["risk_adjusted_tafgs"] - old["risk_adjusted_tafgs"]
            name = new["legal_name"]
        elif new:
            status = "entered"
            rank_change = None
            score_change = None
            name = new["legal_name"]
        else:
            status = "exited"
            rank_change = None
            score_change = None
            name = old["legal_name"]
        changes.append(
            {
                "company_id": company_id,
                "legal_name": name,
                "status": status,
                "previous_rank": old["rank"] if old else None,
                "current_rank": new["rank"] if new else None,
                "rank_change": rank_change,
                "previous_score": old["risk_adjusted_tafgs"] if old else None,
                "current_score": new["risk_adjusted_tafgs"] if new else None,
                "score_change": score_change,
            }
        )
    changes.sort(
        key=lambda item: (
            item["current_rank"] is None,
            item["current_rank"] if item["current_rank"] is not None else 10**9,
        )
    )
    return {
        "previous_run_id": previous_run_id,
        "current_run_id": current_run_id,
        "changes": changes,
    }
