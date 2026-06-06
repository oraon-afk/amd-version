"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle2, ClipboardCheck, Download, FileText, FileUp, Trash2 } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, type DataTableColumn } from "@/components/enterprise/DataTable";
import { StatusBadge } from "@/components/enterprise/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { downloadReportPdf, listAudits } from "@/features/audits/api";
import { isAuditActive } from "@/features/audits/status";
import { formatDate, formatPercent, normalizeScore } from "@/lib/utils";
import { deleteAdminAudit, listAdminDocuments, listAdminReports } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { AdminDocument, Audit, AuditReport } from "@/types/api";

type AdminReport = AuditReport & {
  audit_status?: string | null;
  overall_risk?: string | null;
  confidence_score?: number | null;
};

type AuditHistoryRow = {
  audit: Audit;
  document: AdminDocument | null;
  report: AdminReport | null;
};

export default function AdminAuditHistoryPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["admin-documents"], queryFn: listAdminDocuments });
  const reportsQuery = useQuery({ queryKey: ["admin-reports"], queryFn: listAdminReports });

  const audits = auditsQuery.data ?? [];
  const documents = documentsQuery.data?.uploaded_documents ?? [];
  const reports = (reportsQuery.data ?? []) as AdminReport[];
  const reportsByAudit = new Map(reports.map((report) => [report.audit_id, report]));
  const documentsById = new Map(documents.map((document) => [document.id, document]));
  const rows = audits.map((audit) => ({
    audit,
    document: documentsById.get(audit.document_id) ?? null,
    report: reportsByAudit.get(audit.id) ?? null,
  }));
  const loading = auditsQuery.isLoading || documentsQuery.isLoading || reportsQuery.isLoading;
  const error = auditsQuery.error ?? documentsQuery.error ?? reportsQuery.error;

  const deleteMutation = useMutation({
    mutationFn: deleteAdminAudit,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      queryClient.invalidateQueries({ queryKey: ["admin-reports"] });
      toast({ title: "Audit deleted" });
    },
    onError: (deleteError) => toast({ title: "Delete failed", description: getErrorMessage(deleteError), variant: "error" }),
  });

  const downloadMutation = useMutation({
    mutationFn: downloadReportPdf,
    onSuccess: (blob, auditId) => saveBlob(blob, `audit-report-${auditId}.pdf`),
    onError: (downloadError) => toast({ title: "Report download failed", description: getErrorMessage(downloadError), variant: "error" }),
  });

  const columns: DataTableColumn<AuditHistoryRow>[] = [
    {
      id: "audit_id",
      header: "Audit ID",
      cell: ({ audit }) => <span className="font-mono text-xs text-info">{audit.id}</span>,
      sortValue: ({ audit }) => audit.id,
      searchValue: ({ audit }) => audit.id,
    },
    {
      id: "document",
      header: "Document Name",
      cell: ({ audit, document }) => (
        <div className="min-w-0">
          <div className="truncate font-semibold">{document?.title ?? document?.filename ?? audit.document_id}</div>
          <div className="mt-1 truncate text-xs text-muted">{document?.filename ?? "Document metadata unavailable"}</div>
        </div>
      ),
      sortValue: ({ audit, document }) => document?.title ?? document?.filename ?? audit.document_id,
      searchValue: ({ audit, document }) => `${audit.id} ${document?.title ?? ""} ${document?.filename ?? ""}`,
    },
    {
      id: "domain",
      header: "Domain",
      cell: ({ document }) => <span className="text-muted">{document?.domain ?? "Not returned"}</span>,
      sortValue: ({ document }) => document?.domain ?? "",
      searchValue: ({ document }) => document?.domain ?? "",
    },
    {
      id: "status",
      header: "Status",
      cell: ({ audit }) => <StatusBadge status={audit.status} />,
      sortValue: ({ audit }) => audit.status,
    },
    {
      id: "score",
      header: "Compliance Score",
      cell: ({ report }) => <span className="text-muted">{formatScore(getComplianceScore(report))}</span>,
      sortValue: ({ report }) => getComplianceScore(report) ?? -1,
      exportValue: ({ report }) => formatScore(getComplianceScore(report)),
    },
    {
      id: "created",
      header: "Created Date",
      cell: ({ audit }) => <span className="text-muted">{formatDate(audit.created_at)}</span>,
      sortValue: ({ audit }) => audit.created_at,
      exportValue: ({ audit }) => formatDate(audit.created_at),
    },
    {
      id: "findings",
      header: "Findings Count",
      cell: ({ report }) => <span className="text-muted">{formatCount(getFindingsCount(report))}</span>,
      sortValue: ({ report }) => getFindingsCount(report) ?? -1,
      exportValue: ({ report }) => formatCount(getFindingsCount(report)),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ audit, report }) => (
        <div className="flex flex-wrap gap-2">
          <Link href={`/admin/reports/${audit.id}`}>
            <Button size="sm" variant="secondary">View</Button>
          </Link>
          <Button
            type="button"
            size="icon"
            variant="secondary"
            disabled={!report || downloadMutation.isPending}
            onClick={() => downloadMutation.mutate(audit.id)}
            aria-label={`Download report for ${audit.id}`}
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="destructive"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (window.confirm("Delete this audit and its generated findings/report?")) {
                deleteMutation.mutate(audit.id);
              }
            }}
            aria-label={`Delete audit ${audit.id}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
      enableHiding: false,
      exportValue: ({ audit }) => `/admin/reports/${audit.id}`,
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Check"
        title="Admin Audit History"
        description="Review uploaded audit documents, processing status, compliance scores, findings counts, and generated reports."
        actions={
          <Link href="/admin/compliance/upload">
            <Button>
              <FileUp className="h-4 w-4" /> Upload Audit Document
            </Button>
          </Link>
        }
      />

      {error && (
        <ErrorState
          error={error}
          onRetry={() => {
            auditsQuery.refetch();
            documentsQuery.refetch();
            reportsQuery.refetch();
          }}
        />
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28 w-full" />)
        ) : (
          <>
            <MetricCard icon={ClipboardCheck} label="Total Audits" value={audits.length} detail="All backend audit runs" />
            <MetricCard icon={Activity} label="Running" value={audits.filter((audit) => isAuditActive(audit.status)).length} detail="Queued or processing" tone="cyan" />
            <MetricCard icon={CheckCircle2} label="Completed" value={audits.filter((audit) => audit.status === "completed").length} detail="Report generated" tone="low" />
            <MetricCard icon={FileText} label="Failed" value={audits.filter((audit) => audit.status === "failed").length} detail="Backend failure state" tone="high" />
          </>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Audit Records</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && <Skeleton className="h-64 w-full" />}
          {!loading && rows.length === 0 && (
            <EmptyState
              icon={ClipboardCheck}
              title="No audits found"
              copy="Upload a document to start compliance analysis."
              action={
                <Link href="/admin/compliance/upload">
                  <Button size="sm">Upload Document</Button>
                </Link>
              }
            />
          )}
          {!loading && rows.length > 0 && (
            <DataTable
              data={rows}
              columns={columns}
              getRowId={({ audit }) => audit.id}
              searchPlaceholder="Search audit IDs, documents, or domains"
              exportFilename="admin-audit-history.csv"
              filters={[
                { id: "active", label: "Running or queued", predicate: ({ audit }) => isAuditActive(audit.status) },
                { id: "completed", label: "Completed", predicate: ({ audit }) => audit.status === "completed" },
                { id: "failed", label: "Failed", predicate: ({ audit }) => audit.status === "failed" },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function getComplianceScore(report: AdminReport | null) {
  if (!report) return null;
  return normalizeScore(
    readNumberFrom(report, "compliance_score", "complianceScore", "audit_score", "auditScore", "overall_score", "overallScore", "final_score", "finalScore", "score") ??
      readNumberFrom(report.report_payload ?? {}, "compliance_score", "complianceScore", "audit_score", "auditScore", "overall_score", "overallScore", "final_score", "finalScore", "score"),
  );
}

function getFindingsCount(report: AdminReport | null) {
  if (!report) return null;
  return readNumberFrom(report, "findings_count", "finding_count", "total_violations") ??
    readNumberFrom(report.report_payload ?? {}, "findings_count", "finding_count", "total_violations", "failed_rules") ??
    (Array.isArray(report.report_payload?.findings) ? report.report_payload.findings.length : null);
}

function formatScore(score: number | null) {
  return score === null ? "-" : formatPercent(score);
}

function formatCount(count: number | null) {
  return count === null ? "-" : String(Math.max(0, Math.round(count)));
}

function readNumberFrom(payload: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const number = readNumber(payload[key]);
    if (number !== null) return number;
  }
  return null;
}

function readNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    const parsed = Number(trimmed.endsWith("%") ? trimmed.slice(0, -1) : trimmed);
    if (Number.isFinite(parsed)) return trimmed.endsWith("%") ? parsed / 100 : parsed;
  }
  return null;
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  window.document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
