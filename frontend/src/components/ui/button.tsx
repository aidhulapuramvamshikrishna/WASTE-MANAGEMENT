import * as React from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  href?: string;
  external?: boolean;
  withArrow?: boolean;
  icon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      href,
      external,
      withArrow = false,
      icon,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-sans font-semibold tracking-tight transition-colors duration-150 rounded-[2px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--paper)] disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    const sizeStyles = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-10 px-4 text-sm gap-2",
      lg: "h-12 px-6 text-base gap-2.5",
    }[size];

    const variantStyles = {
      primary:
        "bg-[var(--hivis)] text-[#0E1A16] hover:brightness-95 active:brightness-90 shadow-none font-bold",
      outline:
        "border border-[var(--rule)] bg-transparent text-[var(--ink)] hover:bg-[var(--surface)] hover:border-[var(--ink-2)] active:bg-[var(--paper)]",
      ghost:
        "bg-transparent text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface)] active:bg-[var(--paper)]",
      danger:
        "bg-[var(--special)] text-white hover:brightness-95 active:brightness-90 shadow-none",
    }[variant];

    const arrowIcon = withArrow ? (
      external ? (
        <ArrowUpRight className="w-4 h-4 shrink-0 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      ) : (
        <ArrowRight className="w-4 h-4 shrink-0 transition-transform group-hover:translate-x-0.5" />
      )
    ) : null;

    const content = (
      <>
        {icon && <span className="shrink-0">{icon}</span>}
        <span>{children}</span>
        {arrowIcon}
      </>
    );

    if (href) {
      if (external) {
        return (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(baseStyles, sizeStyles, variantStyles, "group", className)}
          >
            {content}
          </a>
        );
      }
      return (
        <Link
          href={href}
          className={cn(baseStyles, sizeStyles, variantStyles, "group", className)}
        >
          {content}
        </Link>
      );
    }

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(baseStyles, sizeStyles, variantStyles, "group", className)}
        {...props}
      >
        {content}
      </button>
    );
  }
);
Button.displayName = "Button";
