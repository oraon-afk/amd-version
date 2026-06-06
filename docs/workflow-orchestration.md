# Workflow Orchestration

## MVP Approach

Use FastAPI background tasks or a simple internal worker runner. Keep the workflow interface clean so it can later move to Celery, RQ, or a managed queue.

## Audit Workflow

```text
POST /api/v1/audits
  -> create audit_run
  -> create audit_job
  -> enqueue audit workflow

audit workflow
  -> Document Agent
  -> upload temporary chunks to Qdrant
  -> Retrieval Agent
  -> Compliance Agent
  -> Evidence Agent
  -> Report Agent
  -> persist findings, evidence links, risk scores, report metadata
  -> mark audit completed
```

## Status Model

```text
uploaded
processing
retrieving_rules
validating
tracing_evidence
generating_report
completed
failed
expired
```

## Failure Handling

Persist workflow errors in `audit_jobs`:

```text
audit_id
stage
status
error_code
error_message
started_at
completed_at
```

The frontend should show the failed stage clearly and preserve prior successful stage metadata.

## Cleanup Workflow

```text
scheduled cleanup
  -> find uploaded_documents where expires_at < now
  -> delete temporary S3 objects
  -> delete temporary Qdrant vectors
  -> mark document expired
  -> record cleanup result
```

