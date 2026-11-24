import * as React from "react";
import { cn } from "@/lib/utils";

export interface RuleProps extends React.HTMLAttributes<HTMLHRElement> {
  orientation?: "horizontal" | "vertical";
  variant?: "solid" | "dotted" | "dashed";
}

export function Rule({
  orientation = "horizontal",
  variant = "solid",
  className,
  ...props
}: RuleProps) {
  if (orientation === "vertical") {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={cn(
          "w-[1px] h-full bg-[var(--rule)] self-stretch",
          variant === "dotted" && "border-r border-dotted border-[var(--rule)] bg-transparent",
          variant === "dashed" && "border-r border-dashed border-[var(--rule)] bg-transparent",
          className
        )}
        {...(props as React.HTMLAttributes<HTMLDivElement>)}
      />
    );
  }

  return (
    <hr
      className={cn(
        "w-full border-t border-[var(--rule)] my-6",
        variant === "dotted" && "border-dotted",
        variant === "dashed" && "border-dashed",
        className
      )}
      {...props}
    />
  );
}
