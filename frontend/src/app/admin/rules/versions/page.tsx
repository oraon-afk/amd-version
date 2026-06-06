"use client";

import { useQuery } from "@tanstack/react-query";
import { FileClock } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listAdminDocuments } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { formatDate } from "@/lib/utils";

export default function RuleVersionsPage() {
  const documentsQuery = useQuery({ queryKey: ["admin-documents"], queryFn: listAdminDocuments });
  const ruleDocuments = documentsQuery.data?.rule_documents ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Rule Management"
        title="Versions"
        description="Permanent rule document versions indexed into the compliance_rules collection."
      />
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Rule Versions</CardTitle>
          <FileClock className="h-5 w-5 text-info" />
        </CardHeader>
        <CardContent className="space-y-3">
          {documentsQuery.isLoading && <Skeleton className="h-32 w-full" />}
          {documentsQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(documentsQuery.error)}</p>}
          {ruleDocuments.map((document) => (
            <div key={document.id} className="rounded-lg border border-line bg-elevated p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold">{document.filename}</div>
                  <div className="mt-1 text-xs text-muted">
                    {document.category ?? "Uncategorized"} - {document.document_type} - {formatDate(document.created_at)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="cyan">{document.version}</Badge>
                  <Badge variant={document.status === "indexed" ? "low" : "medium"}>{document.status}</Badge>
                </div>
              </div>
            </div>
          ))}
          {!documentsQuery.isLoading && ruleDocuments.length === 0 && (
            <p className="rounded-lg border border-line bg-elevated p-4 text-sm text-muted">No rule versions returned.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
