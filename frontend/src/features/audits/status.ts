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
  const stage =
    mapStatus(audit?.status) ??
    mapStatus(document?.processing_stage) ??
    mapStatus(document?.status) ??
    mapStatus(document?.upload_status);
  if (process.env.NODE_ENV === "development") {
    console.log("Mapped Stage", stage);
  }
  return stage;
}

export function isAuditActive(status?: string | null) {
  const normalized = normalizeStatus(status);
  return Boolean(normalized && !["completed", "failed"].includes(normalized));
}

function mapStatus(status?: string | null): WorkflowStage | null {
  const normalized = normalizeStatus(status);
  if (!normalized) return null;
  if (normalized === "failed" || normalized === "error") return "failed";
  if (normalized === "completed" || normalized === "complete") return "completed";
  if (normalized === "generating_report" || normalized === "reporting" || normalized === "report_generation") {
    return "generating_report";
  }
  if (normalized === "analyzing" || normalized === "validating" || normalized === "llm_analysis" || normalized === "compliance_analysis") {
    return "analyzing";
  }
  if (normalized === "reranking") return "reranking";
  if (normalized === "retrieving_rules" || normalized === "retrieving" || normalized === "retrieval") {
    return "retrieving_rules";
  }
  if (normalized === "embedding" || normalized === "embedded") return "embedding";
  if (normalized === "chunking" || normalized === "chunked") return "chunking";
  if (normalized === "extracting" || normalized === "extraction" || normalized === "processing" || normalized === "running") {
    return "extracting";
  }
  if (normalized === "uploaded" || normalized === "uploading" || normalized === "queued" || normalized === "pending" || normalized === "created") {
    return "uploaded";
  }
  return null;
}

function normalizeStatus(status?: string | null) {
  return String(status ?? "").trim().toLowerCase().replaceAll("-", "_").replaceAll(" ", "_");
}
