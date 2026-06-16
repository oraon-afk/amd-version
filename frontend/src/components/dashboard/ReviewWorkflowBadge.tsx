"use client";

import React from "react";
import { AlertCircle, CheckCircle, Clock, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface ReviewWorkflowBadgeProps {
  status: string;
  className?: string;
}

export function ReviewWorkflowBadge({ status, className }: ReviewWorkflowBadgeProps) {
  let label = status;
  let bgClass = "bg-white/5 text-muted border-white/10";
  let Icon = FileText;

  const normalizedStatus = status.toLowerCase();

  if (normalizedStatus === "pending_review") {
    label = "Pending Review";
    bgClass = "bg-warning/10 text-warning border-warning/30 shadow-[0_0_12px_rgba(255,179,0,0.15)] animate-pulse";
    Icon = Clock;
  } else if (normalizedStatus === "completed" || normalizedStatus === "published") {
    label = "Published";
    bgClass = "bg-success/10 text-success border-success/30 shadow-[0_0_12px_rgba(0,229,255,0.15)]";
    Icon = CheckCircle;
  } else if (normalizedStatus === "under_review") {
    label = "Under Review";
    bgClass = "bg-brand/10 text-brand border-brand/30 shadow-[0_0_12px_rgba(124,77,255,0.15)]";
    Icon = AlertCircle;
  } else if (normalizedStatus === "failed") {
    label = "Failed";
    bgClass = "bg-critical/10 text-critical border-critical/30 shadow-[0_0_12px_rgba(255,23,68,0.15)]";
    Icon = AlertCircle;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider",
        bgClass,
        className
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
    </div>
  );
}
