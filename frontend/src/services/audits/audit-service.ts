import { apiClient } from "@/services/api/client";
import { Audit, AuditReport, Evidence, Finding } from "@/types/api";

export async function createAudit(documentId: string, ruleSetId?: string | null) {
  const { data } = await apiClient.post<Audit>("/audit/run", {
    document_id: documentId,
    rule_set_id: ruleSetId || null,
  });
  return data;
}

export async function listAudits() {
  const { data } = await apiClient.get<Audit[]>("/audits");
  return data;
}

export async function getAudit(auditId: string) {
  const { data } = await apiClient.get<Audit>(`/audits/${auditId}`);
  if (process.env.NODE_ENV === "development") {
    console.log("Audit Status Response", data);
  }
  return data;
}

export async function getFindings(auditId: string) {
  const { data } = await apiClient.get<Finding[]>(`/audits/${auditId}/findings`);
  return data;
}

export async function getEvidence(auditId: string) {
  const { data } = await apiClient.get<Evidence[]>(`/audits/${auditId}/evidence`);
  return data;
}

export async function getReport(auditId: string) {
  const { data } = await apiClient.get<AuditReport>(`/audits/${auditId}/report`);
  return data;
}

export async function downloadReportJson(auditId: string) {
  const { data } = await apiClient.get<Blob>(`/reports/${auditId}/download/json`, {
    responseType: "blob",
  });
  return data;
}

export async function downloadReportPdf(auditId: string) {
  const { data } = await apiClient.get<Blob>(`/reports/${auditId}/download/pdf`, {
    responseType: "blob",
  });
  return data;
}

export async function reviewFinding(
  findingId: string,
  payload: { action: string; comment?: string | null; modified_fields?: Record<string, any> | null }
) {
  const { data } = await apiClient.post(`/findings/${findingId}/review`, payload);
  return data;
}

export async function publishReport(auditId: string) {
  const { data } = await apiClient.post(`/reports/${auditId}/publish`);
  return data;
}

export async function getReviewHistory(auditId: string) {
  const { data } = await apiClient.get<Finding[]>(`/findings/${auditId}/review-history`);
  return data;
}

export async function getFullDiagnostics(auditId: string) {
  const { data } = await apiClient.get(`/audits/${auditId}/diagnostics/full`);
  return data;
}
