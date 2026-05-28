import { Audit, UploadedDocument } from "@/types/api";

export type WorkflowStage =
  | "uploaded"
  | "extracting"
  | "chunking"
  | "embedding"
  | "retrieving_rules"
  | "reranking"
  | "analyzing"
  | "generating_report"
  | "completed"
  | "failed";

export function getWorkflowStage(audit?: Audit | null, document?: UploadedDocument | null): WorkflowStage | null {
  if (audit?.status === "failed" || document?.status === "failed" || document?.upload_status === "failed") {
    return "failed";
  }
  if (audit?.status === "completed" || document?.status === "completed") return "completed";
  if (audit?.status === "generating_report") return "generating_report";
  if (audit?.status === "analyzing" || audit?.status === "validating") return "analyzing";
  if (audit?.status === "reranking") return "reranking";
  if (audit?.status === "retrieving_rules") return "retrieving_rules";
  if (audit?.status === "embedding") return "embedding";
  if (audit?.status === "chunking") return "chunking";
  if (audit?.status === "extracting" || audit?.status === "processing") return "extracting";
  if (audit?.status === "uploaded" || document?.status === "uploaded" || document?.upload_status === "uploaded") {
    return "uploaded";
  }
  return null;
}

export function isAuditActive(status?: string | null) {
  return Boolean(status && !["completed", "failed", "expired"].includes(status));
}
