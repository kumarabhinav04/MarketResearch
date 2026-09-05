from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database import Database


class ReportGenerator:
    def __init__(self, database: Database, report_dir: Path):
        self.database = database
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, run_id: str) -> tuple[Path, Path]:
        run = self.database.get_run(run_id)
        if not run:
            raise KeyError(f"Unknown run: {run_id}")
        rankings = self.database.list_rankings(run_id)
        if not rankings:
            raise ValueError("Run has no rankings")

        markdown = self._render_markdown(run, rankings)
        report_path = self.report_dir / f"{run_id}.md"
        report_path.write_text(markdown, encoding="utf-8")
        report_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

        manifest = {
            "run_id": run_id,
            "as_of_date": run["as_of_date"],
            "status": run["status"],
            "generated_at": datetime.now(UTC).isoformat(),
            "taxonomy_version": run["taxonomy_version"],
            "scoring_version": run["scoring_version"],
            "prompt_version": run["prompt_version"],
            "model_provider": run["model_provider"],
            "model_name": run["model_name"],
            "ranked_company_count": len(rankings),
            "report_sha256": report_hash,
            "evidence_claim_ids": sorted(
                {
                    claim_id
                    for item in rankings
                    for claim_id in item["assessment_json"]["evidence_claim_ids"]
                }
            ),
        }
        manifest_path = self.report_dir / f"{run_id}.manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        return report_path, manifest_path

    def _render_markdown(
        self, run: dict[str, Any], rankings: list[dict[str, Any]]
    ) -> str:
        lines = [
            "# AI Factory Fundamental Growth Ranking",
            "",
            f"**Research cutoff:** {run['as_of_date']}",
            f"**Run ID:** `{run['id']}`",
            f"**Status:** {run['status']}",
            "",
            "> This report ranks fundamental AI-factory growth beneficiaries. It does not predict stock-price returns and is not investment advice. Demo securities and evidence are synthetic.",
            "",
            "## Methodology",
            "",
            "Risk-adjusted TAFGS = Moat Score × Operating Margin Score × Company AI-driven CAGR (%) × (1 − Risk Discount). Confidence and scenario rank ranges are reported separately.",
            "",
            "## Ranking",
            "",
            "| Rank | Company | Role | Score | Bear–bull rank | Evidence confidence | Review |",
            "|---:|---|---|---:|---:|---:|---|",
        ]
        for item in rankings:
            lines.append(
                "| {rank} | {name} ({ticker}) | {segment} | {score:.2f} | {bear}–{bull} | {confidence:.0%} | {review} |".format(
                    rank=item["rank"],
                    name=item["legal_name"],
                    ticker=item["ticker"],
                    segment=item["subsegment"].replace("_", " "),
                    score=item["risk_adjusted_tafgs"],
                    bear=item["bear_rank"],
                    bull=item["bull_rank"],
                    confidence=item["evidence_confidence"],
                    review=item["review_status"],
                )
            )

        for item in rankings:
            assessment = item["assessment_json"]
            forecast = assessment["forecast"]
            lines.extend(
                [
                    "",
                    f"## {item['rank']}. {item['legal_name']} ({item['ticker']})",
                    "",
                    f"- **AI-factory role:** {assessment['narrative'].get('role', 'Unavailable')}",
                    f"- **AI revenue exposure:** {assessment['ai_exposure']:.1%}",
                    f"- **Moat score:** {assessment['moat_score']:.2f}/5",
                    f"- **Operating margin:** {assessment['operating_margin_pct']:.1f}% (score {assessment['operating_margin_score']}/5)",
                    f"- **Company AI-driven CAGR:** {forecast['base_company_ai_cagr']:.1%} base; {forecast['bear_company_ai_cagr']:.1%}–{forecast['bull_company_ai_cagr']:.1%} scenario range",
                    f"- **Risk discount:** {assessment['risk_discount']:.1%}",
                    f"- **Risk-adjusted TAFGS:** {assessment['risk_adjusted_tafgs']:.2f}",
                    f"- **Evidence confidence:** {assessment['evidence_confidence']:.1%}; citation coverage {assessment['citation_coverage']:.1%}",
                    f"- **Catalysts:** {'; '.join(assessment['narrative'].get('catalysts', [])) or 'No approved catalyst narrative.'}",
                    f"- **Warnings:** {'; '.join(assessment['warnings']) or 'None.'}",
                    "",
                    "Evidence IDs: "
                    + ", ".join(f"`{claim_id}`" for claim_id in assessment["evidence_claim_ids"]),
                ]
            )
        lines.extend(
            [
                "",
                "## Governance notes",
                "",
                "- Scores are reproducible from the run manifest and evidence IDs.",
                "- Market-stack weights inform source discovery and market sizing; they are not directly multiplied into TAFGS.",
                "- Publication should require analyst approval of every ranked company.",
                "",
            ]
        )
        return "\n".join(lines)

