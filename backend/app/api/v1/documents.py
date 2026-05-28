from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.document import ComplianceDomainResponse, DocumentResponse
from backend.app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


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


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    return document_service.list_documents(db=db, user=current_user)


@router.get("/domains", response_model=list[ComplianceDomainResponse])
def list_domains(db: Session = Depends(get_db)) -> list[ComplianceDomainResponse]:
    return document_service.list_domains(db=db)
