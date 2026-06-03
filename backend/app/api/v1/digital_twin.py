from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.digital_twin import (
    ComplianceDigitalTwinResponse,
    ComplianceTwinSnapshotResponse,
)
from backend.app.services.digital_twin_service import digital_twin_service

router = APIRouter(prefix="/digital-twin", tags=["digital-twin"])


@router.get("", response_model=ComplianceDigitalTwinResponse)
def get_digital_twin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceDigitalTwinResponse:
    return digital_twin_service.get_or_rebuild(db=db, user=current_user)


@router.post("/rebuild", response_model=ComplianceDigitalTwinResponse)
def rebuild_digital_twin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceDigitalTwinResponse:
    return digital_twin_service.get_or_rebuild(db=db, user=current_user, rebuild=True)


@router.get("/history", response_model=list[ComplianceTwinSnapshotResponse])
def get_digital_twin_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ComplianceTwinSnapshotResponse]:
    return digital_twin_service.history(db=db, user=current_user)
