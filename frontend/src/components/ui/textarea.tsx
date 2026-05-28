import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-36 w-full resize-none rounded-lg border border-line bg-white/6 px-3 py-3 text-sm text-foreground outline-none transition placeholder:text-muted focus:border-violet/70 focus:bg-white/9",
        className,
      )}
      {...props}
    />
  ),
);

Textarea.displayName = "Textarea";

