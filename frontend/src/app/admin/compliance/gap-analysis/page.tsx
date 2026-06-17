"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  AlertTriangle, 
  CheckCircle, 
  HelpCircle, 
  Play, 
  Plus, 
  RotateCcw, 
  ScanSearch, 
  ShieldCheck 
} from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { createComplianceRule, runGapAnalysis } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";

export default function GapAnalysisPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [selectedFramework, setSelectedFramework] = useState<string>("SOC2");

  const {
    data: gapReport,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ["gap-analysis", selectedFramework],
    queryFn: () => runGapAnalysis(selectedFramework),
    enabled: true, // Run automatically on load for initial value
  });

  const createRuleMutation = useMutation({
    mutationFn: (payload: {
      category: string;
      title: string;
      rule_text: string;
      reference?: string;
      version: string;
      description?: string;
    }) => createComplianceRule(payload),
    onSuccess: () => {
      toast({ title: "Compliance rule created", description: "The rule has been successfully saved and vector-indexed." });
      // Invalidate both gap-analysis and compliance rules queries to sync coverage state
      queryClient.invalidateQueries({ queryKey: ["gap-analysis"] });
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
    },
    onError: (err) => {
      toast({
        title: "Rule creation failed",
        description: getErrorMessage(err),
        variant: "error",
      });
    },
  });

  // Calculate metrics
  const totalCount = gapReport?.length ?? 0;
  const coveredCount = gapReport?.filter((r) => r.status === "COVERED").length ?? 0;
  const partialCount = gapReport?.filter((r) => r.status === "PARTIAL").length ?? 0;
  const missingCount = gapReport?.filter((r) => r.status === "MISSING").length ?? 0;

  const coveragePercent = totalCount > 0 ? Math.round(((coveredCount + partialCount * 0.5) / totalCount) * 100) : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance Intelligence"
        title="Semantic Gap Analysis"
        description="Compare existing compliance rules and indexed policy text against structured regulatory frameworks using AI-driven semantic embeddings."
      />

      {/* Framework Selector & Controls */}
      <Card className="border-line bg-panel/60 backdrop-blur-xl">
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <label htmlFor="framework-select" className="text-sm font-medium text-muted">
                Select Standard Framework:
              </label>
              <select
                id="framework-select"
                value={selectedFramework}
                onChange={(e) => setSelectedFramework(e.target.value)}
                className="h-10 w-48 rounded-lg border border-line bg-elevated px-3 text-sm outline-none transition focus:border-cyan/50"
              >
                <option value="SOC2">SOC 2 (Trust Services Criteria)</option>
                <option value="HIPAA">HIPAA (Security Rule)</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => refetch()}
                disabled={isLoading || isFetching}
              >
                <RotateCcw className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`} />
                Re-Analyze
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Metrics */}
      {gapReport && !isLoading && (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border-line bg-panel/50">
            <CardHeader className="pb-2">
              <p className="text-xs uppercase text-muted">Overall Coverage Score</p>
              <CardTitle className="text-3xl font-bold text-cyan">{coveragePercent}%</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-violet to-cyan transition-all duration-500" 
                  style={{ width: `${coveragePercent}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-line bg-panel/50">
            <CardHeader className="pb-2">
              <p className="text-xs uppercase text-cyan">Fully Covered</p>
              <CardTitle className="text-3xl font-bold flex items-center gap-2">
                <CheckCircle className="h-6 w-6 text-cyan" />
                {coveredCount} <span className="text-xs font-normal text-muted">/ {totalCount}</span>
              </CardTitle>
            </CardHeader>
          </Card>

          <Card className="border-line bg-panel/50">
            <CardHeader className="pb-2">
              <p className="text-xs uppercase text-riskMedium">Partially Covered</p>
              <CardTitle className="text-3xl font-bold flex items-center gap-2">
                <AlertTriangle className="h-6 w-6 text-riskMedium" />
                {partialCount} <span className="text-xs font-normal text-muted">/ {totalCount}</span>
              </CardTitle>
            </CardHeader>
          </Card>

          <Card className="border-line bg-panel/50">
            <CardHeader className="pb-2">
              <p className="text-xs uppercase text-riskHigh">Missing Controls</p>
              <CardTitle className="text-3xl font-bold flex items-center gap-2">
                <HelpCircle className="h-6 w-6 text-riskHigh" />
                {missingCount} <span className="text-xs font-normal text-muted">/ {totalCount}</span>
              </CardTitle>
            </CardHeader>
          </Card>
        </section>
      )}

      {/* Main Analysis List */}
      <Card className="border-line bg-panel/50">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Framework Breakdown</CardTitle>
            <p className="text-xs text-muted">
              Detailed comparison showing closest compliance matches and AI suggestions.
            </p>
          </div>
          <ScanSearch className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && (
            <div className="space-y-4">
              <Skeleton className="h-28 w-full" />
              <Skeleton className="h-28 w-full" />
              <Skeleton className="h-28 w-full" />
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-4 text-sm text-riskHigh">
              Failed to load gap analysis: {getErrorMessage(error)}
            </div>
          )}

          {!isLoading && gapReport?.length === 0 && (
            <div className="py-12 text-center text-muted">No analysis results found.</div>
          )}

          {gapReport?.map((req) => {
            const statusLabel = req.status;
            let badgeVariant: "cyan" | "medium" | "high" = "cyan";
            if (statusLabel === "PARTIAL") badgeVariant = "medium";
            if (statusLabel === "MISSING") badgeVariant = "high";

            return (
              <article 
                key={req.control_id} 
                className="rounded-lg border border-line bg-elevated/40 p-5 transition hover:border-line-active hover:bg-elevated/70"
              >
                {/* Header */}
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <h3 className="text-base font-semibold flex items-center gap-2">
                      <span className="text-cyan font-mono text-sm bg-cyan/5 px-2 py-0.5 rounded border border-cyan/10">
                        {req.control_id}
                      </span>
                      {req.title}
                    </h3>
                    <p className="mt-2 text-sm text-muted leading-relaxed max-w-4xl">
                      {req.description}
                    </p>
                  </div>
                  <div className="mt-2 md:mt-0 flex flex-col items-end gap-1 shrink-0">
                    <Badge variant={badgeVariant}>{statusLabel}</Badge>
                    <span className="text-[10px] text-muted/80 font-mono">
                      Match Score: {req.match_score}
                    </span>
                  </div>
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                  {/* Matched Rule Section */}
                  {req.matched_rule ? (
                    <div className="rounded-lg border border-line bg-background/50 p-4 space-y-2">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
                        <ShieldCheck className="h-3.5 w-3.5 text-cyan" />
                        Matched Rule in Library
                      </h4>
                      <div>
                        <div className="text-sm font-semibold">{req.matched_rule.title}</div>
                        <div className="mt-1 text-[11px] text-cyan bg-cyan/5 border border-cyan/15 inline-block px-1.5 py-0.5 rounded">
                          {req.matched_rule.category}
                        </div>
                      </div>
                      <p className="text-xs text-muted/80 line-clamp-3 bg-black/10 p-2 rounded">
                        {req.matched_rule.rule_text}
                      </p>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-dashed border-line bg-white/2 p-4 flex flex-col justify-center items-center text-center">
                      <p className="text-xs text-muted">No strong matching rule found in the active library.</p>
                    </div>
                  )}

                  {/* Suggested Rule Section */}
                  {req.suggested_rule && (
                    <div className="rounded-lg border border-cyan/15 bg-cyan/5 p-4 flex flex-col justify-between gap-3">
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan flex items-center gap-1.5">
                          <Plus className="h-3.5 w-3.5" />
                          AI Suggested Rule Draft
                        </h4>
                        <div>
                          <div className="text-sm font-semibold">{req.suggested_rule.title}</div>
                          <div className="mt-1 flex gap-2">
                            <span className="text-[10px] text-cyan bg-cyan/10 px-1.5 py-0.5 rounded border border-cyan/20">
                              {req.suggested_rule.category}
                            </span>
                            <span className="text-[10px] text-muted/80">
                              Ref: {req.suggested_rule.reference}
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-muted leading-relaxed bg-black/15 p-2 rounded">
                          {req.suggested_rule.rule_text}
                        </p>
                      </div>

                      <Button
                        size="sm"
                        className="w-full bg-cyan hover:bg-cyan/90 text-background font-semibold"
                        disabled={createRuleMutation.isPending}
                        onClick={() => {
                          if (!req.suggested_rule) return;
                          createRuleMutation.mutate({
                            title: req.suggested_rule.title,
                            category: req.suggested_rule.category,
                            rule_text: req.suggested_rule.rule_text,
                            reference: req.suggested_rule.reference,
                            version: "v1",
                            description: req.suggested_rule.description,
                          });
                        }}
                      >
                        <Plus className="h-3.5 w-3.5 mr-1" />
                        Apply & Index Rule
                      </Button>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
