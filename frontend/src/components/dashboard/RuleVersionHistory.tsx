"use client";

import { useQuery } from "@tanstack/react-query";
import { Clock, GitBranch, X } from "lucide-react";
import { listComplianceRules } from "@/services/admin/admin-service";
import { ComplianceRule } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface RuleVersionHistoryProps {
  rule: ComplianceRule | null;
  isOpen: boolean;
  onClose: () => void;
}

export function RuleVersionHistory({
  rule,
  isOpen,
  onClose,
}: RuleVersionHistoryProps) {
  const rulesQuery = useQuery({
    queryKey: ["admin-compliance-rules"],
    queryFn: listComplianceRules,
    enabled: isOpen && !!rule,
  });

  if (!isOpen || !rule) return null;

  const allRules = rulesQuery.data ?? [];

  // Build the version chain by walking parent_rule_id links
  const chainIds = new Set<string>();
  const buildChain = (ruleId: string) => {
    chainIds.add(ruleId);
    const parent = allRules.find((r) => r.id === ruleId)?.parent_rule_id;
    if (parent && !chainIds.has(parent)) buildChain(parent);
    allRules
      .filter((r) => r.parent_rule_id === ruleId)
      .forEach((child) => {
        if (!chainIds.has(child.id)) buildChain(child.id);
      });
  };
  buildChain(rule.id);

  const versionChain = allRules
    .filter((r) => chainIds.has(r.id))
    .sort((a, b) => (b.version_number ?? 1) - (a.version_number ?? 1));

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col overflow-hidden border-l border-line bg-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-cyan" />
            <h2 className="text-base font-semibold text-foreground">
              Version History
            </h2>
          </div>
          <Button size="icon" variant="ghost" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Rule title */}
        <div className="border-b border-line bg-elevated px-5 py-3">
          <p className="truncate text-sm font-medium text-foreground">
            {rule.title}
          </p>
          <p className="text-xs text-muted">{rule.category}</p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {rulesQuery.isLoading && (
            <>
              <Skeleton className="h-20 w-full rounded-lg" />
              <Skeleton className="h-20 w-full rounded-lg" />
              <Skeleton className="h-20 w-full rounded-lg" />
            </>
          )}

          {!rulesQuery.isLoading && versionChain.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <GitBranch className="h-10 w-10 text-muted/30 mb-3" />
              <p className="text-sm text-muted">No version history found.</p>
              <p className="text-xs text-muted/60 mt-1">
                This rule has not been updated yet.
              </p>
            </div>
          )}

          {versionChain.map((v) => {
            const isCurrent = v.id === rule.id;
            return (
              <article
                key={v.id}
                className={`rounded-lg border p-4 transition-colors ${
                  isCurrent
                    ? "border-cyan/40 bg-cyan/5"
                    : "border-line bg-elevated"
                }`}
              >
                {/* Version header */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs font-bold text-foreground">
                      v{v.version_number ?? 1}
                    </span>
                    {isCurrent && (
                      <Badge variant="cyan" className="text-[10px] py-0">
                        Current
                      </Badge>
                    )}
                    <Badge
                      variant={v.status === "active" ? "cyan" : "muted"}
                      className="text-[10px] py-0"
                    >
                      {v.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted flex-shrink-0">
                    <Clock className="h-3 w-3" />
                    {v.created_at
                      ? new Date(v.created_at).toLocaleDateString()
                      : "—"}
                  </div>
                </div>

                {/* Rule content */}
                <p className="mb-1 text-sm font-medium text-foreground">
                  {v.title}
                </p>
                <p className="line-clamp-3 text-xs text-muted leading-5">
                  {v.rule_text}
                </p>

                {/* Meta */}
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                  {v.reference && (
                    <span className="text-xs text-muted">
                      Ref: {v.reference}
                    </span>
                  )}
                  {v.effectivity_date && (
                    <span className="text-xs text-muted">
                      Effective: {v.effectivity_date}
                    </span>
                  )}
                  {v.parent_rule_id && (
                    <span className="font-mono text-xs text-muted/50">
                      ↖ parent: {v.parent_rule_id.slice(0, 8)}…
                    </span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </>
  );
}
