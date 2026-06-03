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

export type UploadBatchDocument = {
  id: string;
  batch_id: string;
  document_id: string | null;
  audit_id: string | null;
  filename: string;
  content_type?: string | null;
  file_size_bytes: number;
  title: string;
  domain: string | null;
  queue_position: number;
  status: string;
  current_stage: string | null;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  processing_time_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type UploadBatch = {
  id: string;
  user_id: string;
  module: "compliance_check" | string;
  status: string;
  total_documents: number;
  completed_documents: number;
  failed_documents: number;
  processed_documents: number;
  pending_documents: number;
  progress_label: string | null;
  running_document: string | null;
  error_message: string | null;
  summary_report: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  documents: UploadBatchDocument[];
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
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
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
  compliance_score?: number | string | null;
  complianceScore?: number | string | null;
  overall_score?: number | string | null;
  score?: number | string | null;
  risk_score?: number | string | null;
  risk_level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string | null;
  findings_count?: number | null;
  compliance_status?: string | null;
  status?: string | null;
  findings?: ReportFindingPayload[];
  report_payload: {
    risk_counts?: Record<string, number>;
    finding_count?: number;
    findings_count?: number;
    total_violations?: number;
    compliance_score?: number;
    complianceScore?: number;
    overall_score?: number;
    score?: number;
    risk_score?: number;
    risk_level?: string;
    compliance_status?: string;
    complianceStatus?: string;
    status?: string;
    findings?: ReportFindingPayload[];
    passed_rules?: number;
    failed_rules?: number;
    recommendations?: string[];
    context_ready?: boolean;
    score_diagnostics?: ScoreDiagnostics;
    [key: string]: unknown;
  };
  report_json_s3_uri: string | null;
  created_at: string;
};

export type ReportFindingPayload = {
  violated_rule?: unknown;
  rule_violated?: unknown;
  matched_rule?: unknown;
  matched_rule_text?: unknown;
  matched_section?: unknown;
  matched_uploaded_text?: unknown;
  evidence?: unknown;
  evidence_text?: unknown;
  extracted_text?: unknown;
  citation?: unknown;
  citation_source?: unknown;
  section_title?: unknown;
  violation_reason?: unknown;
  explanation?: unknown;
  impact?: unknown;
  business_impact?: unknown;
  risk_impact?: unknown;
  recommendation?: unknown;
  severity?: unknown;
  risk_level?: unknown;
  confidence_score?: unknown;
  confidence?: unknown;
  page_number?: unknown;
  [key: string]: unknown;
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

export type RuleUploadBatchItem = {
  id: string;
  batch_id: string;
  rule_document_id: string | null;
  filename: string;
  content_type?: string | null;
  file_size_bytes: number;
  status: string;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  processing_time_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
};

export type RuleUploadBatch = {
  id: string;
  user_id: string;
  module: "rule_management" | string;
  status: string;
  total_documents: number;
  completed_documents: number;
  failed_documents: number;
  processed_documents: number;
  pending_documents: number;
  progress_label: string | null;
  running_document: string | null;
  error_message: string | null;
  summary_report: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  documents: RuleUploadBatchItem[];
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
  status: "active" | "archived" | string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type ScoreDiagnostics = {
  rules_evaluated: number;
  rules_matched: number;
  rules_failed: number;
  match_confidence: number | null;
  compliance_score?: number | string | null;
  score_reasoning: string;
  context_ready: boolean;
  retrieval_query_chars?: number;
  rule_matches?: Array<Record<string, unknown>>;
  failed_rules?: Array<Record<string, unknown>>;
};

export type DigitalTwinPolicyProfile = {
  id: string;
  document_id: string;
  latest_audit_id: string | null;
  latest_report_id: string | null;
  title: string;
  domain: string;
  status: string;
  compliance_score: number | null;
  risk_level: string | null;
  findings_count: number;
  coverage_status: string;
  created_at: string;
  updated_at: string;
};

export type DigitalTwinSnapshot = {
  id: string;
  twin_id: string;
  maturity_score: number;
  coverage_score: number;
  risk_score: number;
  total_policies: number;
  missing_policy_count: number;
  high_risk_policy_count: number;
  summary_text: string;
  snapshot_payload: Record<string, unknown>;
  created_at: string;
};

export type ComplianceDigitalTwin = {
  id: string;
  user_id: string | null;
  name: string;
  status: string;
  maturity_score: number;
  coverage_score: number;
  risk_score: number;
  missing_policies: Array<Record<string, unknown>>;
  risk_heatmap: Array<Record<string, unknown>>;
  policy_inventory: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
  generated_at: string | null;
  created_at: string;
  updated_at: string;
  policies: DigitalTwinPolicyProfile[];
  history: DigitalTwinSnapshot[];
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
