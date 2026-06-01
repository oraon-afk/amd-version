"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { FileSearch, FileUp } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, type DataTableColumn } from "@/components/enterprise/DataTable";
import { RiskBadge } from "@/components/enterprise/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getEvidence, listAudits } from "@/features/audits/api";
import { formatDate } from "@/lib/utils";
import { listAdminDocuments, listAdminReports } from "@/services/admin/admin-service";
import { AdminDocument, Audit, AuditReport } from "@/types/api";

type AdminReport = AuditReport & {
  overall_risk?: string | null;
};

type EvidenceRow = {
  audit: Audit;
  document: AdminDocument | null;
  report: AdminReport | null;
  evidenceCount: number;
};

export default function AdminEvidencePage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["admin-documents"], queryFn: listAdminDocuments });
  const reportsQuery = useQuery({ queryKey: ["admin-reports"], queryFn: listAdminReports });
  const completedAudits = (auditsQuery.data ?? []).filter((audit) => audit.status === "completed");
  const evidenceQueries = useQueries({
    queries: completedAudits.map((audit) => ({
      queryKey: ["evidence", audit.id],
      queryFn: () => getEvidence(audit.id),
      enabled: Boolean(audit.id),
    })),
  });

  const documentsById = new Map((documentsQuery.data?.uploaded_documents ?? []).map((document) => [document.id, document]));
  const reportsByAuditId = new Map(((reportsQuery.data ?? []) as AdminReport[]).map((report) => [report.audit_id, report]));
  const rows: EvidenceRow[] = completedAudits.map((audit, index) => ({
    audit,
    document: documentsById.get(audit.document_id) ?? null,
    report: reportsByAuditId.get(audit.id) ?? null,
    evidenceCount: evidenceQueries[index]?.data?.length ?? 0,
  }));
  const evidenceError = evidenceQueries.find((query) => query.error)?.error;
  const loading =
    auditsQuery.isLoading ||
    documentsQuery.isLoading ||
    reportsQuery.isLoading ||
    evidenceQueries.some((query) => query.isLoading);
  const error = auditsQuery.error ?? documentsQuery.error ?? reportsQuery.error ?? evidenceError;

  const columns: DataTableColumn<EvidenceRow>[] = [
    {
      id: "document",
      header: "Document",
      cell: ({ audit, document }) => (
        <div className="min-w-0">
          <div className="truncate font-semibold">{document?.title ?? audit.document_id}</div>
          <div className="mt-1 truncate text-xs text-muted">{document?.domain ?? "Domain not returned"}</div>
        </div>
      ),
      sortValue: ({ audit, document }) => document?.title ?? audit.document_id,
      searchValue: ({ audit, document }) => `${document?.title ?? ""} ${document?.domain ?? ""} ${audit.id}`,
    },
    {
      id: "evidence",
      header: "Evidence",
      cell: ({ evidenceCount }) => <span className="text-muted">{evidenceCount}</span>,
      sortValue: ({ evidenceCount }) => evidenceCount,
      exportValue: ({ evidenceCount }) => String(evidenceCount),
    },
    {
      id: "risk",
      header: "Risk",
      cell: ({ audit, report }) => <RiskBadge risk={report?.overall_risk ?? audit.overall_risk} />,
      sortValue: ({ audit, report }) => report?.overall_risk ?? audit.overall_risk ?? "",
    },
    {
      id: "completed",
      header: "Completed",
      cell: ({ audit }) => <span className="text-muted">{formatDate(audit.completed_at ?? audit.created_at)}</span>,
      sortValue: ({ audit }) => audit.completed_at ?? audit.created_at,
      exportValue: ({ audit }) => formatDate(audit.completed_at ?? audit.created_at),
    },
    {
      id: "action",
      header: "Action",
      cell: ({ audit }) => (
        <Link href={`/admin/reports/${audit.id}`}>
          <Button size="sm" variant="secondary">Open Evidence</Button>
        </Link>
      ),
      enableHiding: false,
      exportValue: ({ audit }) => `/admin/reports/${audit.id}`,
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Center"
        title="Evidence"
        description="Review generated evidence counts for completed audits and open the full evidence-backed report."
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
          <CardTitle>Evidence Results</CardTitle>
          <FileSearch className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent>
          {loading && <Skeleton className="h-64 w-full" />}
          {!loading && rows.length === 0 && (
            <EmptyState
              icon={FileSearch}
              title="No evidence found"
              copy="Completed compliance audits will appear here when evidence is generated."
            />
          )}
          {!loading && rows.length > 0 && (
            <DataTable
              data={rows}
              columns={columns}
              getRowId={({ audit }) => audit.id}
              searchPlaceholder="Search documents, domains, or audit IDs"
              exportFilename="admin-evidence.csv"
              filters={[
                { id: "with-evidence", label: "Has evidence", predicate: ({ evidenceCount }) => evidenceCount > 0 },
                { id: "no-evidence", label: "No evidence", predicate: ({ evidenceCount }) => evidenceCount === 0 },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
