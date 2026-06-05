import json
import logging
import sys
from datetime import datetime, timezone
from threading import Lock
from time import time
from typing import Any

from backend.app.core.config import settings

_LOG_ONCE_KEYS: set[str] = set()
_LOG_ONCE_LOCK = Lock()


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_once(
    logger: logging.Logger,
    level: int,
    key: str,
    message: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    with _LOG_ONCE_LOCK:
        if key in _LOG_ONCE_KEYS:
            return
        _LOG_ONCE_KEYS.add(key)
    logger.log(level, message, *args, **kwargs)


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
