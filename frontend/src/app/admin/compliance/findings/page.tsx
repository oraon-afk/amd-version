"use client";

import { useQuery } from "@tanstack/react-query";
import { FileSearch, FileUp, ListChecks } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, type DataTableColumn } from "@/components/enterprise/DataTable";
import { RiskBadge } from "@/components/enterprise/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listAudits } from "@/features/audits/api";
import { formatDate, formatPercent, normalizeScore } from "@/lib/utils";
import { listAdminDocuments, listAdminReports } from "@/services/admin/admin-service";
import { Audit, AuditReport, AdminDocument } from "@/types/api";

type AdminReport = AuditReport & {
  overall_risk?: string | null;
};

type FindingSummaryRow = {
  audit: Audit | null;
  document: AdminDocument | null;
  report: AdminReport;
};

export default function AdminFindingsPage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["admin-documents"], queryFn: listAdminDocuments });
  const reportsQuery = useQuery({ queryKey: ["admin-reports"], queryFn: listAdminReports });
  const auditsById = new Map((auditsQuery.data ?? []).map((audit) => [audit.id, audit]));
  const documentsById = new Map((documentsQuery.data?.uploaded_documents ?? []).map((document) => [document.id, document]));
  const rows = ((reportsQuery.data ?? []) as AdminReport[]).map((report) => {
    const audit = auditsById.get(report.audit_id) ?? null;
    return {
      report,
      audit,
      document: audit ? documentsById.get(audit.document_id) ?? null : null,
    };
  });
  const loading = auditsQuery.isLoading || documentsQuery.isLoading || reportsQuery.isLoading;
  const error = auditsQuery.error ?? documentsQuery.error ?? reportsQuery.error;

  const columns: DataTableColumn<FindingSummaryRow>[] = [
    {
      id: "document",
      header: "Document",
      cell: ({ audit, document }) => (
        <div className="min-w-0">
          <div className="truncate font-semibold">{document?.title ?? audit?.document_id ?? "Document not returned"}</div>
          <div className="mt-1 truncate text-xs text-muted">{document?.domain ?? "Domain not returned"}</div>
        </div>
      ),
      sortValue: ({ audit, document }) => document?.title ?? audit?.document_id ?? "",
      searchValue: ({ audit, document }) => `${document?.title ?? ""} ${document?.domain ?? ""} ${audit?.id ?? ""}`,
    },
    {
      id: "findings",
      header: "Findings",
      cell: ({ report }) => <span className="text-muted">{formatCount(getFindingsCount(report))}</span>,
      sortValue: ({ report }) => getFindingsCount(report) ?? -1,
      exportValue: ({ report }) => formatCount(getFindingsCount(report)),
    },
    {
      id: "score",
      header: "Compliance Score",
      cell: ({ report }) => <span className="text-muted">{formatScore(getComplianceScore(report))}</span>,
      sortValue: ({ report }) => getComplianceScore(report) ?? -1,
      exportValue: ({ report }) => formatScore(getComplianceScore(report)),
    },
    {
      id: "risk",
      header: "Risk",
      cell: ({ audit, report }) => <RiskBadge risk={report.overall_risk ?? audit?.overall_risk} />,
      sortValue: ({ audit, report }) => report.overall_risk ?? audit?.overall_risk ?? "",
    },
    {
      id: "created",
      header: "Created",
      cell: ({ report }) => <span className="text-muted">{formatDate(report.created_at)}</span>,
      sortValue: ({ report }) => report.created_at,
      exportValue: ({ report }) => formatDate(report.created_at),
    },
    {
      id: "action",
      header: "Action",
      cell: ({ report }) => (
        <Link href={`/admin/reports/${report.audit_id}`}>
          <Button size="sm" variant="secondary">View Findings</Button>
        </Link>
      ),
      enableHiding: false,
      exportValue: ({ report }) => `/admin/reports/${report.audit_id}`,
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Check"
        title="Findings"
        description="Review real finding counts, risk, and compliance scores from generated audit reports."
        actions={
          <Link href="/admin/compliance/upload">
            <Button>
              <FileUp className="h-4 w-4" /> Upload Audit Document
            </Button>
          </Link>
        }
      />
      {error && <ErrorState error={error} onRetry={() => { auditsQuery.refetch(); documentsQuery.refetch(); reportsQuery.refetch(); }} />}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Finding Results</CardTitle>
          <ListChecks className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent>
          {loading && <Skeleton className="h-64 w-full" />}
          {!loading && rows.length === 0 && (
            <EmptyState
              icon={FileSearch}
              title="No findings found"
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
              getRowId={({ report }) => report.id}
              searchPlaceholder="Search documents, domains, or audit IDs"
              exportFilename="admin-findings.csv"
              filters={[
                { id: "with-findings", label: "Has findings", predicate: ({ report }) => (getFindingsCount(report) ?? 0) > 0 },
                { id: "no-findings", label: "No findings", predicate: ({ report }) => getFindingsCount(report) === 0 },
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
