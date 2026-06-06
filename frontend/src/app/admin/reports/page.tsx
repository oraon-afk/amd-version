"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { AlertTriangle, FileClock, Gauge, ShieldCheck } from "lucide-react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { DataTable, type DataTableColumn } from "@/components/enterprise/DataTable";
import { RiskBadge, StatusBadge } from "@/components/enterprise/StatusBadge";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listAdminReports } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { formatDate, formatPercent } from "@/lib/utils";

type AdminReport = Awaited<ReturnType<typeof listAdminReports>>[number] & {
  audit_status?: string | null;
  overall_risk?: string | null;
  confidence_score?: number | null;
};

export default function AdminReportsPage() {
  const reportsQuery = useQuery({ queryKey: ["admin-reports"], queryFn: listAdminReports });
  const reports = (reportsQuery.data ?? []) as AdminReport[];
  const highRiskCount = reports.filter((report) => report.overall_risk === "HIGH" || report.overall_risk === "CRITICAL").length;
  const mediumRiskCount = reports.filter((report) => report.overall_risk === "MEDIUM").length;
  const confidenceValues = reports
    .map((report) => report.confidence_score)
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  const averageConfidence = confidenceValues.length
    ? confidenceValues.reduce((total, value) => total + value, 0) / confidenceValues.length
    : null;
  const columns: DataTableColumn<AdminReport>[] = [
    {
      id: "summary",
      header: "Summary",
      cell: (report) => (
        <div className="min-w-0">
          <div className="line-clamp-2 font-semibold">{report.summary}</div>
          <div className="mt-1 text-xs text-muted">{report.audit_id}</div>
        </div>
      ),
      sortValue: (report) => report.summary,
      searchValue: (report) => `${report.summary} ${report.audit_id}`,
    },
    {
      id: "status",
      header: "Status",
      cell: (report) => <StatusBadge status={report.audit_status ?? "completed"} />,
      sortValue: (report) => report.audit_status ?? "completed",
    },
    {
      id: "risk",
      header: "Risk",
      cell: (report) => <RiskBadge risk={report.overall_risk} />,
      sortValue: (report) => report.overall_risk ?? "",
    },
    {
      id: "created",
      header: "Created",
      cell: (report) => <span className="text-muted">{formatDate(report.created_at)}</span>,
      sortValue: (report) => report.created_at,
      exportValue: (report) => formatDate(report.created_at),
    },
    {
      id: "action",
      header: "Action",
      cell: (report) => (
        <Link href={`/admin/reports/${report.audit_id}`}>
          <Button size="sm" variant="secondary">Open Results</Button>
        </Link>
      ),
      enableHiding: false,
      exportValue: (report) => `/admin/reports/${report.audit_id}`,
    },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Operations"
        title="Compliance Results"
        description="Search, filter, export, and open generated compliance assessments across users."
      />
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Gauge} label="Result Sets" value={reports.length} detail="Generated assessments" tone="cyan" />
        <MetricCard icon={AlertTriangle} label="High Risk" value={highRiskCount} detail="Critical or high exposure" tone={highRiskCount ? "high" : "low"} />
        <MetricCard icon={ShieldCheck} label="Medium Risk" value={mediumRiskCount} detail="Needs follow-up" tone={mediumRiskCount ? "medium" : "muted"} />
        <MetricCard icon={FileClock} label="Avg Confidence" value={formatPercent(averageConfidence)} detail="Across visible reports" tone="muted" />
      </section>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Report History</CardTitle>
          <FileClock className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-3">
          {reportsQuery.isLoading && <Skeleton className="h-32 w-full" />}
          {reportsQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(reportsQuery.error)}</p>}
          {!reportsQuery.isLoading && reports.length === 0 && (
            <EmptyState icon={FileClock} title="No reports found" copy="Upload a document to start compliance analysis." />
          )}
          {reports.length > 0 && (
            <DataTable
              data={reports}
              columns={columns}
              getRowId={(report) => report.id}
              searchPlaceholder="Search summaries or assessment IDs"
              exportFilename="admin-compliance-results.csv"
              filters={[
                { id: "completed", label: "Completed", predicate: (report) => (report.audit_status ?? "completed") === "completed" },
                { id: "high", label: "High risk", predicate: (report) => report.overall_risk === "HIGH" },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
