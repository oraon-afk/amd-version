import { Badge, type BadgeProps } from "@/components/ui/badge";

const statusLabels: Record<string, string> = {
  queued: "Queued",
  uploaded: "Queued",
  processing: "Processing",
  extracting: "Processing",
  chunking: "Processing",
  embedding: "Analyzing",
  retrieving_rules: "Analyzing",
  reranking: "Reviewing",
  validating: "Reviewing",
  analyzing: "Analyzing",
  generating_report: "Reporting",
  completed: "Completed",
  failed: "Failed",
  reviewing: "Reviewing",
  indexed: "Indexed",
};

const statusVariants: Record<string, BadgeProps["variant"]> = {
  queued: "muted",
  uploaded: "muted",
  processing: "cyan",
  extracting: "cyan",
  chunking: "cyan",
  embedding: "cyan",
  retrieving_rules: "cyan",
  reranking: "medium",
  validating: "medium",
  analyzing: "cyan",
  generating_report: "medium",
  completed: "low",
  failed: "high",
  reviewing: "medium",
  indexed: "low",
};

export function StatusBadge({ status, label }: { status?: string | null; label?: string }) {
  const normalized = status?.toLowerCase() ?? "";
  return (
    <Badge variant={statusVariants[normalized] ?? "muted"}>
      {label ?? statusLabels[normalized] ?? status ?? "Not returned"}
    </Badge>
  );
}

export function RiskBadge({ risk }: { risk?: string | null }) {
  const normalized = risk?.toLowerCase();
  if (normalized === "critical") return <Badge variant="critical">Critical</Badge>;
  if (normalized === "high") return <Badge variant="high">High</Badge>;
  if (normalized === "medium") return <Badge variant="medium">Medium</Badge>;
  if (normalized === "low") return <Badge variant="low">Low</Badge>;
  return <Badge variant="muted">{risk ?? "Risk n/a"}</Badge>;
}
