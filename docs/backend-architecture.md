# Backend Architecture

## Runtime Shape

The backend is a FastAPI modular monolith. It should feel production-ready without introducing distributed-system overhead.

```text
FastAPI route
  -> service
  -> workflow agent
  -> repository / storage / RAG component
```

## Backend Boundaries

```text
app/api/v1
  Defines routes and response contracts.

app/services
  Owns business use cases such as creating audits, uploading documents,
  ingesting rule sets, generating reports, and managing cleanup.

app/agents
  Owns each audit workflow stage. Agents are deterministic orchestration
  modules, not autonomous planners.

app/rag
  Owns document parsing, chunking, embeddings, hybrid retrieval, reranking,
  context validation, citation mapping, and scoring helpers.

app/db
  Owns persistence models and repository methods.

app/storage
  Owns S3 path construction, upload/download helpers, and retention metadata.

app/workers
  Owns background execution for audit workflows and retention cleanup.
```

## Service Boundary Guidance

Keep services aligned with user-facing actions:

```text
AuthService
DocumentService
RuleService
AuditService
ReportService
CleanupService
```

Avoid tiny services that only wrap one function. Add a service only when it owns a real workflow, transaction, or business concept.

## Error Handling

Use shared application exceptions for predictable API responses:

```text
AUTH_INVALID_CREDENTIALS
DOCUMENT_UPLOAD_FAILED
AUDIT_NOT_FOUND
RULESET_NOT_INDEXED
RAG_CONTEXT_TOO_WEAK
STORAGE_OBJECT_EXPIRED
```

## Observability

Log the audit lifecycle with stable event names:

```text
document.uploaded
document.parsed
document.chunked
retrieval.started
retrieval.completed
compliance.findings_generated
evidence.validated
report.generated
audit.completed
audit.failed
cleanup.completed
```

