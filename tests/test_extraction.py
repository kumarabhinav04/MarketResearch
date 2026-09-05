from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from aifactory.database import Database
from aifactory.extraction import EvidenceProposalService
from aifactory.ingestion import make_document
from aifactory.llm import ModelGateway, PromptRegistry


ROOT = Path(__file__).resolve().parents[1]


class FakeGateway(ModelGateway):
    provider = "test"

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_completion_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload = json.loads(user_prompt)
        chunk = payload["document_chunks"][0]
        quote = "Data center demand increased and supply remained constrained."
        self.assertions = {
            "quote_present": quote in chunk["text"],
            "schema_requires_proposals": "proposals" in schema["required"],
            "task_token_budget": max_completion_tokens,
        }
        return {
            "proposals": [
                {
                    "claim_type": "moat_bottleneck_scarcity",
                    "value_numeric": 4.0,
                    "value_text": "A scored judgment based on reported constrained supply.",
                    "unit": "score",
                    "period_end": None,
                    "confidence": 0.8,
                    "evidence_span": quote,
                    "page_or_section": chunk["chunk_id"],
                    "contradiction": False,
                }
            ]
        }


class EvidenceProposalTests(unittest.TestCase):
    def test_model_output_requires_review_before_becoming_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = Database(root / "test.db")
            database.initialize()
            database.upsert_company(
                {
                    "id": "issuer",
                    "legal_name": "Issuer Inc",
                    "ticker": "ISS",
                    "exchange": "NYSE",
                    "security_id": "CIK1",
                    "segment": "compute_servers",
                    "subsegment": "accelerators",
                }
            )
            text = (
                "The company sells accelerated computing systems for data center use. "
                "Data center demand increased and supply remained constrained. "
                "The company is expanding capacity."
            )
            normalized = root / "filing.normalized.txt"
            normalized.write_text(text, encoding="utf-8")
            document = make_document(
                "issuer",
                "regulatory_filing",
                "1",
                "Regulator",
                "Annual filing",
                "https://example.com/filing",
                "2026-02-01",
                text,
            )
            document["local_path"] = str(normalized)
            document["metadata"] = {"normalized_text_path": str(normalized)}
            database.upsert_document(document)
            policy = json.loads(
                (ROOT / "config" / "extraction_policy.json").read_text(encoding="utf-8")
            )
            gateway = FakeGateway()
            service = EvidenceProposalService(
                database,
                gateway,
                PromptRegistry(ROOT / "config" / "prompts"),
                policy,
                "test-model",
            )

            result = service.extract(
                "issuer", document_id=document["id"], as_of_date="2026-03-01"
            )

            self.assertEqual(result["pending_proposals"], 1)
            self.assertEqual(database.list_claims("issuer", "2026-03-01"), [])
            proposal = database.list_claim_proposals("issuer", "pending")[0]
            review = service.review(
                proposal["id"], "accepted", "analyst@example.com", "Verified quote"
            )
            self.assertIsNotNone(review["claim_id"])
            claims = database.list_claims("issuer", "2026-03-01")
            self.assertEqual(claims[0].claim_type, "moat_bottleneck_scarcity")
            self.assertTrue(gateway.assertions["quote_present"])
            self.assertEqual(gateway.assertions["task_token_budget"], 2400)


if __name__ == "__main__":
    unittest.main()
