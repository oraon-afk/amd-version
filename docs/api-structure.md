# API Structure

Base path:

```text
/api/v1
```

## Authentication

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /users/me
```

## Documents

```text
POST   /documents/upload
GET    /documents/{document_id}
DELETE /documents/{document_id}
```

Uploaded documents are temporary. The API should return document metadata and processing status, not raw database-stored document content.

## Audits

```text
POST /audits
GET  /audits
GET  /audits/{audit_id}
GET  /audits/{audit_id}/findings
GET  /audits/{audit_id}/evidence
GET  /audits/{audit_id}/report
```

## Rules

```text
POST /rules/upload
GET  /rulesets
GET  /rulesets/{rule_set_id}
POST /rulesets/{rule_set_id}/reindex
```

## Health

```text
GET /health
```

## Response Shape

Use predictable response envelopes:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

For failures:

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "AUDIT_NOT_FOUND",
    "message": "Audit not found."
  }
}
```

