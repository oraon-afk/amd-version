"use client";

import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, HardDrive } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { getAdminAnalytics, getStorageMonitoring } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { AdminAnalytics, StorageAreaStats, StorageMonitoring } from "@/types/api";

type MappedAnalytics = {
  users: number | null;
  uploaded_documents: number | null;
  rule_documents: number | null;
  audits: number | null;
  completed_audits: number | null;
  failed_audits: number | null;
  high_risk_audits: number | null;
  storage: Record<string, StorageAreaStats>;
  warnings: string[];
};

type MappedStorage = {
  enabled: boolean | null;
  status: string | null;
  root: string | null;
  bucket: string | null;
  buckets: Record<string, string | null>;
  retention_hours: number | null;
  areas: Record<string, StorageAreaStats>;
  warnings: string[];
};

export default function AdminAnalyticsPage() {
  const analyticsQuery = useQuery({ queryKey: ["admin-analytics"], queryFn: getAdminAnalytics });
  const storageQuery = useQuery({ queryKey: ["admin-storage"], queryFn: getStorageMonitoring });
  const analytics = analyticsQuery.data;
  const mappedAnalytics = useMemo(() => mapAnalyticsResponse(analytics), [analytics]);
  const mappedStorage = useMemo(
    () => mapStorageResponse(storageQuery.data, mappedAnalytics),
    [mappedAnalytics, storageQuery.data],
  );
  const renderedState = useMemo(
    () => ({
      analytics_available: Boolean(mappedAnalytics),
      storage_status: mappedStorage.status,
      storage_area_count: Object.keys(mappedStorage.areas).length,
      warnings: [...(mappedAnalytics?.warnings ?? []), ...mappedStorage.warnings],
      metrics: mappedAnalytics
        ? {
            users: mappedAnalytics.users,
            uploaded_documents: mappedAnalytics.uploaded_documents,
            rule_documents: mappedAnalytics.rule_documents,
            audits: mappedAnalytics.audits,
            completed_audits: mappedAnalytics.completed_audits,
            failed_audits: mappedAnalytics.failed_audits,
            high_risk_audits: mappedAnalytics.high_risk_audits,
          }
        : null,
    }),
    [mappedAnalytics, mappedStorage],
  );

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    console.debug("ANALYTICS_RAW_RESPONSE", {
      analytics,
      storage: storageQuery.data,
    });
    console.debug("ANALYTICS_MAPPED_RESPONSE", {
      analytics: mappedAnalytics,
      storage: mappedStorage,
    });
    console.debug("ANALYTICS_RENDERED_STATE", renderedState);
  }, [analytics, mappedAnalytics, mappedStorage, renderedState, storageQuery.data]);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Analytics"
        title="Executive Analytics"
        description="Operational trends, audit reliability, policy coverage, and storage usage for compliance leadership."
      />
      {analyticsQuery.error && (
        <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          {getErrorMessage(analyticsQuery.error)}
        </p>
      )}
      {analyticsQuery.isLoading && <Skeleton className="h-32 w-full" />}
      {mappedAnalytics && (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Metric label="Users" value={mappedAnalytics.users} />
          <Metric label="Uploaded Documents" value={mappedAnalytics.uploaded_documents} />
          <Metric label="Rule Documents" value={mappedAnalytics.rule_documents} />
          <Metric label="Audit Runs" value={mappedAnalytics.audits} />
          <Metric label="Completed Audits" value={mappedAnalytics.completed_audits} />
          <Metric label="Failed Audits" value={mappedAnalytics.failed_audits} />
          <Metric label="High Risk Audits" value={mappedAnalytics.high_risk_audits} />
        </section>
      )}
      {mappedAnalytics && (
        <section className="grid gap-5 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Audit Volume</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <TrendBar label="Completed" value={mappedAnalytics.completed_audits} total={mappedAnalytics.audits} tone="bg-success" />
              <TrendBar label="Failed" value={mappedAnalytics.failed_audits} total={mappedAnalytics.audits} tone="bg-critical" />
              <TrendBar label="High Risk" value={mappedAnalytics.high_risk_audits} total={mappedAnalytics.audits} tone="bg-warning" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Document Inventory</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <TrendBar
                label="Rule documents"
                value={mappedAnalytics.rule_documents}
                total={sumKnown(mappedAnalytics.uploaded_documents, mappedAnalytics.rule_documents)}
                tone="bg-info"
              />
              <TrendBar
                label="Uploaded documents"
                value={mappedAnalytics.uploaded_documents}
                total={sumKnown(mappedAnalytics.uploaded_documents, mappedAnalytics.rule_documents)}
                tone="bg-primary"
              />
              <div className="rounded-lg border border-line bg-elevated p-4 text-sm text-muted">
                Total users: <span className="font-semibold text-foreground">{formatCount(mappedAnalytics.users)}</span>
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
          {storageQuery.error && (
            <p className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
              Storage metrics unavailable. Analytics above are still available.
            </p>
          )}
          <div className="rounded-lg border border-line bg-elevated p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="font-semibold">Status</span>
              <span className="text-muted">{mappedStorage.status ?? "Unavailable"}</span>
            </div>
            {Object.keys(mappedStorage.buckets).length > 0 && (
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                {Object.entries(mappedStorage.buckets).map(([label, bucket]) => (
                  <div key={label} className="rounded-md border border-line bg-white/5 p-2">
                    <div className="text-xs uppercase text-muted">{label.replaceAll("_", " ")}</div>
                    <div className="mt-1 truncate font-medium">{bucket ?? "Not configured"}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {[...(mappedAnalytics?.warnings ?? []), ...mappedStorage.warnings].map((warning) => (
            <p key={warning} className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
              {warning}
            </p>
          ))}
          {!storageQuery.isLoading && Object.entries(mappedStorage.areas).length === 0 && (
            <p className="rounded-lg border border-line bg-elevated p-3 text-sm text-muted">No storage metrics returned by backend.</p>
          )}
          {Object.entries(mappedStorage.areas).map(([area, stats]) => (
            <div key={area} className="rounded-lg border border-line bg-elevated p-4">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-semibold">{area}</span>
                <span className="text-muted">{formatCount(stats.files)} files | {formatBytes(stats.bytes)}</span>
              </div>
              {stats.bytes === null ? (
                <div className="mt-3 rounded-full border border-line bg-white/5 px-3 py-2 text-sm text-muted">Bytes unavailable</div>
              ) : (
                <Progress className="mt-3" value={Math.min(100, stats.bytes / 1024 / 1024)} />
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <div className="text-xs uppercase text-muted">{label}</div>
          <div className="mt-2 text-2xl font-semibold">{formatCount(value)}</div>
        </div>
        <BarChart3 className="h-6 w-6 text-cyan" />
      </CardContent>
    </Card>
  );
}

function TrendBar({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number | null;
  total: number | null;
  tone: string;
}) {
  const percent = percentage(value, total);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted">{formatCount(value)}{percent === null ? "" : ` (${percent}%)`}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate/40">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${percent ?? 0}%` }} />
      </div>
    </div>
  );
}

function mapAnalyticsResponse(analytics?: AdminAnalytics): MappedAnalytics | null {
  if (!analytics) return null;
  return {
    users: readNumber(analytics.users),
    uploaded_documents: readNumber(analytics.uploaded_documents),
    rule_documents: readNumber(analytics.rule_documents),
    audits: readNumber(analytics.audits),
    completed_audits: readNumber(analytics.completed_audits),
    failed_audits: readNumber(analytics.failed_audits),
    high_risk_audits: readNumber(analytics.high_risk_audits),
    storage: analytics.storage ?? {},
    warnings: Array.isArray(analytics.warnings) ? analytics.warnings : [],
  };
}

function mapStorageResponse(storage: StorageMonitoring | undefined, analytics: MappedAnalytics | null): MappedStorage {
  return {
    enabled: typeof storage?.enabled === "boolean" ? storage.enabled : null,
    status: typeof storage?.status === "string" ? storage.status : null,
    root: typeof storage?.root === "string" ? storage.root : null,
    bucket: storage?.bucket ?? null,
    buckets: storage?.buckets ?? {},
    retention_hours: readNumber(storage?.retention_hours),
    areas: storage?.areas ?? analytics?.storage ?? {},
    warnings: Array.isArray(storage?.warnings) ? storage.warnings : [],
  };
}

function readNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function sumKnown(...values: Array<number | null>) {
  let total = 0;
  for (const value of values) {
    if (value === null) return null;
    total += value;
  }
  return total;
}

function percentage(value: number | null, total: number | null) {
  if (value === null || total === null || total < 0) return null;
  if (total === 0) return 0;
  return Math.round((value / total) * 100);
}

function formatCount(value: number | null | undefined) {
  return value === null || value === undefined ? "Unavailable" : String(value);
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes === null || bytes === undefined) return "Unavailable";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
