"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart3, HardDrive } from "lucide-react";
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
      <div>
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="mt-1 text-sm text-muted">Operational metrics and storage usage.</p>
      </div>
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
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Storage Monitoring</CardTitle>
          <HardDrive className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-3">
          {storageQuery.isLoading && <Skeleton className="h-24 w-full" />}
          {storageQuery.data && Object.entries(storageQuery.data.areas).map(([area, stats]) => (
            <div key={area} className="rounded-lg border border-line bg-white/5 p-4">
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

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
