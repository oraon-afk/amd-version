from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    title: str
    domain: str
    role_type: str
    source_type: str
    s3_key: str | None
    qdrant_collection: str
    upload_status: str
    processing_stage: str
    cleanup_status: str
    file_name: str | None
    file_type: str | None
    filename: str
    content_type: str
    s3_uri: str
    status: str
    extracted_text: str | None = None
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class ComplianceDomainResponse(BaseModel):
    id: str | None = None
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class BatchDocumentResponse(BaseModel):
    id: str
    batch_id: str
    document_id: str | None
    audit_id: str | None
    filename: str
    title: str
    domain: str | None
    queue_position: int
    status: str
    current_stage: str | None = None
    error_message: str | None
    processing_time_seconds: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadBatchResponse(BaseModel):
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
    documents: list[BatchDocumentResponse] = []

    model_config = {"from_attributes": True}
