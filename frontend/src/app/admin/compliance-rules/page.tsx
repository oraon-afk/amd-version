"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ListChecks, Plus } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { createComplianceRule, createRuleCategory, listComplianceRules, listRuleCategories } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";

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

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Rule Management"
        title="Rule Library"
        description="Build manual rules, organize categories, and manage the searchable rule library used by audit runs."
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
                <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold">{rule.title}</div>
                    <div className="mt-1 text-xs text-muted">{rule.reference ?? "No reference"} - {rule.version}</div>
                  </div>
                  <Badge variant="cyan">{rule.category}</Badge>
                </div>
                <p className="line-clamp-4 text-sm leading-6 text-muted">{rule.rule_text}</p>
              </article>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
