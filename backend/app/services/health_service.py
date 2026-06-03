from __future__ import annotations

from dataclasses import asdict, dataclass
from time import time
from uuid import NAMESPACE_URL, uuid4, uuid5

from qdrant_client.models import PointIdsList, PointStruct
from sqlalchemy import inspect, text

from backend.app.auth.jwt_service import create_access_token, decode_token
from backend.app.auth.password_service import hash_password, verify_password
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.db.session import engine
from backend.app.rag.indexing.qdrant_store import qdrant_store
from backend.app.rag.indexing.embeddings import embedding_service
from backend.app.services.llm_service import llm_service
from backend.app.storage.s3_client import s3_storage

logger = get_logger(__name__)


@dataclass
class DependencyHealth:
    status: str
    latency_ms: int | None = None
    detail: str | None = None
    metadata: dict | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"connected", "ready"}

    def as_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


def database_health() -> DependencyHealth:
    started = time()
    required_columns = {
        "users": {"id", "email", "password_hash", "name", "role", "is_active", "created_at"},
        "uploaded_documents": {
            "id",
            "user_id",
            "title",
            "domain",
            "role_type",
            "source_type",
            "s3_key",
            "qdrant_collection",
            "upload_status",
            "processing_stage",
            "cleanup_status",
            "file_name",
            "file_type",
            "filename",
            "content_type",
            "s3_uri",
            "status",
            "extracted_text",
            "expires_at",
        },
        "document_chunks": {"id", "document_id", "chunk_index", "chunk_text", "embedding_model", "vector_id"},
        "compliance_domains": {"id", "name", "description"},
        "audit_runs": {"id", "user_id", "document_id", "status", "created_at"},
        "findings": {"id", "audit_id", "document_id", "violated_rule", "confidence_score", "evidence_text", "citation_source"},
        "evidence_links": {"id", "finding_id", "citation_text", "confidence_score"},
        "audit_reports": {"id", "audit_id", "summary", "report_payload"},
        "audit_results": {"id", "document_id", "overall_risk", "confidence_score", "summary", "created_at"},
        "rule_documents": {"id", "user_id", "rule_set_id", "s3_uri", "status"},
        "documents": {
            "id",
            "user_id",
            "title",
            "domain",
            "role_type",
            "source_type",
            "file_name",
            "file_type",
            "s3_key",
            "qdrant_collection",
            "extracted_text",
            "upload_status",
            "processing_stage",
            "created_at",
        },
        "reports": {"id", "audit_id", "summary", "report_payload", "report_json_s3_uri", "created_at"},
    }
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
            inspector = inspect(connection)
            tables = set(inspector.get_table_names(schema="public"))
            missing_tables = sorted(set(required_columns) - tables)
            missing_columns: dict[str, list[str]] = {}
            for table, columns in required_columns.items():
                if table not in tables:
                    continue
                existing = {column["name"] for column in inspector.get_columns(table, schema="public")}
                missing = sorted(columns - existing)
                if missing:
                    missing_columns[table] = missing

        if missing_tables or missing_columns:
            return DependencyHealth(
                status="unhealthy",
                latency_ms=_latency(started),
                detail="Database schema does not match backend requirements.",
                metadata={"missing_tables": missing_tables, "missing_columns": missing_columns},
            )
        return DependencyHealth(status="connected", latency_ms=_latency(started))
    except Exception as exc:
        logger.exception("Database health check failed")
        return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail=_safe_error(exc))


def auth_health() -> DependencyHealth:
    started = time()
    try:
        password_hash = hash_password("health-check-password")
        if not verify_password("health-check-password", password_hash):
            return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail="Password verification failed.")
        token = create_access_token(subject="health-check")
        payload = decode_token(token, expected_type="access")
        if payload.get("sub") != "health-check":
            return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail="JWT subject mismatch.")
        return DependencyHealth(status="ready", latency_ms=_latency(started))
    except Exception as exc:
        logger.exception("Auth health check failed")
        return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail=_safe_error(exc))


def qdrant_health(*, roundtrip: bool = True) -> DependencyHealth:
    started = time()
    if not settings.qdrant_url:
        return DependencyHealth(status="unhealthy", detail="QDRANT_URL is not configured.")
    if not settings.qdrant_url_is_valid:
        return DependencyHealth(status="unhealthy", detail="QDRANT_URL must start with http:// or https://.")

    try:
        collections = {collection.name for collection in qdrant_store.client.get_collections().collections}
        required = {settings.qdrant_rule_collection, settings.qdrant_upload_collection}
        missing = sorted(required - collections)
        if missing:
            return DependencyHealth(
                status="unhealthy",
                latency_ms=_latency(started),
                detail="Missing Qdrant collections.",
                metadata={"missing_collections": missing},
            )

        metadata = {"collections": sorted(required)}
        if roundtrip:
            metadata["roundtrip"] = _qdrant_roundtrip(settings.qdrant_upload_collection)
        return DependencyHealth(status="connected", latency_ms=_latency(started), metadata=metadata)
    except Exception as exc:
        logger.exception("Qdrant health check failed")
        return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail=_safe_error(exc))


def s3_health(*, roundtrip: bool = True) -> DependencyHealth:
    started = time()
    if not settings.upload_bucket:
        return DependencyHealth(status="unhealthy", detail="S3 upload bucket is not configured.")

    try:
        bucket_status = {}
        for label, bucket in {
            "rules": settings.rule_bucket,
            "uploads": settings.upload_bucket,
            "reports": settings.report_bucket,
        }.items():
            if not bucket:
                bucket_status[label] = "not_configured"
                continue
            try:
                s3_storage.client.head_bucket(Bucket=bucket)
                bucket_status[label] = "accessible"
            except Exception as exc:
                bucket_status[label] = _safe_error(exc)

        metadata = {"buckets": bucket_status}
        if not roundtrip and bucket_status.get("uploads") != "accessible":
            return DependencyHealth(
                status="unhealthy",
                latency_ms=_latency(started),
                detail="S3 temporary upload bucket is not accessible.",
                metadata=metadata,
            )
        if roundtrip:
            key = f"_health/{uuid4()}.txt"
            bucket = settings.upload_bucket
            s3_storage.upload_bytes(
                bucket=bucket,
                key=key,
                content=b"ok",
                content_type="text/plain",
            )
            s3_storage.client.head_object(Bucket=bucket, Key=key)
            s3_storage.delete_object(bucket=bucket, key=key)
            metadata["roundtrip"] = "upload_head_delete_ok"

        return DependencyHealth(status="connected", latency_ms=_latency(started), metadata=metadata)
    except Exception as exc:
        logger.exception("S3 health check failed")
        return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail=_safe_error(exc))


def llm_health() -> DependencyHealth:
    started = time()
    provider = settings.llm_provider_normalized
    key_name, base_url_name, model_name = settings.provider_env_names(provider)
    missing = []
    if not settings.llm_api_key:
        missing.append(key_name)
    if not settings.llm_base_url:
        missing.append(base_url_name)
    if not settings.llm_model:
        missing.append(model_name)
    if missing:
        return DependencyHealth(status="unhealthy", detail=f"Missing LLM configuration: {', '.join(missing)}.")
    try:
        result = llm_service.validate_model_availability()
        return DependencyHealth(
            status="connected",
            latency_ms=_latency(started),
            metadata={
                "provider": provider,
                "model": settings.llm_model,
                "fallback_model_configured": bool(settings.llm_fallback_model),
                "secondary_provider": settings.secondary_llm_provider_normalized,
                "reply_preview": _safe_error(result.content),
                "usage": result.usage,
            },
        )
    except Exception as exc:
        logger.exception("LLM health check failed")
        return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail=_safe_error(exc))


def overall_health() -> dict:
    checks = {
        "embeddings": embeddings_health(),
        "database": database_health(),
        "qdrant": qdrant_health(roundtrip=False),
        "s3": s3_health(roundtrip=False),
        "llm": llm_health(),
        "auth": auth_health(),
    }
    healthy = all(check.ok for check in checks.values())
    return {
        "status": "healthy" if healthy else "unhealthy",
        "database": checks["database"].status,
        "qdrant": checks["qdrant"].status,
        "s3": checks["s3"].status,
        "llm": checks["llm"].status,
        "embeddings": checks["embeddings"].status,
        "auth": checks["auth"].status,
        "details": {name: check.as_dict() for name, check in checks.items()},
    }


def startup_diagnostics() -> dict:
    return dict(settings.diagnostics_summary)


def embeddings_health() -> DependencyHealth:
    started = time()
    try:
        vector = embedding_service.embed_query("embedding health check")
        if not vector:
            return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail="Embedding model returned an empty vector.")
        return DependencyHealth(
            status="ready",
            latency_ms=_latency(started),
            metadata={"model": embedding_service.model_name, "dimensions": len(vector)},
        )
    except Exception as exc:
        logger.exception("Embeddings health check failed")
        return DependencyHealth(status="unhealthy", latency_ms=_latency(started), detail=_safe_error(exc))


def _qdrant_roundtrip(collection_name: str) -> str:
    vector_name = qdrant_store._get_vector_name(collection_name)
    vector = [1.0] + [0.0] * 383
    point_id = str(uuid5(NAMESPACE_URL, f"health-{uuid4()}"))
    point = PointStruct(
        id=point_id,
        vector={vector_name: vector} if vector_name else vector,
        payload={"source_type": "health_check", "chunk_id": point_id, "text": "health check"},
    )
    qdrant_store.client.upsert(collection_name=collection_name, points=[point])
    qdrant_store.search(collection_name=collection_name, query_vector=vector, filters={"source_type": "health_check"}, top_k=1)
    qdrant_store.client.delete(collection_name=collection_name, points_selector=PointIdsList(points=[point_id]))
    return "insert_search_delete_ok"


def _latency(started: float) -> int:
    return int((time() - started) * 1000)


def _safe_error(exc: object) -> str:
    text = str(exc)
    if len(text) > 300:
        return text[:297] + "..."
    return text

