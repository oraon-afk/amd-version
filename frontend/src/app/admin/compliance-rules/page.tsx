"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Edit3, GitBranch, History, ListChecks, Plus, Save, Trash2, X } from "lucide-react";
import { useState } from "react";
import { BulkRuleImport } from "@/components/dashboard/BulkRuleImport";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { RuleVersionHistory } from "@/components/dashboard/RuleVersionHistory";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import {
  archiveComplianceRule,
  createComplianceRule,
  createRuleCategory,
  deleteComplianceRule,
  listComplianceRules,
  listRuleCategories,
  updateComplianceRule,
} from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { ComplianceRule } from "@/types/api";

export default function AdminComplianceRulesPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const rulesQuery = useQuery({ queryKey: ["admin-compliance-rules"], queryFn: listComplianceRules });
  const categoriesQuery = useQuery({ queryKey: ["admin-rule-categories"], queryFn: listRuleCategories });
  const [category, setCategory] = useState("Internal Policies");
  const [title, setTitle] = useState("");
  const [reference, setReference] = useState("");
  const [version, setVersion] = useState("v1");
  const [ruleText, setRuleText] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [editingRule, setEditingRule] = useState<ComplianceRule | null>(null);
  const [versionHistoryRule, setVersionHistoryRule] = useState<ComplianceRule | null>(null);

  const createRuleMutation = useMutation({
    mutationFn: () => createComplianceRule({ category, title, reference, version, rule_text: ruleText }),
    onSuccess: () => {
      setTitle("");
      setReference("");
      setRuleText("");
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Compliance rule created" });
    },
    onError: (error) => toast({ title: "Create rule failed", description: getErrorMessage(error), variant: "error" }),
  });

  const createCategoryMutation = useMutation({
    mutationFn: () => createRuleCategory({ name: newCategory }),
    onSuccess: () => {
      setNewCategory("");
      queryClient.invalidateQueries({ queryKey: ["admin-rule-categories"] });
      toast({ title: "Category created" });
    },
    onError: (error) => toast({ title: "Create category failed", description: getErrorMessage(error), variant: "error" }),
  });

  const updateRuleMutation = useMutation({
    mutationFn: () => {
      if (!editingRule) throw new Error("Choose a rule to edit.");
      return updateComplianceRule(editingRule.id, {
        category: editingRule.category,
        title: editingRule.title,
        reference: editingRule.reference ?? "",
        version: editingRule.version,
        rule_text: editingRule.rule_text,
        description: editingRule.description ?? undefined,
        status: editingRule.status === "archived" ? "archived" : "active",
      });
    },
    onSuccess: () => {
      setEditingRule(null);
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Compliance rule updated" });
    },
    onError: (error) => toast({ title: "Update rule failed", description: getErrorMessage(error), variant: "error" }),
  });

  const archiveRuleMutation = useMutation({
    mutationFn: archiveComplianceRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Compliance rule archived" });
    },
    onError: (error) => toast({ title: "Archive rule failed", description: getErrorMessage(error), variant: "error" }),
  });

  const deleteRuleMutation = useMutation({
    mutationFn: deleteComplianceRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Compliance rule deleted" });
    },
    onError: (error) => toast({ title: "Delete rule failed", description: getErrorMessage(error), variant: "error" }),
  });

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Rule Management"
        title="Rule Library"
        description="Build manual rules, organize categories, and manage the searchable rule library used by audit runs."
      />

      {/* Version History Drawer */}
      <RuleVersionHistory
        rule={versionHistoryRule}
        isOpen={!!versionHistoryRule}
        onClose={() => setVersionHistoryRule(null)}
      />
      <section className="grid gap-5 xl:grid-cols-[430px_1fr]">
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Create Rule Category</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input value={newCategory} onChange={(event) => setNewCategory(event.target.value)} placeholder="Category name" />
              <Button className="w-full" disabled={newCategory.trim().length < 2 || createCategoryMutation.isPending} onClick={() => createCategoryMutation.mutate()}>
                <Plus className="h-4 w-4" /> Add Category
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Create Manual Rule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm outline-none focus:border-info/70"
              >
                {(categoriesQuery.data ?? [{ id: null, name: "Internal Policies", description: null }]).map((item) => (
                  <option key={item.id ?? item.name} value={item.name}>{item.name}</option>
                ))}
              </select>
              <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Rule title" />
              <div className="grid gap-3 sm:grid-cols-2">
                <Input value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Reference" />
                <Input value={version} onChange={(event) => setVersion(event.target.value)} placeholder="Version" />
              </div>
              <Textarea value={ruleText} onChange={(event) => setRuleText(event.target.value)} placeholder="Rule text" />
              <Button className="w-full" disabled={title.trim().length < 2 || ruleText.trim().length < 5 || createRuleMutation.isPending} onClick={() => createRuleMutation.mutate()}>
                Create Rule
              </Button>
            </CardContent>
          </Card>

          <BulkRuleImport onImportComplete={() => queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] })} />
        </div>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Rules Library</CardTitle>
            <ListChecks className="h-5 w-5 text-cyan" />
          </CardHeader>
          <CardContent className="space-y-3">
            {rulesQuery.isLoading && <Skeleton className="h-32 w-full" />}
            {rulesQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(rulesQuery.error)}</p>}
            {!rulesQuery.isLoading && rulesQuery.data?.length === 0 && (
              <EmptyState icon={ListChecks} title="No rule documents uploaded" copy="Upload rule documents or create a manual rule to populate the library." />
            )}
            {rulesQuery.data?.map((rule) => (
              <article key={rule.id} className="rounded-lg border border-line bg-elevated p-4">
                {editingRule?.id === rule.id ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Input value={editingRule.title} onChange={(event) => setEditingRule({ ...editingRule, title: event.target.value })} />
                      <Input value={editingRule.version} onChange={(event) => setEditingRule({ ...editingRule, version: event.target.value })} />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Input value={editingRule.category} onChange={(event) => setEditingRule({ ...editingRule, category: event.target.value })} />
                      <Input value={editingRule.reference ?? ""} onChange={(event) => setEditingRule({ ...editingRule, reference: event.target.value })} />
                    </div>
                    <Textarea value={editingRule.rule_text} onChange={(event) => setEditingRule({ ...editingRule, rule_text: event.target.value })} />
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => updateRuleMutation.mutate()} disabled={updateRuleMutation.isPending}>
                        <Save className="h-4 w-4" /> Save
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setEditingRule(null)}>
                        <X className="h-4 w-4" /> Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="break-words text-sm font-semibold">{rule.title}</div>
                        <div className="mt-1 text-xs text-muted">{rule.reference ?? "No reference"} - Version: {rule.version_number ?? 1} ({rule.version})</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant={rule.status === "archived" ? "muted" : "cyan"}>{rule.status}</Badge>
                        <Badge variant="cyan">{rule.category}</Badge>
                      </div>
                    </div>
                    <p className="line-clamp-4 text-sm leading-6 text-muted">{rule.rule_text}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button size="sm" variant="secondary" onClick={() => setEditingRule(rule)}>
                        <Edit3 className="h-4 w-4" /> Edit
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setVersionHistoryRule(rule)}>
                        <History className="h-4 w-4" /> History
                      </Button>
                      <Button size="sm" variant="secondary" disabled={rule.status === "archived" || archiveRuleMutation.isPending} onClick={() => archiveRuleMutation.mutate(rule.id)}>
                        <Archive className="h-4 w-4" /> Archive
                      </Button>
                      <Button size="sm" variant="destructive" disabled={deleteRuleMutation.isPending} onClick={() => deleteRuleMutation.mutate(rule.id)}>
                        <Trash2 className="h-4 w-4" /> Delete
                      </Button>
                    </div>
                  </>
                )}
              </article>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
