from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.models.document import UploadedDocument
from backend.app.db.session import SessionLocal
from backend.app.services.audit_log_service import audit_log_service
from backend.app.storage.s3_client import s3_storage

logger = get_logger(__name__)


async def temp_file_cleanup_loop() -> None:
    while True:
        cleanup_expired_temp_files()
        await asyncio.sleep(settings.cleanup_interval_seconds)


def cleanup_expired_temp_files() -> int:
    deleted = 0
    with SessionLocal() as db:
        documents = db.scalars(
            select(UploadedDocument).where(
                UploadedDocument.expires_at <= datetime.utcnow(),
                UploadedDocument.role_type != "ADMIN",
                UploadedDocument.status.notin_(["expired", "deleted"]),
            ),
        ).all()
        for document in documents:
            try:
                if s3_storage.delete_uri(document.s3_uri):
                    deleted += 1
                document.status = "expired"
                document.upload_status = "expired"
                document.processing_stage = "expired"
                document.cleanup_status = "deleted"
                audit_log_service.log(
                    db=db,
                    action="document.temp_expired",
                    entity_type="uploaded_document",
                    entity_id=document.id,
                    metadata={"storage_uri": document.s3_uri},
                )
            except Exception:
                logger.warning("Expired temp cleanup failed for document %s", document.id, exc_info=True)
        db.commit()
    return deleted
