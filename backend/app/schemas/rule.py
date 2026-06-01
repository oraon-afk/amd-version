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


class RuleUploadBatchItemResponse(BaseModel):
    id: str
    batch_id: str
    rule_document_id: str | None
    filename: str
    status: str
    error_message: str | None
    processing_time_seconds: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RuleUploadBatchResponse(BaseModel):
    id: str
    user_id: str
    module: str
    status: str
    total_documents: int
    completed_documents: int
    failed_documents: int
    running_document: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    documents: list[RuleUploadBatchItemResponse] = []

    model_config = {"from_attributes": True}
