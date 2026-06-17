"""
Feature 6: Open Integration Model & Webhooks.

WebhookService  – CRUD for webhook configurations and delivery management.
WebhookDispatcher – fires outbound HTTP calls on compliance events.
ApiKeyService   – manages external-system API keys (hash-only stored).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.models.user import User
from backend.app.db.models.webhook import ApiKey, Webhook, WebhookDelivery
from backend.app.db.transactions import commit_or_rollback

logger = get_logger(__name__)

# Maximum retry attempts for webhook delivery
MAX_WEBHOOK_RETRIES = 5
# Supported event types
WEBHOOK_EVENTS = {
    "audit.completed",
    "audit.failed",
    "audit.pending_review",
    "finding.critical",
    "report.published",
    "rule.created",
    "rule.updated",
}


# ─────────────────────────── WebhookService ──────────────────────────────────

class WebhookService:
    """CRUD operations for webhook configurations."""

    def create_webhook(
        self,
        *,
        db: Session,
        user: User,
        name: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> Webhook:
        if (user.role or "").upper() != "ADMIN":
            raise PermissionError("Only administrators can create webhooks.")

        invalid = set(events) - WEBHOOK_EVENTS
        if invalid:
            raise ValueError(f"Unknown event types: {invalid}. Valid: {WEBHOOK_EVENTS}")

        webhook = Webhook(
            user_id=user.id,
            name=name,
            url=url,
            events=",".join(events),
            secret=secret,
            is_active=True,
        )
        db.add(webhook)
        commit_or_rollback(db)
        db.refresh(webhook)
        logger.info("Webhook created: id=%s name=%s events=%s", webhook.id, name, events)
        return webhook

    def list_webhooks(self, *, db: Session, user: User) -> list[Webhook]:
        if (user.role or "").upper() != "ADMIN":
            raise PermissionError("Only administrators can list webhooks.")
        return list(db.scalars(select(Webhook).order_by(Webhook.created_at.desc())).all())

    def delete_webhook(self, *, db: Session, user: User, webhook_id: str) -> None:
        if (user.role or "").upper() != "ADMIN":
            raise PermissionError("Only administrators can delete webhooks.")
        webhook = db.scalar(select(Webhook).where(Webhook.id == webhook_id))
        if webhook is None:
            raise ValueError(f"Webhook not found: {webhook_id}")
        db.delete(webhook)
        commit_or_rollback(db)

    def test_webhook(self, *, db: Session, user: User, webhook_id: str) -> dict[str, Any]:
        if (user.role or "").upper() != "ADMIN":
            raise PermissionError("Only administrators can test webhooks.")
        webhook = db.scalar(select(Webhook).where(Webhook.id == webhook_id))
        if webhook is None:
            raise ValueError(f"Webhook not found: {webhook_id}")

        test_payload = {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "This is a test payload from AI Audit & Compliance Assistant."},
        }
        delivery = webhook_dispatcher._send_once(webhook=webhook, payload=test_payload)
        db.add(delivery)
        commit_or_rollback(db)
        return {
            "webhook_id": webhook_id,
            "success": delivery.success,
            "response_status": delivery.response_status,
            "response_body": delivery.response_body,
        }

    def get_deliveries(
        self,
        *,
        db: Session,
        user: User,
        webhook_id: str,
        limit: int = 50,
    ) -> list[WebhookDelivery]:
        if (user.role or "").upper() != "ADMIN":
            raise PermissionError("Only administrators can view webhook deliveries.")
        return list(
            db.scalars(
                select(WebhookDelivery)
                .where(WebhookDelivery.webhook_id == webhook_id)
                .order_by(WebhookDelivery.created_at.desc())
                .limit(limit)
            ).all()
        )


# ─────────────────────────── WebhookDispatcher ───────────────────────────────

class WebhookDispatcher:
    """
    Dispatches outbound HTTP POST requests to all active webhooks
    matching a given event type.

    Designed to be called from background tasks (FastAPI BackgroundTasks)
    so it never blocks the main request path.
    """

    def dispatch(
        self,
        *,
        event: str,
        data: dict[str, Any],
        db: Session | None = None,
    ) -> None:
        """
        Fire webhooks for the given event.

        If db is provided, delivery records are persisted.
        Otherwise, only logs the dispatch attempt.
        """
        if db is None:
            # Lazy-import to avoid circular dependency during module load
            try:
                from backend.app.db.session import SessionLocal
                with SessionLocal() as session:
                    self._dispatch_with_session(event=event, data=data, db=session)
            except Exception as exc:
                logger.exception("Webhook dispatch failed for event %s: %s", event, exc)
            return
        self._dispatch_with_session(event=event, data=data, db=db)

    def _dispatch_with_session(
        self,
        *,
        event: str,
        data: dict[str, Any],
        db: Session,
    ) -> None:
        webhooks = list(
            db.scalars(
                select(Webhook).where(Webhook.is_active == True)  # noqa: E712
            ).all()
        )
        matching = [w for w in webhooks if event in (w.events or "").split(",")]
        if not matching:
            return

        payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }

        for webhook in matching:
            try:
                delivery = self._send_once(webhook=webhook, payload=payload)
                webhook.last_triggered_at = datetime.utcnow()
                db.add(delivery)
            except Exception as exc:
                logger.exception("Failed to deliver webhook %s for event %s: %s", webhook.id, event, exc)

        commit_or_rollback(db)

    def _send_once(self, *, webhook: Webhook, payload: dict[str, Any]) -> WebhookDelivery:
        """Send a single HTTP POST and return a WebhookDelivery record."""
        body = json.dumps(payload, default=str)
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Audit-Compliance/1.0",
        }
        if webhook.secret:
            headers["X-Webhook-Secret"] = webhook.secret

        response_status: int | None = None
        response_body: str | None = None
        success = False
        error_message: str | None = None

        try:
            response = httpx.post(
                webhook.url,
                content=body,
                headers=headers,
                timeout=10.0,
            )
            response_status = response.status_code
            response_body = response.text[:1000]  # Cap stored response
            success = 200 <= response_status < 300
        except Exception as exc:
            error_message = str(exc)[:500]
            logger.warning("Webhook POST failed: %s -> %s: %s", webhook.id, webhook.url, exc)

        return WebhookDelivery(
            webhook_id=webhook.id,
            event=payload.get("event", "unknown"),
            request_body=body[:2000],
            response_status=response_status,
            response_body=response_body,
            success=success,
            retry_count=0,
            error_message=error_message,
        )


# ─────────────────────────── ApiKeyService ───────────────────────────────────

class ApiKeyService:
    """Manage API keys for external systems (plaintext returned once, hash stored)."""

    def create_key(
        self,
        *,
        db: Session,
        user: User,
        name: str,
    ) -> tuple[ApiKey, str]:
        """
        Create a new API key.

        Returns (ApiKey record, raw_key_string).
        The raw key is only returned once and never stored.
        """
        raw_key = f"ak_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = ApiKey(
            user_id=user.id,
            name=name,
            key_hash=key_hash,
            is_active=True,
        )
        db.add(api_key)
        commit_or_rollback(db)
        db.refresh(api_key)
        logger.info("API key created: id=%s name=%s for user=%s", api_key.id, name, user.id)
        return api_key, raw_key

    def list_keys(self, *, db: Session, user: User) -> list[ApiKey]:
        """List API keys for the requesting user."""
        statement = select(ApiKey).where(ApiKey.is_active == True)  # noqa: E712
        if (user.role or "").upper() != "ADMIN":
            statement = statement.where(ApiKey.user_id == user.id)
        return list(db.scalars(statement.order_by(ApiKey.created_at.desc())).all())

    def revoke_key(self, *, db: Session, user: User, key_id: str) -> None:
        """Revoke (soft-delete) an API key."""
        api_key = db.scalar(select(ApiKey).where(ApiKey.id == key_id))
        if api_key is None:
            raise ValueError(f"API key not found: {key_id}")
        if (user.role or "").upper() != "ADMIN" and api_key.user_id != user.id:
            raise PermissionError("Cannot revoke another user's API key.")
        api_key.is_active = False
        commit_or_rollback(db)

    def authenticate_key(self, *, db: Session, raw_key: str) -> User | None:
        """
        Validate a raw API key string.

        Returns the owning User if valid, None otherwise.
        Updates last_used_at on success.
        """
        from backend.app.db.models.user import User as UserModel
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = db.scalar(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True,  # noqa: E712
            )
        )
        if api_key is None:
            return None

        # Check expiry
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        api_key.last_used_at = datetime.utcnow()
        commit_or_rollback(db)
        return db.scalar(select(UserModel).where(UserModel.id == api_key.user_id))


# Singletons
webhook_service = WebhookService()
webhook_dispatcher = WebhookDispatcher()
api_key_service = ApiKeyService()
