"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, UploadCloud, X } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/toast";
import { bulkUploadRuleDocuments, getRuleUploadBatch, listRuleCategories } from "@/services/admin/admin-service";
import { getErrorMessage } from "@/services/api/client";

const terminalStatuses = new Set(["completed", "completed_with_failures", "failed"]);

type RuleFileRow = {
  id: string;
  file: File;
  category: string;
};

export default function BulkRuleUploadPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [fileRows, setFileRows] = useState<RuleFileRow[]>([]);
  const [ruleSetId, setRuleSetId] = useState("default");
  const [category, setCategory] = useState("Internal Policies");
  const [documentType, setDocumentType] = useState("rules");
  const [version, setVersion] = useState("v1");
  const [batchId, setBatchId] = useState<string | null>(null);
  const categoriesQuery = useQuery({ queryKey: ["admin-rule-categories"], queryFn: listRuleCategories });
  const batchQuery = useQuery({
    queryKey: ["rule-upload-batch", batchId],
    queryFn: () => getRuleUploadBatch(batchId!),
    enabled: Boolean(batchId),
    refetchInterval: 2000,
  });
  const batch = batchQuery.data;

  const mutation = useMutation({
    mutationFn: () =>
      bulkUploadRuleDocuments({
        files: fileRows.map((row) => row.file),
        categories: fileRows.map((row) => row.category),
        ruleSetId,
        category,
        documentType,
        version,
      }),
    onSuccess: (nextBatch) => {
      setBatchId(nextBatch.id);
      setFileRows([]);
      queryClient.invalidateQueries({ queryKey: ["admin-documents"] });
      queryClient.invalidateQueries({ queryKey: ["admin-compliance-rules"] });
      toast({ title: "Bulk rule upload queued", description: `${nextBatch.total_documents} rule document(s) will be indexed sequentially.` });
    },
    onError: (error) => toast({ title: "Bulk rule upload failed", description: getErrorMessage(error), variant: "error" }),
  });

  const completed = batch ? batch.completed_documents + batch.failed_documents : 0;
  const progress = batch && batch.total_documents ? Math.round((completed / batch.total_documents) * 100) : 0;
  const isRunning = Boolean(batch && !terminalStatuses.has(batch.status));
  const queuedCount = batch?.documents.filter((item) => item.status === "queued").length ?? 0;
  const runningCount = batch?.documents.filter((item) => item.status !== "queued" && item.status !== "completed" && item.status !== "failed").length ?? 0;
  const canSubmit = fileRows.length > 0 && fileRows.every((row) => row.category) && Boolean(ruleSetId) && !mutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Rule Management"
        title="Bulk Rule Upload"
        description="Index many permanent rule documents into the compliance rule collection without running audits or generating findings."
      />

      <section className="grid gap-5 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Rule Batch Setup</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="block text-sm font-medium">
              Default Domain / Category
              <select
                value={category}
                onChange={(event) => {
                  setCategory(event.target.value);
                  if (event.target.value) {
                    setFileRows((current) => current.map((row) => ({ ...row, category: row.category || event.target.value })));
                  }
                }}
                className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm text-foreground outline-none focus:border-info/70"
              >
                {(categoriesQuery.data ?? [{ id: null, name: "Internal Policies", description: null }]).map((item) => (
                  <option key={item.id ?? item.name} value={item.name}>{item.name}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium">
              Rule Set ID
              <input
                value={ruleSetId}
                onChange={(event) => setRuleSetId(event.target.value)}
                className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm text-foreground outline-none focus:border-info/70"
              />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-medium">
                Type
                <select
                  value={documentType}
                  onChange={(event) => setDocumentType(event.target.value)}
                  className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm text-foreground outline-none focus:border-info/70"
                >
                  <option value="rules">Rules</option>
                  <option value="compliance">Compliance</option>
                  <option value="policies">Policies</option>
                </select>
              </label>
              <label className="block text-sm font-medium">
                Version
                <input
                  value={version}
                  onChange={(event) => setVersion(event.target.value)}
                  className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm text-foreground outline-none focus:border-info/70"
                />
              </label>
            </div>
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-info/45 bg-elevated p-6 text-center transition hover:border-info/70">
              <UploadCloud className="mb-3 h-10 w-10 text-info" />
              <div className="text-sm font-semibold">Choose rule documents</div>
              <div className="mt-1 text-xs text-muted">PDF, DOCX, or TXT. Files are indexed sequentially into compliance_rules.</div>
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.txt,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={(event) => {
                  setFileRows((current) => appendRuleFileRows(current, event.target.files, category));
                  event.currentTarget.value = "";
                }}
              />
            </label>
            {fileRows.length > 0 && (
              <div className="max-h-72 space-y-2 overflow-auto rounded-lg border border-line bg-card p-2">
                {fileRows.map((row) => (
                  <div key={row.id} className="grid gap-3 rounded-md bg-elevated px-3 py-2 text-sm md:grid-cols-[minmax(0,1fr)_220px_32px] md:items-center">
                    <div className="flex min-w-0 items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-info" />
                      <span className="truncate">{row.file.name}</span>
                    </div>
                    <select
                      value={row.category}
                      onChange={(event) => updateRowCategory(setFileRows, row.id, event.target.value)}
                      className="h-10 w-full rounded-lg border border-line bg-panel px-3 text-sm text-foreground outline-none focus:border-info/70"
                      aria-label={`Domain or category for ${row.file.name}`}
                    >
                      {(categoriesQuery.data ?? [{ id: null, name: "Internal Policies", description: null }]).map((item) => (
                        <option key={item.id ?? item.name} value={item.name}>{item.name}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      aria-label={`Remove ${row.file.name}`}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted transition hover:bg-white/10 hover:text-foreground"
                      onClick={() => setFileRows((current) => current.filter((item) => item.id !== row.id))}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <Button
              className="w-full"
              disabled={!canSubmit}
              onClick={() => mutation.mutate()}
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Start Bulk Rule Indexing
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rule Batch Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!batch && <p className="rounded-lg border border-line bg-elevated p-4 text-sm text-muted">No active rule upload batch selected.</p>}
            {batch && (
              <>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                  <Metric label="Total Files" value={String(batch.total_documents)} />
                  <Metric label="Queued" value={String(queuedCount)} />
                  <Metric label="Running" value={String(runningCount)} />
                  <Metric label="Indexed" value={String(batch.completed_documents)} />
                  <Metric label="Failed" value={String(batch.failed_documents)} />
                  <Metric label="Progress" value={`${progress}%`} />
                </div>
                <Progress value={progress} />
                <div className="text-sm text-muted">
                  Current: {isRunning ? batch.running_document ?? "Next rule document" : "Rule batch finished"}
                </div>
                <div className="space-y-2">
                  {batch.documents.map((item) => (
                    <div key={item.id} className="rounded-lg border border-line bg-elevated p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="truncate text-sm font-semibold">{item.filename}</div>
                        <Badge variant={badgeVariant(item.status)}>{statusLabel(item.status)}</Badge>
                      </div>
                      {item.error_message && <p className="mt-2 text-xs text-riskHigh">{item.error_message}</p>}
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function appendRuleFileRows(current: RuleFileRow[], fileList: FileList | null, category: string): RuleFileRow[] {
  const existingIds = new Set(current.map((row) => row.id));
  const rows = [...current];
  for (const file of Array.from(fileList ?? [])) {
    const id = ruleFileRowId(file);
    if (existingIds.has(id)) continue;
    existingIds.add(id);
    rows.push({ id, file, category });
  }
  return rows;
}

function ruleFileRowId(file: File) {
  return `${file.name}-${file.lastModified}-${file.size}`;
}

function updateRowCategory(
  setFileRows: (updater: (current: RuleFileRow[]) => RuleFileRow[]) => void,
  rowId: string,
  category: string,
) {
  setFileRows((current) => current.map((row) => (row.id === rowId ? { ...row, category } : row)));
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-elevated p-3">
      <div className="text-xs uppercase text-muted">{label}</div>
      <div className="mt-2 text-sm font-semibold capitalize">{value}</div>
    </div>
  );
}

function statusLabel(status: string) {
  if (status === "queued") return "Queued";
  if (status === "processing") return "Processing";
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  return status.replaceAll("_", " ");
}

function badgeVariant(status: string): "high" | "low" | "muted" | "cyan" {
  if (status === "failed") return "high";
  if (status === "completed") return "low";
  if (status === "queued") return "muted";
  return "cyan";
}
