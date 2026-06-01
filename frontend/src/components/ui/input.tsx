import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm text-foreground outline-none transition placeholder:text-muted focus:border-info/70 focus:bg-card",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
