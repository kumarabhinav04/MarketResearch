from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Segment(StrEnum):
    COMPUTE_SERVERS = "compute_servers"
    NETWORKING = "networking"
    POWER = "power"
    COOLING = "cooling"
    CONSTRUCTION = "construction"


class SourceTier(StrEnum):
    TIER_1 = "1"
    TIER_2 = "2"
    TIER_3 = "3"


class ClaimType(StrEnum):
    TOTAL_REVENUE = "total_revenue"
    OPERATING_MARGIN = "operating_margin"
    AI_EXPOSURE = "ai_exposure"
    AI_SEGMENT_CAGR_BEAR = "ai_segment_cagr_bear"
    AI_SEGMENT_CAGR_BASE = "ai_segment_cagr_base"
    AI_SEGMENT_CAGR_BULL = "ai_segment_cagr_bull"
    MOAT_ARCHITECTURAL_LOCK_IN = "moat_architectural_lock_in"
    MOAT_SWITCHING_COSTS = "moat_switching_costs"
    MOAT_STANDARDS_AND_IP = "moat_standards_and_ip"
    MOAT_ECOSYSTEM_AND_DESIGN_WINS = "moat_ecosystem_and_design_wins"
    MOAT_BOTTLENECK_SCARCITY = "moat_bottleneck_scarcity"
    MOAT_COMPETITIVE_INTENSITY = "moat_competitive_intensity"
    RISK_CUSTOMER_CONCENTRATION = "risk_customer_concentration"
    RISK_CYCLICALITY = "risk_cyclicality"
    RISK_EXECUTION = "risk_execution"
    RISK_SUPPLY_CHAIN = "risk_supply_chain"
    RISK_GEOPOLITICAL_REGULATORY = "risk_geopolitical_regulatory"
    RISK_COMMODITIZATION = "risk_commoditization"
    ROLE_NARRATIVE = "role_narrative"
    CATALYST = "catalyst"
    CONTRARY_EVIDENCE = "contrary_evidence"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"


@dataclass
class EvidenceClaim:
    id: str
    company_id: str
    document_id: str
    claim_type: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    period_end: str | None
    confidence: float
    evidence_span: str
    page_or_section: str
    source_tier: str
    published_at: str
    as_of_eligible: bool = True
    contradiction: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioForecast:
    bear_ai_segment_cagr: float
    base_ai_segment_cagr: float
    bull_ai_segment_cagr: float
    bear_company_ai_cagr: float
    base_company_ai_cagr: float
    bull_company_ai_cagr: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompanyAssessment:
    company_id: str
    run_id: str
    eligible: bool = True
    segment: str = ""
    evidence_claim_ids: list[str] = field(default_factory=list)
    evidence_confidence: float = 0.0
    citation_coverage: float = 0.0
    ai_exposure: float = 0.0
    moat_components: dict[str, float] = field(default_factory=dict)
    moat_score: float = 0.0
    operating_margin_pct: float = 0.0
    operating_margin_score: int = 1
    forecast: ScenarioForecast | None = None
    risk_components: dict[str, float] = field(default_factory=dict)
    risk_discount: float = 0.0
    base_tafgs: float = 0.0
    risk_adjusted_tafgs: float = 0.0
    bear_risk_adjusted_tafgs: float = 0.0
    bull_risk_adjusted_tafgs: float = 0.0
    rankable: bool = False
    review_required: bool = True
    review_status: str = ReviewStatus.PENDING
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    narrative: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.forecast:
            result["forecast"] = self.forecast.to_dict()
        return result


@dataclass(frozen=True)
class RankingEntry:
    run_id: str
    company_id: str
    rank: int
    bear_rank: int
    bull_rank: int
    risk_adjusted_tafgs: float
    rank_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

