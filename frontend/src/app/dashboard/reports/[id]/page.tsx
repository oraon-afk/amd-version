"use client";

import { useEffect, useMemo, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams, usePathname, useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BookOpenText,
  ChevronDown,
  ClipboardCheck,
  Copy,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Gauge,
  ListChecks,
  type LucideIcon,
  ShieldAlert,
  ShieldCheck,
  Target,
} from "lucide-react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { RiskBadge, StatusBadge } from "@/components/enterprise/StatusBadge";
import { Badge, riskVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import {
  downloadReportJson,
  downloadReportPdf,
  getAudit,
  getEvidence,
  getFindings,
  getReport,
} from "@/features/audits/api";
import { ProcessingStatus } from "@/features/audits/components/ProcessingStatus";
import { isAuditActive } from "@/features/audits/status";
import { listDocuments } from "@/features/uploads/api";
import { cn, formatDate, formatPercent } from "@/lib/utils";
import { listAdminDocuments } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { AuditReport, Evidence, Finding, ReportFindingPayload, ScoreDiagnostics } from "@/types/api";

type RiskCounts = {
  critical: number;
  high: number;
  medium: number;
  low: number;
};

type FindingView = {
  id: string;
  finding?: Finding;
  payload: ReportFindingPayload;
  evidence: Evidence[];
  severity: string | null;
  ruleViolated: string;
  evidenceText: string;
  matchedPolicySection: string;
  impact: string;
  recommendation: string;
  confidence: number | null;
  sourcePage: number | null;
  documentSection: string;
  extractedText: string;
  matchedRule: string;
  violationReason: string;
};

type EvidenceCardData = {
  id: string;
  documentSection: string;
  extractedText: string;
  matchedRule: string;
  violationReason: string;
  sourcePage: number | null;
  confidence: number | null;
  sourceType: string;
};

const NOT_RETURNED = "Not returned by backend";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const auditId = params.id;
  const isAdminPath = pathname.startsWith("/admin");
  const reportsPath = isAdminPath ? "/admin/reports" : "/dashboard/reports";
  const { toast } = useToast();

  const auditQuery = useQuery({
    queryKey: ["audit", auditId],
    queryFn: () => getAudit(auditId),
    enabled: Boolean(auditId),
    refetchInterval: (query) => (isAuditActive(query.state.data?.status) ? 1500 : false),
  });
  const audit = auditQuery.data ?? null;
  const reportReady = audit?.status === "completed";
  const reportQuery = useQuery({
    queryKey: ["report", auditId],
    queryFn: () => getReport(auditId),
    enabled: Boolean(auditId) && reportReady,
    retry: false,
  });
  const findingsQuery = useQuery({
    queryKey: ["findings", auditId],
    queryFn: () => getFindings(auditId),
    enabled: Boolean(auditId) && reportReady,
  });
  const evidenceQuery = useQuery({
    queryKey: ["evidence", auditId],
    queryFn: () => getEvidence(auditId),
    enabled: Boolean(auditId) && reportReady,
  });
  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments, enabled: !isAdminPath });
  const adminDocumentsQuery = useQuery({ queryKey: ["admin-documents"], queryFn: listAdminDocuments, enabled: isAdminPath });

  const report = reportQuery.data ?? null;
  const findings = findingsQuery.data ?? [];
  const evidence = evidenceQuery.data ?? [];
  const documents = isAdminPath ? adminDocumentsQuery.data?.uploaded_documents ?? [] : documentsQuery.data ?? [];
  const document = documents.find((item) => item.id === audit?.document_id) ?? null;
  const reportFindings = useMemo(() => getReportFindings(report), [report]);
  const findingViews = useMemo(
    () => buildFindingViews(findings, evidence, reportFindings),
    [findings, evidence, reportFindings],
  );
  const riskCounts = useMemo(() => getRiskCounts(report, findingViews), [report, findingViews]);
  const complianceScore = getComplianceScore(report);
  const findingsCount = getFindingsCount(report, findingViews);
  const riskLevel = getRiskLevel(report, audit?.overall_risk, riskCounts);
  const confidence = getOverallConfidence(report, audit?.confidence_score, findingViews);
  const complianceStatus = getComplianceStatus(report, complianceScore, findingsCount);
  const aiSummary = getAiSummary(report);
  const keyRisks = getKeyRisks(findingViews);
  const recommendations = getRecommendations(report, findingViews);
  const scoreDiagnostics = getScoreDiagnostics(report);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development" || !report) return;

    const integrity = {
      compliance_score: complianceScore,
      findings: findingViews,
      summary: aiSummary,
      risk_level: riskLevel,
    };

    console.log("Report API Response", { response: report, integrity });
    if (
      integrity.compliance_score === null ||
      integrity.findings.length === 0 ||
      !integrity.summary ||
      !integrity.risk_level
    ) {
      console.warn("Report data integrity check", integrity);
    }
  }, [aiSummary, complianceScore, findingViews, report, riskLevel]);

  const jsonDownload = useMutation({
    mutationFn: () => downloadReportJson(auditId),
    onSuccess: (blob) => saveBlob(blob, `compliance-intelligence-${auditId}.json`),
    onError: (error) => toast({ title: "JSON download failed", description: getErrorMessage(error), variant: "error" }),
  });
  const pdfDownload = useMutation({
    mutationFn: () => downloadReportPdf(auditId),
    onSuccess: (blob) => saveBlob(blob, `compliance-intelligence-${auditId}.pdf`),
    onError: (error) => toast({ title: "PDF download failed", description: getErrorMessage(error), variant: "error" }),
  });

  const documentsLoading = isAdminPath ? adminDocumentsQuery.isLoading : documentsQuery.isLoading;
  const documentsError = isAdminPath ? adminDocumentsQuery.error : documentsQuery.error;
  const loading =
    auditQuery.isLoading ||
    documentsLoading ||
    (reportReady && (reportQuery.isLoading || findingsQuery.isLoading || evidenceQuery.isLoading));
  const error =
    auditQuery.error ??
    (reportReady ? reportQuery.error ?? findingsQuery.error ?? evidenceQuery.error : null) ??
    documentsError;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance results"
        title="Compliance Intelligence Report"
        description="Evidence-backed audit findings, policy matches, and remediation context from the backend analysis."
        actions={
          <>
            <Button type="button" variant="secondary" onClick={() => router.push(reportsPath)}>
              <ArrowLeft className="h-4 w-4" /> Compliance Results
            </Button>
            {report && (
              <ExportCenter
                auditId={auditId}
                findings={findingViews}
                evidence={evidence}
                onPdf={() => pdfDownload.mutate()}
                onJson={() => jsonDownload.mutate()}
                pdfPending={pdfDownload.isPending}
                jsonPending={jsonDownload.isPending}
              />
            )}
          </>
        }
      />

      {loading && <Skeleton className="h-72 w-full" />}
      {error && <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">{getErrorMessage(error)}</p>}
      {audit && isAuditActive(audit.status) && <ProcessingStatus audit={audit} document={document} isProcessing />}
      {audit?.status === "failed" && (
        <p className="flex gap-2 rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          <AlertCircle className="h-4 w-4 shrink-0" /> {audit.error_message ?? "Backend analysis failed before results were generated."}
        </p>
      )}
      {!loading && !error && (!audit || (!report && !isAuditActive(audit.status) && audit.status !== "failed")) && (
        <EmptyState icon={FileText} title="Results not available" copy="The backend has not returned compliance results for this assessment." />
      )}

      {audit && report && (
        <>
          <TopAuditMetrics
            score={complianceScore}
            riskLevel={riskLevel}
            findingsCount={findingsCount}
            confidence={confidence}
            auditStatus={audit.status}
          />

          <section className="grid gap-4 xl:grid-cols-[0.72fr_1.28fr]">
            <AssessmentContext auditId={auditId} report={report} documentTitle={document?.title} documentDomain={document?.domain} />
            <ExecutiveSummary
              complianceStatus={complianceStatus}
              complianceScore={complianceScore}
              riskCounts={riskCounts}
              keyRisks={keyRisks}
              aiSummary={aiSummary}
            />
          </section>

          <section className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
            <ComplianceScorePanel score={complianceScore} diagnostics={scoreDiagnostics} />
            <RiskBreakdown riskCounts={riskCounts} />
          </section>

          <EnterpriseFindingsSection findings={findingViews} onCopy={(view) => copyFindingBrief(view, toast)} />

          <EvidenceCards evidenceCards={buildEvidenceCards(findingViews)} onCopy={(card) => copyEvidenceCard(card, toast)} />

          <RecommendedActions recommendations={recommendations} />
        </>
      )}
    </div>
  );
}

function TopAuditMetrics({
  score,
  riskLevel,
  findingsCount,
  confidence,
  auditStatus,
}: {
  score: number | null;
  riskLevel: string | null;
  findingsCount: number;
  confidence: number | null;
  auditStatus: string;
}) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <MetricPanel icon={Gauge} label="Overall Compliance Score" value={formatScore(score)} tone={scoreTone(score)} />
      <MetricPanel
        icon={ShieldAlert}
        label="Risk Level"
        value={riskLevel ?? "Risk unavailable"}
        tone={riskLevelTone(riskLevel)}
        badge={<RiskBadge risk={riskLevel} />}
      />
      <MetricPanel icon={ListChecks} label="Findings Count" value={String(findingsCount)} tone={findingsCount ? "medium" : "low"} />
      <MetricPanel icon={Target} label="Confidence" value={formatConfidence(confidence)} tone="cyan" />
      <MetricPanel icon={ClipboardCheck} label="Audit Status" value={auditStatus} tone="low" badge={<StatusBadge status={auditStatus} />} />
    </section>
  );
}

function MetricPanel({
  icon: Icon,
  label,
  value,
  tone,
  badge,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone: "critical" | "high" | "medium" | "low" | "cyan" | "muted";
  badge?: ReactNode;
}) {
  const toneClasses = {
    critical: "border-critical/35 bg-critical/10 text-critical",
    high: "border-riskHigh/35 bg-riskHigh/10 text-riskHigh",
    medium: "border-riskMedium/35 bg-riskMedium/10 text-riskMedium",
    low: "border-riskLow/35 bg-riskLow/10 text-riskLow",
    cyan: "border-cyan/35 bg-cyan/10 text-cyan",
    muted: "border-line bg-white/5 text-muted",
  };

  return (
    <div className={cn("rounded-lg border p-4", toneClasses[tone])}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted">
          <Icon className="h-4 w-4" />
          {label}
        </div>
        {badge}
      </div>
      <div className="mt-4 min-h-8 break-words text-2xl font-semibold text-foreground">{value}</div>
    </div>
  );
}

function AssessmentContext({
  auditId,
  report,
  documentTitle,
  documentDomain,
}: {
  auditId: string;
  report: AuditReport;
  documentTitle?: string;
  documentDomain?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Assessment Context</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <ContextRow label="Audit ID" value={auditId} />
        <ContextRow label="Document" value={documentTitle ?? NOT_RETURNED} />
        <ContextRow label="Domain" value={documentDomain ?? NOT_RETURNED} />
        <ContextRow label="Report Status" value={report.status ?? getPayloadString(report, "status") ?? NOT_RETURNED} />
        <ContextRow label="Generated" value={formatDate(report.created_at)} />
      </CardContent>
    </Card>
  );
}

function ContextRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-line bg-white/5 p-3 text-sm">
      <span className="shrink-0 text-muted">{label}</span>
      <span className="min-w-0 break-words text-right font-medium text-foreground">{value}</span>
    </div>
  );
}

function ExecutiveSummary({
  complianceStatus,
  complianceScore,
  riskCounts,
  keyRisks,
  aiSummary,
}: {
  complianceStatus: string;
  complianceScore: number | null;
  riskCounts: RiskCounts;
  keyRisks: string[];
  aiSummary: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Executive Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <SummaryTile label="Compliance Status" value={complianceStatus} />
          <SummaryTile label="Overall Score" value={formatScore(complianceScore)} />
          <SummaryTile label="Critical Findings" value={String(riskCounts.critical)} />
          <SummaryTile label="High Findings" value={String(riskCounts.high)} />
          <SummaryTile label="Medium Findings" value={String(riskCounts.medium)} />
        </div>
        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="rounded-lg border border-line bg-white/5 p-4">
            <div className="mb-3 text-xs font-semibold uppercase text-muted">Key Risks</div>
            {keyRisks.length === 0 ? (
              <p className="text-sm text-muted">No key risks were returned by the backend.</p>
            ) : (
              <ul className="space-y-2 text-sm leading-6">
                {keyRisks.map((risk) => (
                  <li key={risk} className="flex gap-2">
                    <ShieldAlert className="mt-1 h-4 w-4 shrink-0 text-warning" />
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="rounded-lg border border-line bg-white/5 p-4">
            <div className="mb-3 text-xs font-semibold uppercase text-muted">AI Summary</div>
            <p className="text-sm leading-6 text-foreground">{aiSummary}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-black/15 p-3">
      <div className="text-xs font-semibold uppercase text-muted">{label}</div>
      <div className="mt-2 break-words text-lg font-semibold">{value}</div>
    </div>
  );
}

function ComplianceScorePanel({ score, diagnostics }: { score: number | null; diagnostics: ScoreDiagnostics | null }) {
  const progress = scoreToProgress(score);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Overall Compliance Score</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-5 md:flex-row md:items-center">
          <div className="grid h-32 w-32 shrink-0 place-items-center rounded-full border border-primary/35 bg-primary/10">
            <div className="px-2 text-center">
              <div className={cn("text-2xl font-semibold", score === null && "text-base leading-5")}>{formatScore(score)}</div>
              <div className="mt-1 text-xs font-semibold uppercase text-muted">{scorePosture(score)}</div>
            </div>
          </div>
          <div className="min-w-0 flex-1">
            {progress === null ? (
              <div className="rounded-full border border-line bg-white/5 px-3 py-2 text-sm text-muted">Score unavailable</div>
            ) : (
              <Progress value={progress} />
            )}
            <p className="mt-3 text-sm leading-6 text-muted">{diagnostics?.score_reasoning ?? "Score diagnostics were not returned for this report."}</p>
          </div>
        </div>
        {diagnostics && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryTile label="Rules Evaluated" value={String(diagnostics.rules_evaluated)} />
            <SummaryTile label="Rules Matched" value={String(diagnostics.rules_matched)} />
            <SummaryTile label="Rules Failed" value={String(diagnostics.rules_failed)} />
            <SummaryTile label="Match Confidence" value={formatConfidence(diagnostics.match_confidence)} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RiskBreakdown({ riskCounts }: { riskCounts: RiskCounts }) {
  const total = riskCounts.critical + riskCounts.high + riskCounts.medium + riskCounts.low;
  const rows = [
    { label: "Critical", value: riskCounts.critical, className: "bg-critical" },
    { label: "High", value: riskCounts.high, className: "bg-riskHigh" },
    { label: "Medium", value: riskCounts.medium, className: "bg-riskMedium" },
    { label: "Low", value: riskCounts.low, className: "bg-riskLow" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) => {
          const percent = total ? Math.round((row.value / total) * 100) : 0;
          return (
            <div key={row.label} className="rounded-lg border border-line bg-white/5 p-3">
              <div className="mb-2 flex items-center justify-between gap-3 text-sm">
                <span className="font-medium">{row.label}</span>
                <span className="text-muted">{row.value} findings</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/8">
                <div className={cn("h-full rounded-full", row.className)} style={{ width: `${percent}%` }} />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function EnterpriseFindingsSection({ findings, onCopy }: { findings: FindingView[]; onCopy: (finding: FindingView) => void }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Enterprise Findings</CardTitle>
        <Badge variant={findings.length ? "medium" : "low"}>{findings.length} findings</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        {findings.length === 0 && (
          <EmptyState icon={ShieldCheck} title="No findings returned" copy="The backend report and findings API did not return violations for this assessment." />
        )}
        {findings.map((finding) => (
          <FindingCard key={finding.id} finding={finding} onCopy={() => onCopy(finding)} />
        ))}
      </CardContent>
    </Card>
  );
}

function FindingCard({ finding, onCopy }: { finding: FindingView; onCopy: () => void }) {
  return (
    <article className="rounded-lg border border-line bg-white/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase text-muted">Rule Violated</div>
          <h3 className="mt-1 break-words text-base font-semibold">{finding.ruleViolated}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={riskVariant(finding.severity)}>{finding.severity ?? "Severity n/a"}</Badge>
          <Badge variant="cyan">{formatConfidence(finding.confidence)}</Badge>
          <Badge variant="muted">{formatPage(finding.sourcePage)}</Badge>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <DetailBlock label="Evidence Text" value={finding.evidenceText} />
        <DetailBlock label="Matched Policy Section" value={finding.matchedPolicySection} />
        <DetailBlock label="Impact" value={finding.impact} />
        <DetailBlock label="Recommendation" value={finding.recommendation} />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-black/15 p-3">
        <div className="text-sm">
          <div className="font-semibold">Finding Brief</div>
          <div className="text-xs text-muted">Copy the evidence-backed finding for remediation work.</div>
        </div>
        <Button type="button" size="sm" variant="secondary" onClick={onCopy}>
          <Copy className="h-4 w-4" /> Copy
        </Button>
      </div>

      <EvidenceViewer finding={finding} />
    </article>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase text-muted">{label}</div>
      <p className="min-h-20 rounded-lg border border-line bg-black/20 p-3 text-sm leading-6">{value}</p>
    </div>
  );
}

function EvidenceViewer({ finding }: { finding: FindingView }) {
  return (
    <details className="group mt-4 rounded-lg border border-line bg-black/20">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold">
        <span className="flex min-w-0 items-center gap-2">
          <BookOpenText className="h-4 w-4 shrink-0 text-info" />
          Expandable Evidence Viewer
        </span>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted transition group-open:rotate-180" />
      </summary>
      <div className="space-y-3 border-t border-line p-4">
        <EvidenceFact label="Document Section" value={finding.documentSection} />
        <EvidenceFact label="Highlighted Evidence" value={finding.extractedText} highlightWith={finding.matchedRule} />
        <EvidenceFact label="Matched Rule" value={finding.matchedRule} />
        <EvidenceFact label="Violation Reason" value={finding.violationReason} />
        {finding.evidence.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase text-muted">Source Citations</div>
            {finding.evidence.map((item) => (
              <div key={item.id} className="rounded-lg border border-line bg-white/5 p-3 text-sm leading-6">
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge variant="muted">{item.source_type.replaceAll("_", " ")}</Badge>
                  <Badge variant="muted">{item.section_title ?? item.citation_label ?? "Section not returned"}</Badge>
                  <Badge variant="muted">{formatPage(item.page_number)}</Badge>
                  <Badge variant="cyan">{formatConfidence(item.confidence_score)}</Badge>
                </div>
                <HighlightedText text={item.citation_text} termsFrom={finding.matchedRule} />
              </div>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

function EvidenceFact({ label, value, highlightWith }: { label: string; value: string; highlightWith?: string }) {
  return (
    <div className="rounded-lg border border-line bg-white/5 p-3">
      <div className="mb-1 text-xs font-semibold uppercase text-muted">{label}</div>
      {highlightWith ? (
        <HighlightedText text={value} termsFrom={highlightWith} />
      ) : (
        <p className="whitespace-pre-wrap text-sm leading-6">{value}</p>
      )}
    </div>
  );
}

function HighlightedText({ text, termsFrom }: { text: string; termsFrom: string }) {
  const terms = importantTerms(termsFrom);
  const parts = text.split(/(\s+)/);
  return (
    <p className="whitespace-pre-wrap text-sm leading-6">
      {parts.map((part, index) => {
        const normalized = normalizeEvidenceToken(part);
        if (normalized && terms.has(normalized)) {
          return (
            <mark key={`${part}-${index}`} className="rounded bg-warning/25 px-1 text-foreground">
              {part}
            </mark>
          );
        }
        return <span key={`${part}-${index}`}>{part}</span>;
      })}
    </p>
  );
}

function EvidenceCards({ evidenceCards, onCopy }: { evidenceCards: EvidenceCardData[]; onCopy: (card: EvidenceCardData) => void }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Evidence Cards</CardTitle>
        <Badge variant="cyan">{evidenceCards.length} evidence cards</Badge>
      </CardHeader>
      <CardContent className="grid gap-4 lg:grid-cols-2">
        {evidenceCards.length === 0 && <p className="text-sm text-muted">No evidence snippets were returned for this assessment.</p>}
        {evidenceCards.map((card) => (
          <EvidenceCard key={card.id} card={card} onCopy={() => onCopy(card)} />
        ))}
      </CardContent>
    </Card>
  );
}

function EvidenceCard({ card, onCopy }: { card: EvidenceCardData; onCopy: () => void }) {
  return (
    <article className="rounded-lg border border-line bg-white/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase text-muted">Document Section</div>
          <h3 className="mt-1 break-words text-sm font-semibold">{card.documentSection}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="muted">{formatPage(card.sourcePage)}</Badge>
          <Badge variant="muted">{card.sourceType.replaceAll("_", " ")}</Badge>
          <Badge variant="cyan">{formatConfidence(card.confidence)}</Badge>
        </div>
      </div>
      <div className="mt-3 space-y-3">
        <EvidenceFact label="Source Chunk" value={truncateText(card.extractedText, 420)} highlightWith={card.matchedRule} />
        <EvidenceFact label="Matched Rule" value={card.matchedRule} />
        <EvidenceFact label="Violation Reason" value={card.violationReason} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="secondary" onClick={onCopy}>
          <Copy className="h-4 w-4" /> Copy
        </Button>
        <details className="group min-w-48 flex-1 rounded-lg border border-line bg-black/15">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-sm font-semibold">
            <span>Expand evidence</span>
            <ChevronDown className="h-4 w-4 text-muted transition group-open:rotate-180" />
          </summary>
          <div className="border-t border-line p-3 text-sm leading-6">
            <p className="whitespace-pre-wrap">{card.extractedText}</p>
          </div>
        </details>
      </div>
    </article>
  );
}

function RecommendedActions({ recommendations }: { recommendations: string[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommendations</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {recommendations.length === 0 && <p className="text-sm text-muted">No remediation actions were returned by the backend.</p>}
        {recommendations.map((recommendation, index) => (
          <div key={`${recommendation}-${index}`} className="flex gap-3 rounded-lg border border-line bg-white/5 p-3 text-sm leading-6">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-primary/15 text-xs font-semibold text-info">{index + 1}</span>
            <span>{recommendation}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ExportCenter({
  auditId,
  findings,
  evidence,
  onPdf,
  onJson,
  pdfPending,
  jsonPending,
}: {
  auditId: string;
  findings: FindingView[];
  evidence: Evidence[];
  onPdf: () => void;
  onJson: () => void;
  pdfPending: boolean;
  jsonPending: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" variant="secondary" onClick={onPdf} disabled={pdfPending}>
        <Download className="h-4 w-4" /> PDF
      </Button>
      <Button type="button" variant="secondary" onClick={() => downloadFindingsCsv(auditId, findings)}>
        <FileText className="h-4 w-4" /> CSV
      </Button>
      <Button type="button" variant="secondary" onClick={() => downloadFindingsSpreadsheet(auditId, findings, evidence)}>
        <FileSpreadsheet className="h-4 w-4" /> Excel
      </Button>
      <Button type="button" variant="secondary" onClick={onJson} disabled={jsonPending}>
        <FileJson className="h-4 w-4" /> JSON
      </Button>
    </div>
  );
}

function getComplianceScore(report: AuditReport | null) {
  if (!report) return null;
  return (
    readNumberFrom(report, "compliance_score", "complianceScore", "overall_score", "overallScore", "score", "risk_score") ??
    readNumberFrom(getReportPayload(report), "compliance_score", "complianceScore", "overall_score", "overallScore", "score", "risk_score")
  );
}

function getFindingsCount(report: AuditReport | null, findings: FindingView[]) {
  const count =
    (report ? readNumberFrom(report, "findings_count", "finding_count", "total_violations") : null) ??
    (report ? readNumberFrom(getReportPayload(report), "findings_count", "finding_count", "total_violations", "failed_rules") : null);
  return count === null ? findings.length : Math.max(Math.max(0, Math.round(count)), findings.length);
}

function getRiskCounts(report: AuditReport | null, findings: FindingView[]): RiskCounts {
  const riskCounts = report ? readRecord(getReportPayload(report), "risk_counts") : {};
  const fromReport = {
    critical: readNumberFrom(riskCounts, "CRITICAL", "critical") ?? 0,
    high: readNumberFrom(riskCounts, "HIGH", "high") ?? 0,
    medium: readNumberFrom(riskCounts, "MEDIUM", "medium") ?? 0,
    low: readNumberFrom(riskCounts, "LOW", "low") ?? 0,
  };
  const hasReportCounts = Object.values(fromReport).some((value) => value > 0);
  if (hasReportCounts) {
    return {
      critical: Math.round(fromReport.critical),
      high: Math.round(fromReport.high),
      medium: Math.round(fromReport.medium),
      low: Math.round(fromReport.low),
    };
  }

  return findings.reduce<RiskCounts>(
    (counts, finding) => {
      const severity = normalizeSeverity(finding.severity);
      if (severity === "CRITICAL") counts.critical += 1;
      if (severity === "HIGH") counts.high += 1;
      if (severity === "MEDIUM") counts.medium += 1;
      if (severity === "LOW") counts.low += 1;
      return counts;
    },
    { critical: 0, high: 0, medium: 0, low: 0 },
  );
}

function getRiskLevel(report: AuditReport | null, auditRisk: string | null | undefined, riskCounts: RiskCounts) {
  const reportRisk = report
    ? getString(report.risk_level, getPayloadValue(report, "risk_level"), getPayloadValue(report, "riskLevel"))
    : null;
  if (reportRisk) return reportRisk.toUpperCase();
  if (auditRisk) return auditRisk;
  if (riskCounts.critical > 0) return "CRITICAL";
  if (riskCounts.high > 0) return "HIGH";
  if (riskCounts.medium > 0) return "MEDIUM";
  if (riskCounts.low > 0) return "LOW";
  return null;
}

function getOverallConfidence(report: AuditReport | null, auditConfidence: number | null | undefined, findings: FindingView[]) {
  const reportConfidence = report ? readNumberFrom(report, "confidence", "confidence_score") ?? readNumberFrom(getReportPayload(report), "confidence", "confidence_score") : null;
  if (reportConfidence !== null) return reportConfidence;
  if (typeof auditConfidence === "number" && Number.isFinite(auditConfidence)) return auditConfidence;
  const values = findings.map((finding) => finding.confidence).filter((value): value is number => value !== null);
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function getComplianceStatus(report: AuditReport | null, score: number | null, findingsCount: number) {
  const explicit = report
    ? getString(
        report.compliance_status,
        getPayloadValue(report, "compliance_status"),
        getPayloadValue(report, "complianceStatus"),
      )
    : null;
  if (explicit) return explicit;
  if (findingsCount > 0) return "Review required";
  if (score === null) return "Status unavailable";
  return scoreToProgress(score)! >= 80 ? "Compliant" : "Review required";
}

function getAiSummary(report: AuditReport | null) {
  if (!report) return NOT_RETURNED;
  return getString(getPayloadValue(report, "summary"), report.summary) ?? NOT_RETURNED;
}

function getReportFindings(report: AuditReport | null): ReportFindingPayload[] {
  if (!report) return [];
  const direct = report.findings;
  const nested = getReportPayload(report).findings;
  const findings = Array.isArray(direct) ? direct : Array.isArray(nested) ? nested : [];
  return findings.filter((item): item is ReportFindingPayload => Boolean(item) && typeof item === "object" && !Array.isArray(item));
}

function buildFindingViews(findings: Finding[], evidence: Evidence[], payloadFindings: ReportFindingPayload[]): FindingView[] {
  if (findings.length > 0) {
    return findings.map((finding, index) => {
      const payload = matchPayloadFinding(finding, payloadFindings, index);
      return toFindingView({
        id: finding.id,
        finding,
        payload,
        evidence: evidence.filter((item) => item.finding_id === finding.id),
        index,
      });
    });
  }

  return payloadFindings.map((payload, index) =>
    toFindingView({
      id: `report-finding-${index}`,
      payload,
      evidence: [],
      index,
    }),
  );
}

function matchPayloadFinding(finding: Finding, payloadFindings: ReportFindingPayload[], index: number) {
  const normalizedRule = normalizeText(finding.violated_rule);
  return (
    payloadFindings[index] ??
    payloadFindings.find((item) => normalizeText(getString(item.violated_rule, item.rule_violated, item.matched_rule) ?? "") === normalizedRule) ??
    {}
  );
}

function toFindingView({
  id,
  finding,
  payload,
  evidence,
  index,
}: {
  id: string;
  finding?: Finding;
  payload: ReportFindingPayload;
  evidence: Evidence[];
  index: number;
}): FindingView {
  const firstEvidence = evidence[0];
  const severity = normalizeSeverity(
    getString(payload.severity, payload.risk_level, finding?.severity, finding?.risk_level),
  );
  const ruleViolated =
    getString(payload.violated_rule, payload.rule_violated, finding?.violated_rule, payload.matched_rule, payload.matched_rule_text) ??
    `Finding ${index + 1}`;
  const evidenceText =
    getString(payload.evidence_text, payload.evidence, finding?.evidence_text, payload.matched_uploaded_text, payload.extracted_text, firstEvidence?.citation_text) ??
    NOT_RETURNED;
  const matchedPolicySection =
    getString(
      payload.matched_section,
      payload.citation_source,
      payload.citation,
      payload.section_title,
      finding?.citation_source,
      firstEvidence?.section_title,
      firstEvidence?.citation_label,
    ) ?? NOT_RETURNED;
  const extractedText =
    getString(payload.extracted_text, payload.matched_uploaded_text, finding?.evidence_text, firstEvidence?.citation_text, evidenceText) ??
    NOT_RETURNED;
  const matchedRule = getString(payload.matched_rule_text, payload.matched_rule, payload.violated_rule, finding?.violated_rule, ruleViolated) ?? NOT_RETURNED;
  const violationReason = getString(payload.violation_reason, payload.explanation, finding?.explanation) ?? NOT_RETURNED;

  return {
    id,
    finding,
    payload,
    evidence,
    severity,
    ruleViolated,
    evidenceText,
    matchedPolicySection,
    impact: getString(payload.impact, payload.business_impact, payload.risk_impact, finding?.explanation) ?? NOT_RETURNED,
    recommendation: getString(payload.recommendation, finding?.recommendation) ?? NOT_RETURNED,
    confidence:
      readNumberFrom(payload, "confidence_score", "confidence") ??
      readNumber(finding?.confidence_score) ??
      readNumber(finding?.confidence) ??
      readNumber(firstEvidence?.confidence_score),
    sourcePage: readInteger(payload.page_number) ?? firstEvidence?.page_number ?? null,
    documentSection: getString(payload.section_title, payload.matched_section, firstEvidence?.section_title, firstEvidence?.citation_label, matchedPolicySection) ?? NOT_RETURNED,
    extractedText,
    matchedRule,
    violationReason,
  };
}

function buildEvidenceCards(findings: FindingView[]): EvidenceCardData[] {
  return findings.flatMap((finding) => {
    if (finding.evidence.length > 0) {
      return finding.evidence.map((evidence, index) => ({
        id: `${finding.id}-${evidence.id}`,
        documentSection: evidence.section_title ?? evidence.citation_label ?? finding.documentSection,
        extractedText: evidence.citation_text || finding.extractedText,
        matchedRule: finding.matchedRule,
        violationReason: finding.violationReason,
        sourcePage: evidence.page_number ?? finding.sourcePage,
        confidence: readNumber(evidence.confidence_score) ?? finding.confidence,
        sourceType: evidence.source_type,
      }));
    }

    if (finding.extractedText === NOT_RETURNED && finding.evidenceText === NOT_RETURNED) return [];
    return [
      {
        id: `${finding.id}-payload-evidence`,
        documentSection: finding.documentSection,
        extractedText: finding.extractedText,
        matchedRule: finding.matchedRule,
        violationReason: finding.violationReason,
        sourcePage: finding.sourcePage,
        confidence: finding.confidence,
        sourceType: "report_payload",
      },
    ];
  });
}

function getKeyRisks(findings: FindingView[]) {
  return uniqueStrings(
    findings
      .filter((finding) => ["CRITICAL", "HIGH", "MEDIUM"].includes(normalizeSeverity(finding.severity) ?? ""))
      .map((finding) => getString(finding.impact, finding.ruleViolated, finding.violationReason)),
  ).slice(0, 5);
}

function getRecommendations(report: AuditReport | null, findings: FindingView[]) {
  const payloadRecommendations = report ? getReportPayload(report).recommendations : undefined;
  const recommendations = Array.isArray(payloadRecommendations)
    ? payloadRecommendations.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
    : [];
  return uniqueStrings([...recommendations, ...findings.map((finding) => finding.recommendation)]);
}

function getScoreDiagnostics(report: AuditReport | null): ScoreDiagnostics | null {
  if (!report) return null;
  const diagnostics = getReportPayload(report).score_diagnostics;
  if (!diagnostics || typeof diagnostics !== "object" || Array.isArray(diagnostics)) return null;
  return diagnostics as ScoreDiagnostics;
}

function getPayloadValue(report: AuditReport, key: string) {
  return getReportPayload(report)[key];
}

function getPayloadString(report: AuditReport, key: string) {
  return getString(getReportPayload(report)[key]);
}

function getReportPayload(report: AuditReport | null): Record<string, unknown> {
  const payload = report?.report_payload;
  return payload && typeof payload === "object" && !Array.isArray(payload) ? payload : {};
}

function readRecord(payload: Record<string, unknown>, key: string) {
  const value = payload[key];
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readNumberFrom(payload: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const number = readNumber(payload[key]);
    if (number !== null) return number;
  }
  return null;
}

function readNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const trimmed = value.trim();
    const parsed = Number(trimmed.endsWith("%") ? trimmed.slice(0, -1) : trimmed);
    if (Number.isFinite(parsed)) return trimmed.endsWith("%") ? parsed / 100 : parsed;
  }
  return null;
}

function readInteger(value: unknown) {
  const number = readNumber(value);
  return number === null ? null : Math.round(number);
}

function getString(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === "string" && value.trim().length > 0) return value.trim();
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }
  return null;
}

function normalizeSeverity(value?: string | null) {
  const normalized = value?.trim().toUpperCase();
  if (!normalized) return null;
  if (normalized.includes("CRITICAL")) return "CRITICAL";
  if (normalized.includes("HIGH")) return "HIGH";
  if (normalized.includes("MEDIUM")) return "MEDIUM";
  if (normalized.includes("LOW")) return "LOW";
  return normalized;
}

function normalizeText(value: string) {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function uniqueStrings(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.map((value) => value?.trim()).filter((value): value is string => Boolean(value))));
}

function importantTerms(value: string) {
  const stopWords = new Set(["the", "and", "that", "with", "from", "this", "shall", "must", "will", "policy", "rule"]);
  return new Set(
    value
      .split(/\s+/)
      .map(normalizeEvidenceToken)
      .filter((term) => term.length > 4 && !stopWords.has(term))
      .slice(0, 18),
  );
}

function normalizeEvidenceToken(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9-]/g, "");
}

function scoreToProgress(score: number | null) {
  if (score === null) return null;
  const normalized = score <= 1 ? score * 100 : score;
  return Math.max(0, Math.min(100, normalized));
}

function formatScore(score: number | null) {
  return score === null ? "Score unavailable" : formatPercent(score);
}

function formatConfidence(value: number | null | undefined) {
  return value === null || value === undefined ? "Confidence unavailable" : formatPercent(value);
}

function formatPage(value: number | null | undefined) {
  return value === null || value === undefined ? "Page unavailable" : `Page ${value}`;
}

function truncateText(value: string, maxLength: number) {
  return value.length > maxLength ? `${value.slice(0, maxLength).trim()}...` : value;
}

function scorePosture(score: number | null) {
  const progress = scoreToProgress(score);
  if (progress === null) return "Not returned";
  if (progress >= 85) return "Strong";
  if (progress >= 65) return "Moderate";
  return "Needs attention";
}

function scoreTone(score: number | null): "critical" | "high" | "medium" | "low" | "cyan" | "muted" {
  const progress = scoreToProgress(score);
  if (progress === null) return "muted";
  if (progress >= 85) return "low";
  if (progress >= 65) return "medium";
  return "high";
}

function riskLevelTone(riskLevel: string | null): "critical" | "high" | "medium" | "low" | "cyan" | "muted" {
  const normalized = normalizeSeverity(riskLevel);
  if (normalized === "CRITICAL") return "critical";
  if (normalized === "HIGH") return "high";
  if (normalized === "MEDIUM") return "medium";
  if (normalized === "LOW") return "low";
  return "muted";
}

function copyFindingBrief(finding: FindingView, toast: ReturnType<typeof useToast>["toast"]) {
  copyText(
    [
      `Rule Violated: ${finding.ruleViolated}`,
      `Severity: ${finding.severity ?? "Not returned"}`,
      `Evidence Text: ${finding.evidenceText}`,
      `Matched Policy Section: ${finding.matchedPolicySection}`,
      `Impact: ${finding.impact}`,
      `Recommendation: ${finding.recommendation}`,
      `Confidence: ${formatConfidence(finding.confidence)}`,
      `Source Page: ${formatPage(finding.sourcePage)}`,
    ].join("\n\n"),
    "Finding copied",
    toast,
  );
}

function copyEvidenceCard(card: EvidenceCardData, toast: ReturnType<typeof useToast>["toast"]) {
  copyText(
    [
      `Document Section: ${card.documentSection}`,
      `Source Type: ${card.sourceType}`,
      `Extracted Text: ${card.extractedText}`,
      `Matched Rule: ${card.matchedRule}`,
      `Violation Reason: ${card.violationReason}`,
      `Source Page: ${formatPage(card.sourcePage)}`,
      `Confidence: ${formatConfidence(card.confidence)}`,
    ].join("\n\n"),
    "Evidence copied",
    toast,
  );
}

function copyText(text: string, title: string, toast: ReturnType<typeof useToast>["toast"]) {
  if (!navigator.clipboard) {
    toast({ title: "Copy unavailable", description: "Clipboard access is not available in this browser.", variant: "error" });
    return;
  }
  navigator.clipboard
    .writeText(text)
    .then(() => toast({ title, description: "The audit detail is ready to paste." }))
    .catch((error) => toast({ title: "Copy failed", description: getErrorMessage(error), variant: "error" }));
}

function downloadFindingsCsv(auditId: string, findings: FindingView[]) {
  const header = ["Rule Violated", "Severity", "Confidence", "Source Page", "Evidence Text", "Matched Policy Section", "Impact", "Recommendation"]
    .map(escapeCsv)
    .join(",");
  const body = findings.map((finding) =>
    [
      finding.ruleViolated,
      finding.severity ?? "",
      formatConfidence(finding.confidence),
      formatPage(finding.sourcePage),
      finding.evidenceText,
      finding.matchedPolicySection,
      finding.impact,
      finding.recommendation,
    ]
      .map(escapeCsv)
      .join(","),
  );
  saveBlob(new Blob([[header, ...body].join("\n")], { type: "text/csv;charset=utf-8" }), `compliance-findings-${auditId}.csv`);
}

function downloadFindingsSpreadsheet(auditId: string, findings: FindingView[], evidence: Evidence[]) {
  const header = ["Rule Violated", "Severity", "Confidence", "Source Page", "Evidence Text", "Matched Policy Section", "Impact", "Recommendation"].join("\t");
  const body = findings.map((finding) =>
    [
      finding.ruleViolated,
      finding.severity ?? "",
      formatConfidence(finding.confidence),
      formatPage(finding.sourcePage),
      finding.evidenceText,
      finding.matchedPolicySection,
      finding.impact,
      finding.recommendation,
    ].join("\t"),
  );
  const evidenceBody = evidence.map((item) => [item.section_title ?? item.citation_label ?? "", item.citation_text, formatPage(item.page_number)].join("\t"));
  saveBlob(
    new Blob([[header, ...body, "", "Evidence", ...evidenceBody].join("\n")], { type: "application/vnd.ms-excel;charset=utf-8" }),
    `compliance-findings-${auditId}.xls`,
  );
}

function escapeCsv(value: string) {
  const escaped = value.replaceAll('"', '""');
  return /[",\n]/.test(escaped) ? `"${escaped}"` : escaped;
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  window.document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
