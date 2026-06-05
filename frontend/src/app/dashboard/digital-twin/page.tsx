"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, FileWarning, Flame, Gauge, History, RefreshCw, ShieldCheck, type LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useMemo } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { formatDate, formatPercent, normalizeScore, scoreToProgress } from "@/lib/utils";
import { getErrorMessage } from "@/services/api/client";
import { getComplianceDigitalTwin, rebuildComplianceDigitalTwin } from "@/services/digital-twin/digital-twin-service";
import { ComplianceDigitalTwin } from "@/types/api";

export default function ComplianceDigitalTwinPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const twinQuery = useQuery({
    queryKey: ["compliance-digital-twin"],
    queryFn: getComplianceDigitalTwin,
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });
  const rebuildMutation = useMutation({
    mutationFn: rebuildComplianceDigitalTwin,
    onSuccess: (nextTwin) => {
      queryClient.setQueryData(["compliance-digital-twin"], nextTwin);
      queryClient.invalidateQueries({ queryKey: ["compliance-digital-twin"] });
      queryClient.refetchQueries({ queryKey: ["compliance-digital-twin"] });
      toast({ title: "Digital Twin refreshed" });
    },
    onError: (error) => toast({ title: "Refresh failed", description: getErrorMessage(error), variant: "error" }),
  });

  const twin = twinQuery.data ?? null;
  const twinMetrics = useMemo(() => (twin ? getTwinMetrics(twin) : null), [twin]);
  const twinFindings = useMemo(() => (twin ? getTwinFindings(twin) : []), [twin]);
  const findingsByDomain = useMemo(() => getFindingsByDomain(twinFindings), [twinFindings]);
  const policyCountsByDomain = useMemo(() => (twin ? getPolicyCountsByDomain(twin) : new Map<string, number>()), [twin]);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development" || !twinMetrics) return;
    console.log("Twin Metrics", twinMetrics);
    console.log("Twin Findings", twinFindings);
  }, [twinFindings, twinMetrics]);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Digital Twin"
        title="Organization Compliance Twin"
        description="Aggregated policy coverage, maturity, missing policies, risk heatmap, and compliance history from uploaded documents."
        actions={
          <Button type="button" variant="secondary" onClick={() => rebuildMutation.mutate()} disabled={rebuildMutation.isPending}>
            <RefreshCw className={rebuildMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Refresh Twin
          </Button>
        }
      />

      {twinQuery.isLoading && <Skeleton className="h-72 w-full" />}
      {twinQuery.error && (
        <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
          {getErrorMessage(twinQuery.error)}
        </p>
      )}
      {!twinQuery.isLoading && !twinQuery.error && !twin && (
        <EmptyState icon={ShieldCheck} title="Digital Twin unavailable" copy="Upload and audit policies to generate the organization profile." />
      )}

      {twin && (
        <>
          <TwinMetrics twin={twin} />
          <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <MaturityPanel twin={twin} />
            <RiskHeatmap twin={twin} findingsByDomain={findingsByDomain} policyCountsByDomain={policyCountsByDomain} />
          </section>
          <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <MissingPolicies twin={twin} />
            <PolicyInventory twin={twin} />
          </section>
          <HistoryPanel twin={twin} />
        </>
      )}
    </div>
  );
}

function TwinMetrics({ twin }: { twin: ComplianceDigitalTwin }) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Metric index={0} icon={Gauge} label="Maturity" value={formatTwinScore(twin.maturity_score)} />
      <Metric index={1} icon={ShieldCheck} label="Coverage" value={formatTwinScore(twin.coverage_score)} />
      <Metric index={2} icon={Flame} label="Risk Pressure" value={formatTwinScore(twin.risk_score)} />
      <Metric index={3} icon={History} label="Snapshots" value={String(twin.history.length)} />
    </section>
  );
}

function Metric({ icon: Icon, label, value, index }: { icon: LucideIcon; label: string; value: string; index: number }) {
  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay: index * 0.07, type: "spring", stiffness: 200, damping: 20 }}
      className="rounded-lg border border-line bg-card p-4 transition-all duration-200 hover:shadow-[0_16px_32px_rgba(124,77,255,0.1)]"
    >
      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted">
        <Icon className="h-4 w-4 text-info" />
        {label}
      </div>
      <div className="mt-3 text-2xl font-semibold">{value}</div>
    </motion.div>
  );
}

function MaturityPanel({ twin }: { twin: ComplianceDigitalTwin }) {
  const summaryText = getString(twin.summary.summary_text) ?? "Digital Twin summary unavailable.";
  return (
    <Card>
      <CardHeader>
        <CardTitle>Compliance Maturity</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={scoreToProgress(twin.maturity_score) ?? 0} />
        <div className="grid gap-3 sm:grid-cols-3">
          <Fact label="Maturity Band" value={getString(twin.summary.maturity_band) ?? "Not returned"} />
          <Fact label="Coverage Band" value={getString(twin.summary.coverage_band) ?? "Not returned"} />
          <Fact label="Risk Band" value={getString(twin.summary.risk_band) ?? "Not returned"} />
        </div>
        <p className="rounded-lg border border-line bg-white/5 p-3 text-sm leading-6 text-muted">{summaryText}</p>
      </CardContent>
    </Card>
  );
}

function RiskHeatmap({
  twin,
  findingsByDomain,
  policyCountsByDomain,
}: {
  twin: ComplianceDigitalTwin;
  findingsByDomain: Map<string, number>;
  policyCountsByDomain: Map<string, number>;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Heatmap</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        {twin.risk_heatmap.map((row, index) => {
          const domain = getString(row.domain) ?? "Unknown";
          const domainKey = normalizeDomain(domain);
          const risk = getString(row.risk_level) ?? "UNKNOWN";
          const policyCount = Math.max(getNumber(row.policy_count) ?? 0, policyCountsByDomain.get(domainKey) ?? 0);
          const findings = Math.max(getNumber(row.findings_count) ?? 0, findingsByDomain.get(domainKey) ?? 0);
          return (
            <motion.div
              key={domain}
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
              className="rounded-lg border border-line bg-white/5 p-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-violet/30 hover:shadow-[0_12px_24px_rgba(124,77,255,0.08)]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-semibold capitalize">{domain}</span>
                <Badge variant={riskVariant(risk)}>{risk}</Badge>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted">
                <span>Policies: {policyCount}</span>
                <span>Findings: {findings}</span>
              </div>
            </motion.div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function MissingPolicies({ twin }: { twin: ComplianceDigitalTwin }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Missing Policies</CardTitle>
        <Badge variant={twin.missing_policies.length ? "high" : "low"}>{twin.missing_policies.length}</Badge>
      </CardHeader>
      <CardContent className="space-y-2">
        {twin.missing_policies.length === 0 && (
          <EmptyState icon={ShieldCheck} title="No gaps detected" copy="Every configured compliance domain has at least one uploaded policy." />
        )}
        {twin.missing_policies.map((policy) => {
          const domain = getString(policy.domain) ?? "Unknown domain";
          return (
            <motion.div key={domain} initial={{ x: -12, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.3 }} className="rounded-lg border border-line bg-white/5 p-3">
              <div className="flex items-center gap-2 text-sm font-semibold capitalize">
                <FileWarning className="h-4 w-4 text-warning" />
                {domain}
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{getString(policy.reason) ?? "No uploaded policy found."}</p>
            </motion.div>
          );
        })}
      </CardContent>
    </Card>
  );
}

function PolicyInventory({ twin }: { twin: ComplianceDigitalTwin }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Policy Inventory</CardTitle>
      </CardHeader>
      <CardContent className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
        {twin.policies.length === 0 && <p className="text-sm text-muted">No uploaded compliance policies are available yet.</p>}
        {twin.policies.map((policy, index) => (
          <motion.div
            key={policy.id}
            initial={{ x: -12, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: index * 0.04, duration: 0.3 }}
            className="rounded-lg border border-line bg-white/5 p-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-violet/25"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{policy.title}</div>
                <div className="mt-1 text-xs text-muted capitalize">{policy.domain} - {policy.coverage_status}</div>
              </div>
              <Badge variant={riskVariant(policy.risk_level ?? "LOW")}>{policy.risk_level ?? "No risk"}</Badge>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-3">
              <span>Score: {policy.compliance_score === null ? "n/a" : formatTwinScore(policy.compliance_score)}</span>
              <span>Findings: {policy.findings_count}</span>
              <span>Status: {policy.status}</span>
            </div>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  );
}

function HistoryPanel({ twin }: { twin: ComplianceDigitalTwin }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Compliance History</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {twin.history.length === 0 && <p className="text-sm text-muted">No historical snapshots are available.</p>}
        {twin.history.map((snapshot, index) => (
          <motion.div
            key={snapshot.id}
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: index * 0.06, duration: 0.3 }}
            className="antigravity-float-slow rounded-lg border border-line bg-white/5 p-3 transition-all duration-200 hover:-translate-y-0.5 hover:border-violet/25"
          >
            <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted">
              <Activity className="h-4 w-4 text-info" />
              {formatDate(snapshot.created_at)}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
              <span>{formatTwinScore(snapshot.maturity_score)}</span>
              <span>{formatTwinScore(snapshot.coverage_score)}</span>
              <span>{formatTwinScore(snapshot.risk_score)}</span>
            </div>
            <p className="mt-3 text-xs leading-5 text-muted">{snapshot.summary_text}</p>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-white/5 p-3">
      <div className="text-xs font-semibold uppercase text-muted">{label}</div>
      <div className="mt-2 text-sm font-semibold capitalize">{value}</div>
    </div>
  );
}

function getString(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function getNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatTwinScore(value: number | null | undefined) {
  return formatPercent(normalizeScore(value) ?? value);
}

function getTwinMetrics(twin: ComplianceDigitalTwin) {
  return {
    maturity_score: twin.maturity_score,
    coverage_score: twin.coverage_score,
    risk_score: twin.risk_score,
    snapshots: twin.history.length,
    policies: twin.policies.length,
    heatmap_findings: twin.risk_heatmap.reduce((total, row) => total + (getNumber(row.findings_count) ?? 0), 0),
    policy_findings: twin.policies.reduce((total, policy) => total + policy.findings_count, 0),
  };
}

function getTwinFindings(twin: ComplianceDigitalTwin) {
  return twin.policies
    .filter((policy) => policy.findings_count > 0)
    .map((policy) => ({
      document_id: policy.document_id,
      latest_audit_id: policy.latest_audit_id,
      domain: policy.domain,
      findings_count: policy.findings_count,
      compliance_score: policy.compliance_score,
      status: policy.status,
    }));
}

function getFindingsByDomain(findings: ReturnType<typeof getTwinFindings>) {
  const counts = new Map<string, number>();
  findings.forEach((item) => {
    const domain = normalizeDomain(item.domain);
    counts.set(domain, (counts.get(domain) ?? 0) + item.findings_count);
  });
  return counts;
}

function getPolicyCountsByDomain(twin: ComplianceDigitalTwin) {
  const counts = new Map<string, number>();
  twin.policies.forEach((policy) => {
    const domain = normalizeDomain(policy.domain);
    counts.set(domain, (counts.get(domain) ?? 0) + 1);
  });
  return counts;
}

function normalizeDomain(value: unknown) {
  return String(value ?? "").trim().toLowerCase().replaceAll("_", "-").split(/\s+/).join(" ");
}

function riskVariant(risk: string): "high" | "medium" | "low" | "muted" {
  const normalized = risk.toUpperCase();
  if (normalized === "HIGH" || normalized === "CRITICAL" || normalized === "MISSING") return "high";
  if (normalized === "MEDIUM") return "medium";
  if (normalized === "LOW") return "low";
  return "muted";
}
