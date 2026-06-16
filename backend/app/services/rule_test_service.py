"""
Feature 4: Configurable Rule Engine – Rule Test Service.

Allows administrators to test a single compliance rule against
sample document text using the same RAG + LLM pipeline as a full audit,
without persisting any results.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.models.rule import ComplianceRule
from backend.app.db.models.user import User

logger = get_logger(__name__)


class RuleTestService:
    """Test a compliance rule against sample text using the live evaluation pipeline."""

    def test_rule(
        self,
        *,
        db: Session,
        user: User,
        rule_id: str,
        sample_document_text: str,
    ) -> dict[str, Any]:
        """
        Evaluate a single compliance rule against sample text.

        Returns:
            {
                rule_matched: bool,
                confidence: float,
                matched_chunks: list[str],
                explanation: str,
                rule_id: str,
                rule_title: str,
            }
        """
        if (user.role or "").upper() != "ADMIN":
            raise PermissionError("Only administrators can test compliance rules.")

        rule = db.scalar(select(ComplianceRule).where(ComplianceRule.id == rule_id))
        if rule is None:
            raise ValueError(f"Compliance rule not found: {rule_id}")

        try:
            from backend.app.agents.retrieval_agent import retrieval_agent
            from backend.app.agents.compliance_agent import compliance_agent
        except ImportError as exc:
            raise RuntimeError("Agent dependencies not available.") from exc

        # Use the full retrieval pipeline restricted to this single rule's text
        try:
            retrieval = retrieval_agent.retrieve_rules(
                document_text=sample_document_text,
                domain=rule.category,
                rule_set_id=None,
                audit_id=None,
                document_id=None,
            )
        except Exception as exc:
            logger.warning("Retrieval failed during rule test: %s", exc)
            return {
                "rule_id": rule_id,
                "rule_title": rule.title,
                "rule_matched": False,
                "confidence": 0.0,
                "matched_chunks": [],
                "explanation": f"Retrieval error: {exc}",
            }

        # Filter retrieval results to only include this rule
        relevant_results = [
            r for r in retrieval.results
            if (r.payload or {}).get("rule_id") == rule_id
            or rule.rule_text[:80] in str((r.payload or {}).get("text", ""))
        ]

        if not relevant_results:
            # Fall back to all retrieved results for a best-effort test
            relevant_results = retrieval.results[:3]

        if not relevant_results:
            return {
                "rule_id": rule_id,
                "rule_title": rule.title,
                "rule_matched": False,
                "confidence": 0.0,
                "matched_chunks": [],
                "explanation": "No relevant rule chunks were retrieved for the sample text.",
            }

        try:
            # Run compliance analysis against the filtered rule candidates
            # Use a short sample chunk list
            sample_chunks: list[dict] = [
                {"chunk_id": "sample_0", "text": sample_document_text[:1500], "page_number": 1}
            ]
            analysis = compliance_agent.evaluate_analysis(
                document_text=sample_document_text,
                document_chunks=sample_chunks,
                rule_results=relevant_results,
                audit_id=None,
                document_id=None,
                domain=rule.category,
            )

            has_finding = any(
                rule.rule_text[:40].lower() in (f.violated_rule or "").lower()
                or rule.title.lower() in (f.violated_rule or "").lower()
                for f in analysis.findings
            )

            matched_chunks = [
                str((r.payload or {}).get("text", ""))[:300]
                for r in relevant_results
            ]

            avg_confidence = (
                sum(f.confidence_score for f in analysis.findings) / len(analysis.findings)
                if analysis.findings
                else analysis.compliance_score
            )

            return {
                "rule_id": rule_id,
                "rule_title": rule.title,
                "rule_matched": not has_finding,
                "confidence": round(avg_confidence, 4),
                "matched_chunks": matched_chunks[:3],
                "explanation": analysis.summary or (
                    f"Rule '{rule.title}' {'satisfied' if not has_finding else 'violated'} "
                    f"with compliance score {analysis.compliance_score:.0%}."
                ),
            }
        except Exception as exc:
            logger.warning("LLM evaluation failed during rule test: %s", exc)
            return {
                "rule_id": rule_id,
                "rule_title": rule.title,
                "rule_matched": False,
                "confidence": 0.0,
                "matched_chunks": [],
                "explanation": f"LLM evaluation error: {exc}",
            }


rule_test_service = RuleTestService()
