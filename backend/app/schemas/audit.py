from datetime import datetime
import math
from typing import Any

from pydantic import BaseModel, computed_field


class CreateAuditRequest(BaseModel):
    document_id: str
    rule_set_id: str | None = None


class AuditResponse(BaseModel):
    id: str
    document_id: str
    rule_set_id: str | None
    status: str
    overall_risk: str | None
    confidence_score: float | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    id: str
    audit_id: str
    document_id: str | None
    violated_rule: str
    finding_type: str
    severity: str
    risk_level: str
    confidence_score: float
    confidence: float
    evidence_text: str | None
    citation_source: str | None
    explanation: str
    recommendation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    id: str
    finding_id: str
    source_type: str
    qdrant_point_id: str | None
    document_id: str | None
    page_number: int | None
    section_title: str | None
    citation_text: str
    citation_label: str | None
    confidence_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: str
    audit_id: str
    summary: str
    report_payload: dict[str, Any]
    report_json_s3_uri: str | None
    created_at: datetime

    @computed_field
    @property
    def compliance_score(self) -> float | None:
        return _read_number(
            self.report_payload,
            "compliance_score",
            "complianceScore",
            "overall_score",
            "overallScore",
            "score",
            "risk_score",
        )

    @computed_field
    @property
    def findings(self) -> list[dict[str, Any]]:
        findings = self.report_payload.get("findings")
        return findings if isinstance(findings, list) else []

    @computed_field
    @property
    def findings_count(self) -> int:
        count = _read_number(
            self.report_payload,
            "finding_count",
            "findings_count",
            "total_violations",
            "failed_rules",
        )
        if count is not None:
            return max(int(count), len(self.findings))
        return len(self.findings)

    @computed_field
    @property
    def risk_level(self) -> str | None:
        explicit = self.report_payload.get("risk_level") or self.report_payload.get("riskLevel")
        if explicit:
            return str(explicit).upper()

        risk_counts = self.report_payload.get("risk_counts")
        if not isinstance(risk_counts, dict):
            return None
        if _read_number(risk_counts, "CRITICAL", "critical"):
            return "CRITICAL"
        if _read_number(risk_counts, "HIGH", "high"):
            return "HIGH"
        if _read_number(risk_counts, "MEDIUM", "medium"):
            return "MEDIUM"
        if _read_number(risk_counts, "LOW", "low"):
            return "LOW"
        return None

    @computed_field
    @property
    def status(self) -> str | None:
        status = self.report_payload.get("status")
        return str(status) if status is not None else None

    @computed_field
    @property
    def compliance_status(self) -> str | None:
        explicit = self.report_payload.get("compliance_status") or self.report_payload.get("complianceStatus")
        if explicit:
            return str(explicit)
        if self.findings_count > 0:
            return "Review required"
        score = self.compliance_score
        if score is None:
            return None
        normalized = score if score <= 1 else score / 100
        return "Compliant" if normalized >= 0.8 else "Review required"

    model_config = {"from_attributes": True}


def _read_number(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
        if isinstance(value, str):
            try:
                number = float(value.strip().removesuffix("%"))
            except ValueError:
                continue
            if math.isfinite(number):
                return number / 100 if value.strip().endswith("%") else number
    return None
