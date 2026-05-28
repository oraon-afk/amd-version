# Backend

FastAPI backend for authentication, document upload, compliance audit workflows, RAG retrieval, evidence tracing, report generation, and metadata persistence.

## Main Layers

```text
app/api/v1       HTTP endpoints
app/auth         JWT and password handling
app/core         config, logging, exceptions
app/db           SQLAlchemy models and repositories
app/schemas      Pydantic contracts
app/services     business services
app/agents       lightweight workflow agents
app/rag          ingestion, retrieval, indexing, scoring
app/storage      S3 integration and retention helpers
app/workers      audit and cleanup workflow runners
```

## Implementation Rule

Keep routes thin. Route files should call services, not perform RAG, storage, or database workflow orchestration directly.

