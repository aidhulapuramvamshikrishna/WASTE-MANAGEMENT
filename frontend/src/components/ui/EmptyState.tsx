import * as React from "react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
  onAction,
  icon,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "p-12 text-center border border-dashed border-[var(--rule)] bg-[var(--surface)]/50 rounded-[4px] flex flex-col items-center justify-center max-w-lg mx-auto my-8",
        className
      )}
      {...props}
    >
      <div className="p-3 bg-[var(--paper)] text-[var(--ink-2)] rounded-[2px] mb-4">
        {icon || <Inbox className="w-6 h-6 stroke-[1.5]" aria-hidden="true" />}
      </div>
      <h3 className="font-sans font-bold text-base text-[var(--ink)] tracking-tight mb-2">
        {title}
      </h3>
      <p className="font-sans text-xs text-[var(--ink-2)] max-w-sm mb-6 leading-relaxed">
        {description}
      </p>
      {actionLabel && (actionHref || onAction) && (
        <Button
          size="sm"
          variant="primary"
          href={actionHref}
          onClick={onAction}
          withArrow
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
