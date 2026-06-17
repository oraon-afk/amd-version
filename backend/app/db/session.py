from collections.abc import Generator
import logging
import socket
from time import sleep

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import InvalidatePoolError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_once

logger = get_logger(__name__)


class Base(DeclarativeBase):
    pass


class DatabaseUnavailableError(SQLAlchemyError):
    pass


class _EngineProxy:
    def __init__(self) -> None:
        self._engine: Engine | None = None
        self._engine_url: str | None = None

    def get_engine(self) -> Engine:
        database_url = _current_database_url()
        if self._engine is None or self._engine_url != database_url:
            self._engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=max(1, settings.database_pool_recycle_seconds),
                future=True,
            )
            self._engine_url = database_url
        return self._engine

    def connect(self, *args, **kwargs):
        return self.get_engine().connect(*args, **kwargs)

    def begin(self, *args, **kwargs):
        return self.get_engine().begin(*args, **kwargs)

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    def __getattr__(self, name: str):
        return getattr(self.get_engine(), name)


class EngineResolvingSession(Session):
    def get_bind(self, *args, **kwargs):
        bind = super().get_bind(*args, **kwargs)
        if isinstance(bind, _EngineProxy):
            return bind.get_engine()
        return bind


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _current_database_url() -> str:
    database_url = str(settings.database_url or "").strip()
    if not database_url:
        raise DatabaseUnavailableError("DATABASE_URL is not configured.")
    return _normalize_database_url(database_url)


engine = _EngineProxy()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=EngineResolvingSession,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    ensure_database_configured()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_database_configured() -> None:
    _current_database_url()


def validate_database_hostname() -> bool:
    database_url = _current_database_url()
    try:
        parsed = make_url(database_url)
    except Exception as exc:
        raise DatabaseUnavailableError("DATABASE_URL is invalid.") from exc

    if parsed.get_backend_name().startswith("sqlite"):
        return True

    host = parsed.host
    if not host:
        raise DatabaseUnavailableError("DATABASE_URL host is missing.")

    try:
        socket.getaddrinfo(host, parsed.port or _default_database_port(parsed.get_backend_name()), type=socket.SOCK_STREAM)
    except OSError as exc:
        raise DatabaseUnavailableError(f"Database hostname '{host}' could not be resolved: {exc}") from exc
    return True


def check_database_connection(*, attempts: int | None = None, validate_hostname: bool = True) -> bool:
    _retry_database_operation(
        lambda: _check_database_connection_once(validate_hostname=validate_hostname),
        attempts=attempts,
        label="database_connectivity_check",
    )
    return True


def _seed_compliance_domains() -> None:
    DEFAULT_DOMAINS = [
        ("banking", "Banking, lending, KYC, and controls"),
        ("finance", "Finance, procurement, and reporting controls"),
        ("healthcare", "Healthcare privacy, safety, and operations"),
        ("hr-policy", "Employee and HR policy compliance"),
        ("legal", "Legal agreements and obligations"),
        ("security", "Information security, network safety, and system controls"),
    ]
    with engine.begin() as connection:
        for name, description in DEFAULT_DOMAINS:
            connection.execute(
                text(
                    """
                    INSERT INTO compliance_domains (id, name, description)
                    VALUES (gen_random_uuid(), :name, :description)
                    ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                    """
                ),
                {"name": name, "description": description},
            )


def init_db() -> None:
    import backend.app.db.models  # noqa: F401

    _retry_database_operation(lambda: Base.metadata.create_all(bind=engine), label="database_create_all")
    _retry_database_operation(_ensure_incremental_columns, label="database_incremental_columns")
    _retry_database_operation(_seed_compliance_domains, label="database_seed_compliance_domains")


def recover_from_database_error(exc: BaseException) -> None:
    if not _should_dispose_pool(exc):
        return
    engine.dispose()
    log_once(
        logger,
        logging.WARNING,
        "database_pool_disposed_after_invalidation",
        "DATABASE_POOL_DISPOSED reason=connection_invalidated root_cause=%s",
        database_error_root_cause(exc),
    )


def is_database_exception(exc: BaseException) -> bool:
    return any(isinstance(item, (SQLAlchemyError, DatabaseUnavailableError)) for item in _iter_exception_chain(exc))


def database_error_root_cause(exc: BaseException) -> str:
    chain = list(_iter_exception_chain(exc))
    preferred = next((item for item in chain if isinstance(item, DatabaseUnavailableError)), None)
    root = preferred or (chain[-1] if chain else exc)
    message = str(root).strip() or root.__class__.__name__
    if len(message) > 300:
        return message[:297] + "..."
    return message


def _check_database_connection_once(*, validate_hostname: bool) -> None:
    if validate_hostname:
        validate_database_hostname()
    with engine.connect() as connection:
        connection.execute(text("select 1"))


def _retry_database_operation(operation, *, attempts: int | None = None, label: str) -> None:
    total_attempts = max(1, attempts or settings.database_connect_retries)
    last_exc: Exception | None = None
    for attempt in range(1, total_attempts + 1):
        try:
            operation()
            return
        except Exception as exc:
            last_exc = exc
            recover_from_database_error(exc)
            if attempt >= total_attempts:
                break
            sleep(_retry_delay(attempt))
    assert last_exc is not None
    raise last_exc


def _retry_delay(attempt: int) -> float:
    return max(0.05, settings.database_retry_backoff_seconds) * (2 ** (attempt - 1))


def _default_database_port(backend_name: str) -> int | None:
    if backend_name.startswith("postgresql"):
        return 5432
    if backend_name.startswith("mysql"):
        return 3306
    return None


def _should_dispose_pool(exc: BaseException) -> bool:
    for item in _iter_exception_chain(exc):
        if isinstance(item, InvalidatePoolError):
            return True
        if getattr(item, "connection_invalidated", False):
            return True
    return False


def _iter_exception_chain(exc: BaseException):
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _ensure_incremental_columns() -> None:
    additions = {
        "users": {
            "role": "VARCHAR(20) DEFAULT 'USER'",
            "is_active": "BOOLEAN DEFAULT TRUE",
        },
        "uploaded_documents": {
            "title": "VARCHAR(255)",
            "domain": "VARCHAR(100)",
            "role_type": "VARCHAR(20) DEFAULT 'USER'",
            "source_type": "VARCHAR(50)",
            "s3_key": "VARCHAR(1024)",
            "qdrant_collection": "VARCHAR(100)",
            "upload_status": "VARCHAR(50)",
            "processing_stage": "VARCHAR(80) DEFAULT 'uploaded'",
            "cleanup_status": "VARCHAR(80) DEFAULT 'not_scheduled'",
            "file_name": "VARCHAR(512)",
            "file_type": "VARCHAR(120)",
            "extracted_text": "TEXT",
        },
        "findings": {
            "document_id": "UUID",
            "confidence": "FLOAT",
            "evidence_text": "TEXT",
            "citation_source": "TEXT",
            "needs_review": "BOOLEAN DEFAULT FALSE",
            "review_status": "VARCHAR(20) DEFAULT 'not_required'",
            "is_active": "BOOLEAN DEFAULT TRUE",
            "reviewed_by": "UUID",
            "reviewed_at": "TIMESTAMP",
            "review_comment": "TEXT",
            "original_finding_snapshot": "JSONB",
        },
        "audit_runs": {
            "review_deadline": "TIMESTAMP",
        },
        "compliance_score_diagnostics": {
            "retry_attempts": "JSONB",
            "final_prompt": "TEXT",
            "final_llm_response": "TEXT",
            "context_chunks_snapshot": "JSONB",
            "heuristic_confidence": "FLOAT",
            "blended_confidence": "FLOAT",
        },
        "rule_documents": {
            "category": "VARCHAR(100)",
            "document_type": "VARCHAR(80) DEFAULT 'rules'",
            "version": "VARCHAR(50) DEFAULT 'v1'",
            "storage_path": "VARCHAR(1024)",
        },
        "documents": {
            "title": "VARCHAR(255)",
            "domain": "VARCHAR(100)",
            "role_type": "VARCHAR(20)",
            "source_type": "VARCHAR(50)",
            "file_name": "VARCHAR(512)",
            "file_type": "VARCHAR(120)",
            "s3_key": "VARCHAR(1024)",
            "qdrant_collection": "VARCHAR(100)",
            "extracted_text": "TEXT",
            "upload_status": "VARCHAR(50)",
            "processing_stage": "VARCHAR(80)",
            "created_at": "TIMESTAMP",
        },
        "reports": {
            "audit_id": "UUID",
            "summary": "TEXT",
            "report_payload": "JSON",
            "report_json_s3_uri": "VARCHAR(1024)",
            "created_at": "TIMESTAMP",
        },
        "audit_results": {
            "document_id": "UUID",
            "overall_risk": "TEXT",
            "confidence_score": "FLOAT",
            "summary": "TEXT",
            "created_at": "TIMESTAMP",
        },
        "batch_documents": {
            "domain": "VARCHAR(100)",
            "content_type": "VARCHAR(120) DEFAULT 'application/octet-stream'",
            "staging_path": "VARCHAR(1024)",
            "file_size_bytes": "INTEGER DEFAULT 0",
            "retry_count": "INTEGER DEFAULT 0",
            "max_retries": "INTEGER DEFAULT 2",
            "last_error_at": "TIMESTAMP",
        },
        "upload_batches": {
            "processed_documents": "INTEGER DEFAULT 0",
            "summary_report": "JSON",
        },
        "rule_upload_batches": {
            "processed_documents": "INTEGER DEFAULT 0",
            "summary_report": "JSON",
        },
        "rule_upload_batch_items": {
            "content_type": "VARCHAR(120) DEFAULT 'application/octet-stream'",
            "staging_path": "VARCHAR(1024)",
            "file_size_bytes": "INTEGER DEFAULT 0",
            "retry_count": "INTEGER DEFAULT 0",
            "max_retries": "INTEGER DEFAULT 2",
            "last_error_at": "TIMESTAMP",
        },
        "compliance_rules": {
            "status": "VARCHAR(50) DEFAULT 'active'",
            "version_number": "INTEGER DEFAULT 1",
            "parent_rule_id": "UUID",
            "custom_attributes": "JSONB",
            "effectivity_date": "DATE",
            "expiry_date": "DATE",
        },
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        for table_name, columns in additions.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl_type in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"))
