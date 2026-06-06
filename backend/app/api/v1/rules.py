from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import require_admin
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.rule import RuleDocumentResponse
from backend.app.services.rule_service import rule_service

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("/upload", response_model=RuleDocumentResponse)
async def upload_rule(
    file: UploadFile = File(...),
    rule_set_id: str = Form(...),
    domain: str | None = Form(default=None),
    category: str | None = Form(default=None),
    jurisdiction: str | None = Form(default=None),
    document_type: str = Form(default="rules"),
    version: str = Form(default="v1"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RuleDocumentResponse:
    return await rule_service.upload_and_index_rule(
        db=db,
        user=current_user,
        file=file,
        rule_set_id=rule_set_id,
        domain=domain,
        category=category,
        jurisdiction=jurisdiction,
        document_type=document_type,
        version=version,
    )
