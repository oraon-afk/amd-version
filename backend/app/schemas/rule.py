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
    status: str = "active"
    created_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RuleUploadBatchItemResponse(BaseModel):
    id: str
    batch_id: str
    rule_document_id: str | None
    filename: str
    content_type: str | None = None
    file_size_bytes: int = 0
    status: str
    retry_count: int = 0
    max_retries: int = 0
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
    processed_documents: int = 0
    pending_documents: int = 0
    progress_label: str | None = None
    running_document: str | None
    error_message: str | None
    summary_report: dict | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    documents: list[RuleUploadBatchItemResponse] = []

    model_config = {"from_attributes": True}
