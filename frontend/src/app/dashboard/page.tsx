"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import Link from "next/link";
import { Activity, ClipboardList, FileText, FolderUp, Gauge, ShieldCheck, UploadCloud, type LucideIcon } from "lucide-react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge, riskVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getReport, listAudits } from "@/features/audits/api";
import { ProcessingStatus } from "@/features/audits/components/ProcessingStatus";
import { isAuditActive } from "@/features/audits/status";
import { listComplianceDomains, listDocuments } from "@/features/uploads/api";
import { UploadDropzone } from "@/features/uploads/components/UploadDropzone";
import { frontendConfig } from "@/lib/config";
import { formatDate, formatPercent, normalizeScore } from "@/lib/utils";

export default function DashboardPage() {
  const auditsQuery = useQuery({ queryKey: ["audits"], queryFn: listAudits });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const domainsQuery = useQuery({ queryKey: ["compliance-domains"], queryFn: listComplianceDomains });
  const audits = auditsQuery.data ?? [];
  const documents = documentsQuery.data ?? [];
  const domains = domainsQuery.data ?? [];
  const completedAudits = audits.filter((audit) => audit.status === "completed");
  const activeAudits = audits.filter((audit) => isAuditActive(audit.status));
  const failedAudits = audits.filter((audit) => audit.status === "failed");
  const latestAudit = audits[0] ?? null;
  const latestCompletedAudit = completedAudits[0] ?? null;
  const latestDocument = latestAudit
    ? documents.find((document) => document.id === latestAudit.document_id) ?? null
    : documents[0] ?? null;

  const latestReportQuery = useQuery({
    queryKey: ["report", latestCompletedAudit?.id, "dashboard-summary"],
    queryFn: () => getReport(latestCompletedAudit!.id),
    enabled: Boolean(latestCompletedAudit),
    staleTime: frontendConfig.queryStaleTimeMs,
  });

  const reportPayload = latestReportQuery.data?.report_payload ?? {};
  const complianceScore = readScore(
    reportPayload,
    "compliance_score",
    "complianceScore",
    "audit_score",
    "auditScore",
    "overall_score",
    "overallScore",
    "final_score",
    "finalScore",
    "score",
  );
  const findingCount = readNumber(reportPayload, "finding_count");
  const highRiskFindings = readRiskCount(readRecord(reportPayload, "risk_counts"));
  const recentResults = audits.filter((audit) => !isAuditActive(audit.status));
  const openRiskAssessments = audits.filter((audit) => audit.overall_risk === "HIGH" || audit.overall_risk === "MEDIUM");
  const error = auditsQuery.error ?? documentsQuery.error ?? domainsQuery.error ?? latestReportQuery.error;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Executive summary"
        title="Compliance Intelligence Dashboard"
        description="Organization health, active audits, policy coverage, risk exposure, and AI-generated compliance findings from the live backend."
        actions={
          <Link href="/dashboard/reports">
            <Button variant="secondary">
              <FileText className="h-4 w-4" /> Compliance Results
            </Button>
          </Link>
        }
      />

      {error && (
        <ErrorState
          error={error}
          onRetry={() => {
            auditsQuery.refetch();
            documentsQuery.refetch();
            latestReportQuery.refetch();
          }}
        />
      )}

      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">Executive Summary</h2>
          <p className="text-sm text-muted">The four signals leaders need within the first few seconds.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {auditsQuery.isLoading || documentsQuery.isLoading || domainsQuery.isLoading ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32 w-full" />)
        ) : (
          <>
            <motion.div initial={{ y: 18, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0, duration: 0.35 }}>
              <MetricCard
                icon={Gauge}
                label="Compliance Score"
                value={complianceScore === null ? "-" : formatPercent(complianceScore)}
                detail={latestCompletedAudit ? "Latest completed backend assessment" : "No completed result returned"}
                tone={complianceScore !== null && complianceScore >= 0.8 ? "low" : "cyan"}
              />
            </motion.div>
            <motion.div initial={{ y: 18, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.08, duration: 0.35 }}>
              <MetricCard icon={Activity} label="Active Audits" value={activeAudits.length} detail="Queued or processing now" tone="cyan" />
            </motion.div>
            <motion.div initial={{ y: 18, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.16, duration: 0.35 }}>
              <MetricCard icon={UploadCloud} label="Documents" value={documents.length} detail={`${failedAudits.length} failed assessment runs`} tone="muted" />
            </motion.div>
            <motion.div initial={{ y: 18, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.24, duration: 0.35 }}>
              <MetricCard icon={ShieldCheck} label="Critical Findings" value={highRiskFindings ?? "-"} detail="Critical or high-risk counts returned" tone={highRiskFindings ? "high" : "muted"} />
            </motion.div>
          </>
        )}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,0.9fr)_minmax(420px,1.1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Backend Signals</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <SignalRow label="Compliance domains" value={`${domains.length} returned`} />
            <SignalRow label="Completed audits" value={`${completedAudits.length} of ${audits.length}`} />
            <SignalRow label="Open risk assessments" value={String(openRiskAssessments.length)} />
            <div className="rounded-lg border border-line bg-elevated p-3 text-sm text-muted">
              Latest result: <span className="font-semibold text-foreground">{latestCompletedAudit ? formatDate(latestCompletedAudit.created_at) : "No completed audit yet"}</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <QuickAction href="/dashboard/upload" icon={FolderUp} label="Upload & Analyze" copy="Start a new document assessment." />
            <QuickAction href="/dashboard/reports" icon={FileText} label="Review Results" copy="Search findings and evidence." />
            <QuickAction href="/dashboard/audits" icon={ClipboardList} label="Track Runs" copy="Monitor queued and active reviews." />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(420px,1fr)]">
        <ProcessingStatus audit={latestAudit} document={latestDocument} />
        <UploadDropzone compact />
      </section>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>Recent Activity</CardTitle>
          <ShieldCheck className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-3">
          {(auditsQuery.isLoading || documentsQuery.isLoading) && <Skeleton className="h-32 w-full" />}
          {!auditsQuery.isLoading && recentResults.length === 0 && (
            <EmptyState
              icon={FolderUp}
              title="No audit results yet"
              copy="Completed and failed backend audit runs will appear here."
              action={
                <Link href="/dashboard/upload">
                  <Button size="sm">Upload Document</Button>
                </Link>
              }
            />
          )}
          {recentResults.map((audit, index) => {
            const document = documents.find((item) => item.id === audit.document_id);
            return (
              <motion.div
                key={audit.id}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.06, duration: 0.35 }}
                className="rounded-lg border border-line bg-white/5 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-violet/35 hover:bg-white/7 hover:shadow-[0_16px_32px_rgba(124,77,255,0.1)]"
              >
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
                      <Button size="sm" variant="secondary">Open Results</Button>
                    </Link>
                  ) : (
                    <span className="text-riskHigh">{audit.error_message ?? "Audit did not complete."}</span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}

function QuickAction({
  href,
  icon: Icon,
  label,
  copy,
}: {
  href: string;
  icon: LucideIcon;
  label: string;
  copy: string;
}) {
  return (
    <Link href={href} className="group rounded-lg border border-line bg-white/5 p-4 transition hover:border-violet/40 hover:bg-violet/10 hover:shadow-[0_12px_24px_rgba(124,77,255,0.1)]">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-cyan/30 bg-cyan/10 text-cyan">
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-sm font-semibold group-hover:text-cyan">{label}</div>
      <div className="mt-1 text-xs leading-5 text-muted">{copy}</div>
    </Link>
  );
}

function SignalRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-elevated p-3">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <span className="font-semibold text-foreground">{value}</span>
      </div>
    </div>
  );
}

function readNumber(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    const parsed = Number(trimmed.endsWith("%") ? trimmed.slice(0, -1) : trimmed);
    if (Number.isFinite(parsed)) return trimmed.endsWith("%") ? parsed / 100 : parsed;
  }
  return null;
}

function readScore(payload: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const score = normalizeScore(readNumber(payload, key));
    if (score !== null) return score;
  }
  return null;
}

function readRecord(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function readRiskCount(riskCounts: Record<string, unknown>) {
  const directCritical = riskCounts.CRITICAL ?? riskCounts.critical;
  const high = riskCounts.HIGH ?? riskCounts.high;
  const value = directCritical ?? high;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
