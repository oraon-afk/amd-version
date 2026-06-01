"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart3, HardDrive } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { getAdminAnalytics, getStorageMonitoring } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";

export default function AdminAnalyticsPage() {
  const analyticsQuery = useQuery({ queryKey: ["admin-analytics"], queryFn: getAdminAnalytics });
  const storageQuery = useQuery({ queryKey: ["admin-storage"], queryFn: getStorageMonitoring });
  const analytics = analyticsQuery.data;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Analytics"
        title="Executive Analytics"
        description="Operational trends, audit reliability, policy coverage, and storage usage for compliance leadership."
      />
      {(analyticsQuery.error || storageQuery.error) && (
        <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          {getErrorMessage(analyticsQuery.error ?? storageQuery.error)}
        </p>
      )}
      {analyticsQuery.isLoading && <Skeleton className="h-32 w-full" />}
      {analytics && (
        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="Completion Rate" value={analytics.audits ? Math.round((analytics.completed_audits / analytics.audits) * 100) : 0} suffix="%" />
          <Metric label="Failure Count" value={analytics.failed_audits} />
          <Metric label="Rule Coverage Docs" value={analytics.rule_documents} />
        </section>
      )}
      {analytics && (
        <section className="grid gap-5 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Audit Volume</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <TrendBar label="Completed" value={analytics.completed_audits} total={Math.max(analytics.audits, 1)} tone="bg-success" />
              <TrendBar label="Failed" value={analytics.failed_audits} total={Math.max(analytics.audits, 1)} tone="bg-critical" />
              <TrendBar label="High Risk" value={analytics.high_risk_audits} total={Math.max(analytics.audits, 1)} tone="bg-warning" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Policy Coverage</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <TrendBar label="Rule documents" value={analytics.rule_documents} total={Math.max(analytics.uploaded_documents + analytics.rule_documents, 1)} tone="bg-info" />
              <TrendBar label="Uploaded documents" value={analytics.uploaded_documents} total={Math.max(analytics.uploaded_documents + analytics.rule_documents, 1)} tone="bg-primary" />
              <div className="rounded-lg border border-line bg-elevated p-4 text-sm text-muted">
                Total users: <span className="font-semibold text-foreground">{analytics.users}</span>
              </div>
            </CardContent>
          </Card>
        </section>
      )}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Storage Monitoring</CardTitle>
          <HardDrive className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-3">
          {storageQuery.isLoading && <Skeleton className="h-24 w-full" />}
          {storageQuery.data && Object.entries(storageQuery.data.areas).map(([area, stats]) => (
            <div key={area} className="rounded-lg border border-line bg-elevated p-4">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-semibold">{area}</span>
                <span className="text-muted">{stats.files} files | {formatBytes(stats.bytes)}</span>
              </div>
              <Progress className="mt-3" value={Math.min(100, stats.bytes / 1024 / 1024)} />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <div className="text-xs uppercase text-muted">{label}</div>
          <div className="mt-2 text-2xl font-semibold">{value}{suffix}</div>
        </div>
        <BarChart3 className="h-6 w-6 text-cyan" />
      </CardContent>
    </Card>
  );
}

function TrendBar({ label, value, total, tone }: { label: string; value: number; total: number; tone: string }) {
  const percent = Math.round((value / total) * 100);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted">{value} ({percent}%)</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate/40">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(100, percent)}%` }} />
      </div>
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
