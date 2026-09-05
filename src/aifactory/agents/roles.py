from __future__ import annotations

import copy
import json
import logging
from abc import ABC, abstractmethod
from statistics import fmean
from typing import Any, TypedDict

from ..llm import ModelGateway, ModelGatewayError, OfflineModelGateway, PromptRegistry
from ..models import ClaimType, CompanyAssessment, EvidenceClaim
from ..scoring import (
    ScoringError,
    calculate_assessment_scores,
    create_forecast,
    operating_margin_score,
    risk_discount,
    weighted_component_score,
)
from ..telemetry import METRICS, timed_operation


LOGGER = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    run_id: str
    as_of_date: str
    company: dict[str, Any]
    claims: list[EvidenceClaim]
    assessment: CompanyAssessment
    policy: dict[str, Any]


class ResearchAgent(ABC):
    name: str

    def __call__(self, state: WorkflowState) -> dict[str, Any]:
        with timed_operation("agent_execution", LOGGER, agent=self.name):
            METRICS.increment(f"agent_{self.name}_total")
            return self.run(state)

    @abstractmethod
    def run(self, state: WorkflowState) -> dict[str, Any]:
        raise NotImplementedError


class EligibilityAgent(ResearchAgent):
    name = "eligibility"

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        company = state["company"]
        assessment.eligible = bool(company.get("eligible"))
        assessment.segment = company.get("segment", "")
        if not assessment.eligible:
            assessment.validation_errors.append("Security is not eligible for the public-company universe")
        if not company.get("security_id") or not company.get("exchange"):
            assessment.eligible = False
            assessment.validation_errors.append("Security master identity is incomplete")
        return {"assessment": assessment}


class EvidenceAgent(ResearchAgent):
    name = "evidence"

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        claims = state["claims"]
        assessment.evidence_claim_ids = [claim.id for claim in claims]
        if not claims:
            assessment.validation_errors.append("No as-of-date eligible evidence")
            return {"assessment": assessment}
        tier_weights = {"1": 1.0, "2": 0.8, "3": 0.45}
        weighted = [claim.confidence * tier_weights.get(claim.source_tier, 0.25) for claim in claims]
        assessment.evidence_confidence = round(fmean(weighted), 6)
        contradictions = [claim.id for claim in claims if claim.contradiction]
        if contradictions:
            assessment.warnings.append(
                f"Contradictory evidence requires adjudication: {', '.join(contradictions)}"
            )
        return {"assessment": assessment}


class ExposureAgent(ResearchAgent):
    name = "exposure"

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        claim = _best_numeric_claim(state["claims"], ClaimType.AI_EXPOSURE)
        if claim is None:
            assessment.validation_errors.append("Missing AI-factory revenue exposure")
        elif not 0.0 <= float(claim.value_numeric) <= 1.0:
            assessment.validation_errors.append("AI-factory revenue exposure is outside [0,1]")
        else:
            assessment.ai_exposure = float(claim.value_numeric)
        return {"assessment": assessment}


class MoatAgent(ResearchAgent):
    name = "moat"
    mapping = {
        "architectural_lock_in": ClaimType.MOAT_ARCHITECTURAL_LOCK_IN,
        "switching_costs": ClaimType.MOAT_SWITCHING_COSTS,
        "standards_and_ip": ClaimType.MOAT_STANDARDS_AND_IP,
        "ecosystem_and_design_wins": ClaimType.MOAT_ECOSYSTEM_AND_DESIGN_WINS,
        "bottleneck_scarcity": ClaimType.MOAT_BOTTLENECK_SCARCITY,
        "competitive_intensity": ClaimType.MOAT_COMPETITIVE_INTENSITY,
    }

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        components: dict[str, float] = {}
        for name, claim_type in self.mapping.items():
            claim = _best_numeric_claim(state["claims"], claim_type)
            if claim is not None:
                components[name] = float(claim.value_numeric)
        assessment.moat_components = components
        try:
            assessment.moat_score = round(
                weighted_component_score(components, state["policy"]["moat_weights"]), 6
            )
        except ScoringError as exc:
            assessment.validation_errors.append(f"Moat assessment invalid: {exc}")
        return {"assessment": assessment}


class MarginAgent(ResearchAgent):
    name = "margin"

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        claim = _best_numeric_claim(
            state["claims"], ClaimType.OPERATING_MARGIN, tier_1_required=True
        )
        if claim is None:
            assessment.validation_errors.append("Missing Tier 1 operating-margin evidence")
            return {"assessment": assessment}
        margin = float(claim.value_numeric)
        assessment.operating_margin_pct = margin
        assessment.operating_margin_score = operating_margin_score(margin)
        if margin < 0:
            assessment.warnings.append("Company has a negative operating margin")
        return {"assessment": assessment}


class GrowthForecastAgent(ResearchAgent):
    name = "growth_forecast"

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        bear = _best_numeric_claim(state["claims"], ClaimType.AI_SEGMENT_CAGR_BEAR)
        base = _best_numeric_claim(state["claims"], ClaimType.AI_SEGMENT_CAGR_BASE)
        bull = _best_numeric_claim(state["claims"], ClaimType.AI_SEGMENT_CAGR_BULL)
        if not all((bear, base, bull)):
            assessment.validation_errors.append("Three-scenario growth forecast is incomplete")
            return {"assessment": assessment}
        try:
            assessment.forecast = create_forecast(
                assessment.ai_exposure,
                float(bear.value_numeric),
                float(base.value_numeric),
                float(bull.value_numeric),
            )
        except ScoringError as exc:
            assessment.validation_errors.append(f"Growth forecast invalid: {exc}")
        return {"assessment": assessment}


class RiskAgent(ResearchAgent):
    name = "risk"
    mapping = {
        "customer_concentration": ClaimType.RISK_CUSTOMER_CONCENTRATION,
        "cyclicality": ClaimType.RISK_CYCLICALITY,
        "execution": ClaimType.RISK_EXECUTION,
        "supply_chain": ClaimType.RISK_SUPPLY_CHAIN,
        "geopolitical_regulatory": ClaimType.RISK_GEOPOLITICAL_REGULATORY,
        "commoditization": ClaimType.RISK_COMMODITIZATION,
    }

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        components: dict[str, float] = {}
        for name, claim_type in self.mapping.items():
            claim = _best_numeric_claim(state["claims"], claim_type)
            if claim is not None:
                components[name] = float(claim.value_numeric)
        assessment.risk_components = components
        try:
            assessment.risk_discount = round(
                risk_discount(
                    components,
                    state["policy"]["risk_weights"],
                    state["policy"]["maximum_risk_discount"],
                ),
                6,
            )
        except ScoringError as exc:
            assessment.validation_errors.append(f"Risk assessment invalid: {exc}")
        return {"assessment": assessment}


class SkepticAgent(ResearchAgent):
    name = "skeptic_auditor"
    required_claims = {
        ClaimType.TOTAL_REVENUE,
        ClaimType.OPERATING_MARGIN,
        ClaimType.AI_EXPOSURE,
        ClaimType.AI_SEGMENT_CAGR_BEAR,
        ClaimType.AI_SEGMENT_CAGR_BASE,
        ClaimType.AI_SEGMENT_CAGR_BULL,
        *MoatAgent.mapping.values(),
        *RiskAgent.mapping.values(),
    }

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        policy = state["policy"]
        present = {claim.claim_type for claim in state["claims"] if claim.evidence_span.strip()}
        assessment.citation_coverage = round(
            len({str(item) for item in self.required_claims}.intersection(present))
            / len(self.required_claims),
            6,
        )

        financial_claims = {
            ClaimType.TOTAL_REVENUE,
            ClaimType.OPERATING_MARGIN,
        }
        missing_tier_1 = [
            str(claim_type)
            for claim_type in financial_claims
            if _best_numeric_claim(state["claims"], claim_type, tier_1_required=True) is None
        ]
        if missing_tier_1:
            assessment.validation_errors.append(
                f"Financial claims lack Tier 1 support: {', '.join(sorted(missing_tier_1))}"
            )
        if any(claim.contradiction for claim in state["claims"]):
            assessment.validation_errors.append("Unresolved contradictory evidence")
        if assessment.evidence_confidence < policy["minimum_evidence_confidence"]:
            assessment.validation_errors.append("Evidence confidence is below the policy threshold")
        if assessment.citation_coverage < policy["minimum_citation_coverage"]:
            assessment.validation_errors.append("Citation coverage is below the policy threshold")

        try:
            if not assessment.validation_errors:
                calculate_assessment_scores(assessment)
        except ScoringError as exc:
            assessment.validation_errors.append(f"Final score validation failed: {exc}")

        assessment.rankable = assessment.eligible and not assessment.validation_errors
        assessment.review_required = True
        return {"assessment": assessment}


class NarrativeAgent(ResearchAgent):
    name = "narrative"

    def __init__(
        self,
        gateway: ModelGateway | None = None,
        prompts: PromptRegistry | None = None,
    ):
        self.gateway = gateway or OfflineModelGateway()
        self.prompts = prompts

    def run(self, state: WorkflowState) -> dict[str, Any]:
        assessment = copy.deepcopy(state["assessment"])
        roles = [
            claim.value_text
            for claim in state["claims"]
            if claim.claim_type == ClaimType.ROLE_NARRATIVE and claim.value_text
        ]
        catalysts = [
            claim.value_text
            for claim in state["claims"]
            if claim.claim_type == ClaimType.CATALYST and claim.value_text
        ]
        contrary = [
            claim.value_text or claim.evidence_span
            for claim in state["claims"]
            if claim.claim_type == ClaimType.CONTRARY_EVIDENCE
        ]
        assessment.narrative = {
            "role": roles[0] if roles else "Role evidence unavailable.",
            "catalysts": catalysts,
            "contrary_evidence": contrary,
            "generation_mode": "evidence_template",
        }

        if not isinstance(self.gateway, OfflineModelGateway) and self.prompts:
            system_prompt = self.prompts.render("report narrative agent", state["as_of_date"])
            user_prompt = json.dumps(
                {
                    "company": state["company"],
                    "assessment": assessment.to_dict(),
                    "evidence": [claim.to_dict() for claim in state["claims"]],
                },
                sort_keys=True,
            )
            schema = {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "moat_narrative": {"type": "string"},
                    "catalysts": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["role", "moat_narrative", "catalysts", "risks"],
            }
            try:
                generated = self.gateway.complete_json(system_prompt, user_prompt, schema)
                generated["generation_mode"] = "model"
                assessment.narrative = generated
            except ModelGatewayError as exc:
                assessment.warnings.append(f"Model narrative fallback used: {exc}")
        return {"assessment": assessment}


def _best_numeric_claim(
    claims: list[EvidenceClaim],
    claim_type: str,
    tier_1_required: bool = False,
) -> EvidenceClaim | None:
    candidates = [
        claim
        for claim in claims
        if claim.claim_type == claim_type
        and claim.value_numeric is not None
        and not claim.contradiction
        and (not tier_1_required or claim.source_tier == "1")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.published_at, item.confidence))
