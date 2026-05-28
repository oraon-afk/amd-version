from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.agents.compliance_agent import ComplianceAnalysis, FindingDraft


@dataclass
class ReportDraft:
    summary: str
    payload: dict


class ReportAgent:
    def generate(
        self,
        *,
        findings: list[FindingDraft],
        context_ready: bool,
        rule_count: int = 0,
        analysis: ComplianceAnalysis | None = None,
    ) -> ReportDraft:
        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for finding in findings:
            risk_counts[finding.risk_level] = risk_counts.get(finding.risk_level, 0) + 1

        if analysis is not None and analysis.summary:
            summary = analysis.summary
        elif not context_ready:
            summary = "Audit completed with weak rule-retrieval context. Findings require manual review."
        elif findings:
            summary = f"Audit identified {len(findings)} potential compliance finding(s)."
        else:
            summary = "Audit completed without high-confidence missing-clause findings."

        total_rules = max(rule_count, len(findings), 1)
        failed_rules = len(findings)
        passed_rules = max(total_rules - failed_rules, 0)
        compliance_score = (
            analysis.compliance_score
            if analysis is not None
            else round(max(0.0, 1.0 - (failed_rules / total_rules)), 4)
        )
        analysis_payload = analysis.raw_payload if analysis is not None else {}
        metadata = analysis_payload.get("metadata") if isinstance(analysis_payload, dict) else {}
        status = analysis_payload.get("status") if isinstance(analysis_payload, dict) else None
        structured_findings = [
            {
                "violated_rule": finding.violated_rule,
                "severity": finding.severity,
                "confidence_score": finding.confidence_score,
                "explanation": finding.explanation,
                "recommendation": finding.recommendation,
                "evidence": finding.evidence_text,
                "citation": finding.citation_source,
                "matched_section": finding.rule_result.payload.get("section_title")
                or finding.rule_result.payload.get("section")
                or finding.citation_source,
                "matched_rule_text": finding.matched_rule_text,
                "matched_uploaded_text": finding.matched_uploaded_text,
            }
            for finding in findings
        ]
        return ReportDraft(
            summary=summary,
            payload=self._report_payload(
                compliance_score=compliance_score,
                summary=summary,
                structured_findings=structured_findings,
                failed_rules=failed_rules,
                passed_rules=passed_rules,
                risk_counts=risk_counts,
                context_ready=context_ready,
                metadata=dict(metadata) if isinstance(metadata, dict) else {},
                status=str(status or "generated"),
            ),
        )

    @staticmethod
    def _report_payload(
        *,
        compliance_score: float,
        summary: str,
        structured_findings: list[dict[str, Any]],
        failed_rules: int,
        passed_rules: int,
        risk_counts: dict[str, int],
        context_ready: bool,
        metadata: dict[str, Any],
        status: str,
    ) -> dict[str, Any]:
        return {
                "compliance_score": compliance_score,
                "total_violations": failed_rules,
                "summary": summary,
                "risk_counts": risk_counts,
                "finding_count": failed_rules,
                "findings": structured_findings,
                "passed_rules": passed_rules,
                "failed_rules": failed_rules,
                "recommendations": [finding["recommendation"] for finding in structured_findings],
                "context_ready": context_ready,
                "metadata": metadata,
                "status": status,
        }


report_agent = ReportAgent()
