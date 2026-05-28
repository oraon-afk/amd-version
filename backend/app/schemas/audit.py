from datetime import datetime
from typing import Any

from pydantic import BaseModel


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

    model_config = {"from_attributes": True}
