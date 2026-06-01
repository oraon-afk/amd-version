import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
  {
    variants: {
      variant: {
        default: "border-primary/35 bg-primary/15 text-info",
        critical: "border-red-500/40 bg-red-500/15 text-red-300",
        high: "border-riskHigh/35 bg-riskHigh/15 text-riskHigh",
        medium: "border-riskMedium/35 bg-riskMedium/15 text-riskMedium",
        low: "border-riskLow/35 bg-riskLow/15 text-riskLow",
        cyan: "border-cyan/35 bg-cyan/15 text-cyan",
        muted: "border-line bg-white/6 text-muted",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export function riskVariant(risk?: string | null): BadgeProps["variant"] {
  if (risk === "CRITICAL") return "critical";
  if (risk === "HIGH") return "high";
  if (risk === "MEDIUM") return "medium";
  if (risk === "LOW") return "low";
  return "muted";
}
