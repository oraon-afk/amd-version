import { cn } from "@/lib/utils";

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn("h-2 overflow-hidden rounded-full bg-white/8", className)}>
      <div
        className="progress-fill relative h-full overflow-hidden rounded-full bg-gradient-to-r from-violet to-cyan transition-all"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      >
        <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent" style={{ animation: "shimmer 2s infinite" }} />
      </div>
    </div>
  );
}
