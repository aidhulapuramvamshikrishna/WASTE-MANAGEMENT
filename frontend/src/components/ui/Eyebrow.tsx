import * as React from "react";
import { cn } from "@/lib/utils";

export interface EyebrowProps extends React.HTMLAttributes<HTMLDivElement> {
  step?: string;
}

export function Eyebrow({ className, step, children, ...props }: EyebrowProps) {
  return (
    <div
      className={cn(
        "font-mono text-xs uppercase tracking-[0.08em] font-medium text-[var(--ink-2)] flex items-center gap-2 select-none",
        className
      )}
      {...props}
    >
      {step && (
        <>
          <span className="text-[var(--ink)] font-bold">{step}</span>
          <span className="text-[var(--rule)]" aria-hidden="true">
            /
          </span>
        </>
      )}
      <span>{children}</span>
    </div>
  );
}
