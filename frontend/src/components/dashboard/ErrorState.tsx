import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/services/api/client";

export function ErrorState({
  error,
  onRetry,
  title = "Unable to load data",
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
}) {
  return (
    <div className="rounded-lg border border-riskHigh/30 bg-riskHigh/10 p-4 text-sm text-riskHigh">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 gap-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="min-w-0">
            <div className="font-semibold">{title}</div>
            <p className="mt-1 text-riskHigh/90">{getErrorMessage(error)}</p>
          </div>
        </div>
        {onRetry && (
          <Button type="button" size="sm" variant="secondary" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" /> Retry
          </Button>
        )}
      </div>
    </div>
  );
}
