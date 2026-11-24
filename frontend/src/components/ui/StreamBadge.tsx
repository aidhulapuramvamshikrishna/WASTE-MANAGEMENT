import * as React from "react";
import { HelpCircle, Leaf, Package, ShieldAlert, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StreamType } from "@/lib/types";

export interface StreamBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  stream: StreamType | "uncertain" | string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
}

export function getStreamMeta(stream: string) {
  const normalized = stream.toLowerCase().replace(/[\s-]/g, "_");
  switch (normalized) {
    case "wet":
      return {
        label: "Wet Waste",
        colorClass: "bg-[var(--wet)] text-white",
        borderClass: "border-[var(--wet)]",
        textClass: "text-[var(--wet)]",
        icon: Leaf,
        binName: "Green Bin (Compost)",
      };
    case "dry":
      return {
        label: "Dry Waste",
        colorClass: "bg-[var(--dry)] text-white",
        borderClass: "border-[var(--dry)]",
        textClass: "text-[var(--dry)]",
        icon: Package,
        binName: "Blue Bin (Recycling / MRF)",
      };
    case "sanitary":
      return {
        label: "Sanitary",
        colorClass: "bg-[var(--sanitary)] text-white",
        borderClass: "border-[var(--sanitary)]",
        textClass: "text-[var(--sanitary)]",
        icon: ShieldAlert,
        binName: "Yellow / Incineration",
      };
    case "special_care":
    case "special":
      return {
        label: "Special Care",
        colorClass: "bg-[var(--special)] text-white",
        borderClass: "border-[var(--special)]",
        textClass: "text-[var(--special)]",
        icon: TriangleAlert,
        binName: "Red / Hazardous E-Waste",
      };
    case "uncertain":
      return {
        label: "Uncertain",
        colorClass: "bg-[var(--caution)] text-white",
        borderClass: "border-[var(--caution)]",
        textClass: "text-[var(--caution)]",
        icon: HelpCircle,
        binName: "Manual Inspection Required",
      };
    default:
      return {
        label: stream,
        colorClass: "bg-[var(--ink-2)] text-white",
        borderClass: "border-[var(--ink-2)]",
        textClass: "text-[var(--ink-2)]",
        icon: Package,
        binName: "General Municipal Stream",
      };
  }
}

export function StreamBadge({
  stream,
  size = "md",
  showIcon = true,
  className,
  ...props
}: StreamBadgeProps) {
  const meta = getStreamMeta(stream);
  const Icon = meta.icon;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px] gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
    lg: "px-3.5 py-1.5 text-sm gap-2",
  }[size];

  const iconSizes = {
    sm: "w-3 h-3",
    md: "w-3.5 h-3.5",
    lg: "w-4 h-4",
  }[size];

  return (
    <span
      className={cn(
        "inline-flex items-center font-mono font-medium uppercase tracking-wider rounded-[2px]",
        meta.colorClass,
        sizeClasses,
        className
      )}
      {...props}
    >
      {showIcon && <Icon className={cn(iconSizes, "shrink-0 stroke-[1.75]")} aria-hidden="true" />}
      <span>{meta.label}</span>
    </span>
  );
}
