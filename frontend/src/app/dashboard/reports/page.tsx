"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { FileCheck2, FileUp, ShieldAlert, ShieldCheck } from "lucide-react";
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

type ResultRow = {
  audit: Audit;
  document: UploadedDocument | null;
};

export default function ComplianceResultsPage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const audits = auditsQuery.data ?? [];
  const documents = documentsQuery.data ?? [];
  const rows = audits.map((audit) => ({
    audit,
    document: documents.find((document) => document.id === audit.document_id) ?? null,
  }));
  const completed = audits.filter((audit) => audit.status === "completed");
  const active = audits.filter((audit) => isAuditActive(audit.status));
  const highRisk = audits.filter((audit) => audit.overall_risk === "HIGH");
  const error = auditsQuery.error ?? documentsQuery.error;
  const loading = auditsQuery.isLoading || documentsQuery.isLoading;

  const columns: DataTableColumn<ResultRow>[] = [
    {
      id: "document",
      header: "Document",
      cell: ({ audit, document }) => (
        <div className="min-w-0">
          <div className="truncate font-semibold">{document?.title ?? audit.document_id}</div>
          <div className="mt-1 truncate text-xs text-muted">{document?.domain ?? "Domain not returned"}</div>
        </div>
      ),
      sortValue: ({ document, audit }) => document?.title ?? audit.document_id,
      searchValue: ({ document, audit }) => `${document?.title ?? ""} ${document?.domain ?? ""} ${audit.id}`,
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
      id: "action",
      header: "Action",
      cell: ({ audit }) => (
        <Link href={`/dashboard/reports/${audit.id}`}>
          <Button size="sm" variant="secondary">
            {audit.status === "completed" ? "Open Results" : "View Status"}
          </Button>
        </Link>
      ),
      enableHiding: false,
      exportValue: ({ audit }) => `/dashboard/reports/${audit.id}`,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance results"
        title="Risk & Compliance Findings"
        description="Search, filter, export, and open every AI compliance assessment returned by the backend."
        actions={
          <Link href="/dashboard/upload">
            <Button>
              <FileUp className="h-4 w-4" /> Upload & Analyze
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
        {loading ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28 w-full" />)
        ) : (
          <>
            <MetricCard icon={FileCheck2} label="Assessments" value={audits.length} detail="All backend audit runs" />
            <MetricCard icon={ShieldCheck} label="Completed" value={completed.length} detail="Results generated" tone="low" />
            <MetricCard icon={ShieldAlert} label="Open Risks" value={highRisk.length} detail="High-risk assessments" tone={highRisk.length ? "high" : "muted"} />
            <MetricCard icon={FileUp} label="In Review" value={active.length} detail="Queued or processing" tone="medium" />
          </>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Assessment Results</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && <Skeleton className="h-64 w-full" />}
          {!loading && rows.length === 0 && (
            <EmptyState
              icon={FileCheck2}
              title="No compliance results yet"
              copy="Upload a document and run an AI assessment to create the first result."
              action={
                <Link href="/dashboard/upload">
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
              searchPlaceholder="Search documents, domains, or assessment IDs"
              exportFilename="compliance-results.csv"
              filters={[
                { id: "completed", label: "Completed", predicate: ({ audit }) => audit.status === "completed" },
                { id: "active", label: "In review", predicate: ({ audit }) => isAuditActive(audit.status) },
                { id: "high", label: "High risk", predicate: ({ audit }) => audit.overall_risk === "HIGH" },
                { id: "failed", label: "Failed", predicate: ({ audit }) => audit.status === "failed" },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
