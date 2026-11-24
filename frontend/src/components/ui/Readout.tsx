import * as React from "react";
import { cn } from "@/lib/utils";

export interface ReadoutProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: React.ReactNode;
  unit?: string;
  monoValue?: boolean;
}

export function Readout({
  label,
  value,
  unit,
  monoValue = true,
  className,
  ...props
}: ReadoutProps) {
  return (
    <div
      className={cn(
        "flex items-baseline justify-between py-2 border-b border-[var(--rule)] text-sm font-sans gap-4",
        className
      )}
      {...props}
    >
      <span className="font-mono text-xs uppercase tracking-wider text-[var(--ink-2)] shrink-0">
        {label}
      </span>
      <span className="flex-1 mx-2 border-b border-dotted border-[var(--rule)] self-center h-0" aria-hidden="true" />
      <span
        className={cn(
          "text-right font-medium text-[var(--ink)]",
          monoValue ? "font-mono text-xs tabular-nums" : "text-sm"
        )}
      >
        {value}
        {unit && <span className="text-[var(--ink-2)] ml-1 font-normal">{unit}</span>}
      </span>
    </div>
  );
}
