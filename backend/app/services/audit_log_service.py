from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.core.logging import get_logger
from backend.app.db.models.log import AuditLog
from backend.app.db.models.user import User

logger = get_logger(__name__)


class AuditLogService:
    def log(
        self,
        *,
        db: Session,
        action: str,
        user: User | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict | None = None,
        message: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        try:
            db.add(
                AuditLog(
                    user_id=user.id if user else None,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    metadata_json=metadata or {},
                    message=message,
                    ip_address=ip_address,
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.warning("Audit log write failed for action %s", action, exc_info=True)


audit_log_service = AuditLogService()
