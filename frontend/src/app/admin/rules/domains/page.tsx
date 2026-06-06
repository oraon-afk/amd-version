"use client";

import { useQuery } from "@tanstack/react-query";
import { Database } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listRuleCategories } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";

export default function RuleDomainsPage() {
  const categoriesQuery = useQuery({ queryKey: ["admin-rule-categories"], queryFn: listRuleCategories });
  const categories = categoriesQuery.data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Rule Management"
        title="Domains"
        description="Compliance framework domains used to classify rule libraries and retrieval filters."
      />
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Rule Domains</CardTitle>
          <Database className="h-5 w-5 text-info" />
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {categoriesQuery.isLoading && Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-24 w-full" />)}
          {categoriesQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(categoriesQuery.error)}</p>}
          {categories.map((category) => (
            <div key={category.id ?? category.name} className="rounded-lg border border-line bg-elevated p-4">
              <div className="text-sm font-semibold">{category.name}</div>
              <p className="mt-2 text-sm text-muted">{category.description ?? "No description returned."}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
