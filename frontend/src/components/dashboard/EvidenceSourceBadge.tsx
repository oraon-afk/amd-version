"use client";

import { Database, Globe, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface EvidenceSourceBadgeProps {
  sourceType: string;
  className?: string;
}

const SOURCE_META: Record<
  string,
  { label: string; icon: React.ElementType; className: string }
> = {
  external_collector: {
    label: "Live Collector",
    icon: Globe,
    className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  compliance_rule: {
    label: "Compliance Rule",
    icon: Database,
    className: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  },
  uploaded_document: {
    label: "Document",
    icon: FileText,
    className: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  },
};

export function EvidenceSourceBadge({
  sourceType,
  className,
}: EvidenceSourceBadgeProps) {
  const meta =
    SOURCE_META[sourceType] ??
    SOURCE_META["uploaded_document"];

  const Icon = meta.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        meta.className,
        className
      )}
    >
      <Icon className="h-3 w-3 flex-shrink-0" />
      {meta.label}
    </span>
  );
}
