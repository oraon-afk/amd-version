import { apiClient } from "@/services/api/client";
import {
  AdminAnalytics,
  AdminDocument,
  AdminDocumentsResponse,
  AdminRuleDocument,
  AuditLog,
  AuditReport,
  ComplianceRule,
  QdrantMonitoring,
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
