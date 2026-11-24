import * as React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  message: string;
  code?: string | number;
  onRetry?: () => void;
}

export function ErrorState({
  title = "System Anomaly / Telemetry Fault",
  message,
  code,
  onRetry,
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "p-6 border border-[var(--special)]/40 bg-[var(--surface)] rounded-[4px] flex flex-col sm:flex-row items-start gap-4",
        className
      )}
      {...props}
    >
      <div className="p-2 bg-[var(--special)]/10 text-[var(--special)] rounded-[2px] shrink-0">
        <AlertTriangle className="w-5 h-5 stroke-[2]" aria-hidden="true" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-1">
          <h4 className="font-sans font-bold text-sm text-[var(--ink)] tracking-tight">
            {title}
          </h4>
          {code && (
            <span className="font-mono text-[11px] uppercase tracking-wider text-[var(--special)] bg-[var(--special)]/10 px-1.5 py-0.5 rounded-[2px]">
              ERR_{code}
            </span>
          )}
        </div>
        <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-4">
          {message}
        </p>
        {onRetry && (
          <Button
            size="sm"
            variant="outline"
            onClick={onRetry}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Retry Sensor Diagnostic
          </Button>
        )}
      </div>
    </div>
  );
}
