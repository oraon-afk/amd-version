"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Circle, FileText, FileUp, Loader2, UploadCloud, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";
import { getAudit } from "@/features/audits/api";
import { ProcessingStatus } from "@/features/audits/components/ProcessingStatus";
import { getErrorMessage } from "@/services/api/client";
import { Audit, UploadedDocument } from "@/types/api";
import { createAudit, listComplianceDomains, uploadDocument } from "../api";

type UploadDropzoneProps = {
  compact?: boolean;
  redirectOnComplete?: boolean;
  onDocumentUploaded?: (document: UploadedDocument) => void;
  onAuditUpdate?: (audit: Audit) => void;
  onAuditComplete?: (audit: Audit) => void;
};

export function UploadDropzone({
  compact = false,
  redirectOnComplete = true,
  onDocumentUploaded,
  onAuditUpdate,
  onAuditComplete,
}: UploadDropzoneProps) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { toast } = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [domain, setDomain] = useState("");
  const [mode, setMode] = useState<"file" | "text">("file");
  const [text, setText] = useState("");
  const [uploadedDocument, setUploadedDocument] = useState<UploadedDocument | null>(null);
  const [latestAudit, setLatestAudit] = useState<Audit | null>(null);
  const [auditRunning, setAuditRunning] = useState(false);
  const [isDragHover, setIsDragHover] = useState(false);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const domainsQuery = useQuery({ queryKey: ["compliance-domains"], queryFn: listComplianceDomains });
  const domains = domainsQuery.data ?? [];
  const domainOptions = domains.map((item) => ({
    value: item.name,
    label: item.name,
    description: item.description,
  }));

  const mutation = useMutation({
    mutationFn: async () => {
      const payloads = prepareUploadPayload({ mode, files, text, title, domain });
      setLatestAudit(null);
      setUploadedDocument(null);
      setAuditRunning(false);

      let completedAudit: Audit | null = null;
      for (const payload of payloads) {
        const document = await uploadDocument(payload);
        setUploadedDocument(document);
        onDocumentUploaded?.(document);

        const audit = await createAudit(document.id);
        setLatestAudit(audit);
        setAuditRunning(true);
        onAuditUpdate?.(audit);

        completedAudit = await waitForAuditCompletion(
          audit.id,
          (nextAudit) => {
            if (!isMounted.current) return;
            setLatestAudit(nextAudit);
            onAuditUpdate?.(nextAudit);
          },
          () => isMounted.current,
        );
      }
      setAuditRunning(false);
      if (!completedAudit) throw new Error("No assessment was created.");
      return completedAudit;
    },
    onSuccess: (audit) => {
      const auditStatus = normalizeWorkflowStatus(audit.status);
      setFiles([]);
      setText("");
      setTitle("");
      queryClient.invalidateQueries({ queryKey: ["audits"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["report", audit.id] });
      queryClient.invalidateQueries({ queryKey: ["compliance-digital-twin"] });
      toast({
        title: auditStatus === "failed" ? "Assessment failed" : "Assessment completed",
        description: auditStatus === "failed" ? audit.error_message ?? "Backend analysis failed." : "Compliance results generated from backend analysis.",
        variant: auditStatus === "failed" ? "error" : "success",
      });
      onAuditComplete?.(audit);
      if (auditStatus === "completed" && redirectOnComplete) router.push(`/dashboard/reports/${audit.id}`);
    },
    onError: (error) => {
      setAuditRunning(false);
      toast({ title: "Upload failed", description: getErrorMessage(error), variant: "error" });
    },
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Upload Document</CardTitle>
        <FileUp className="h-5 w-5 text-cyan" />
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 md:grid-cols-[1fr_220px]">
          <label className="block text-sm font-medium">
            Document Title
            <Input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Document title"
              className="mt-2"
            />
          </label>
          <label className="block text-sm font-medium">
            Domain
            <SearchableSelect
              value={domain}
              onChange={setDomain}
              options={domainOptions}
              placeholder={domainsQuery.isLoading ? "Loading domains" : "Select domain"}
              disabled={domainsQuery.isLoading || domains.length === 0}
              className="mt-2"
              ariaLabel="Compliance domain"
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2 rounded-lg border border-line bg-white/5 p-1">
          <button
            type="button"
            onClick={() => setMode("file")}
            className={`rounded-md px-3 py-2 text-sm transition ${mode === "file" ? "bg-primary/25 text-foreground" : "text-muted hover:text-foreground"}`}
          >
            Single Upload
          </button>
          <button
            type="button"
            onClick={() => setMode("text")}
            className={`rounded-md px-3 py-2 text-sm transition ${mode === "text" ? "bg-primary/25 text-foreground" : "text-muted hover:text-foreground"}`}
          >
            Text Input
          </button>
        </div>

        {mode === "file" ? (
          <motion.label
            whileHover={{ scale: 1.005 }}
            onDragOver={(event) => event.preventDefault()}
            onDragEnter={() => setIsDragHover(true)}
            onDragLeave={() => setIsDragHover(false)}
            onDrop={(event) => {
              event.preventDefault();
              setIsDragHover(false);
              selectFiles(event.dataTransfer.files, setFiles);
            }}
            className={`relative flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed p-6 text-center transition-all duration-300 ${
              isDragHover
                ? "border-cyan bg-cyan/10 shadow-[0_0_30px_rgba(0,229,255,0.25)] cosmic-glow-cyan"
                : "border-primary/45 bg-white/5 hover:border-cyan/60 hover:bg-cyan/5"
            } ${compact ? "min-h-40" : "min-h-52"}`}
          >
            <UploadCloud className={`mb-3 h-10 w-10 transition-colors duration-300 ${isDragHover ? "text-cyan" : "text-cyan/70"}`} />
            <div className="text-sm font-semibold">{isDragHover ? "Release to upload" : "Drop one file or browse"}</div>
            <div className="mt-2 text-xs text-muted">PDF, DOCX, or TXT. Bulk compliance uploads live in the dedicated Bulk Upload screen.</div>
            <div className="mt-4 rounded-lg bg-primary/20 px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-primary/30">Browse Files</div>
            <input
              type="file"
              accept=".pdf,.docx,.txt,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(event) => selectFiles(event.target.files, setFiles)}
              className="hidden"
            />
            <AnimatePresence>
              {files.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mt-4 w-full max-w-xl space-y-2"
                >
                  {files.map((file, index) => (
                    <motion.div
                      key={`${file.name}-${file.lastModified}`}
                      initial={{ scale: 0.85, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0.7, opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.06, type: "spring", stiffness: 300, damping: 25 }}
                      className="antigravity-float-slow flex max-w-full items-center justify-between gap-2 rounded-lg border border-line bg-white/7 px-3 py-2 text-sm"
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <FileText className="h-4 w-4 shrink-0 text-cyan" />
                        <span className="truncate">{file.name}</span>
                      </div>
                      <button
                        type="button"
                        aria-label={`Remove ${file.name}`}
                        className="rounded-md p-1 text-muted transition hover:bg-white/10 hover:text-foreground"
                        onClick={(event) => {
                          event.preventDefault();
                          setFiles((current) => current.filter((item) => item !== file));
                        }}
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.label>
        ) : (
          <Textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste source text for compliance analysis"
          />
        )}

        <AuditWorkflowChecklist
          uploaded={Boolean(uploadedDocument)}
          audit={latestAudit}
          running={auditRunning || mutation.isPending}
          failed={normalizeWorkflowStatus(latestAudit?.status) === "failed" || Boolean(mutation.error)}
        />

        {(uploadedDocument || latestAudit || auditRunning) && (
          <ProcessingStatus audit={latestAudit} document={uploadedDocument} isProcessing={auditRunning} />
        )}

        {domainsQuery.error && (
          <p className="flex items-center gap-2 text-sm text-riskHigh">
            <AlertCircle className="h-4 w-4" /> {getErrorMessage(domainsQuery.error)}
          </p>
        )}
        {mutation.error && <p className="text-sm text-riskHigh">{getErrorMessage(mutation.error)}</p>}
        <Button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="w-full"
        >
          {mutation.isPending ? "Running Assessment" : "Run AI Assessment"}
        </Button>
      </CardContent>
    </Card>
  );
}

function AuditWorkflowChecklist({
  uploaded,
  audit,
  running,
  failed,
}: {
  uploaded: boolean;
  audit: Audit | null;
  running: boolean;
  failed: boolean;
}) {
  const status = normalizeWorkflowStatus(audit?.status);
  const completed = status === "completed";
  const steps = [
    { label: "Uploaded", done: uploaded || completed, active: running && !uploaded, failed: failed && !uploaded },
    { label: "Text Extracted", done: isAtLeast(status, "chunking"), active: status === "processing" || status === "extracting", failed: failed && uploaded },
    { label: "Chunks Prepared", done: isAtLeast(status, "embedding"), active: status === "chunking", failed: failed && uploaded },
    { label: "Embeddings Created", done: isAtLeast(status, "retrieving_rules"), active: status === "embedding", failed: failed && uploaded },
    { label: "Rules Retrieved", done: isAtLeast(status, "reranking"), active: status === "retrieving_rules", failed: failed && uploaded },
    { label: "Rules Reranked", done: isAtLeast(status, "analyzing"), active: status === "reranking", failed: failed && uploaded },
    { label: "Compliance Analysis Complete", done: isAtLeast(status, "generating_report"), active: status === "analyzing" || status === "validating", failed: failed && uploaded },
    { label: "Results Generated", done: completed, active: status === "generating_report", failed: failed && uploaded },
  ];

  return (
    <div className="space-y-2 rounded-lg border border-line bg-black/15 p-3">
      {steps.map((step, index) => (
        <motion.div
          key={step.label}
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.06, duration: 0.3 }}
        >
          <WorkflowLine label={step.label} done={step.done} active={step.active} failed={step.failed} />
        </motion.div>
      ))}
    </div>
  );
}

function WorkflowLine({
  label,
  done,
  active,
  failed,
}: {
  label: string;
  done: boolean;
  active: boolean;
  failed: boolean;
}) {
  const Icon = failed ? AlertCircle : done ? CheckCircle2 : active ? Loader2 : Circle;

  return (
    <motion.div
      animate={active ? { scale: 1.03, backgroundColor: "rgba(124, 77, 255, 0.08)" } : { scale: 1, backgroundColor: "transparent" }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`flex items-center gap-2 rounded-md px-2 py-1 text-sm transition-colors ${active ? "cosmic-glow-orchid" : ""}`}
    >
      <Icon className={`h-4 w-4 ${failed ? "text-riskHigh" : done ? "text-riskLow" : active ? "animate-spin text-cyan" : "text-muted"}`} />
      <span className={failed ? "text-riskHigh" : done ? "text-foreground" : "text-muted"}>{label}</span>
    </motion.div>
  );
}

function prepareUploadPayload({
  mode,
  files,
  text,
  title,
  domain,
}: {
  mode: "file" | "text";
  files: File[];
  text: string;
  title: string;
  domain: string;
}) {
  if (!domain.trim()) throw new Error("Select a compliance domain");
  if (mode === "text") {
    if (!title.trim()) throw new Error("Enter a document title");
    if (text.trim().length < 20) throw new Error("Enter enough text to analyze");
    return [{ title: title.trim(), domain, rawText: text }];
  }

  const selectedFiles = files.slice(0, 1);
  if (selectedFiles.length === 0) throw new Error("Select a file first");
  return selectedFiles.map((file, index) => ({
    title: title.trim() && selectedFiles.length === 1 ? title.trim() : titleFromFile(file.name, index),
    domain,
    file,
  }));
}

function selectFiles(fileList: FileList | null, setFiles: (updater: (current: File[]) => File[]) => void) {
  const nextFiles = Array.from(fileList ?? []);
  if (nextFiles.length === 0) return;
  setFiles(() => nextFiles.slice(0, 1));
}

function titleFromFile(fileName: string, index: number) {
  const title = fileName.replace(/\.[^.]+$/, "").trim();
  return title || `Document ${index + 1}`;
}

async function waitForAuditCompletion(
  auditId: string,
  onUpdate: (audit: Audit) => void,
  isActive: () => boolean,
) {
  const terminalStatuses = new Set(["completed", "failed"]);
  while (isActive()) {
    if (!isActive()) throw new Error("Assessment polling stopped because the upload view was closed.");
    await sleep(1000);
    if (!isActive()) throw new Error("Assessment polling stopped because the upload view was closed.");
    const audit = await getAudit(auditId);
    onUpdate(audit);
    if (terminalStatuses.has(normalizeWorkflowStatus(audit.status))) return audit;
  }
  throw new Error("Assessment polling stopped because the upload view was closed.");
}

function isAtLeast(status: string | null, target: string) {
  const normalizedStatus = normalizeWorkflowStatus(status);
  const normalizedTarget = normalizeWorkflowStatus(target);
  if (normalizedStatus === "completed") return true;
  const order = [
    "uploaded",
    "processing",
    "extracting",
    "chunking",
    "embedding",
    "retrieving_rules",
    "reranking",
    "validating",
    "analyzing",
    "generating_report",
  ];
  if (!normalizedStatus) return false;
  return order.indexOf(normalizedStatus) >= order.indexOf(normalizedTarget);
}

function normalizeWorkflowStatus(status?: string | null) {
  const normalized = String(status ?? "").trim().toLowerCase().replaceAll("-", "_").replaceAll(" ", "_");
  if (normalized === "complete") return "completed";
  if (normalized === "error") return "failed";
  if (normalized === "retrieving" || normalized === "retrieval") return "retrieving_rules";
  if (normalized === "reporting" || normalized === "report_generation") return "generating_report";
  if (normalized === "llm_analysis" || normalized === "compliance_analysis") return "analyzing";
  if (normalized === "extraction" || normalized === "running") return "processing";
  return normalized;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
