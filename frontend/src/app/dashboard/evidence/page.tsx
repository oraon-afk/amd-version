"use client";

import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { BookOpenText, FileSearch, FolderUp } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getEvidence, listAudits } from "@/features/audits/api";
import { listDocuments } from "@/features/uploads/api";
import { frontendConfig } from "@/lib/config";
import { formatDate, formatPercent } from "@/lib/utils";

export default function EvidencePage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });

  const completedAudits = useMemo(
    () => (auditsQuery.data ?? []).filter((a) => a.status === "completed" || a.status === "pending_review"),
    [auditsQuery.data],
  );

  const evidenceQueries = useQueries({
    queries: completedAudits.map((audit) => ({
      queryKey: ["evidence", audit.id],
      queryFn: () => getEvidence(audit.id),
      staleTime: frontendConfig.queryStaleTimeMs,
      gcTime: frontendConfig.queryGcTimeMs,
    })),
  });

  const allEvidence = useMemo(() => {
    const documentsById = new Map((documentsQuery.data ?? []).map((d) => [d.id, d]));
    return completedAudits.flatMap((audit, i) => {
      const evidence = evidenceQueries[i]?.data ?? [];
      const document = documentsById.get(audit.document_id);
      return evidence.map((e) => ({ ...e, audit, document }));
    });
  }, [completedAudits, evidenceQueries, documentsQuery.data]);

  const loading = auditsQuery.isLoading || documentsQuery.isLoading || evidenceQueries.some((q) => q.isLoading);
  const error = auditsQuery.error ?? documentsQuery.error ?? evidenceQueries.find((q) => q.error)?.error;

  const uniqueDocumentCount = new Set(allEvidence.map((e) => e.audit.document_id)).size;
  const highConfidenceCount = allEvidence.filter((e) => (e.confidence_score ?? 0) >= 0.8).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance Intelligence"
        title="Evidence Library"
        description="All evidence snippets gathered from your compliance audits — source citations, page numbers, sections, and confidence scores."
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
      <section className="grid gap-4 md:grid-cols-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-28 w-full" />)
        ) : (
          <>
            <MetricCard icon={BookOpenText} label="Total Evidence" value={allEvidence.length} detail="Citations across all audits" tone="cyan" />
            <MetricCard icon={FileSearch} label="Audited Documents" value={uniqueDocumentCount} detail="Documents with evidence" tone="muted" />
            <MetricCard icon={BookOpenText} label="High Confidence" value={highConfidenceCount} detail="Evidence with ≥80% confidence" tone="low" />
          </>
        )}
      </section>

      {/* Evidence Cards */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>Evidence Citations</CardTitle>
          <Badge variant="cyan">{allEvidence.length} evidence items</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading && <Skeleton className="h-64 w-full" />}
          {!loading && allEvidence.length === 0 && (
            <EmptyState
              icon={FileSearch}
              title="No evidence collected yet"
              copy="Complete a compliance audit to see evidence citations here."
              action={
                <Link href="/dashboard/upload">
                  <Button size="sm">Upload Document</Button>
                </Link>
              }
            />
          )}
          {!loading && allEvidence.map((ev) => (
            <article
              key={ev.id}
              className="rounded-lg border border-line bg-white/5 p-4 transition hover:-translate-y-0.5 hover:border-violet/35 hover:shadow-[0_16px_32px_rgba(124,77,255,0.1)]"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold uppercase text-muted">Document Section</div>
                  <h3 className="mt-1 break-words text-sm font-semibold">
                    {ev.section_title ?? ev.citation_label ?? "Section not returned"}
                  </h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {ev.page_number != null && (
                    <Badge variant="muted">Page {ev.page_number}</Badge>
                  )}
                  <Badge variant="muted">{(ev.source_type ?? "unknown").replaceAll("_", " ")}</Badge>
                  {ev.confidence_score != null && (
                    <Badge variant="cyan">{formatPercent(ev.confidence_score)}</Badge>
                  )}
                </div>
              </div>

              {ev.citation_text && (
                <p className="mt-3 rounded border border-line bg-black/20 p-3 text-xs leading-6 text-foreground/80">
                  {ev.citation_text}
                </p>
              )}

              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                <div className="flex items-center gap-3">
                  <span className="font-medium text-foreground">
                    {ev.document?.title ?? ev.audit.document_id}
                  </span>
                  {ev.document?.domain && <span>· {ev.document.domain}</span>}
                  <span>· {formatDate(ev.audit.created_at)}</span>
                </div>
                <Link href={`/dashboard/reports/${ev.audit.id}`}>
                  <Button size="sm" variant="secondary">Open Report</Button>
                </Link>
              </div>
            </article>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

