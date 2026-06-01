"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Activity, CheckCircle2, ClipboardCheck, FileUp, ShieldAlert } from "lucide-react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { DataTable, type DataTableColumn } from "@/components/enterprise/DataTable";
import { RiskBadge, StatusBadge } from "@/components/enterprise/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listAudits } from "@/features/audits/api";
import { isAuditActive } from "@/features/audits/status";
import { listDocuments } from "@/features/uploads/api";
import { formatDate, formatPercent } from "@/lib/utils";
import { Audit, UploadedDocument } from "@/types/api";

type AuditRow = {
  audit: Audit;
  document: UploadedDocument | null;
};

export default function AuditManagementPage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const audits = auditsQuery.data ?? [];
  const documents = documentsQuery.data ?? [];
  const activeAudits = audits.filter((audit) => isAuditActive(audit.status));
  const completedAudits = audits.filter((audit) => audit.status === "completed");
  const failedAudits = audits.filter((audit) => audit.status === "failed");
  const highRiskAudits = audits.filter((audit) => audit.overall_risk === "HIGH");
  const error = auditsQuery.error ?? documentsQuery.error;
  const rows = audits.map((audit) => ({
    audit,
    document: documents.find((item) => item.id === audit.document_id) ?? null,
  }));
  const columns: DataTableColumn<AuditRow>[] = [
    {
      id: "id",
      header: "Run ID",
      cell: ({ audit }) => <span className="font-mono text-xs text-info">{audit.id}</span>,
      sortValue: ({ audit }) => audit.id,
      searchValue: ({ audit }) => audit.id,
    },
    {
      id: "document",
      header: "Document",
      cell: ({ audit, document }) => (
        <div className="min-w-0">
          <div className="truncate font-medium">{document?.title ?? audit.document_id}</div>
          <div className="mt-1 truncate text-xs text-muted">{document?.domain ?? "Domain not returned"}</div>
        </div>
      ),
      sortValue: ({ audit, document }) => document?.title ?? audit.document_id,
      searchValue: ({ audit, document }) => `${document?.title ?? ""} ${document?.domain ?? ""} ${audit.document_id}`,
    },
    {
      id: "status",
      header: "Status",
      cell: ({ audit }) => <StatusBadge status={audit.status} />,
      sortValue: ({ audit }) => audit.status,
    },
    {
      id: "risk",
      header: "Risk",
      cell: ({ audit }) => <RiskBadge risk={audit.overall_risk} />,
      sortValue: ({ audit }) => audit.overall_risk ?? "",
    },
    {
      id: "confidence",
      header: "Confidence",
      cell: ({ audit }) => <span className="text-muted">{formatPercent(audit.confidence_score)}</span>,
      sortValue: ({ audit }) => audit.confidence_score ?? 0,
      exportValue: ({ audit }) => formatPercent(audit.confidence_score),
    },
    {
      id: "started",
      header: "Started",
      cell: ({ audit }) => <span className="text-muted">{formatDate(audit.started_at ?? audit.created_at)}</span>,
      sortValue: ({ audit }) => audit.started_at ?? audit.created_at,
      exportValue: ({ audit }) => formatDate(audit.started_at ?? audit.created_at),
    },
    {
      id: "completed",
      header: "Completed",
      cell: ({ audit }) => <span className="text-muted">{formatDate(audit.completed_at)}</span>,
      sortValue: ({ audit }) => audit.completed_at ?? "",
      exportValue: ({ audit }) => formatDate(audit.completed_at),
    },
    {
      id: "action",
      header: "Action",
      cell: ({ audit }) => (
        <Link href={`/dashboard/reports/${audit.id}`}>
          <Button size="sm" variant="secondary">{audit.status === "completed" ? "Open Results" : "View Status"}</Button>
        </Link>
      ),
      enableHiding: false,
      exportValue: ({ audit }) => `/dashboard/reports/${audit.id}`,
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Operations"
        title="Audit Runs"
        description="Track running, completed, failed, and high-risk audits with status, confidence, and timestamps returned by the audit service."
        actions={
          <Link href="/dashboard/upload">
            <Button>
              <FileUp className="h-4 w-4" /> Upload & Run Audit
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
          }}
        />
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {auditsQuery.isLoading ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28 w-full" />)
        ) : (
          <>
            <MetricCard icon={Activity} label="Open Audits" value={activeAudits.length} detail="Running or queued" />
            <MetricCard icon={CheckCircle2} label="Completed" value={completedAudits.length} detail="Report generated" tone="low" />
            <MetricCard icon={ShieldAlert} label="High Risk" value={highRiskAudits.length} detail="Returned by backend risk score" tone="high" />
            <MetricCard icon={ClipboardCheck} label="Failed" value={failedAudits.length} detail="Backend failure state" tone={failedAudits.length ? "high" : "muted"} />
          </>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Audit Records</CardTitle>
        </CardHeader>
        <CardContent>
          {(auditsQuery.isLoading || documentsQuery.isLoading) && <Skeleton className="h-56 w-full" />}
          {!auditsQuery.isLoading && audits.length === 0 && (
            <EmptyState
              icon={ClipboardCheck}
              title="No audits returned"
              copy="Run an audit from the upload workspace to create the first backend audit record."
              action={
                <Link href="/dashboard/upload">
                  <Button size="sm">Upload Document</Button>
                </Link>
              }
            />
          )}
          {audits.length > 0 && (
            <DataTable
              data={rows}
              columns={columns}
              getRowId={({ audit }) => audit.id}
              searchPlaceholder="Search run IDs, documents, or domains"
              exportFilename="assessment-runs.csv"
              filters={[
                { id: "active", label: "Running or queued", predicate: ({ audit }) => isAuditActive(audit.status) },
                { id: "completed", label: "Completed", predicate: ({ audit }) => audit.status === "completed" },
                { id: "failed", label: "Failed", predicate: ({ audit }) => audit.status === "failed" },
                { id: "high", label: "High risk", predicate: ({ audit }) => audit.overall_risk === "HIGH" },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
