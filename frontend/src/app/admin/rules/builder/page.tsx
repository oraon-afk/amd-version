"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle,
  ChevronRight,
  FlaskConical,
  Loader2,
  Plus,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import {
  createComplianceRule,
  listRuleCategories,
  testComplianceRule,
} from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { RuleTestResult } from "@/types/api";

export default function RuleBuilderPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const categoriesQuery = useQuery({
    queryKey: ["admin-rule-categories"],
    queryFn: listRuleCategories,
  });

  // Rule fields
  const [category, setCategory] = useState("");
  const [title, setTitle] = useState("");
  const [ruleText, setRuleText] = useState("");
  const [reference, setReference] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [effectivityDate, setEffectivityDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");

  // Test panel
  const [sampleText, setSampleText] = useState("");
  const [savedRuleId, setSavedRuleId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<RuleTestResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  const canSave =
    category.trim().length >= 2 &&
    title.trim().length >= 2 &&
    ruleText.trim().length >= 5;

  const createMutation = useMutation({
    mutationFn: () =>
      createComplianceRule({
        category: category.trim(),
        title: title.trim(),
        rule_text: ruleText.trim(),
        reference: reference.trim() || undefined,
        version: "v1",
        custom_attributes:
          jurisdiction.trim()
            ? { jurisdiction: jurisdiction.trim() }
            : undefined,
        effectivity_date: effectivityDate || undefined,
        expiry_date: expiryDate || undefined,
      }),
    onSuccess: (data) => {
      setSavedRuleId(data.id);
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Rule saved", description: "You can now test it below." });
    },
    onError: (error) =>
      toast({
        title: "Failed to save rule",
        description: getErrorMessage(error),
        variant: "error",
      }),
  });

  const handleTest = async () => {
    if (!savedRuleId) {
      toast({
        title: "Save the rule first",
        description: "Save the rule before running a test.",
        variant: "error",
      });
      return;
    }
    if (!sampleText.trim()) {
      toast({ title: "Enter sample document text", variant: "error" });
      return;
    }
    setTestLoading(true);
    setTestResult(null);
    setTestError(null);
    try {
      const result = await testComplianceRule(savedRuleId, sampleText.trim());
      setTestResult(result);
    } catch (err: any) {
      setTestError(err.response?.data?.detail || "Test failed.");
    } finally {
      setTestLoading(false);
    }
  };

  const confidencePct = testResult
    ? Math.round(testResult.confidence * 100)
    : null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Rule Management"
        title="Rule Builder"
        description="Create a new compliance rule with metadata, then test it against sample document text before it goes live."
      />

      <div className="grid gap-6 xl:grid-cols-2">
        {/* ── Left: Rule Form ─────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-cyan" />
              Define Rule
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Category */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted uppercase tracking-wide">
                Category *
              </label>
              {categoriesQuery.isLoading ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="h-10 w-full rounded-lg border border-line bg-elevated px-3 text-sm outline-none focus:border-cyan/70"
                >
                  <option value="">— Select category —</option>
                  {(categoriesQuery.data ?? []).map((item) => (
                    <option key={item.id ?? item.name} value={item.name}>
                      {item.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Title */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted uppercase tracking-wide">
                Rule Title *
              </label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Data Encryption at Rest"
              />
            </div>

            {/* Rule Text */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted uppercase tracking-wide">
                Rule Text *
              </label>
              <Textarea
                value={ruleText}
                onChange={(e) => setRuleText(e.target.value)}
                placeholder="Describe the compliance requirement in plain language. Be specific."
                className="min-h-[120px]"
              />
              <p className="text-xs text-muted/60">
                {ruleText.length} chars · minimum 5
              </p>
            </div>

            {/* Reference + Jurisdiction */}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted uppercase tracking-wide">
                  Reference
                </label>
                <Input
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="GDPR Art. 5(1)(f)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted uppercase tracking-wide">
                  Jurisdiction
                </label>
                <Input
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                  placeholder="EU, US, Global…"
                />
              </div>
            </div>

            {/* Dates */}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted uppercase tracking-wide">
                  Effectivity Date
                </label>
                <Input
                  type="date"
                  value={effectivityDate}
                  onChange={(e) => setEffectivityDate(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted uppercase tracking-wide">
                  Expiry Date
                </label>
                <Input
                  type="date"
                  value={expiryDate}
                  onChange={(e) => setExpiryDate(e.target.value)}
                />
              </div>
            </div>

            {/* Save button */}
            <Button
              className="w-full"
              disabled={!canSave || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              {savedRuleId ? "Saved ✓ (Save again to create new)" : "Save Rule"}
            </Button>

            {savedRuleId && (
              <div className="flex items-center gap-2 rounded-lg bg-cyan/10 border border-cyan/20 px-3 py-2 text-xs text-cyan">
                <CheckCircle className="h-3 w-3 flex-shrink-0" />
                Rule saved — ID: {savedRuleId.slice(0, 12)}…
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Right: Test Panel ─────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-amber-400" />
              Test Rule
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted">
              Save the rule first, then paste a sample document excerpt below
              and click <strong>Run Test</strong> to evaluate how the rule
              performs against it.
            </p>

            <div className="space-y-1">
              <label className="text-xs font-medium text-muted uppercase tracking-wide">
                Sample Document Text
              </label>
              <Textarea
                value={sampleText}
                onChange={(e) => setSampleText(e.target.value)}
                placeholder="Paste a paragraph or excerpt from a policy document here…"
                className="min-h-[160px]"
              />
            </div>

            <Button
              className="w-full"
              variant={savedRuleId ? "default" : "secondary"}
              disabled={testLoading || !savedRuleId || !sampleText.trim()}
              onClick={handleTest}
            >
              {testLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Evaluating…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Run Test
                </>
              )}
            </Button>

            {!savedRuleId && (
              <p className="text-xs text-muted/60 text-center">
                Save the rule on the left to enable testing.
              </p>
            )}

            {/* Test error */}
            {testError && (
              <div className="flex items-start gap-2 rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-xs text-riskHigh">
                <XCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                {testError}
              </div>
            )}

            {/* Test results */}
            {testResult && (
              <div className="space-y-3">
                <div
                  className={`flex items-center gap-3 rounded-lg border p-4 ${
                    testResult.rule_matched
                      ? "border-emerald-500/30 bg-emerald-500/10"
                      : "border-riskHigh/30 bg-riskHigh/10"
                  }`}
                >
                  {testResult.rule_matched ? (
                    <CheckCircle className="h-6 w-6 text-emerald-400 flex-shrink-0" />
                  ) : (
                    <XCircle className="h-6 w-6 text-riskHigh flex-shrink-0" />
                  )}
                  <div>
                    <p className="font-semibold text-sm text-foreground">
                      {testResult.rule_matched ? "Rule Matched" : "No Match"}
                    </p>
                    <p className="text-xs text-muted">
                      Confidence:{" "}
                      <span className="font-mono font-bold text-foreground">
                        {confidencePct}%
                      </span>
                    </p>
                  </div>
                </div>

                {/* Confidence bar */}
                <div>
                  <div className="flex justify-between text-xs text-muted mb-1">
                    <span>Confidence Score</span>
                    <span className="font-mono">{confidencePct}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-line overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        (confidencePct ?? 0) >= 70
                          ? "bg-emerald-500"
                          : (confidencePct ?? 0) >= 40
                          ? "bg-amber-500"
                          : "bg-riskHigh"
                      }`}
                      style={{ width: `${confidencePct}%` }}
                    />
                  </div>
                </div>

                {/* Explanation */}
                {testResult.explanation && (
                  <div className="rounded-lg border border-line bg-elevated p-3">
                    <p className="text-xs font-medium text-muted mb-1 uppercase tracking-wide">
                      Explanation
                    </p>
                    <p className="text-sm text-foreground leading-relaxed">
                      {testResult.explanation}
                    </p>
                  </div>
                )}

                {/* Matched chunks */}
                {testResult.matched_chunks?.length > 0 && (
                  <div className="rounded-lg border border-line bg-elevated p-3">
                    <p className="text-xs font-medium text-muted mb-2 uppercase tracking-wide">
                      Matched Chunks ({testResult.matched_chunks.length})
                    </p>
                    <div className="space-y-2">
                      {testResult.matched_chunks.map((chunk, i) => (
                        <div
                          key={i}
                          className="rounded border border-line bg-surface p-2 text-xs text-muted font-mono leading-5 line-clamp-3"
                        >
                          {chunk}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
