"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, FileText, ShieldAlert, Users, type LucideIcon } from "lucide-react";
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
      <div>
        <h1 className="text-2xl font-semibold">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-muted">System overview, audit activity, storage, and vector collection health.</p>
      </div>

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
            <CardTitle>Qdrant Collection Monitoring</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {qdrantQuery.isLoading && <Skeleton className="h-24 w-full" />}
            {qdrantQuery.data && (
              <>
                <div className="rounded-lg border border-line bg-white/5 p-3 text-sm">
                  Status: <span className="font-semibold">{qdrantQuery.data.status}</span>
                  {qdrantQuery.data.error && <span className="ml-2 text-riskHigh">{qdrantQuery.data.error}</span>}
                </div>
                {qdrantQuery.data.collections.map((collection) => (
                  <div key={collection.name} className="rounded-lg border border-line bg-white/5 p-3 text-sm">
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
              <div key={log.id} className="rounded-lg border border-line bg-white/5 p-3 text-sm">
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

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div>
          <div className="text-xs uppercase text-muted">{label}</div>
          <div className="mt-2 text-2xl font-semibold">{value}</div>
        </div>
        <Icon className="h-6 w-6 text-cyan" />
      </CardContent>
    </Card>
  );
}
