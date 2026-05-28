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
