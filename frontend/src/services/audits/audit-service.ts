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

export async function getFindingExplanation(findingId: string) {
  const { data } = await apiClient.get<{
    finding_id: string;
    explanation_text: string;
    evidence_list: Array<{ text: string; page?: number | null; section?: string | null }>;
    confidence_score: number;
  }>(`/findings/${findingId}/explanation`);
  return data;
}

export async function getRemediationPlan(findingId: string) {
  const { data } = await apiClient.get<{
    id: string;
    finding_id: string;
    steps: string[];
    estimated_effort_hours: number;
    priority: string;
    suggested_owner_role: string;
    approved: boolean;
    created_at: string;
  }>(`/findings/${findingId}/remediation-plan`);
  return data;
}

export async function updateRemediationPlan(findingId: string, payload: {
  steps?: string[];
  estimated_effort_hours?: number;
  priority?: string;
  suggested_owner_role?: string;
  approved?: boolean;
}) {
  const { data } = await apiClient.put<{
    id: string;
    finding_id: string;
    steps: string[];
    estimated_effort_hours: number;
    priority: string;
    suggested_owner_role: string;
    approved: boolean;
    created_at: string;
  }>(`/findings/${findingId}/remediation-plan`, payload);
  return data;
}

export type CustomReport = {
  id: string;
  audit_id: string;
  template: string;
  sections: string[];
  generated_json: {
    title: string;
    metadata: {
      audit_id: string;
      document_title: string;
      template: string;
      generated_at: string;
      overall_risk: string;
      compliance_score: number;
      total_findings: number;
      high_severity: number;
      medium_severity: number;
      low_severity: number;
    };
    sections: Record<string, string>;
  };
  created_at: string;
};

export async function generateCustomReport(auditId: string, payload: { template: string; sections: string[] }) {
  const { data } = await apiClient.post<CustomReport>(`/reports/${auditId}/custom`, payload);
  return data;
}

export async function getCustomReport(reportId: string) {
  const { data } = await apiClient.get<CustomReport>(`/reports/custom/${reportId}`);
  return data;
}

export async function updateCustomReport(reportId: string, payload: { generated_json: any }) {
  const { data } = await apiClient.put<CustomReport>(`/reports/custom/${reportId}`, payload);
  return data;
}

export async function downloadCustomReport(reportId: string, format: string) {
  const { data } = await apiClient.get<Blob>(`/reports/custom/${reportId}/download/${format}`, {
    responseType: "blob",
  });
  return data;
}

