"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Database, FileText, ShieldAlert, Users, type LucideIcon } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getAdminAnalytics, getAuditLogs, getQdrantMonitoring } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { formatDate } from "@/lib/utils";

export default function AdminDashboardPage() {
  const analyticsQuery = useQuery({ queryKey: ["admin-analytics"], queryFn: getAdminAnalytics });
  const qdrantQuery = useQuery({ queryKey: ["admin-qdrant"], queryFn: getQdrantMonitoring });
  const logsQuery = useQuery({ queryKey: ["admin-logs"], queryFn: getAuditLogs });
  const analytics = analyticsQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Administration"
        title="Admin Dashboard"
        description="System health, audit activity, storage, and vector collection monitoring for the compliance workspace."
      />

      {(analyticsQuery.error || qdrantQuery.error || logsQuery.error) && (
        <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          {getErrorMessage(analyticsQuery.error ?? qdrantQuery.error ?? logsQuery.error)}
        </p>
      )}

      {analyticsQuery.isLoading && <Skeleton className="h-32 w-full" />}
      {analytics && (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric icon={Users} label="Users" value={analytics.users} />
          <Metric icon={FileText} label="Uploaded Docs" value={analytics.uploaded_documents} />
          <Metric icon={Activity} label="Audit Runs" value={analytics.audits} />
          <Metric icon={ShieldAlert} label="High Risk" value={analytics.high_risk_audits} />
        </section>
      )}

      <section className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Vector Storage Health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {qdrantQuery.isLoading && <Skeleton className="h-24 w-full" />}
            {qdrantQuery.data && (
              <>
                <div className="rounded-lg border border-line bg-elevated p-4 text-sm">
                  <div className="flex items-center gap-2 font-semibold">
                    <Database className="h-4 w-4 text-info" /> Qdrant status: {qdrantQuery.data.status}
                  </div>
                  {qdrantQuery.data.error && <span className="ml-2 text-riskHigh">{qdrantQuery.data.error}</span>}
                </div>
                {qdrantQuery.data.collections.map((collection, index) => (
                  <div key={`${collection.name}-${index}`} className="rounded-lg border border-line bg-elevated p-4 text-sm">
                    <div className="font-semibold">{collection.name}</div>
                    <div className="mt-1 text-muted">
                      Points: {collection.points_count ?? "-"} | Vectors: {collection.vectors_count ?? "-"}
                    </div>
                  </div>
                ))}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent System Logs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {logsQuery.isLoading && <Skeleton className="h-24 w-full" />}
            {logsQuery.data?.slice(0, 8).map((log) => (
              <div key={log.id} className="rounded-lg border border-line bg-elevated p-4 text-sm">
                <div className="font-semibold">{log.action}</div>
                <div className="mt-1 text-xs text-muted">{log.entity_type ?? "system"} - {formatDate(log.created_at)}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: number | null }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div>
          <div className="text-xs uppercase text-muted">{label}</div>
          <div className="mt-2 text-2xl font-semibold">{value ?? "Unavailable"}</div>
        </div>
        <Icon className="h-6 w-6 text-cyan" />
      </CardContent>
    </Card>
  );
}
