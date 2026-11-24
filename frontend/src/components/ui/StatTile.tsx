import * as React from "react";
import { cn } from "@/lib/utils";

export interface StatTileProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string | number;
  label: string;
  sublabel?: string;
  unit?: string;
  highlight?: boolean;
}

export function StatTile({
  value,
  label,
  sublabel,
  unit,
  highlight = false,
  className,
  ...props
}: StatTileProps) {
  return (
    <div
      className={cn(
        "p-5 md:p-6 bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] flex flex-col justify-between transition-colors",
        highlight && "border-[var(--hivis)] bg-[var(--surface)]",
        className
      )}
      {...props}
    >
      <div className="flex items-baseline gap-1.5">
        <span
          className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight font-sans text-[var(--ink)]"
          style={{ fontStretch: "75%" }}
        >
          {value}
        </span>
        {unit && (
          <span className="font-mono text-sm md:text-base font-medium text-[var(--ink-2)]">
            {unit}
          </span>
        )}
      </div>
      <div className="mt-4 pt-3 border-t border-[var(--rule)]">
        <div className="font-mono text-xs uppercase tracking-wider font-medium text-[var(--ink-2)]">
          {label}
        </div>
        {sublabel && (
          <div className="font-mono text-[11px] text-[var(--ink-2)] mt-0.5 opacity-80">
            {sublabel}
          </div>
        )}
      </div>
    </div>
  );
}
