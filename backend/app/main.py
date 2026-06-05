import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from pathlib import Path
import sys
from time import time

if __package__ == "app":
    repo_root = str(Path(__file__).resolve().parents[2])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging, get_logger, log_once
from backend.app.db.session import (
    check_database_connection,
    database_error_root_cause,
    init_db,
    is_database_exception,
    recover_from_database_error,
)
from backend.app.rag.indexing.embeddings import embedding_service
from backend.app.rag.indexing.qdrant_store import qdrant_store
from backend.app.rag.retrieval.reranker import reranker
from backend.app.services.llm_service import llm_service
from backend.app.services.health_service import startup_diagnostics
from backend.app.storage.s3_client import s3_storage
from backend.app.workers.cleanup import cleanup_expired_temp_files, temp_file_cleanup_loop

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_startup_configuration()
    for warning in settings.configuration_warnings:
        log_once(logger, logging.WARNING, f"config:{warning}", "CONFIGURATION_WARNING %s", warning)
    logger.info("Startup diagnostics: %s", startup_diagnostics())
    database_ready = _startup_database_health_check()
    if database_ready and settings.auto_create_tables:
        try:
            init_db()
        except Exception as exc:
            database_ready = False
            recover_from_database_error(exc)
            _log_database_startup_failure(exc, event="DATABASE_SCHEMA_INIT_FAILED")
    elif not database_ready and settings.auto_create_tables:
        log_once(
            logger,
            logging.WARNING,
            "database_schema_init_skipped",
            "DATABASE_SCHEMA_INIT_SKIPPED reason=database_unavailable",
        )

    if database_ready:
        try:
            deleted = cleanup_expired_temp_files()
            if deleted:
                logger.info("Cleaned %s expired temporary upload(s) on startup", deleted)
        except Exception as exc:
            logger.warning("Startup temp cleanup failed: %s", exc)
    else:
        log_once(
            logger,
            logging.WARNING,
            "startup_cleanup_skipped_database_unavailable",
            "STARTUP_TEMP_CLEANUP_SKIPPED reason=database_unavailable",
        )

    cleanup_task = asyncio.create_task(temp_file_cleanup_loop()) if database_ready else None
    app.state.cleanup_task = cleanup_task

    embedding_dimensions = 384
    if settings.preload_models_on_startup:
        try:
            embedding_service.preload()
            embedding_dimensions = embedding_service.dimensions()
            logger.info(
                "embedding model ready: %s dimensions=%s",
                embedding_service.model_name,
                embedding_dimensions,
            )
        except Exception as exc:
            logger.warning("embedding preload failed: %s", exc)

    for name, check in (
        ("s3", lambda: (s3_storage.warm(), s3_storage.check_connection())[-1]),
        ("qdrant", lambda: qdrant_store.ensure_collections(vector_size=embedding_dimensions)),
        ("llm", llm_service.warm),
    ):
        try:
            result = check()
            if result is False:
                logger.warning("%s connection not configured or unavailable", name)
            else:
                logger.info("%s connection ready", name)
        except Exception as exc:
            logger.warning("%s connection check failed: %s", name, exc)

    if settings.preload_models_on_startup and settings.enable_reranking:
        try:
            if reranker.preload():
                logger.info("reranker model ready: %s", reranker.model_name)
            else:
                logger.warning("reranker unavailable; lexical reranking fallback will be used")
        except Exception as exc:
            logger.warning("reranker preload failed: %s", exc)

    yield

    if cleanup_task is not None:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
if settings.api_v1_prefix.rstrip("/") != "/api":
    app.include_router(api_router, prefix="/api", include_in_schema=False)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started = time()
    try:
        response = await call_next(request)
        latency_ms = int((time() - started) * 1000)
        logger.info(
            "%s %s -> %s in %sms",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        return response
    except Exception as exc:
        latency_ms = int((time() - started) * 1000)
        if is_database_exception(exc):
            recover_from_database_error(exc)
            root_cause = database_error_root_cause(exc)
            log_once(
                logger,
                logging.WARNING,
                "database_request_unavailable",
                "DATABASE_UNAVAILABLE method=%s path=%s latency_ms=%s root_cause=%s",
                request.method,
                request.url.path,
                latency_ms,
                root_cause,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Database temporarily unavailable.",
                    "error": {
                        "message": "Database temporarily unavailable. Please check DATABASE_URL and database hostname/DNS.",
                        "code": "database_unavailable",
                    },
                },
            )
        logger.exception(
            "Unhandled request error on %s %s after %sms",
            request.method,
            request.url.path,
            latency_ms,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": {
                    "message": str(exc) if settings.debug else "Unexpected backend error.",
                    "code": "internal_server_error",
                },
            },
        )


def _startup_database_health_check() -> bool:
    try:
        check_database_connection(validate_hostname=True)
        logger.info("database connection ready")
        return True
    except Exception as exc:
        recover_from_database_error(exc)
        _log_database_startup_failure(exc, event="DATABASE_STARTUP_CHECK_FAILED")
        return False


def _log_database_startup_failure(exc: Exception, *, event: str) -> None:
    root_cause = database_error_root_cause(exc)
    message = (
        f"{event} root_cause={root_cause} action=Verify DATABASE_URL, database hostname, network/DNS, "
        "and Supabase project status."
    )
    key = event.lower()
    if "supabase.co" in root_cause.lower():
        key = f"{key}:supabase"
        message = (
            f"{event} provider=supabase root_cause={root_cause} "
            "action=Verify the Supabase project host in DATABASE_URL, project status, and local DNS/network."
        )
    log_once(logger, logging.WARNING, key, "%s", message)
