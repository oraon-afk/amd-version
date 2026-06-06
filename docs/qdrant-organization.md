# Qdrant Organization

## Collections

Use two collections to separate permanent rule vectors from temporary uploaded-document vectors.

```text
compliance_rules
  Permanent vectors for regulatory and internal compliance rules.

audit_document_chunks
  Temporary vectors for uploaded documents under active or recent audits.
```

## Vector Payload

```text
tenant_id
organization_id
source_type
document_id
audit_id
rule_set_id
rule_document_id
domain
jurisdiction
page_number
section_title
chunk_id
chunk_index
text_hash
s3_uri
expires_at
citation_label
```

## Filtering Strategy

Always filter by:

```text
organization_id
source_type
```

For rules, also filter by:

```text
rule_set_id
domain
jurisdiction
status
```

For uploaded documents, also filter by:

```text
audit_id
document_id
expires_at
```

## Lifecycle

- Rule vectors remain until a rule set is archived or reindexed.
- Uploaded document vectors are deleted after the retention window.
- Every temporary vector should include `expires_at`.

