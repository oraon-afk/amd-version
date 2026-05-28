export type User = {
  id: string;
  email: string;
  name?: string;
  full_name: string | null;
  role: "ADMIN" | "USER" | string;
  is_active: boolean;
  created_at?: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type UploadedDocument = {
  id: string;
  title: string;
  domain: string;
  role_type: "ADMIN" | "USER" | string;
  source_type: "file" | "text";
  s3_key: string | null;
  qdrant_collection: string;
  upload_status: string;
  processing_stage: string;
  cleanup_status: string;
  file_name: string | null;
  file_type: string | null;
  filename: string;
  content_type: string;
  s3_uri: string;
  status: string;
  extracted_text: string | null;
  created_at: string;
  expires_at: string;
};

export type ComplianceDomain = {
  id: string | null;
  name: string;
  description: string | null;
};

export type Audit = {
  id: string;
  document_id: string;
  rule_set_id: string | null;
  status: string;
  overall_risk: "LOW" | "MEDIUM" | "HIGH" | null;
  confidence_score: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type Finding = {
  id: string;
  audit_id: string;
  document_id: string | null;
  violated_rule: string;
  finding_type: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  confidence_score: number;
  confidence: number;
  evidence_text: string | null;
  citation_source: string | null;
  explanation: string;
  recommendation: string;
  created_at: string;
};

export type Evidence = {
  id: string;
  finding_id: string;
  source_type: string;
  qdrant_point_id: string | null;
  document_id: string | null;
  page_number: number | null;
  section_title: string | null;
  citation_text: string;
  citation_label: string | null;
  confidence_score: number;
  created_at: string;
};

export type AuditReport = {
  id: string;
  audit_id: string;
  summary: string;
  report_payload: {
    risk_counts?: Record<string, number>;
    finding_count?: number;
    compliance_score?: number;
    passed_rules?: number;
    failed_rules?: number;
    recommendations?: string[];
    context_ready?: boolean;
    [key: string]: unknown;
  };
  report_json_s3_uri: string | null;
  created_at: string;
};

export type AdminDocumentsResponse = {
  uploaded_documents: AdminDocument[];
  rule_documents: AdminRuleDocument[];
};

export type AdminDocument = UploadedDocument & {
  user_id: string;
  storage_path?: string | null;
};

export type AdminRuleDocument = {
  id: string;
  user_id: string;
  rule_set_id: string;
  domain: string | null;
  category: string | null;
  jurisdiction: string | null;
  document_type: string;
  version: string;
  filename: string;
  content_type: string;
  s3_uri: string;
  storage_path: string | null;
  status: string;
  indexed_at: string | null;
  created_at: string;
};

export type ComplianceRule = {
  id: string;
  rule_document_id: string | null;
  category: string;
  title: string;
  description: string | null;
  rule_text: string;
  reference: string | null;
  version: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type RuleCategory = {
  id: string | null;
  name: string;
  description: string | null;
};

export type AdminAnalytics = {
  users: number;
  uploaded_documents: number;
  rule_documents: number;
  audits: number;
  completed_audits: number;
  failed_audits: number;
  high_risk_audits: number;
  storage: Record<string, { files: number; bytes: number }>;
};

export type AuditLog = {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, unknown> | null;
  message: string | null;
  ip_address: string | null;
  created_at: string;
};

export type QdrantMonitoring = {
  status: string;
  rule_collection: string;
  upload_collection: string;
  error?: string;
  collections: Array<{
    name: string;
    points_count: number | null;
    vectors_count: number | null;
    is_rule_collection: boolean;
    is_upload_collection: boolean;
  }>;
};

export type StorageMonitoring = {
  root: string;
  retention_hours: number;
  areas: Record<string, { files: number; bytes: number }>;
};
