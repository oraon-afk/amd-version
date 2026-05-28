# PostgreSQL Schema Suggestions

## Core Tables

```text
organizations
  id
  name
  created_at
  updated_at

users
  id
  organization_id
  email
  password_hash
  full_name
  role
  is_active
  created_at
  updated_at

rule_sets
  id
  organization_id
  name
  domain
  jurisdiction
  version
  status
  created_at
  updated_at

rule_documents
  id
  rule_set_id
  filename
  content_type
  s3_uri
  sha256
  indexed_at
  created_at

uploaded_documents
  id
  organization_id
  user_id
  filename
  content_type
  s3_uri
  sha256
  status
  expires_at
  created_at

audit_runs
  id
  organization_id
  user_id
  document_id
  rule_set_id
  status
  overall_risk
  confidence_score
  started_at
  completed_at
  created_at

findings
  id
  audit_id
  rule_document_id
  finding_type
  severity
  risk_level
  confidence_score
  explanation
  recommendation
  created_at

evidence_links
  id
  finding_id
  source_type
  qdrant_point_id
  document_id
  page_number
  section_title
  char_start
  char_end
  citation_text
  confidence_score
  created_at

audit_reports
  id
  audit_id
  report_json_s3_uri
  report_pdf_s3_uri
  summary
  created_at
```

## Storage Rule

PostgreSQL stores metadata, status, scores, references, and S3 paths. It must not store raw PDFs or full uploaded document bodies.

