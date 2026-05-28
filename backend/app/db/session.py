from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


engine = create_engine(
    _normalize_database_url(settings.database_url),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    return True


def init_db() -> None:
    import backend.app.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_incremental_columns()


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
