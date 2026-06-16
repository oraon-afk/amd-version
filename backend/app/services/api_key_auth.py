"""
Feature 6: API Key authentication dependency.

Provides get_api_key_user() FastAPI dependency that validates
the X-API-Key header against stored API key hashes.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from backend.app.db.models.user import User
from backend.app.db.session import get_db

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key_user(
    raw_key: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: authenticate an external system via X-API-Key header.

    Returns the User who owns the API key.
    Raises HTTP 401 if no key provided or invalid.
    """
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required for this endpoint.",
        )

    # Import here to avoid circular imports during startup
    from backend.app.services.webhook_service import api_key_service

    user = api_key_service.authenticate_key(db=db, raw_key=raw_key)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
        )
    return user
