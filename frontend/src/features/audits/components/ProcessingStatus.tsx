"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Audit, UploadedDocument } from "@/types/api";
import { getWorkflowStage, WorkflowStage } from "../status";

export function ProcessingStatus({
  audit,
  document,
  isProcessing = false,
}: {
  audit?: Audit | null;
  document?: UploadedDocument | null;
  isProcessing?: boolean;
}) {
  const stage = getWorkflowStage(audit, document) ?? (isProcessing ? "analyzing" : null);
  const failed = stage === "failed";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!stage && <p className="text-sm text-muted">No document is currently processing.</p>}
        <StatusRow label="uploaded" active={stage === "uploaded"} done={isPast(stage, "uploaded")} failed={failed} />
        <StatusRow label="extracting" active={stage === "extracting"} done={isPast(stage, "extracting")} failed={failed} />
        <StatusRow label="chunking" active={stage === "chunking"} done={isPast(stage, "chunking")} failed={failed} />
        <StatusRow label="embedding" active={stage === "embedding"} done={isPast(stage, "embedding")} failed={failed} />
        <StatusRow label="retrieving_rules" active={stage === "retrieving_rules"} done={isPast(stage, "retrieving_rules")} failed={failed} />
        <StatusRow label="reranking" active={stage === "reranking"} done={isPast(stage, "reranking")} failed={failed} />
        <StatusRow label="analyzing" active={stage === "analyzing"} done={isPast(stage, "analyzing")} failed={failed} />
        <StatusRow label="generating_report" active={stage === "generating_report"} done={isPast(stage, "generating_report")} failed={failed} />
        <StatusRow label="completed" active={stage === "completed"} done={stage === "completed"} failed={failed} />
        <StatusRow label="failed" active={failed} done={false} failed={failed} />
        {audit?.error_message && (
          <p className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-3 text-sm text-riskHigh">
            {audit.error_message}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function StatusRow({
  label,
  active,
  done,
  failed,
}: {
  label: WorkflowStage;
  active: boolean;
  done: boolean;
  failed: boolean;
}) {
  const Icon = failed && label === "failed" ? XCircle : active && !done ? Loader2 : done ? CheckCircle2 : Circle;

  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg border border-line bg-white/5 px-3 py-2 text-sm",
        active && "border-cyan/40 bg-cyan/10 text-foreground",
        done && "border-riskLow/35 bg-riskLow/10",
        failed && label === "failed" && "border-riskHigh/40 bg-riskHigh/10 text-riskHigh",
      )}
    >
      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4 text-muted", active && "text-cyan", done && "text-riskLow", failed && label === "failed" && "text-riskHigh", active && !done && "animate-spin")} />
        <span className="capitalize">{label.replace("_", " ")}</span>
      </div>
      <span className="text-xs text-muted">{statusText({ label, active, done, failed })}</span>
    </div>
  );
}

function statusText({
  label,
  active,
  done,
  failed,
}: {
  label: WorkflowStage;
  active: boolean;
  done: boolean;
  failed: boolean;
}) {
  if (failed && label === "failed") return "Failed";
  if (done) return "Done";
  if (active) return "Running";
  return "Waiting";
}

function isPast(stage: WorkflowStage | null, target: WorkflowStage) {
  if (!stage || stage === "failed") return false;
  if (stage === "completed") return target !== "completed" && target !== "failed";
  return stageRank(stage) > stageRank(target);
}

function stageRank(stage: WorkflowStage) {
  if (stage === "uploaded") return 1;
  if (stage === "extracting") return 2;
  if (stage === "chunking") return 3;
  if (stage === "embedding") return 4;
  if (stage === "retrieving_rules") return 5;
  if (stage === "reranking") return 6;
  if (stage === "analyzing") return 7;
  if (stage === "generating_report") return 8;
  if (stage === "completed") return 9;
  return 0;
}
