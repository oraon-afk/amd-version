from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

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
    def trace(self, *, finding: FindingDraft, db: Session | None = None) -> list[EvidenceDraft]:
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
        uploaded_evidence = EvidenceDraft(
            source_type="uploaded_document",
            qdrant_point_id=uploaded_chunk.get("qdrant_point_id") or payload.get("uploaded_point_id"),
            document_id=uploaded_chunk.get("document_id") or payload.get("document_id"),
            page_number=uploaded_chunk.get("page_number"),
            section_title=uploaded_chunk.get("section_title") or uploaded_chunk.get("section") or "Matched uploaded excerpt",
            citation_text=finding.matched_uploaded_text[:2000],
            citation_label=uploaded_chunk.get("citation_label") or finding.citation_source,
            confidence_score=finding.confidence_score,
        )

        results = [rule_evidence, uploaded_evidence]

        # ── Evidence 3: external collector evidence if db is available ────────
        if db is not None:
            doc_id = uploaded_evidence.document_id
            category = payload.get("category") if payload else None

            from backend.app.db.models.collector import EvidenceCollector, ExternalEvidence

            conditions = []
            if doc_id:
                conditions.append(
                    ExternalEvidence.collector_id.in_(
                        select(EvidenceCollector.id).where(EvidenceCollector.document_id == doc_id)
                    )
                )
            if category:
                conditions.append(
                    ExternalEvidence.collector_id.in_(
                        select(EvidenceCollector.id).where(EvidenceCollector.target_domain == category)
                    )
                )

            if conditions:
                try:
                    external_records = db.scalars(
                        select(ExternalEvidence).where(or_(*conditions))
                    ).all()

                    for record in external_records:
                        results.append(
                            EvidenceDraft(
                                source_type="external_collector",
                                qdrant_point_id=None,
                                document_id=doc_id,
                                page_number=None,
                                section_title=record.citation_label or "External Collector Evidence",
                                citation_text=record.evidence_text or "",
                                citation_label=record.citation_label,
                                confidence_score=record.confidence_score * 0.8,
                            )
                        )
                except Exception as exc:
                    # Non-fatal during audit workflow run
                    import logging
                    logging.getLogger(__name__).warning("Failed to fetch external evidence: %s", exc)

        return results


evidence_agent = EvidenceAgent()
