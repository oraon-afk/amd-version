from fastapi import APIRouter

from backend.app.services.health_service import (
    auth_health,
    database_health,
    llm_health,
    embeddings_health,
    overall_health,
    qdrant_health,
    s3_health,
    startup_diagnostics,
)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return overall_health()


@router.get("/health/database")
def health_database() -> dict:
    return database_health().as_dict()


@router.get("/health/vector")
def health_vector() -> dict:
    return qdrant_health(roundtrip=True).as_dict()


@router.get("/health/storage")
def health_storage() -> dict:
    return s3_health(roundtrip=True).as_dict()


@router.get("/health/llm")
def health_llm() -> dict:
    return llm_health().as_dict()


@router.get("/health/embeddings")
def health_embeddings() -> dict:
    return embeddings_health().as_dict()


@router.get("/health/auth")
def health_auth() -> dict:
    return auth_health().as_dict()


@router.get("/health/config")
def health_config() -> dict:
    return startup_diagnostics()
