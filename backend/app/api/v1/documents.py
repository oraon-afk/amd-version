from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.document import ComplianceDomainResponse, DocumentResponse, UploadBatchResponse
from backend.app.services.bulk_upload_service import bulk_compliance_upload_service
from backend.app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["documents"])
batch_router = APIRouter(prefix="/batches", tags=["batches"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str = Form(...),
    domain: str = Form(...),
    file: UploadFile | None = File(default=None),
    raw_text: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    return await document_service.upload_document(
        db=db,
        user=current_user,
        title=title,
        domain=domain,
        file=file,
        raw_text=raw_text,
    )


@router.post("/bulk-upload", response_model=UploadBatchResponse)
async def bulk_upload_documents(
    background_tasks: BackgroundTasks,
    domain: str | None = Form(default=None),
    domains: list[str] | None = Form(default=None),
    file_domains: str | None = Form(default=None),
    rule_set_id: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadBatchResponse:
    batch = await bulk_compliance_upload_service.create_batch(
        db=db,
        user=current_user,
        files=files,
        domain=domain,
        domains=domains,
        file_domains=file_domains,
        rule_set_id=rule_set_id,
    )
    if batch.status != "failed":
        background_tasks.add_task(
            bulk_compliance_upload_service.process_batch,
            batch_id=batch.id,
            rule_set_id=rule_set_id,
        )
    return bulk_compliance_upload_service.get_batch(db=db, user=current_user, batch_id=batch.id)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    return document_service.list_documents(db=db, user=current_user)


@router.get("/domains", response_model=list[ComplianceDomainResponse])
def list_domains(db: Session = Depends(get_db)) -> list[ComplianceDomainResponse]:
    return document_service.list_domains(db=db)


@batch_router.get("/{batch_id}", response_model=UploadBatchResponse)
def get_upload_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadBatchResponse:
    return bulk_compliance_upload_service.get_batch(db=db, user=current_user, batch_id=batch_id)
