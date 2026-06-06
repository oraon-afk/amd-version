# Data And Storage

## S3 Buckets

Permanent rule storage:

```text
s3://compliance-rules-prod/
  tenants/{tenant_id}/rules/{domain}/{rule_set_id}/{version}/original.pdf
  tenants/{tenant_id}/rules/{domain}/{rule_set_id}/{version}/normalized.txt
  tenants/{tenant_id}/rules/{domain}/{rule_set_id}/{version}/manifest.json
```

Temporary upload storage:

```text
s3://audit-temp-uploads-prod/
  tenants/{tenant_id}/users/{user_id}/audits/{audit_id}/original.pdf
  tenants/{tenant_id}/users/{user_id}/audits/{audit_id}/extracted.txt
```

Report storage:

```text
s3://audit-reports-prod/
  tenants/{tenant_id}/audits/{audit_id}/report.json
  tenants/{tenant_id}/audits/{audit_id}/report.pdf
```

## PostgreSQL Tables

```text
organizations
users
refresh_tokens
rule_sets
rule_documents
rule_index_jobs
uploaded_documents
audit_runs
audit_jobs
findings
evidence_links
audit_reports
storage_objects
cleanup_jobs
```

## Qdrant Collections

```text
compliance_rules
audit_document_chunks
```

Recommended payload:

```text
tenant_id
source_type
document_id
audit_id
rule_set_id
domain
jurisdiction
page_number
section_title
chunk_id
text_hash
s3_uri
expires_at
citation_label
```

## Retention Rules

- Compliance rules are permanent until explicitly archived.
- User uploads are temporary and must have `expires_at`.
- Raw uploaded documents are not stored in PostgreSQL.
- Temporary S3 objects and temporary Qdrant vectors should be removed by cleanup jobs.

