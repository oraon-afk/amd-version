"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { FileText, FolderUp, ShieldCheck } from "lucide-react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Badge, riskVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listAudits } from "@/features/audits/api";
import { ProcessingStatus } from "@/features/audits/components/ProcessingStatus";
import { listDocuments } from "@/features/uploads/api";
import { UploadDropzone } from "@/features/uploads/components/UploadDropzone";
import { isAuditActive } from "@/features/audits/status";
import { formatDate, formatPercent } from "@/lib/utils";
import { getErrorMessage } from "@/services/api/client";

export default function DashboardPage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const audits = auditsQuery.data ?? [];
  const documents = documentsQuery.data ?? [];
  const latestAudit = audits[0] ?? null;
  const latestDocument = latestAudit
    ? documents.find((document) => document.id === latestAudit.document_id) ?? null
    : documents[0] ?? null;
  const recentResults = audits.filter((audit) => !isAuditActive(audit.status));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">AI Audit Workspace</h1>
          <p className="mt-1 text-sm text-muted">Upload a document, run the backend audit workflow, and review generated reports.</p>
        </div>
        <Link href="/dashboard/reports">
          <Button variant="secondary">
            <FileText className="h-4 w-4" /> Audit Reports
          </Button>
        </Link>
      </div>

      {(auditsQuery.error || documentsQuery.error) && (
        <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          {getErrorMessage(auditsQuery.error ?? documentsQuery.error)}
        </p>
      )}

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]">
        <UploadDropzone />
        <ProcessingStatus audit={latestAudit} document={latestDocument} />
      </section>

      <section>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>Recent Audit Results</CardTitle>
            <ShieldCheck className="h-5 w-5 text-cyan" />
          </CardHeader>
          <CardContent className="space-y-3">
            {(auditsQuery.isLoading || documentsQuery.isLoading) && <Skeleton className="h-32 w-full" />}
            {!auditsQuery.isLoading && recentResults.length === 0 && (
              <EmptyState
                icon={FolderUp}
                title="No audit results yet"
                copy="Completed and failed backend audit runs will appear here."
              />
            )}
            {recentResults.map((audit) => {
              const document = documents.find((item) => item.id === audit.document_id);
              return (
                <div key={audit.id} className="rounded-lg border border-line bg-white/5 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold">{document?.title ?? audit.id}</div>
                      <div className="mt-1 text-xs text-muted">
                        {document?.domain ?? "Domain not returned"} - {formatDate(audit.created_at)}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={audit.status === "failed" ? "high" : "cyan"}>{audit.status}</Badge>
                      <Badge variant={riskVariant(audit.overall_risk)}>{audit.overall_risk ?? "Risk not returned"}</Badge>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
                    <span className="text-muted">Analysis confidence: {formatPercent(audit.confidence_score)}</span>
                    {audit.status === "completed" ? (
                      <Link href={`/dashboard/reports/${audit.id}`}>
                        <Button size="sm" variant="secondary">Open Report</Button>
                      </Link>
                    ) : (
                      <span className="text-riskHigh">{audit.error_message ?? "Audit did not complete."}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
