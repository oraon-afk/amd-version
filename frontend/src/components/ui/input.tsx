import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-lg border border-line bg-white/6 px-3 text-sm text-foreground outline-none transition placeholder:text-muted focus:border-violet/70 focus:bg-white/9",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";

