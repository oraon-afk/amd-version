import { apiClient } from "@/services/api/client";
import { ComplianceDomain, UploadBatch, UploadedDocument } from "@/types/api";

export type UploadDocumentPayload = {
  title: string;
  domain: string;
  file?: File | null;
  rawText?: string;
};

export async function uploadDocument(payload: UploadDocumentPayload) {
  const formData = new FormData();
  formData.append("title", payload.title);
  formData.append("domain", payload.domain);
  if (payload.file) formData.append("file", payload.file);
  if (payload.rawText?.trim()) formData.append("raw_text", payload.rawText.trim());
  const { data } = await apiClient.post<UploadedDocument>("/documents/upload", formData);
  return data;
}

export async function bulkUploadDocuments(payload: { files: File[]; domain?: string | null; domains?: string[]; ruleSetId?: string | null }) {
  const formData = new FormData();
  if (payload.domain?.trim()) formData.append("domain", payload.domain.trim());
  payload.domains?.forEach((domain) => formData.append("domains", domain));
  if (payload.domains?.length) {
    formData.append(
      "file_domains",
      JSON.stringify(payload.files.map((file, index) => ({ file: file.name, domain: payload.domains?.[index] ?? "" }))),
    );
  }
  if (payload.ruleSetId?.trim()) formData.append("rule_set_id", payload.ruleSetId.trim());
  payload.files.forEach((file) => formData.append("files", file));
  const { data } = await apiClient.post<UploadBatch>("/documents/bulk-upload", formData);
  return data;
}

export async function getUploadBatch(batchId: string) {
  const { data } = await apiClient.get<UploadBatch>(`/batches/${batchId}`);
  return data;
}

export async function listDocuments() {
  const { data } = await apiClient.get<UploadedDocument[]>("/documents");
  return data;
}

export async function listComplianceDomains() {
  const { data } = await apiClient.get<ComplianceDomain[]>("/documents/domains");
  return data;
}
