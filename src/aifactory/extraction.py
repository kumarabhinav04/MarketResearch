from __future__ import annotations

import json
import math
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .database import Database
from .llm import ModelGateway, OfflineModelGateway, PromptRegistry
from .models import ClaimType, EvidenceClaim


class EvidenceExtractionError(RuntimeError):
    pass


class EvidenceProposalService:
    """Retrieves filing passages and stores model output as review-only proposals."""

    def __init__(
        self,
        database: Database,
        gateway: ModelGateway,
        prompts: PromptRegistry,
        policy: dict[str, Any],
        model_name: str,
    ):
        self.database = database
        self.gateway = gateway
        self.prompts = prompts
        self.policy = policy
        self.model_name = model_name
        configured = set(policy.get("claim_definitions", {}))
        allowed = {item.value for item in ClaimType}
        unknown = configured.difference(allowed)
        if unknown:
            raise EvidenceExtractionError(
                f"Extraction policy contains unknown claim types: {sorted(unknown)}"
            )

    def extract(
        self,
        company_id: str,
        *,
        document_id: str | None = None,
        as_of_date: str | None = None,
        document_limit: int = 3,
    ) -> dict[str, Any]:
        if isinstance(self.gateway, OfflineModelGateway):
            raise EvidenceExtractionError("Evidence extraction requires a configured model")
        company = self.database.get_company(company_id)
        if not company:
            raise EvidenceExtractionError("Company not found")
        cutoff = date.fromisoformat(as_of_date or date.today().isoformat())
        if document_id:
            document = self.database.get_document(document_id)
            documents = [document] if document else []
        else:
            documents = self.database.list_extractable_documents(
                company_id, document_limit
            )
        documents = [
            item
            for item in documents
            if item
            and item["company_id"] == company_id
            and date.fromisoformat(str(item["published_at"])[:10]) <= cutoff
        ]
        if not documents:
            raise EvidenceExtractionError("No eligible extractable documents were found")

        created = 0
        invalid = 0
        skipped = 0
        document_results: list[dict[str, Any]] = []
        for document in documents:
            result = self._extract_document(company, document, cutoff.isoformat())
            created += result["pending_proposals"]
            invalid += result["invalid_proposals"]
            skipped += int(result["status"] == "no_relevant_chunks")
            document_results.append(result)
        self.database.audit(
            "evidence_proposal_service",
            "evidence_extraction_completed",
            {
                "company_id": company_id,
                "documents": len(documents),
                "pending_proposals": created,
                "invalid_proposals": invalid,
                "documents_without_relevant_chunks": skipped,
                "policy_version": self.policy["version"],
                "model_provider": self.gateway.provider,
                "model_name": self.model_name,
            },
            company_id=company_id,
        )
        return {
            "company_id": company_id,
            "documents_processed": len(documents),
            "pending_proposals": created,
            "invalid_proposals": invalid,
            "document_results": document_results,
        }

    def review(
        self,
        proposal_id: str,
        decision: str,
        reviewer: str,
        comment: str,
    ) -> dict[str, Any]:
        if decision not in {"accepted", "rejected"}:
            raise EvidenceExtractionError("Decision must be accepted or rejected")
        proposal = self.database.get_claim_proposal(proposal_id)
        if not proposal:
            raise EvidenceExtractionError("Claim proposal not found")
        if proposal["status"] != "pending":
            raise EvidenceExtractionError(
                f"Only pending proposals can be reviewed; current status is {proposal['status']}"
            )
        if decision == "accepted" and proposal["validation_errors_json"]:
            raise EvidenceExtractionError("Invalid proposals cannot be accepted")
        claim_id: str | None = None
        if decision == "accepted":
            payload = proposal["payload_json"]
            claim_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"accepted:{proposal_id}"))
            self.database.upsert_claim(
                EvidenceClaim(
                    id=claim_id,
                    company_id=proposal["company_id"],
                    document_id=proposal["document_id"],
                    claim_type=proposal["claim_type"],
                    value_numeric=payload.get("value_numeric"),
                    value_text=payload.get("value_text"),
                    unit=payload.get("unit"),
                    period_end=payload.get("period_end"),
                    confidence=float(payload["confidence"]),
                    evidence_span=payload["evidence_span"],
                    page_or_section=payload["page_or_section"],
                    source_tier=payload["source_tier"],
                    published_at=payload["published_at"],
                    as_of_eligible=bool(payload.get("as_of_eligible", True)),
                    contradiction=bool(payload.get("contradiction", False)),
                ),
                extraction_method=(
                    f"accepted_model_proposal:{proposal['model_provider']}:"
                    f"{proposal['model_name']}"
                ),
            )
        self.database.review_claim_proposal(
            proposal_id, decision, reviewer, comment
        )
        self.database.audit(
            reviewer,
            "claim_proposal_reviewed",
            {
                "proposal_id": proposal_id,
                "decision": decision,
                "claim_id": claim_id,
                "comment": comment,
            },
            company_id=proposal["company_id"],
        )
        return {"proposal_id": proposal_id, "decision": decision, "claim_id": claim_id}

    def _extract_document(
        self,
        company: dict[str, Any],
        document: dict[str, Any],
        as_of_date: str,
    ) -> dict[str, Any]:
        text = _load_document_text(document)
        selected_chunks, relevant_types = _retrieve_chunks(text, self.policy)
        if not selected_chunks:
            return {
                "document_id": document["id"],
                "status": "no_relevant_chunks",
                "pending_proposals": 0,
                "invalid_proposals": 0,
            }
        definitions = {
            claim_type: self.policy["claim_definitions"][claim_type]
            for claim_type in relevant_types
        }
        system_prompt = self.prompts.render(
            "evidence proposal extraction agent",
            as_of_date,
            role_file="extraction.txt",
        )
        user_prompt = json.dumps(
            {
                "company": {
                    "id": company["id"],
                    "legal_name": company["legal_name"],
                    "ticker": company["ticker"],
                    "segment": company["segment"],
                    "subsegment": company["subsegment"],
                },
                "document": {
                    "id": document["id"],
                    "title": document["title"],
                    "source_type": document["source_type"],
                    "source_tier": document["source_tier"],
                    "published_at": document["published_at"],
                    "injection_flags": document["injection_flags_json"],
                },
                "claim_definitions": definitions,
                "maximum_proposals": self.policy["max_proposals_per_document"],
                "document_chunks": selected_chunks,
            },
            sort_keys=True,
        )
        schema = {
            "type": "object",
            "properties": {
                "proposals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_type": {"type": "string"},
                            "value_numeric": {"type": ["number", "null"]},
                            "value_text": {"type": ["string", "null"]},
                            "unit": {"type": ["string", "null"]},
                            "period_end": {"type": ["string", "null"]},
                            "confidence": {"type": "number"},
                            "evidence_span": {"type": "string"},
                            "page_or_section": {"type": "string"},
                            "contradiction": {"type": "boolean"},
                        },
                        "required": [
                            "claim_type",
                            "value_numeric",
                            "value_text",
                            "unit",
                            "period_end",
                            "confidence",
                            "evidence_span",
                            "page_or_section",
                            "contradiction",
                        ],
                    },
                }
            },
            "required": ["proposals"],
        }
        generated = self.gateway.complete_json(
            system_prompt,
            user_prompt,
            schema,
            max_completion_tokens=int(self.policy["model_max_completion_tokens"]),
        )
        raw_proposals = generated.get("proposals", [])
        if not isinstance(raw_proposals, list):
            raise EvidenceExtractionError("Model proposals must be an array")
        raw_proposals = raw_proposals[: int(self.policy["max_proposals_per_document"])]
        chunk_map = {item["chunk_id"]: item["text"] for item in selected_chunks}
        pending = 0
        invalid = 0
        for raw in raw_proposals:
            proposal, errors = _validate_proposal(
                raw,
                document,
                chunk_map,
                definitions,
                self.policy,
            )
            proposal_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{document['id']}:{json.dumps(proposal, sort_keys=True)}",
                )
            )
            status = "invalid" if errors else "pending"
            self.database.upsert_claim_proposal(
                {
                    "id": proposal_id,
                    "company_id": company["id"],
                    "document_id": document["id"],
                    "claim_type": proposal.get("claim_type", "invalid"),
                    "payload": proposal,
                    "status": status,
                    "validation_errors": errors,
                    "model_provider": self.gateway.provider,
                    "model_name": self.model_name,
                    "prompt_version": self.policy["version"],
                }
            )
            if errors:
                invalid += 1
            else:
                pending += 1
        return {
            "document_id": document["id"],
            "status": "completed",
            "chunks_considered": len(selected_chunks),
            "relevant_claim_types": relevant_types,
            "pending_proposals": pending,
            "invalid_proposals": invalid,
        }


def _load_document_text(document: dict[str, Any]) -> str:
    metadata = document.get("metadata_json", {})
    normalized_path = metadata.get("normalized_text_path")
    path = Path(normalized_path or document.get("local_path") or "")
    if not path.is_file():
        raise EvidenceExtractionError("Document content is not available locally")
    if path.stat().st_size > 75 * 1024 * 1024:
        raise EvidenceExtractionError("Document exceeds the extraction size limit")
    if path.suffix.lower() == ".pdf":
        raise EvidenceExtractionError("PDF extraction requires the optional document parser")
    if normalized_path or path.suffix.lower() in {".txt", ".json"}:
        return path.read_text(encoding="utf-8", errors="replace")
    body = path.read_bytes()
    soup = BeautifulSoup(body, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def _retrieve_chunks(
    text: str, policy: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    size = int(policy["chunk_size_chars"])
    overlap = int(policy["chunk_overlap_chars"])
    step = max(1, size - overlap)
    chunks = [text[start : start + size] for start in range(0, len(text), step)]
    scored: list[tuple[int, int, set[str]]] = []
    relevant_types: set[str] = set()
    definitions = policy["claim_definitions"]
    for index, chunk in enumerate(chunks):
        lowered = chunk.casefold()
        matched_types: set[str] = set()
        score = 0
        for claim_type, definition in definitions.items():
            keyword_score = sum(
                lowered.count(str(keyword).casefold())
                for keyword in definition.get("keywords", [])
            )
            if keyword_score:
                matched_types.add(claim_type)
                relevant_types.add(claim_type)
                score += keyword_score
        if score:
            scored.append((score, index, matched_types))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = scored[: int(policy["max_context_chunks"])]
    return (
        [
            {
                "chunk_id": f"chunk:{index}",
                "matched_claim_types": sorted(matched),
                "text": chunks[index],
            }
            for _, index, matched in selected
        ],
        sorted(relevant_types),
    )


def _validate_proposal(
    raw: Any,
    document: dict[str, Any],
    chunks: dict[str, str],
    definitions: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(raw, dict):
        return {"claim_type": "invalid"}, ["Proposal must be an object"]
    proposal = {
        "claim_type": str(raw.get("claim_type") or ""),
        "value_numeric": raw.get("value_numeric"),
        "value_text": raw.get("value_text"),
        "unit": raw.get("unit"),
        "period_end": raw.get("period_end"),
        "confidence": raw.get("confidence"),
        "evidence_span": str(raw.get("evidence_span") or "").strip(),
        "page_or_section": str(raw.get("page_or_section") or ""),
        "source_tier": document["source_tier"],
        "published_at": document["published_at"],
        "as_of_eligible": True,
        "contradiction": bool(raw.get("contradiction", False)),
    }
    errors: list[str] = []
    claim_type = proposal["claim_type"]
    definition = definitions.get(claim_type)
    if not definition:
        errors.append("Claim type is not allowed for the retrieved context")
    quote = proposal["evidence_span"]
    if not (
        int(policy["minimum_quote_chars"])
        <= len(quote)
        <= int(policy["maximum_quote_chars"])
    ):
        errors.append("Evidence quote length is outside policy bounds")
    chunk = chunks.get(proposal["page_or_section"])
    if chunk is None:
        errors.append("Proposal references an unknown chunk")
    elif quote not in chunk:
        errors.append("Evidence quote is not an exact substring of the cited chunk")
    confidence = proposal["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        errors.append("Confidence must be numeric")
        proposal["confidence"] = 0.0
    elif not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= float(
        policy["maximum_model_confidence"]
    ):
        errors.append("Confidence is outside the model-proposal range")
    else:
        proposal["confidence"] = float(confidence)
    if definition and "minimum" in definition:
        value = proposal["value_numeric"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append("Numeric claim requires value_numeric")
        elif not math.isfinite(float(value)) or not (
            float(definition["minimum"])
            <= float(value)
            <= float(definition["maximum"])
        ):
            errors.append("Proposed numeric value is outside the claim range")
        else:
            proposal["value_numeric"] = float(value)
        if proposal["unit"] != definition.get("unit"):
            errors.append("Proposed unit does not match the extraction policy")
    elif definition:
        if proposal["value_numeric"] is not None:
            errors.append("Narrative claim may not contain value_numeric")
        if not str(proposal.get("value_text") or "").strip():
            errors.append("Narrative claim requires value_text")
    period_end = proposal.get("period_end")
    if period_end:
        try:
            date.fromisoformat(str(period_end)[:10])
        except ValueError:
            errors.append("period_end must be an ISO date or null")
    return proposal, errors
