-- AI Audit & Compliance Workspace PostgreSQL schema
-- Collection names are configured outside Postgres:
-- QDRANT_RULE_COLLECTION=compliance_rules
-- QDRANT_UPLOAD_COLLECTION=audit_document_chunks

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(320) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'USER',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS uploaded_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  domain VARCHAR(100) NOT NULL,
  source_type VARCHAR(50) NOT NULL DEFAULT 'file',
  s3_key VARCHAR(1024),
  qdrant_collection VARCHAR(100) NOT NULL DEFAULT 'audit_document_chunks',
  upload_status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
  file_name VARCHAR(512),
  filename VARCHAR(512) NOT NULL,
  content_type VARCHAR(120) NOT NULL,
  s3_uri VARCHAR(1024) NOT NULL,
  sha256 VARCHAR(64) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
  extracted_text TEXT,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rule_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  rule_set_id VARCHAR(100) NOT NULL,
  domain VARCHAR(100),
  category VARCHAR(100),
  jurisdiction VARCHAR(100),
  document_type VARCHAR(80) NOT NULL DEFAULT 'rules',
  version VARCHAR(50) NOT NULL DEFAULT 'v1',
  filename VARCHAR(512) NOT NULL,
  content_type VARCHAR(120) NOT NULL,
  s3_uri VARCHAR(1024) NOT NULL,
  storage_path VARCHAR(1024),
  sha256 VARCHAR(64) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'indexed',
  indexed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS compliance_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_document_id UUID REFERENCES rule_documents(id),
  category VARCHAR(100) NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  rule_text TEXT NOT NULL,
  reference VARCHAR(512),
  version VARCHAR(50) NOT NULL DEFAULT 'v1',
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS compliance_domains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES uploaded_documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding_model VARCHAR(255) NOT NULL,
  vector_id VARCHAR(128) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  document_id UUID NOT NULL REFERENCES uploaded_documents(id),
  rule_set_id VARCHAR(100),
  status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
  overall_risk VARCHAR(20),
  confidence_score FLOAT,
  error_message TEXT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id UUID NOT NULL REFERENCES audit_runs(id),
  document_id UUID REFERENCES uploaded_documents(id),
  violated_rule TEXT NOT NULL,
  finding_type VARCHAR(50) NOT NULL DEFAULT 'missing_clause',
  severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
  risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
  confidence_score FLOAT NOT NULL DEFAULT 0,
  confidence FLOAT NOT NULL DEFAULT 0,
  evidence_text TEXT,
  citation_source TEXT,
  explanation TEXT NOT NULL,
  recommendation TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID NOT NULL REFERENCES findings(id),
  source_type VARCHAR(50) NOT NULL,
  qdrant_point_id VARCHAR(128),
  document_id UUID,
  page_number INTEGER,
  section_title VARCHAR(512),
  citation_text TEXT NOT NULL,
  citation_label VARCHAR(512),
  confidence_score FLOAT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id UUID NOT NULL REFERENCES audit_runs(id),
  summary TEXT NOT NULL,
  report_payload JSONB NOT NULL,
  report_json_s3_uri VARCHAR(1024),
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  action VARCHAR(120) NOT NULL,
  entity_type VARCHAR(80),
  entity_id VARCHAR(128),
  metadata_json JSONB,
  ip_address VARCHAR(80),
  message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);
