"use client";

import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { AlertTriangle, FileSearch, FolderUp, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge, riskVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getFindings, listAudits } from "@/features/audits/api";
import { listDocuments } from "@/features/uploads/api";
import { frontendConfig } from "@/lib/config";
import { formatDate, formatPercent } from "@/lib/utils";

export default function FindingsPage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });

  const completedAudits = useMemo(
    () => (auditsQuery.data ?? []).filter((a) => a.status === "completed" || a.status === "pending_review"),
    [auditsQuery.data],
  );

  const findingsQueries = useQueries({
    queries: completedAudits.map((audit) => ({
      queryKey: ["findings", audit.id],
      queryFn: () => getFindings(audit.id),
      staleTime: frontendConfig.queryStaleTimeMs,
      gcTime: frontendConfig.queryGcTimeMs,
    })),
  });

  const allFindings = useMemo(() => {
    const documentsById = new Map((documentsQuery.data ?? []).map((d) => [d.id, d]));
    return completedAudits.flatMap((audit, i) => {
      const findings = findingsQueries[i]?.data ?? [];
      const document = documentsById.get(audit.document_id);
      return findings.map((f) => ({ ...f, audit, document }));
    });
  }, [completedAudits, findingsQueries, documentsQuery.data]);

  const loading = auditsQuery.isLoading || documentsQuery.isLoading || findingsQueries.some((q) => q.isLoading);
  const error = auditsQuery.error ?? documentsQuery.error ?? findingsQueries.find((q) => q.error)?.error;

  const criticalCount = allFindings.filter((f) => f.severity === "CRITICAL").length;
  const highCount = allFindings.filter((f) => f.severity === "HIGH").length;
  const mediumCount = allFindings.filter((f) => f.severity === "MEDIUM").length;
  const lowCount = allFindings.filter((f) => f.severity === "LOW").length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance Intelligence"
        title="Findings"
        description="All compliance violations detected across your audit runs, grouped by severity and risk level."
        actions={
          <Link href="/dashboard/upload">
            <Button variant="secondary">
              <FolderUp className="h-4 w-4" /> Upload Document
            </Button>
          </Link>
        }
      />

      {error && <ErrorState error={error} onRetry={() => { auditsQuery.refetch(); documentsQuery.refetch(); }} />}

      {/* KPI Cards */}
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : (
          <>
            <MetricCard icon={ShieldAlert} label="Critical" value={criticalCount} detail="CRITICAL severity findings" tone="high" />
            <MetricCard icon={AlertTriangle} label="High" value={highCount} detail="HIGH severity findings" tone="high" />
            <MetricCard icon={AlertTriangle} label="Medium" value={mediumCount} detail="MEDIUM severity findings" tone="cyan" />
            <MetricCard icon={ShieldAlert} label="Low" value={lowCount} detail="LOW severity findings" tone="muted" />
          </>
        )}
      </section>

      {/* Findings List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>All Findings</CardTitle>
          <Badge variant={allFindings.length ? "medium" : "low"}>{allFindings.length} findings</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading && <Skeleton className="h-64 w-full" />}
          {!loading && allFindings.length === 0 && (
            <EmptyState
              icon={FileSearch}
              title="No findings yet"
              copy="Run a compliance audit to see findings here."
              action={
                <Link href="/dashboard/upload">
                  <Button size="sm">Upload Document</Button>
                </Link>
              }
            />
          )}
          {!loading && allFindings.map((finding) => (
            <article
              key={finding.id}
              className="rounded-lg border border-line bg-white/5 p-4 transition hover:-translate-y-0.5 hover:border-violet/35 hover:shadow-[0_16px_32px_rgba(124,77,255,0.1)]"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold uppercase text-muted">Rule Violated</div>
                  <h3 className="mt-1 break-words text-sm font-semibold">
                    {finding.explanation ?? "No rule description returned"}
                  </h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant={riskVariant(finding.severity)}>{finding.severity ?? "N/A"}</Badge>
                  <Badge variant={riskVariant(finding.risk_level)}>{finding.risk_level ?? "N/A"}</Badge>
                  {finding.confidence_score != null && (
                    <Badge variant="cyan">{formatPercent(finding.confidence_score)}</Badge>
                  )}
                </div>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {finding.recommendation && (
                  <div>
                    <div className="mb-1 text-xs font-semibold uppercase text-muted">Recommendation</div>
                    <p className="rounded border border-line bg-black/15 p-3 text-xs leading-5">{finding.recommendation}</p>
                  </div>
                )}
                <div>
                  <div className="mb-1 text-xs font-semibold uppercase text-muted">Document</div>
                  <p className="rounded border border-line bg-black/15 p-3 text-xs leading-5">
                    {finding.document?.title ?? finding.audit.document_id}
                    <span className="ml-2 text-muted">· {finding.document?.domain ?? "Unknown domain"}</span>
                  </p>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                <span>{formatDate(finding.created_at)}</span>
                <div className="flex gap-2">
                  {finding.review_status && (
                    <Badge variant={finding.review_status === "reviewed" ? "low" : "medium"}>
                      {finding.review_status}
                    </Badge>
                  )}
                  <Link href={`/dashboard/reports/${finding.audit.id}`}>
                    <Button size="sm" variant="secondary">Open Report</Button>
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

