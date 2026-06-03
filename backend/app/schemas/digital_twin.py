from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ComplianceTwinPolicyProfileResponse(BaseModel):
    id: str
    document_id: str
    latest_audit_id: str | None
    latest_report_id: str | None
    title: str
    domain: str
    status: str
    compliance_score: float | None
    risk_level: str | None
    findings_count: int
    coverage_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceTwinSnapshotResponse(BaseModel):
    id: str
    twin_id: str
    maturity_score: float
    coverage_score: float
    risk_score: float
    total_policies: int
    missing_policy_count: int
    high_risk_policy_count: int
    summary_text: str
    snapshot_payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceDigitalTwinResponse(BaseModel):
    id: str
    user_id: str | None
    name: str
    status: str
    maturity_score: float
    coverage_score: float
    risk_score: float
    missing_policies: list[dict[str, Any]]
    risk_heatmap: list[dict[str, Any]]
    policy_inventory: list[dict[str, Any]]
    summary: dict[str, Any]
    generated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    policies: list[ComplianceTwinPolicyProfileResponse] = []
    history: list[ComplianceTwinSnapshotResponse] = []

    model_config = {"from_attributes": True}
