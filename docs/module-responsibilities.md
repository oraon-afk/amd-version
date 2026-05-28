# Module Responsibilities

## Backend

```text
api/v1/
  FastAPI routers and endpoint contracts.

auth/
  Password hashing, JWT creation, token validation, authenticated dependencies.

core/
  Configuration, logging, security primitives, shared exceptions.

db/models/
  SQLAlchemy database models.

db/repositories/
  Database access methods. No business workflows here.

schemas/
  Pydantic request and response contracts.

services/
  Business logic and transaction boundaries.

agents/
  Workflow modules for document processing, retrieval, compliance comparison,
  evidence tracing, and report generation.

rag/
  Ingestion, indexing, retrieval, reranking, prompts, scoring.

storage/
  S3 client, storage path construction, retention policy helpers.

workers/
  Background audit execution and cleanup workflows.

utils/
  Small pure helpers for IDs, file validation, timestamps.
```

## Frontend

```text
app/
  Next.js routes and page composition.

features/
  Domain-specific UI, hooks, API calls, and types.

components/
  Shared UI primitives, layout, and navigation.

lib/
  API client, auth helpers, constants, formatters.

types/
  Shared TypeScript types.
```

