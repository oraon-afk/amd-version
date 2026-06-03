import asyncio
from contextlib import asynccontextmanager, suppress
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
from backend.app.core.logging import configure_logging, get_logger
from backend.app.db.session import check_database_connection, init_db
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
    logger.info("Startup diagnostics: %s", startup_diagnostics())
    if settings.auto_create_tables:
        init_db()
    try:
        deleted = cleanup_expired_temp_files()
        if deleted:
            logger.info("Cleaned %s expired temporary upload(s) on startup", deleted)
    except Exception as exc:
        logger.warning("Startup temp cleanup failed: %s", exc)

    cleanup_task = asyncio.create_task(temp_file_cleanup_loop())
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
        ("postgresql", check_database_connection),
        ("s3", lambda: (s3_storage.warm(), s3_storage.check_connection())[-1]),
        ("qdrant", lambda: qdrant_store.ensure_collections(vector_size=embedding_dimensions)),
        ("llm", llm_service.warm),
    ):
        try:
            check()
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
