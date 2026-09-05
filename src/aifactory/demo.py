from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .database import Database
from .ingestion import EvidencePackageIngestor, make_document
from .models import ClaimType, EvidenceClaim, Segment, SourceTier


@dataclass(frozen=True)
class DemoCompany:
    name: str
    ticker: str
    segment: str
    subsegment: str
    exposure: float
    margin: float
    moat: float
    growth: float
    risk_discount: float


DEMO_COMPANIES = [
    DemoCompany("VectorForge Accelerators", "VFA", Segment.COMPUTE_SERVERS, "accelerators", 0.82, 54, 4.8, 0.32, 0.18),
    DemoCompany("Atlas Rack Systems", "ARS", Segment.COMPUTE_SERVERS, "ai_servers", 0.55, 12, 3.5, 0.28, 0.22),
    DemoCompany("Nova Memory Fabric", "NMF", Segment.COMPUTE_SERVERS, "hbm", 0.68, 28, 4.2, 0.30, 0.20),
    DemoCompany("Quanta Storage Works", "QSW", Segment.COMPUTE_SERVERS, "storage", 0.35, 18, 3.0, 0.22, 0.24),
    DemoCompany("PhotonMesh Optics", "PMO", Segment.NETWORKING, "optics", 0.72, 31, 4.4, 0.34, 0.19),
    DemoCompany("FabricScale Networks", "FSN", Segment.NETWORKING, "switches", 0.64, 42, 4.5, 0.29, 0.17),
    DemoCompany("LinkCore Silicon", "LCS", Segment.NETWORKING, "nic_dpu", 0.58, 36, 4.1, 0.31, 0.21),
    DemoCompany("CableGrid Interconnect", "CGI", Segment.NETWORKING, "cabling", 0.46, 16, 2.9, 0.25, 0.18),
    DemoCompany("GridFort Switchgear", "GFS", Segment.POWER, "switchgear", 0.48, 19, 4.0, 0.24, 0.13),
    DemoCompany("TurbineWorks Energy", "TWE", Segment.POWER, "generation", 0.31, 14, 3.7, 0.19, 0.20),
    DemoCompany("Continuum UPS", "CUP", Segment.POWER, "ups", 0.62, 22, 4.2, 0.26, 0.16),
    DemoCompany("VoltSpan Transformers", "VST", Segment.POWER, "transformers", 0.57, 17, 4.5, 0.28, 0.12),
    DemoCompany("AquaLoop Cooling", "ALC", Segment.COOLING, "liquid_cooling", 0.76, 24, 4.3, 0.35, 0.17),
    DemoCompany("CryoFlow Systems", "CFS", Segment.COOLING, "cdu", 0.69, 21, 4.0, 0.33, 0.20),
    DemoCompany("ThermalTower Industries", "TTI", Segment.COOLING, "cooling_towers", 0.38, 13, 3.1, 0.18, 0.16),
    DemoCompany("ChillerEdge Controls", "CEC", Segment.COOLING, "chillers", 0.51, 18, 3.8, 0.23, 0.15),
    DemoCompany("ModularBuild Data Centers", "MDC", Segment.CONSTRUCTION, "modular_construction", 0.44, 9, 3.4, 0.27, 0.23),
    DemoCompany("CommissionWorks Engineering", "CWE", Segment.CONSTRUCTION, "commissioning", 0.39, 12, 3.2, 0.21, 0.14),
    DemoCompany("HyperSite Constructors", "HSC", Segment.CONSTRUCTION, "general_contracting", 0.61, 8, 3.6, 0.30, 0.26),
    DemoCompany("Precision MEP Group", "PMG", Segment.CONSTRUCTION, "design", 0.52, 11, 3.9, 0.26, 0.18),
]


def seed_demo(database: Database, taxonomy: dict[str, Any]) -> dict[str, int]:
    for segment in taxonomy["segments"]:
        database.upsert_market_segment(segment, taxonomy["version"])

    companies: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []

    for index, seed in enumerate(DEMO_COMPANIES, start=1):
        company_id = f"demo-{index:03d}"
        companies.append(
            {
                "id": company_id,
                "legal_name": seed.name,
                "ticker": seed.ticker,
                "exchange": "DEMO",
                "security_id": f"DEMO{index:06d}",
                "segment": str(seed.segment),
                "subsegment": seed.subsegment,
                "eligible": True,
                "demo": True,
                "metadata": {
                    "synthetic": True,
                    "warning": "Demonstration data; not investment research",
                },
            }
        )

        revenue = 900.0 + index * 135.0
        financial_text = (
            f"Synthetic FY2025 revenue was USD {revenue:.1f} million and reported operating "
            f"margin was {seed.margin:.1f} percent."
        )
        strategy_text = (
            f"Synthetic management estimate: {seed.exposure * 100:.1f} percent of revenue "
            f"is attributable to AI-factory infrastructure. The company supplies {seed.subsegment}."
        )
        technical_text = (
            "Synthetic scenario and rubric evidence created solely to exercise the platform's "
            "forecast, moat, risk, citation, review, and ranking controls."
        )
        financial = make_document(
            company_id,
            "regulatory_filing",
            SourceTier.TIER_1,
            f"{seed.name} Demo Filings",
            "Synthetic FY2025 annual report",
            f"https://demo.invalid/{company_id}/annual-report",
            "2026-02-15",
            financial_text,
            demo=True,
        )
        strategy = make_document(
            company_id,
            "company_ir",
            SourceTier.TIER_1,
            f"{seed.name} Demo IR",
            "Synthetic investor presentation",
            f"https://demo.invalid/{company_id}/investor-presentation",
            "2026-05-10",
            strategy_text,
            demo=True,
        )
        technical = make_document(
            company_id,
            "technical_document",
            SourceTier.TIER_2,
            "AI Factory Demo Evidence Lab",
            "Synthetic scenario evidence pack",
            f"https://demo.invalid/{company_id}/scenario-evidence",
            "2026-06-30",
            technical_text,
            demo=True,
        )
        documents.extend([financial, strategy, technical])

        claims.extend(
            [
                _claim(company_id, financial, ClaimType.TOTAL_REVENUE, revenue, "USD million", 0.99, financial_text),
                _claim(company_id, financial, ClaimType.OPERATING_MARGIN, seed.margin, "percent", 0.99, financial_text),
                _claim(company_id, strategy, ClaimType.AI_EXPOSURE, seed.exposure, "ratio", 0.92, strategy_text),
                _text_claim(company_id, strategy, ClaimType.ROLE_NARRATIVE, f"Supplies {seed.subsegment} to the {seed.segment} layer.", strategy_text),
                _text_claim(company_id, strategy, ClaimType.CATALYST, "Synthetic AI-factory demand, product-cycle, and backlog catalyst.", strategy_text),
                _claim(company_id, technical, ClaimType.AI_SEGMENT_CAGR_BEAR, max(0.01, seed.growth - 0.10), "ratio", 0.78, technical_text),
                _claim(company_id, technical, ClaimType.AI_SEGMENT_CAGR_BASE, seed.growth, "ratio", 0.82, technical_text),
                _claim(company_id, technical, ClaimType.AI_SEGMENT_CAGR_BULL, seed.growth + 0.10, "ratio", 0.76, technical_text),
            ]
        )

        moat_types = [
            ClaimType.MOAT_ARCHITECTURAL_LOCK_IN,
            ClaimType.MOAT_SWITCHING_COSTS,
            ClaimType.MOAT_STANDARDS_AND_IP,
            ClaimType.MOAT_ECOSYSTEM_AND_DESIGN_WINS,
            ClaimType.MOAT_BOTTLENECK_SCARCITY,
            ClaimType.MOAT_COMPETITIVE_INTENSITY,
        ]
        moat_offsets = [0.20, -0.10, 0.10, 0.05, -0.20, -0.05]
        for claim_type, offset in zip(moat_types, moat_offsets, strict=True):
            claims.append(
                _claim(
                    company_id,
                    technical,
                    claim_type,
                    min(5.0, max(0.0, seed.moat + offset)),
                    "score_0_5",
                    0.76,
                    technical_text,
                )
            )

        target_severity = min(5.0, seed.risk_discount / 0.35 * 5.0)
        risk_types = [
            ClaimType.RISK_CUSTOMER_CONCENTRATION,
            ClaimType.RISK_CYCLICALITY,
            ClaimType.RISK_EXECUTION,
            ClaimType.RISK_SUPPLY_CHAIN,
            ClaimType.RISK_GEOPOLITICAL_REGULATORY,
            ClaimType.RISK_COMMODITIZATION,
        ]
        risk_offsets = [0.3, 0.1, -0.2, 0.2, -0.1, -0.3]
        for claim_type, offset in zip(risk_types, risk_offsets, strict=True):
            claims.append(
                _claim(
                    company_id,
                    technical,
                    claim_type,
                    min(5.0, max(0.0, target_severity + offset)),
                    "severity_0_5",
                    0.74,
                    technical_text,
                )
            )

    return EvidencePackageIngestor(database).ingest(
        {"companies": companies, "documents": documents, "claims": claims}
    )


def _claim(
    company_id: str,
    document: dict[str, Any],
    claim_type: str,
    value: float,
    unit: str,
    confidence: float,
    evidence_span: str,
) -> dict[str, Any]:
    claim_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{document['id']}:{claim_type}:{value}",
        )
    )
    return EvidenceClaim(
        id=claim_id,
        company_id=company_id,
        document_id=document["id"],
        claim_type=str(claim_type),
        value_numeric=float(value),
        value_text=None,
        unit=unit,
        period_end="2025-12-31",
        confidence=confidence,
        evidence_span=evidence_span,
        page_or_section="Synthetic evidence section",
        source_tier=str(document["source_tier"]),
        published_at=document["published_at"],
    ).to_dict()


def _text_claim(
    company_id: str,
    document: dict[str, Any],
    claim_type: str,
    value: str,
    evidence_span: str,
) -> dict[str, Any]:
    claim_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document['id']}:{claim_type}:{value}"))
    return EvidenceClaim(
        id=claim_id,
        company_id=company_id,
        document_id=document["id"],
        claim_type=str(claim_type),
        value_numeric=None,
        value_text=value,
        unit=None,
        period_end=None,
        confidence=0.85,
        evidence_span=evidence_span,
        page_or_section="Synthetic evidence section",
        source_tier=str(document["source_tier"]),
        published_at=document["published_at"],
    ).to_dict()

