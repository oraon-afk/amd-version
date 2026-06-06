"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Trash2, UploadCloud } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { deleteAdminDocument, listAdminDocuments, listRuleCategories, uploadRuleDocument } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";
import { formatDate } from "@/lib/utils";

export default function AdminRuleDocumentsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const documentsQuery = useQuery({ queryKey: ["admin-documents"], queryFn: listAdminDocuments });
  const categoriesQuery = useQuery({ queryKey: ["admin-rule-categories"], queryFn: listRuleCategories });
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("Internal Policies");
  const [ruleSetId, setRuleSetId] = useState("default");
  const [documentType, setDocumentType] = useState("rules");
  const [version, setVersion] = useState("v1");

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a rule document first.");
      return uploadRuleDocument({ file, category, ruleSetId, documentType, version });
    },
    onSuccess: () => {
      setFile(null);
      queryClient.invalidateQueries({ queryKey: ["admin-documents"] });
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Rule document indexed", description: "Embeddings were stored in Qdrant." });
    },
    onError: (error) => toast({ title: "Rule upload failed", description: getErrorMessage(error), variant: "error" }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAdminDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-documents"] });
      toast({ title: "Document deleted" });
    },
    onError: (error) => {
      const description =
        typeof error === "object" && error && "status" in error && error.status === 409
          ? "Document cannot be deleted because dependent audit records still exist."
          : getErrorMessage(error);
      toast({ title: "Delete failed", description, variant: "error" });
    },
  });

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Rule Management"
        title="Upload Rule"
        description="Upload one permanent compliance framework document into compliance_rules. No audit, findings, reports, or compliance score are generated here."
      />
      <section className="grid gap-5 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Upload Rule Document</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="block text-sm font-medium">
              Category
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm outline-none focus:border-info/70"
              >
                {(categoriesQuery.data ?? [{ id: null, name: "Internal Policies", description: null }]).map((item) => (
                  <option key={item.id ?? item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium">
              Rule Set ID
              <Input className="mt-2" value={ruleSetId} onChange={(event) => setRuleSetId(event.target.value)} />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-medium">
                Type
                <select
                  value={documentType}
                  onChange={(event) => setDocumentType(event.target.value)}
                  className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm outline-none focus:border-info/70"
                >
                  <option value="rules">Rules</option>
                  <option value="compliance">Compliance</option>
                  <option value="policies">Policies</option>
                </select>
              </label>
              <label className="block text-sm font-medium">
                Version
                <Input className="mt-2" value={version} onChange={(event) => setVersion(event.target.value)} />
              </label>
            </div>
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-info/45 bg-elevated p-6 text-center transition hover:border-info/70">
              <UploadCloud className="mb-3 h-9 w-9 text-info" />
              <div className="text-sm font-semibold">{file ? file.name : "Choose PDF, DOCX, or TXT"}</div>
              <input
                type="file"
                accept=".pdf,.docx,.txt,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <Button className="w-full" disabled={!file || uploadMutation.isPending} onClick={() => uploadMutation.mutate()}>
              {uploadMutation.isPending ? "Indexing" : "Upload Rule Document"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Rule Uploads</CardTitle>
            <FileText className="h-5 w-5 text-cyan" />
          </CardHeader>
          <CardContent className="space-y-3">
            {documentsQuery.isLoading && <Skeleton className="h-32 w-full" />}
            {documentsQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(documentsQuery.error)}</p>}
            {!documentsQuery.isLoading && documentsQuery.data?.rule_documents.length === 0 && (
              <EmptyState icon={FileText} title="No rule documents uploaded" copy="Upload a rule document to populate the permanent rule library." />
            )}
            {documentsQuery.data?.rule_documents.map((document) => (
              <div key={document.id} className="rounded-lg border border-line bg-elevated p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{document.filename}</div>
                    <div className="mt-1 text-xs text-muted">
                      {document.category ?? "Uncategorized"} - {document.document_type} - {formatDate(document.created_at)}
                    </div>
                    <div className="mt-2 text-xs text-muted">{document.storage_path}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={document.status === "indexed" ? "low" : "medium"}>{document.status}</Badge>
                    <Button size="icon" variant="destructive" onClick={() => deleteMutation.mutate(document.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
