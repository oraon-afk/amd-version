import { type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const toneClasses = {
  cyan: "border-cyan/35 bg-cyan/10 text-cyan",
  low: "border-riskLow/35 bg-riskLow/10 text-riskLow",
  medium: "border-riskMedium/35 bg-riskMedium/10 text-riskMedium",
  high: "border-riskHigh/35 bg-riskHigh/10 text-riskHigh",
  muted: "border-line bg-white/6 text-muted",
};

export function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = "cyan",
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  detail?: string;
  tone?: keyof typeof toneClasses;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">{label}</div>
            <div className="mt-2 text-3xl font-semibold tracking-tight">{value}</div>
          </div>
          <div className={cn("grid h-10 w-10 place-items-center rounded-lg border", toneClasses[tone])}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {detail && <p className="mt-3 text-sm text-muted">{detail}</p>}
      </CardContent>
    </Card>
  );
}
