import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.jwt_service import create_access_token, create_refresh_token
from backend.app.auth.password_service import hash_password, verify_password
from backend.app.auth.auth_dependencies import get_current_user
from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_once
from backend.app.db.models.user import User
from backend.app.db.session import database_error_root_cause, get_db, recover_from_database_error
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.services.audit_log_service import audit_log_service

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    email = payload.email.lower()
    try:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        user = User(
            email=email,
            name=payload.full_name or email,
            password_hash=hash_password(payload.password),
            role=_registration_role(db=db, email=email, requested_role=payload.role),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        audit_log_service.log(
            db=db,
            user=user,
            action="auth.registered",
            entity_type="user",
            entity_id=user.id,
            metadata={"role": user.role},
        )
        return user
    except HTTPException:
        raise
    except IntegrityError as exc:
        db.rollback()
        logger.warning("User registration integrity error for %s: %s", email, exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        recover_from_database_error(exc)
        log_once(
            logger,
            logging.WARNING,
            "auth_register_database_unavailable",
            "AUTH_REGISTER_DATABASE_UNAVAILABLE root_cause=%s",
            database_error_root_cause(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Please try again shortly.",
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
    except SQLAlchemyError as exc:
        recover_from_database_error(exc)
        log_once(
            logger,
            logging.WARNING,
            "auth_login_database_unavailable",
            "AUTH_LOGIN_DATABASE_UNAVAILABLE root_cause=%s",
            database_error_root_cause(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Please try again shortly.",
        ) from exc

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    audit_log_service.log(
        db=db,
        user=user,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        metadata={"role": user.role},
    )
    return TokenResponse(
        access_token=create_access_token(subject=user.id, extra_claims={"role": user.role}),
        refresh_token=create_refresh_token(subject=user.id, extra_claims={"role": user.role}),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def _registration_role(*, db: Session, email: str, requested_role: str | None) -> str:
    existing_count = db.scalar(select(func.count()).select_from(User)) or 0
    if existing_count == 0:
        return "ADMIN"
    if email.lower() in settings.default_admin_email_list:
        return "ADMIN"
    normalized = (requested_role or "USER").strip().upper()
    if normalized in {"ADMIN", "USER"}:
        return normalized
    return "USER"
