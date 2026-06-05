from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from backend.app.core.config import settings


def create_access_token(*, subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expires_delta = timedelta(minutes=settings.jwt_access_token_minutes)
    return _create_token(subject=subject, token_type="access", expires_delta=expires_delta, extra_claims=extra_claims)


def create_refresh_token(*, subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expires_delta = timedelta(days=settings.jwt_refresh_token_days)
    return _create_token(subject=subject, token_type="refresh", expires_delta=expires_delta, extra_claims=extra_claims)


def decode_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    if not payload.get("sub"):
        raise ValueError("Token subject is missing")
    return payload


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _jwt_secret(), algorithm=settings.jwt_algorithm)


def _jwt_secret() -> str:
    secret = str(settings.jwt_secret_key or "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")
    return secret
