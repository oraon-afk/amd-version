from datetime import datetime

from pydantic import BaseModel


class RuleDocumentResponse(BaseModel):
    id: str
    rule_set_id: str
    domain: str | None
    category: str | None
    jurisdiction: str | None
    document_type: str
    version: str
    filename: str
    content_type: str
    s3_uri: str
    storage_path: str | None
    status: str
    indexed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceRuleResponse(BaseModel):
    id: str
    rule_document_id: str | None
    category: str
    title: str
    description: str | None
    rule_text: str
    reference: str | None
    version: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
