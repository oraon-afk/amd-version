"use client";

import { AnimatePresence, motion } from "framer-motion";
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

  const stages: WorkflowStage[] = [
    "uploaded",
    "extracting",
    "chunking",
    "embedding",
    "retrieving_rules",
    "reranking",
    "analyzing",
    "generating_report",
    "completed",
    "failed",
  ];
  const activeIndex = stages.findIndex((stageLabel) => stage === stageLabel);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {!stage && <p className="text-sm text-muted">No document is currently processing.</p>}
        <AnimatePresence initial={false}>
          {stages.map((stageLabel, index) => {
            const active = stage === stageLabel;
            const done = stageLabel === "completed" ? stage === "completed" : stageLabel === "failed" ? false : isPast(stage, stageLabel);
            const trail = done && !failed && activeIndex > index;
            return (
              <motion.div
                key={stageLabel}
                layout
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ delay: index * 0.05, duration: 0.3, ease: "easeOut" }}
              >
                <StatusRow
                  label={stageLabel}
                  active={active}
                  done={done}
                  failed={failed}
                  trail={trail}
                />
              </motion.div>
            );
          })}
        </AnimatePresence>
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
  trail,
}: {
  label: WorkflowStage;
  active: boolean;
  done: boolean;
  failed: boolean;
  trail: boolean;
}) {
  const Icon = failed && label === "failed" ? XCircle : active && !done ? Loader2 : done ? CheckCircle2 : Circle;
  const stateKey = failed && label === "failed" ? "failed" : active ? "active" : done ? "done" : "waiting";

  return (
    <motion.div
      layout
      animate={
        active && label !== "failed"
          ? { scale: 1.05, boxShadow: "0 0 20px rgba(124, 77, 255, 0.3)" }
          : { scale: 1, boxShadow: "0 0 0px transparent" }
      }
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className={cn(
        "flex items-center justify-between rounded-lg border border-line bg-white/5 px-3 py-2 text-sm transition-colors",
        active && label !== "failed" && "border-violet/40 bg-violet/10 text-foreground cosmic-glow-orchid",
        active && label === "failed" && "border-riskHigh/40 bg-riskHigh/10 text-riskHigh",
        done && !active && "border-cyan/25 bg-cyan/8",
        failed && label === "failed" && "border-riskHigh/40 bg-riskHigh/10 text-riskHigh",
        trail && "pipeline-trail",
      )}
    >
      <div className="flex items-center gap-2">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={stateKey}
            initial={{ opacity: 0, scale: 0.82 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.82 }}
            transition={{ duration: 0.16 }}
            className="grid h-4 w-4 place-items-center"
          >
            <Icon className={cn("h-4 w-4 text-muted", active && label !== "failed" && "text-violet", active && label === "failed" && "text-riskHigh", done && "text-cyan", failed && label === "failed" && "text-riskHigh", active && !done && "animate-spin")} />
          </motion.span>
        </AnimatePresence>
        <span className="capitalize">{label.replace("_", " ")}</span>
      </div>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={`${stateKey}-copy`}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 4 }}
          transition={{ duration: 0.16 }}
          className="text-xs text-muted"
        >
          {statusText({ label, active, done, failed })}
        </motion.span>
      </AnimatePresence>
    </motion.div>
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
