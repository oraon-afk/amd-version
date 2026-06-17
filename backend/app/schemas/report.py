from datetime import datetime
from pydantic import BaseModel, Field

class CustomReportCreateRequest(BaseModel):
    template: str = Field(..., description="The template type, e.g., 'Executive', 'Auditor', 'Board', 'Technical'")
    sections: list[str] = Field(..., description="List of section names to include, e.g., ['Overview', 'Findings', 'Remediation Plans', 'Evidence Appendix']")

class CustomReportEditRequest(BaseModel):
    generated_json: dict = Field(..., description="The edited JSON payload of the report containing title, metadata, and sections dict")

class CustomReportResponse(BaseModel):
    id: str
    audit_id: str
    template: str
    sections: list[str]
    generated_json: dict
    created_at: datetime

    class Config:
        from_attributes = True
