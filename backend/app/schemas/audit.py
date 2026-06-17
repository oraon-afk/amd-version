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
    review_deadline: datetime | None = None

    @computed_field
    @property
    def has_pending_reviews(self) -> bool:
        """True when the audit is in pending_review state."""
        return self.status == "pending_review"

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
    # Feature 1: HITL review fields
    needs_review: bool = False
    review_status: str = "not_required"
    is_active: bool = True
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None

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
            "audit_score",
            "auditScore",
            "overall_score",
            "overallScore",
            "final_score",
            "finalScore",
            "score",
            normalize_percent=True,
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


class ComplianceScoreDiagnosticResponse(BaseModel):
    id: str
    audit_id: str
    report_id: str | None
    rules_evaluated: int
    rules_matched: int
    rules_failed: int
    match_confidence: float | None
    score_reasoning: str
    diagnostics_payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class FullDiagnosticsResponse(ComplianceScoreDiagnosticResponse):
    """Feature 2: Extended response from GET /audits/{id}/diagnostics/full."""
    retry_attempts: list[dict[str, Any]] | None = None
    final_prompt: str | None = None
    final_llm_response: str | None = None
    context_chunks_snapshot: list[dict[str, Any]] | None = None
    heuristic_confidence: float | None = None
    blended_confidence: float | None = None


# ── Feature 1: HITL schemas ──────────────────────────────────────────────────

class FindingReviewRequest(BaseModel):
    action: str  # "accept" | "reject" | "modify"
    comment: str | None = None
    modified_fields: dict[str, Any] | None = None


class FindingReviewResponse(BaseModel):
    finding_id: str
    review_status: str
    reviewed_by: str
    reviewed_at: datetime
    previous_state: dict[str, Any] | None = None


class PublishReportResponse(BaseModel):
    report_id: str
    audit_id: str
    status: str
    published_at: datetime
    download_urls: dict[str, str]


class EvidenceItemSchema(BaseModel):
    text: str
    page: int | None = None
    section: str | None = None


class FindingExplanationResponse(BaseModel):
    finding_id: str
    explanation_text: str
    evidence_list: list[EvidenceItemSchema]
    confidence_score: float


def _read_number(payload: dict[str, Any], *keys: str, normalize_percent: bool = False) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            number = float(value)
            return number / 100 if normalize_percent and number > 1 else number
        if isinstance(value, str):
            try:
                number = float(value.strip().removesuffix("%"))
            except ValueError:
                continue
            if math.isfinite(number):
                return number / 100 if normalize_percent and (value.strip().endswith("%") or number > 1) else number
    return None
