import { apiClient } from "@/services/api/client";
import {
  AdminAnalytics,
  AdminDocument,
  AdminDocumentsResponse,
  AdminRuleDocument,
  AuditLog,
  AuditReport,
  ComplianceRule,
  DeploymentConfig,
  QdrantMonitoring,
  RuleTestResult,
  RuleUploadBatch,
  RuleCategory,
  StorageMonitoring,
  User,
} from "@/types/api";

export type RuleUploadPayload = {
  file: File;
  ruleSetId: string;
  category: string;
  jurisdiction?: string;
  documentType: string;
  version: string;
};

export type BulkRuleUploadPayload = Omit<RuleUploadPayload, "file"> & {
  files: File[];
  categories?: string[];
  domains?: string[];
};

export type AdminDocumentUploadPayload = {
  title: string;
  domain: string;
  file?: File | null;
  rawText?: string | null;
};

export type ComplianceRulePayload = {
  category: string;
  title: string;
  description?: string;
  rule_text: string;
  reference?: string;
  version: string;
  custom_attributes?: Record<string, unknown> | null;
  effectivity_date?: string | null;
  expiry_date?: string | null;
};

export type ComplianceRuleUpdatePayload = Partial<ComplianceRulePayload> & {
  status?: "active" | "archived";
};

export async function listAdminUsers() {
  const { data } = await apiClient.get<User[]>("/admin/users");
  return data;
}

export async function listAdminDocuments() {
  const { data } = await apiClient.get<AdminDocumentsResponse>("/admin/documents");
  return data;
}

export async function uploadRuleDocument(payload: RuleUploadPayload) {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("rule_set_id", payload.ruleSetId);
  formData.append("category", payload.category);
  formData.append("document_type", payload.documentType);
  formData.append("version", payload.version);
  if (payload.jurisdiction?.trim()) formData.append("jurisdiction", payload.jurisdiction.trim());
  const { data } = await apiClient.post<AdminRuleDocument>("/admin/rules/upload", formData);
  return data;
}

export async function bulkUploadRuleDocuments(payload: BulkRuleUploadPayload) {
  const formData = new FormData();
  payload.files.forEach((file) => formData.append("files", file));
  formData.append("rule_set_id", payload.ruleSetId);
  formData.append("category", payload.category);
  payload.categories?.forEach((category) => formData.append("categories", category));
  payload.domains?.forEach((domain) => formData.append("domains", domain));
  formData.append("document_type", payload.documentType);
  formData.append("version", payload.version);
  if (payload.jurisdiction?.trim()) formData.append("jurisdiction", payload.jurisdiction.trim());
  const { data } = await apiClient.post<RuleUploadBatch>("/admin/rules/bulk-upload", formData);
  return data;
}

export async function getRuleUploadBatch(batchId: string) {
  const { data } = await apiClient.get<RuleUploadBatch>(`/admin/rule-batches/${batchId}`);
  return data;
}

export async function uploadAdminDocument(payload: AdminDocumentUploadPayload) {
  const formData = new FormData();
  formData.append("title", payload.title);
  formData.append("domain", payload.domain);
  if (payload.file) formData.append("file", payload.file);
  if (payload.rawText?.trim()) formData.append("raw_text", payload.rawText.trim());
  const { data } = await apiClient.post<AdminDocument>("/admin/documents/upload", formData);
  return data;
}

export async function deleteAdminDocument(documentId: string) {
  const { data } = await apiClient.delete<{ status: string; id: string }>(`/admin/document/${documentId}`);
  return data;
}

export async function deleteAdminAudit(auditId: string) {
  const { data } = await apiClient.delete<{ status: string; id: string }>(`/admin/audits/${auditId}`);
  return data;
}

export async function listAdminReports() {
  const { data } = await apiClient.get<AuditReport[]>("/admin/audit-reports");
  return data;
}

export async function listComplianceRules() {
  const { data } = await apiClient.get<ComplianceRule[]>("/admin/compliance-rules");
  return data;
}

export async function createComplianceRule(payload: ComplianceRulePayload) {
  const { data } = await apiClient.post<ComplianceRule>("/admin/compliance-rules", payload);
  return data;
}

export async function updateComplianceRule(ruleId: string, payload: ComplianceRuleUpdatePayload) {
  const { data } = await apiClient.patch<ComplianceRule>(`/admin/compliance-rules/${ruleId}`, payload);
  return data;
}

export async function archiveComplianceRule(ruleId: string) {
  const { data } = await apiClient.post<ComplianceRule>(`/admin/compliance-rules/${ruleId}/archive`);
  return data;
}

export async function deleteComplianceRule(ruleId: string) {
  const { data } = await apiClient.delete<{ status: string; id: string }>(`/admin/compliance-rules/${ruleId}`);
  return data;
}

export async function testComplianceRule(ruleId: string, sampleDocumentText: string) {
  const { data } = await apiClient.post<RuleTestResult>(`/admin/compliance-rules/${ruleId}/test`, {
    sample_document_text: sampleDocumentText,
  });
  return data;
}

export async function getDeploymentConfig() {
  const { data } = await apiClient.get<DeploymentConfig>("/admin/deployment/config");
  return data;
}

export async function reloadDeployment() {
  const { data } = await apiClient.post<{ status: string; components_reloaded: string[] }>("/admin/deployment/reload");
  return data;
}

export async function listRuleCategories() {
  const { data } = await apiClient.get<RuleCategory[]>("/admin/rule-categories");
  return data;
}

export async function createRuleCategory(payload: { name: string; description?: string }) {
  const { data } = await apiClient.post<RuleCategory>("/admin/rule-categories", payload);
  return data;
}

export async function getAdminAnalytics() {
  const { data } = await apiClient.get<AdminAnalytics>("/admin/analytics");
  return data;
}

export async function getAuditLogs() {
  const { data } = await apiClient.get<AuditLog[]>("/admin/logs");
  return data;
}

export async function getStorageMonitoring() {
  const { data } = await apiClient.get<StorageMonitoring>("/admin/storage");
  return data;
}

export async function getQdrantMonitoring() {
  const { data } = await apiClient.get<QdrantMonitoring>("/admin/qdrant");
  return data;
}
