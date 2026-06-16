"""
Feature 6: Webhooks & API Keys – FastAPI router.

Routes:
  GET    /admin/webhooks                     - List webhooks (admin)
  POST   /admin/webhooks                     - Create webhook (admin)
  DELETE /admin/webhooks/{id}                - Delete webhook (admin)
  POST   /admin/webhooks/{id}/test           - Test webhook (admin)
  GET    /admin/webhooks/{id}/deliveries     - View delivery log (admin)
  GET    /admin/api-keys                     - List API keys (admin or owner)
  POST   /admin/api-keys                     - Create API key (admin)
  DELETE /admin/api-keys/{id}                - Revoke API key (admin or owner)
  POST   /webhooks/trigger-audit             - Inbound webhook (API Key auth)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.db.session import get_db
from backend.app.schemas.audit import AuditResponse, CreateAuditRequest
from backend.app.services.api_key_auth import get_api_key_user
from backend.app.services.audit_service import audit_service
from backend.app.services.webhook_service import api_key_service, webhook_dispatcher, webhook_service

router = APIRouter(tags=["webhooks"])


# ─────────────────────── Pydantic Schemas (local) ───────────────────────────

class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    events: list[str]
    secret: str | None = None


class WebhookResponse(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: Any
    last_triggered_at: Any = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj: Any) -> "WebhookResponse":
        return cls(
            id=obj.id,
            name=obj.name,
            url=obj.url,
            events=(obj.events or "").split(",") if obj.events else [],
            is_active=obj.is_active,
            created_at=obj.created_at,
            last_triggered_at=obj.last_triggered_at,
        )


class WebhookDeliveryResponse(BaseModel):
    id: str
    webhook_id: str
    event: str
    response_status: int | None
    success: bool
    retry_count: int
    created_at: Any

    model_config = {"from_attributes": True}


class CreateApiKeyRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: Any
    last_used_at: Any = None
    expires_at: Any = None
    # raw_key is only present on creation
    raw_key: str | None = None

    model_config = {"from_attributes": True}


class TriggerAuditRequest(BaseModel):
    document_id: str
    rule_set_id: str | None = None
    callback_url: str | None = None


# ─────────────────────────── Webhook CRUD ───────────────────────────────────

@router.get("/admin/webhooks", response_model=list[WebhookResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WebhookResponse]:
    try:
        webhooks = webhook_service.list_webhooks(db=db, user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [WebhookResponse.from_orm_obj(w) for w in webhooks]


@router.post("/admin/webhooks", response_model=WebhookResponse, status_code=201)
def create_webhook(
    payload: CreateWebhookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WebhookResponse:
    try:
        webhook = webhook_service.create_webhook(
            db=db,
            user=current_user,
            name=payload.name,
            url=payload.url,
            events=payload.events,
            secret=payload.secret,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WebhookResponse.from_orm_obj(webhook)


@router.delete("/admin/webhooks/{webhook_id}", status_code=204, response_class=Response)
def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        webhook_service.delete_webhook(db=db, user=current_user, webhook_id=webhook_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/admin/webhooks/{webhook_id}/test")
def test_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        return webhook_service.test_webhook(db=db, user=current_user, webhook_id=webhook_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/admin/webhooks/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def get_webhook_deliveries(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WebhookDeliveryResponse]:
    try:
        deliveries = webhook_service.get_deliveries(db=db, user=current_user, webhook_id=webhook_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]


# ─────────────────────────── API Keys ───────────────────────────────────────

@router.get("/admin/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApiKeyResponse]:
    keys = api_key_service.list_keys(db=db, user=current_user)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("/admin/api-keys", response_model=ApiKeyResponse, status_code=201)
def create_api_key(
    payload: CreateApiKeyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKeyResponse:
    api_key, raw_key = api_key_service.create_key(db=db, user=current_user, name=payload.name)
    response = ApiKeyResponse.model_validate(api_key)
    response.raw_key = raw_key  # Return plaintext once only
    return response


@router.delete("/admin/api-keys/{key_id}", status_code=204, response_class=Response)
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        api_key_service.revoke_key(db=db, user=current_user, key_id=key_id)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ─────────────────────────── Inbound Webhook ────────────────────────────────

@router.post("/webhooks/trigger-audit", response_model=AuditResponse)
def trigger_audit_external(
    payload: TriggerAuditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    api_user: User = Depends(get_api_key_user),
) -> AuditResponse:
    """
    Inbound webhook endpoint: external systems can start an audit
    using an API key instead of a JWT token.
    """
    try:
        audit = audit_service.create_audit(
            db=db,
            user=api_user,
            payload=CreateAuditRequest(
                document_id=payload.document_id,
                rule_set_id=payload.rule_set_id,
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    background_tasks.add_task(audit_service.run_audit_background, audit.id)
    return audit
