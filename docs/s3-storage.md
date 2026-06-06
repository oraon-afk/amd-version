# S3 Storage Structure

## Permanent Rules

```text
s3://compliance-rules-prod/
  tenants/{tenant_id}/rules/{domain}/{rule_set_id}/{version}/original.pdf
  tenants/{tenant_id}/rules/{domain}/{rule_set_id}/{version}/normalized.txt
  tenants/{tenant_id}/rules/{domain}/{rule_set_id}/{version}/manifest.json
```

## Temporary Uploaded Documents

```text
s3://audit-temp-uploads-prod/
  tenants/{tenant_id}/users/{user_id}/audits/{audit_id}/original.pdf
  tenants/{tenant_id}/users/{user_id}/audits/{audit_id}/extracted.txt
```

## Generated Reports

```text
s3://audit-reports-prod/
  tenants/{tenant_id}/audits/{audit_id}/report.json
  tenants/{tenant_id}/audits/{audit_id}/report.pdf
```

## Retention

Temporary uploaded documents should use both:

- Application-level `expires_at` metadata
- S3 lifecycle policy

Recommended MVP retention:

```text
24 to 72 hours
```

