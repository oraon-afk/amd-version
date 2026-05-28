import logging
import sys
from time import time
from typing import Any

from backend.app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_pipeline_stage(
    logger: logging.Logger,
    stage: str,
    *,
    audit_id: str | None,
    document_id: str | None,
    domain: str | None,
    started_at: float,
    status: str,
    **metadata: Any,
) -> None:
    """Emit a consistent audit pipeline log line with required trace fields."""

    processing_time_ms = int((time() - started_at) * 1000)
    clean_metadata = {key: value for key, value in metadata.items() if value is not None}
    logger.info(
        "[%s] audit_id=%s document_id=%s domain=%s processing_time_ms=%s status=%s metadata=%s",
        stage.strip().upper(),
        audit_id or "",
        document_id or "",
        domain or "",
        processing_time_ms,
        status,
        clean_metadata,
    )
