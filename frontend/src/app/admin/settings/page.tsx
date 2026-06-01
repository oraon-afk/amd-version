"use client";

import { useQuery } from "@tanstack/react-query";
import { Database, HardDrive, ScrollText, ServerCog, type LucideIcon } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getAuditLogs, getQdrantMonitoring, getStorageMonitoring } from "@/services/admin/admin-service";
import { apiClient, getErrorMessage } from "@/services/api/client";
import { formatDate } from "@/lib/utils";

type HealthConfig = {
  app_env: string;
  database_configured: boolean;
  qdrant_configured: boolean;
  llm_provider?: string;
  llm_configured?: boolean;
  jwt_configured: boolean;
  storage_root?: string;
  temp_retention_hours?: number;
};

export default function AdminSettingsPage() {
  const configQuery = useQuery({
    queryKey: ["health-config"],
    queryFn: async () => {
      const { data } = await apiClient.get<HealthConfig>("/health/config");
      return data;
    },
  });
  const storageQuery = useQuery({ queryKey: ["admin-storage"], queryFn: getStorageMonitoring });
  const qdrantQuery = useQuery({ queryKey: ["admin-qdrant"], queryFn: getQdrantMonitoring });
  const logsQuery = useQuery({ queryKey: ["admin-logs"], queryFn: getAuditLogs });

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Administration" title="Settings" description="Backend configuration, security posture, system logs, and infrastructure status." />
      <div className="flex gap-2 overflow-x-auto border-b border-line pb-3 text-sm">
        {["Profile", "Security", "Notifications", "Integrations", "Preferences"].map((tab, index) => (
          <span key={tab} className={`shrink-0 rounded-lg border px-3 py-2 ${index === 3 ? "border-info/40 bg-primary/20 text-foreground" : "border-line bg-elevated text-muted"}`}>
            {tab}
          </span>
        ))}
      </div>
      {(configQuery.error || storageQuery.error || qdrantQuery.error || logsQuery.error) && (
        <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          {getErrorMessage(configQuery.error ?? storageQuery.error ?? qdrantQuery.error ?? logsQuery.error)}
        </p>
      )}
      <section className="grid gap-5 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Backend</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {configQuery.isLoading && <Skeleton className="h-28 w-full" />}
            {configQuery.data && (
              <>
                <Info icon={ServerCog} label="Environment" value={configQuery.data.app_env} />
                <Info icon={Database} label="Database" value={configQuery.data.database_configured ? "Configured" : "Needs attention"} />
                <Info icon={ServerCog} label="LLM" value={`${configQuery.data.llm_provider ?? "unknown"} ${configQuery.data.llm_configured ? "ready" : "needs attention"}`} />
                <Info icon={ServerCog} label="JWT" value={configQuery.data.jwt_configured ? "Configured" : "Needs attention"} />
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Storage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {storageQuery.isLoading && <Skeleton className="h-28 w-full" />}
            {storageQuery.data && (
              <>
                <Info icon={HardDrive} label="Root" value={storageQuery.data.root} />
                <Info icon={HardDrive} label="Temp TTL" value={`${storageQuery.data.retention_hours} hours`} />
                {Object.entries(storageQuery.data.areas).map(([area, stats]) => (
                  <Info key={area} icon={HardDrive} label={area} value={`${stats.files} files`} />
                ))}
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Qdrant</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {qdrantQuery.isLoading && <Skeleton className="h-28 w-full" />}
            {qdrantQuery.data && (
              <>
                <Info icon={Database} label="Status" value={qdrantQuery.data.status} />
                <Info icon={Database} label="Rules" value={qdrantQuery.data.rule_collection} />
                <Info icon={Database} label="Uploads" value={qdrantQuery.data.upload_collection} />
              </>
            )}
          </CardContent>
        </Card>
      </section>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>System Logs</CardTitle>
          <ScrollText className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-3">
          {logsQuery.isLoading && <Skeleton className="h-32 w-full" />}
          {logsQuery.data?.map((log) => (
            <div key={log.id} className="rounded-lg border border-line bg-elevated p-3 text-sm">
              <div className="font-semibold">{log.action}</div>
              <div className="mt-1 text-xs text-muted">{log.entity_type ?? "system"} - {formatDate(log.created_at)}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function Info({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-elevated p-3">
      <Icon className="h-4 w-4 text-info" />
      <div className="min-w-0">
        <div className="text-xs uppercase text-muted">{label}</div>
        <div className="truncate">{value}</div>
      </div>
    </div>
  );
}
