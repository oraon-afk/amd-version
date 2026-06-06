import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function InfoRow({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon?: LucideIcon;
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-3 rounded-lg border border-line bg-white/5 p-3 text-sm", className)}>
      <div className="flex min-w-0 items-center gap-3">
        {Icon && <Icon className="h-4 w-4 shrink-0 text-info" />}
        <span className="text-muted">{label}</span>
      </div>
      <span className="min-w-0 truncate text-right font-medium text-foreground">{value}</span>
    </div>
  );
}
