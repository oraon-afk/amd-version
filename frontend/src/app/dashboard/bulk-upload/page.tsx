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
import { bulkUploadDocuments, getUploadBatch, listComplianceDomains } from "@/features/uploads/api";
import { getErrorMessage } from "@/services/api/client";

const terminalStatuses = new Set(["completed", "completed_with_failures", "failed"]);
const MAX_BULK_DOCUMENTS = 100;

type ComplianceFileRow = {
  id: string;
  file: File;
  domain: string;
};

export default function BulkComplianceUploadPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [fileRows, setFileRows] = useState<ComplianceFileRow[]>([]);
  const [defaultDomain, setDefaultDomain] = useState("");
  const [ruleSetId, setRuleSetId] = useState("");
  const [batchId, setBatchId] = useState<string | null>(null);
  const domainsQuery = useQuery({ queryKey: ["compliance-domains"], queryFn: listComplianceDomains });
  const batchQuery = useQuery({
    queryKey: ["upload-batch", batchId],
    queryFn: () => getUploadBatch(batchId!),
    enabled: Boolean(batchId),
    refetchInterval: 2000,
  });
  const batch = batchQuery.data;

  const mutation = useMutation({
    mutationFn: () =>
      bulkUploadDocuments({
        files: fileRows.map((row) => row.file),
        domains: fileRows.map((row) => row.domain),
        ruleSetId,
      }),
    onSuccess: (nextBatch) => {
      setBatchId(nextBatch.id);
      setFileRows([]);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      toast({ title: "Bulk compliance upload queued", description: `${nextBatch.total_documents} document(s) will be audited sequentially.` });
    },
    onError: (error) => toast({ title: "Bulk upload failed", description: getErrorMessage(error), variant: "error" }),
  });

  const completed = batch ? batch.completed_documents + batch.failed_documents : 0;
  const progress = batch && batch.total_documents ? Math.round((completed / batch.total_documents) * 100) : 0;
  const isRunning = Boolean(batch && !terminalStatuses.has(batch.status));
  const queuedCount = batch?.documents.filter((item) => item.status === "queued").length ?? 0;
  const runningCount = batch?.documents.filter((item) => item.status !== "queued" && item.status !== "completed" && item.status !== "failed").length ?? 0;
  const canSubmit = fileRows.length > 0 && fileRows.every((row) => row.domain) && !mutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance Check"
        title="Bulk Upload Documents"
        description="Upload many temporary compliance documents and audit them one at a time against the active rule library."
      />

      <section className="grid gap-5 xl:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Batch Setup</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="block text-sm font-medium">
              Default Domain
              <select
                value={defaultDomain}
                onChange={(event) => {
                  setDefaultDomain(event.target.value);
                  if (event.target.value) {
                    setFileRows((current) => current.map((row) => ({ ...row, domain: row.domain || event.target.value })));
                  }
                }}
                className="mt-2 h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm text-foreground outline-none focus:border-info/70"
              >
                <option value="">{domainsQuery.isLoading ? "Loading domains" : "Optional default"}</option>
                {(domainsQuery.data ?? []).map((item) => (
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
                placeholder="default"
              />
            </label>
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-info/45 bg-elevated p-6 text-center transition hover:border-info/70">
              <UploadCloud className="mb-3 h-10 w-10 text-info" />
              <div className="text-sm font-semibold">Choose compliance documents</div>
              <div className="mt-1 text-xs text-muted">PDF, DOCX, or TXT. Files are queued, then audited sequentially.</div>
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.txt,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
                onChange={(event) => {
                  const result = appendFileRows(fileRows, event.target.files, defaultDomain);
                  setFileRows(result.rows);
                  if (result.rejectedCount > 0) {
                    toast({
                      title: "Bulk upload limit reached",
                      description: `Only ${MAX_BULK_DOCUMENTS} documents can be queued at once.`,
                      variant: "error",
                    });
                  }
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
                      value={row.domain}
                      onChange={(event) => updateRowDomain(setFileRows, row.id, event.target.value)}
                      className="h-10 w-full rounded-lg border border-line bg-panel px-3 text-sm text-foreground outline-none focus:border-info/70"
                      aria-label={`Domain for ${row.file.name}`}
                    >
                      <option value="">Select domain</option>
                      {(domainsQuery.data ?? []).map((item) => (
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
              Start Bulk Compliance Audit
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Batch Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!batch && <p className="rounded-lg border border-line bg-elevated p-4 text-sm text-muted">No active bulk upload batch selected.</p>}
            {batch && (
              <>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                  <Metric label="Total Files" value={String(batch.total_documents)} />
                  <Metric label="Queued" value={String(queuedCount)} />
                  <Metric label="Running" value={String(runningCount)} />
                  <Metric label="Completed" value={String(batch.completed_documents)} />
                  <Metric label="Failed" value={String(batch.failed_documents)} />
                  <Metric label="Progress" value={`${progress}%`} />
                </div>
                <Progress value={progress} />
                <div className="text-sm text-muted">
                  Current: {isRunning ? batch.running_document ?? "Next document" : "Batch processing finished"}
                </div>
                <div className="space-y-2">
                  {batch.documents.map((item) => (
                    <div key={item.id} className="rounded-lg border border-line bg-elevated p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold">{item.filename}</div>
                          <div className="mt-1 text-xs text-muted">
                            Queue #{item.queue_position} - {item.domain ?? "Domain not returned"} - {item.current_stage ?? item.status}
                          </div>
                        </div>
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

function appendFileRows(current: ComplianceFileRow[], fileList: FileList | null, defaultDomain: string) {
  const existingIds = new Set(current.map((row) => row.id));
  const incomingRows: ComplianceFileRow[] = [];
  for (const file of Array.from(fileList ?? [])) {
    const id = fileRowId(file);
    if (existingIds.has(id)) continue;
    existingIds.add(id);
    incomingRows.push({ id, file, domain: defaultDomain });
  }

  const availableSlots = Math.max(0, MAX_BULK_DOCUMENTS - current.length);
  return {
    rows: [...current, ...incomingRows.slice(0, availableSlots)],
    rejectedCount: Math.max(0, incomingRows.length - availableSlots),
  };
}

function fileRowId(file: File) {
  return `${file.name}-${file.lastModified}-${file.size}`;
}

function updateRowDomain(
  setFileRows: (updater: (current: ComplianceFileRow[]) => ComplianceFileRow[]) => void,
  rowId: string,
  domain: string,
) {
  setFileRows((current) => current.map((row) => (row.id === rowId ? { ...row, domain } : row)));
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
  const normalized = status.replaceAll("_", " ");
  if (status === "queued") return "Queued";
  if (status === "extracting" || status === "chunking" || status === "embedding" || status === "processing") return "Processing";
  if (status === "retrieving_rules" || status === "reranking" || status === "analyzing" || status === "generating_report") return "Analyzing";
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  return normalized;
}

function badgeVariant(status: string): "high" | "low" | "muted" | "cyan" {
  if (status === "failed") return "high";
  if (status === "completed") return "low";
  if (status === "queued") return "muted";
  return "cyan";
}
