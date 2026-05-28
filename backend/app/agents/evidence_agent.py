from __future__ import annotations

from dataclasses import dataclass

from backend.app.agents.compliance_agent import FindingDraft
from backend.app.rag.scoring.citation_score import citation_quality_score


@dataclass
class EvidenceDraft:
    source_type: str
    qdrant_point_id: str | None
    document_id: str | None
    page_number: int | None
    section_title: str | None
    citation_text: str
    citation_label: str | None
    confidence_score: float


class EvidenceAgent:
    def trace(self, *, finding: FindingDraft) -> list[EvidenceDraft]:
        payload = finding.rule_result.payload
        uploaded_chunk = finding.matched_document_chunk or {}

        # ── Evidence 1: the compliance rule that was matched ─────────────────
        rule_evidence = EvidenceDraft(
            source_type=str(payload.get("source_type", "compliance_rule")),
            qdrant_point_id=finding.rule_result.point_id,
            document_id=payload.get("document_id"),
            page_number=payload.get("page_number"),
            section_title=payload.get("section_title"),
            citation_text=str(payload.get("text", ""))[:2000],
            citation_label=payload.get("citation_label"),
            confidence_score=citation_quality_score(payload),
        )

        # ── Evidence 2: the matching excerpt from the uploaded document ───────
        #
        # Original gaps:
        #   • qdrant_point_id was always None — if the uploaded chunk was also
        #     stored in Qdrant (e.g. in qdrant_upload_collection) we lose the
        #     reference and cannot cross-link.  Populate from payload when
        #     available so the audit trail stays complete.
        #   • document_id was always None — the rule payload often carries
        #     "uploaded_by" / "document_id" metadata; propagate it here.
        uploaded_evidence = EvidenceDraft(
            source_type="uploaded_document",
            # Pull the Qdrant point ID for the uploaded chunk if the rule
            # payload exposes it (e.g. stored as "uploaded_point_id").  Falls
            # back to None when not present so existing behaviour is unchanged.
            qdrant_point_id=uploaded_chunk.get("qdrant_point_id") or payload.get("uploaded_point_id"),
            # Propagate document_id from the rule payload when available.
            document_id=uploaded_chunk.get("document_id") or payload.get("document_id"),
            page_number=uploaded_chunk.get("page_number"),
            section_title=uploaded_chunk.get("section_title") or uploaded_chunk.get("section") or "Matched uploaded excerpt",
            citation_text=finding.matched_uploaded_text[:2000],
            citation_label=uploaded_chunk.get("citation_label") or finding.citation_source,
            confidence_score=finding.confidence_score,
        )

        return [rule_evidence, uploaded_evidence]


evidence_agent = EvidenceAgent()
