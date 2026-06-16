"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  CheckCircle,
  Cloud,
  Database,
  Loader2,
  RefreshCw,
  Server,
  Zap,
  HardDrive,
  Cpu,
} from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { getDeploymentConfig, reloadDeployment } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";

const MODE_META: Record<
  string,
  { label: string; icon: React.ElementType; description: string; color: string }
> = {
  cloud: {
    label: "Cloud",
    icon: Cloud,
    description: "All services run on managed cloud infrastructure (AWS/GCP/Azure).",
    color: "text-cyan",
  },
  hybrid: {
    label: "Hybrid",
    icon: Server,
    description: "Some services run locally (e.g. Qdrant, embedder) while LLM and storage remain in the cloud.",
    color: "text-amber-400",
  },
  onprem: {
    label: "On-Premise",
    icon: HardDrive,
    description: "All services run on your own infrastructure. No data leaves your environment.",
    color: "text-emerald-400",
  },
};

const COMPONENT_META: Record<
  string,
  { label: string; icon: React.ElementType }
> = {
  vector_db: { label: "Vector DB (Qdrant)", icon: Database },
  storage: { label: "Object Storage", icon: HardDrive },
  embedding: { label: "Embedding Model", icon: Cpu },
  llm: { label: "LLM Provider", icon: Zap },
};

export default function DeploymentSettingsPage() {
  const { toast } = useToast();

  const configQuery = useQuery({
    queryKey: ["deployment-config"],
    queryFn: getDeploymentConfig,
    refetchOnWindowFocus: false,
  });

  const reloadMutation = useMutation({
    mutationFn: reloadDeployment,
    onSuccess: (data) => {
      configQuery.refetch();
      toast({
        title: "Deployment reloaded",
        description: `Reloaded: ${data.components_reloaded?.join(", ") || "all components"}`,
      });
    },
    onError: (error) =>
      toast({
        title: "Reload failed",
        description: getErrorMessage(error),
        variant: "error",
      }),
  });

  const config = configQuery.data;
  const modeMeta = MODE_META[config?.mode ?? "cloud"] ?? MODE_META.cloud;
  const ModeIcon = modeMeta.icon;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Infrastructure"
        title="Deployment Settings"
        description="View the current deployment mode and component configuration. Environment variables control the actual values."
      />

      {/* Mode Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ModeIcon className={`h-4 w-4 ${modeMeta.color}`} />
            Deployment Mode
          </CardTitle>
        </CardHeader>
        <CardContent>
          {configQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-xl ${
                    config?.mode === "onprem"
                      ? "bg-emerald-500/10"
                      : config?.mode === "hybrid"
                      ? "bg-amber-500/10"
                      : "bg-cyan/10"
                  }`}
                >
                  <ModeIcon className={`h-5 w-5 ${modeMeta.color}`} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {modeMeta.label} Mode
                  </p>
                  <p className="text-xs text-muted max-w-sm">
                    {modeMeta.description}
                  </p>
                </div>
              </div>

              <Button
                variant="secondary"
                disabled={reloadMutation.isPending}
                onClick={() => reloadMutation.mutate()}
                className="flex-shrink-0"
              >
                {reloadMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                Hot Reload
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Components Grid */}
      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(COMPONENT_META).map(([key, meta]) => {
          const ComponentIcon = meta.icon;
          const compData = config?.components?.[key as keyof typeof config.components];

          return (
            <Card key={key}>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <ComponentIcon className="h-4 w-4 text-cyan" />
                  {meta.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {configQuery.isLoading ? (
                  <Skeleton className="h-10 w-full" />
                ) : compData ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted">Type</span>
                      <Badge variant="cyan" className="font-mono text-xs">
                        {compData.type}
                      </Badge>
                    </div>
                    {"url" in compData && compData.url && (
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted flex-shrink-0">Endpoint</span>
                        <span className="text-xs font-mono text-foreground truncate max-w-[200px]">
                          {compData.url}
                        </span>
                      </div>
                    )}
                    {"model" in compData && compData.model && (
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted flex-shrink-0">Model</span>
                        <span className="text-xs font-mono text-foreground truncate max-w-[200px]">
                          {compData.model}
                        </span>
                      </div>
                    )}
                    {"endpoint" in compData && compData.endpoint && (
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted flex-shrink-0">Endpoint</span>
                        <span className="text-xs font-mono text-foreground truncate max-w-[200px]">
                          {compData.endpoint}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-1 text-xs text-emerald-400 mt-1">
                      <CheckCircle className="h-3 w-3" />
                      Configured
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-xs text-muted/60 py-2">
                    <ComponentIcon className="h-4 w-4" />
                    Not configured / using default
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Info box */}
      <Card className="border-line bg-elevated">
        <CardContent className="pt-4">
          <p className="text-xs text-muted leading-5">
            <strong className="text-foreground">How to change deployment mode:</strong>{" "}
            Set <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">DEPLOYMENT_MODE</code> to{" "}
            <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">cloud</code>,{" "}
            <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">hybrid</code>, or{" "}
            <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">onprem</code> in your{" "}
            <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">.env</code> file.
            Set <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">OLLAMA_URL</code>,{" "}
            <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">MINIO_ENDPOINT</code>, or{" "}
            <code className="font-mono text-xs bg-line px-1 py-0.5 rounded">LOCAL_QDRANT_URL</code>{" "}
            to route traffic to local services. Click{" "}
            <strong className="text-foreground">Hot Reload</strong> to apply changes without restarting the backend.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
