import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  copy,
  action,
}: {
  icon: LucideIcon;
  title: string;
  copy: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-white/4 p-8 text-center">
      <Icon className="mx-auto mb-3 h-8 w-8 text-cyan" />
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mx-auto mt-2 max-w-sm text-sm text-muted">{copy}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
