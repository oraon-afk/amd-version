"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, FileText, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Badge, riskVariant } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { getEvidence, getFindings, getReport } from "@/features/audits/api";
import { UploadDropzone } from "@/features/uploads/components/UploadDropzone";
import { listDocuments } from "@/features/uploads/api";
import { formatDate, formatPercent } from "@/lib/utils";
import { getErrorMessage } from "@/services/api/client";
import { Audit, Evidence, Finding, UploadedDocument } from "@/types/api";

export default function UploadPage() {
  const [activeDocument, setActiveDocument] = useState<UploadedDocument | null>(null);
  const [activeAudit, setActiveAudit] = useState<Audit | null>(null);
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const documents = documentsQuery.data ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Upload Workspace</h1>
        <p className="mt-1 text-sm text-muted">Upload a file or paste raw text, then submit it for backend compliance analysis.</p>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <UploadDropzone
          redirectOnComplete={false}
          onDocumentUploaded={setActiveDocument}
          onAuditUpdate={setActiveAudit}
          onAuditComplete={setActiveAudit}
        />
        <div className="space-y-5">
          <AuditReportPanel audit={activeAudit} document={activeDocument} />
          <Card>
            <CardHeader>
              <CardTitle>Upload History</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {documentsQuery.isLoading && <Skeleton className="h-28 w-full" />}
              {!documentsQuery.isLoading && documents.length === 0 && (
                <EmptyState icon={FileText} title="No uploads yet" copy="Uploaded documents will appear here after you create an audit." />
              )}
              {documents.slice(0, 5).map((document) => (
                <div key={document.id} className="rounded-lg border border-line bg-white/5 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <FileText className="h-5 w-5 shrink-0 text-cyan" />
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">{document.title}</div>
                        <div className="text-xs text-muted">{document.domain} - {formatDate(document.created_at)}</div>
                      </div>
                    </div>
                    <Badge>{document.upload_status}</Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function AuditReportPanel({ audit, document }: { audit: Audit | null; document: UploadedDocument | null }) {
  const auditId = audit?.id ?? "";
  const reportQuery = useQuery({ queryKey: ["report", auditId], queryFn: () => getReport(auditId), enabled: audit?.status === "completed" });
  const findingsQuery = useQuery({ queryKey: ["findings", auditId], queryFn: () => getFindings(auditId), enabled: audit?.status === "completed" });
  const evidenceQuery = useQuery({ queryKey: ["evidence", auditId], queryFn: () => getEvidence(auditId), enabled: audit?.status === "completed" });

  const findings = findingsQuery.data ?? [];
  const evidence = evidenceQuery.data ?? [];
  const report = reportQuery.data ?? null;
  const error = reportQuery.error ?? findingsQuery.error ?? evidenceQuery.error;
  const reportMetadata = report ? readRecord(report.report_payload, "metadata") : {};
  const llmStatus = report ? readString(report.report_payload, "status") ?? readString(reportMetadata, "llm_status") : null;
  const retryAttempts = report ? readNumber(reportMetadata, "retry_attempts") : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Generated Audit Report</CardTitle>
        <ShieldCheck className="h-5 w-5 text-cyan" />
      </CardHeader>
      <CardContent className="space-y-4">
        {!audit && (
          <EmptyState icon={FileText} title="Awaiting audit" copy="Run AI Audit to generate the report here." />
        )}
        {audit && audit.status !== "completed" && audit.status !== "failed" && (
          <div className="space-y-3 rounded-lg border border-cyan/25 bg-cyan/10 p-4">
            <div className="text-sm font-semibold">Audit running</div>
            <div className="text-sm text-muted">{document?.title ?? "Uploaded document"} is currently at: {audit.status}</div>
            <Progress value={progressForStatus(audit.status)} />
          </div>
        )}
        {audit?.status === "failed" && (
          <p className="flex gap-2 rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
            <AlertCircle className="h-4 w-4 shrink-0" /> {audit.error_message ?? "Backend audit failed."}
          </p>
        )}
        {error && <p className="text-sm text-riskHigh">{getErrorMessage(error)}</p>}
        {audit?.status === "completed" && (reportQuery.isLoading || findingsQuery.isLoading || evidenceQuery.isLoading) && (
          <Skeleton className="h-52 w-full" />
        )}
        {audit?.status === "completed" && report && (
          <>
            {llmStatus === "fallback_generated" && (
              <p className="flex gap-2 rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
                <AlertCircle className="h-4 w-4 shrink-0" /> Fallback report generated after LLM retries failed.
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <Metric label="Compliance status" value={findings.length ? "Review required" : "Compliant"} />
              <Metric label="Confidence score" value={formatPercent(audit.confidence_score)} />
              <Metric label="Violations" value={String(findings.length)} />
              <Metric label="Risk" value={audit.overall_risk ?? "LOW"} badge={audit.overall_risk} />
              <Metric label="LLM status" value={llmStatus ?? "generated"} />
              <Metric label="Retry attempts" value={retryAttempts === null ? "Not returned" : String(retryAttempts)} />
            </div>
            <Section title="Final summary" value={report.summary} />
            <Section title="AI explanation" value={String(report.report_payload.summary ?? report.summary)} />
            <div>
              <div className="mb-2 text-xs font-semibold uppercase text-muted">Violations</div>
              <div className="space-y-3">
                {findings.length === 0 && <p className="rounded-lg border border-line bg-white/5 p-3 text-sm">No violations returned.</p>}
                {findings.slice(0, 4).map((finding) => (
                  <FindingPreview key={finding.id} finding={finding} evidence={evidence.filter((item) => item.finding_id === finding.id)} />
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, badge }: { label: string; value: string; badge?: string | null }) {
  return (
    <div className="rounded-lg border border-line bg-white/5 p-3">
      <div className="text-xs uppercase text-muted">{label}</div>
      <div className="mt-2 text-sm font-semibold">
        {badge ? <Badge variant={riskVariant(badge)}>{value}</Badge> : value}
      </div>
    </div>
  );
}

function Section({ title, value }: { title: string; value: string }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase text-muted">{title}</div>
      <p className="rounded-lg border border-line bg-black/20 p-3 text-sm leading-6">{value}</p>
    </div>
  );
}

function FindingPreview({ finding, evidence }: { finding: Finding; evidence: Evidence[] }) {
  const source = evidence[0];
  return (
    <article className="rounded-lg border border-line bg-white/5 p-3">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="text-sm font-semibold">{finding.violated_rule}</div>
        <Badge variant={riskVariant(finding.risk_level)}>{finding.risk_level}</Badge>
      </div>
      <Section title="Rule reference" value={finding.citation_source ?? source?.citation_label ?? "Not returned"} />
      <Section title="Evidence trace" value={finding.evidence_text ?? source?.citation_text ?? "Not returned"} />
      <Section title="AI explanation" value={finding.explanation} />
    </article>
  );
}

function progressForStatus(status: string) {
  if (status === "uploaded") return 12;
  if (status === "processing" || status === "extracting") return 35;
  if (status === "chunking") return 42;
  if (status === "embedding") return 52;
  if (status === "retrieving_rules") return 64;
  if (status === "reranking") return 72;
  if (status === "validating" || status === "analyzing") return 82;
  if (status === "generating_report") return 90;
  if (status === "completed") return 100;
  return 5;
}

function readNumber(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readString(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function readRecord(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
