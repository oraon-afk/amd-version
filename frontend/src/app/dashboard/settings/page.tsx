"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, Database, LogOut, Mail, ServerCog, ShieldCheck, UserRound, type LucideIcon } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient, getErrorMessage } from "@/services/api/client";
import { useAuth } from "@/providers/auth-provider";

type HealthConfig = {
  app_env: string;
  debug: boolean;
  database_configured: boolean;
  qdrant_configured: boolean;
  qdrant_url_valid: boolean;
  s3_rule_bucket_configured: boolean;
  s3_temp_bucket_configured: boolean;
  s3_report_bucket_configured: boolean;
  llm_provider?: string;
  llm_configured?: boolean;
  openrouter_configured?: boolean;
  cors_origins_count: number;
  jwt_configured: boolean;
};

export default function DashboardSettingsPage() {
  const { user, logout } = useAuth();
  const configQuery = useQuery({
    queryKey: ["health-config"],
    queryFn: async () => {
      const { data } = await apiClient.get<HealthConfig>("/health/config");
      return data;
    },
  });

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Administration" title="Settings" description="Account context, security posture, preferences, and live backend configuration." />
      <div className="flex gap-2 overflow-x-auto border-b border-line pb-3 text-sm">
        {["Profile", "Security", "Notifications", "Integrations", "Preferences"].map((tab, index) => (
          <span key={tab} className={`shrink-0 rounded-lg border px-3 py-2 ${index === 0 ? "border-info/40 bg-primary/20 text-foreground" : "border-line bg-elevated text-muted"}`}>
            {tab}
          </span>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-5 flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-primary text-2xl font-bold shadow-glow">
                {(user?.full_name ?? user?.email ?? "A").slice(0, 1).toUpperCase()}
              </div>
              <div className="min-w-0">
                <div className="truncate text-lg font-semibold">{user?.full_name ?? user?.email ?? "User"}</div>
                <div className="text-sm text-muted">{user?.role ?? "Authenticated user"}</div>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              <Info icon={Mail} label="Email" value={user?.email ?? "Not returned"} />
              <Info icon={Building2} label="Company" value="Not returned by backend" />
              <Info icon={ShieldCheck} label="Access" value={user?.is_active ? "Active JWT session" : "Inactive"} />
              <Info icon={UserRound} label="Role" value={user?.role ?? "Not returned"} />
            </div>
            <Button onClick={logout} variant="destructive" className="mt-6 w-full">
              <LogOut className="h-4 w-4" /> Logout
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Backend Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {configQuery.isLoading && <Skeleton className="h-40 w-full" />}
            {configQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(configQuery.error)}</p>}
            {configQuery.data && (
              <>
                <Info icon={ServerCog} label="Environment" value={configQuery.data.app_env} />
                <Info icon={Database} label="Database" value={configQuery.data.database_configured ? "Configured" : "Not configured"} />
                <Info icon={ServerCog} label="Vector Store" value={configQuery.data.qdrant_configured && configQuery.data.qdrant_url_valid ? "Configured" : "Needs attention"} />
                <Info icon={ServerCog} label="S3 Buckets" value={configQuery.data.s3_temp_bucket_configured && configQuery.data.s3_rule_bucket_configured && configQuery.data.s3_report_bucket_configured ? "Configured" : "Needs attention"} />
                <Info icon={ServerCog} label="LLM Provider" value={configQuery.data.llm_provider ?? "Not returned"} />
                <Info icon={ServerCog} label="LLM Status" value={configQuery.data.llm_configured ? "Configured" : "Needs attention"} />
                <Info icon={ShieldCheck} label="JWT" value={configQuery.data.jwt_configured ? "Configured" : "Needs attention"} />
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Info({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-elevated p-3">
      <Icon className="h-4 w-4 text-info" />
      <div>
        <div className="text-xs uppercase text-muted">{label}</div>
        <div>{value}</div>
      </div>
    </div>
  );
}
