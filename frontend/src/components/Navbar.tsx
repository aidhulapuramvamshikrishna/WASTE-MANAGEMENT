"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Moon, Sun, X } from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", label: "Scan", prefetch: true },
  { href: "/history", label: "History", prefetch: true },
  { href: "/insights", label: "Insights", prefetch: true },
  { href: "/model", label: "Model", prefetch: true },
  { href: "/about", label: "About", prefetch: true },
];

export function Navbar() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const menuButtonRef = React.useRef<HTMLButtonElement>(null);
  const mobileNavRef = React.useRef<HTMLDivElement>(null);

  // Close mobile menu on Escape and return focus to button
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && mobileMenuOpen) {
        setMobileMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mobileMenuOpen]);

  // Close mobile menu when pathname changes (render-time state adjustment pattern)
  const [prevPathname, setPrevPathname] = React.useState(pathname);
  if (pathname !== prevPathname) {
    setPrevPathname(pathname);
    setMobileMenuOpen(false);
  }

  return (
    <>
      {/* WCAG 2.2 Skip Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-[var(--hivis)] focus:text-[#0E1A16] focus:font-mono focus:text-xs focus:font-bold focus:outline-none focus:ring-2 focus:ring-[var(--ink)]"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-40 w-full bg-[var(--paper)]/95 backdrop-blur-sm border-b border-[var(--rule)] transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Brand Mark + Wordmark */}
          <Link
            href="/"
            className="flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] rounded-[2px]"
          >
            {/* 2x2 Stream Mark (DESIGN.md §8) */}
            <div
              className="grid grid-cols-2 gap-[2px] w-4 h-4 p-[1px] bg-[var(--surface)] border border-[var(--rule)] rounded-[1px] shrink-0"
              aria-hidden="true"
            >
              <span className="w-1.5 h-1.5 bg-[var(--wet)] rounded-[0.5px]" title="Wet" />
              <span className="w-1.5 h-1.5 bg-[var(--dry)] rounded-[0.5px]" title="Dry" />
              <span className="w-1.5 h-1.5 bg-[var(--sanitary)] rounded-[0.5px]" title="Sanitary" />
              <span className="w-1.5 h-1.5 bg-[var(--special)] rounded-[0.5px]" title="Special Care" />
            </div>

            {/* Wordmark in condensed Archivo 800 */}
            <span
              className="font-sans font-extrabold text-lg tracking-tight uppercase text-[var(--ink)] select-none"
              style={{ fontStretch: "75%" }}
            >
              EcoSort
            </span>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 sm:gap-2" aria-label="Main navigation">
            {NAV_LINKS.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname?.startsWith(link.href);

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  prefetch={link.prefetch}
                  className={cn(
                    "relative px-3 py-1.5 text-xs sm:text-sm font-sans font-medium transition-colors select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] rounded-[2px]",
                    isActive
                      ? "text-[var(--ink)] font-semibold"
                      : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  {link.label}
                  {isActive && (
                    <span
                      className="absolute bottom-0 left-2 right-2 h-[2px] bg-[var(--hivis)]"
                      aria-hidden="true"
                    />
                  )}
                </Link>
              );
            })}

            {/* Theme Toggle Button */}
            <div className="ml-2 pl-2 border-l border-[var(--rule)]">
              <button
                type="button"
                onClick={toggleTheme}
                aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
                className="p-1.5 text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface)] border border-transparent hover:border-[var(--rule)] rounded-[2px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-pointer"
              >
                {theme === "light" ? (
                  <Moon className="w-4 h-4" aria-hidden="true" />
                ) : (
                  <Sun className="w-4 h-4" aria-hidden="true" />
                )}
              </button>
            </div>
          </nav>

          {/* Mobile Right Controls: Theme Toggle + Menu Disclosure Button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              className="p-2 text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-pointer"
            >
              {theme === "light" ? (
                <Moon className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Sun className="w-4 h-4" aria-hidden="true" />
              )}
            </button>

            <button
              id="mobile-menu-toggle"
              ref={menuButtonRef}
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-nav"
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              className="p-2 text-[var(--ink)] bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] hover:border-[var(--ink)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-pointer"
            >
              {mobileMenuOpen ? (
                <X className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Menu className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Disclosure Nav Panel */}
        {mobileMenuOpen && (
          <div
            id="mobile-nav"
            ref={mobileNavRef}
            className="md:hidden border-t border-[var(--rule)] bg-[var(--surface)] px-4 py-3 shadow-lg"
            aria-label="Mobile navigation"
          >
            <div className="flex flex-col divide-y divide-[var(--rule)]">
              {NAV_LINKS.map((link) => {
                const isActive =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname?.startsWith(link.href);

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    prefetch={link.prefetch}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center justify-between py-3 font-sans text-sm font-medium transition-colors select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)]",
                      isActive
                        ? "text-[var(--ink)] font-bold"
                        : "text-[var(--ink-2)] hover:text-[var(--ink)]"
                    )}
                    aria-current={isActive ? "page" : undefined}
                  >
                    <span>{link.label}</span>
                    {isActive && (
                      <span className="font-mono text-[10px] text-[var(--ink)] font-bold bg-[var(--hivis)] px-1.5 py-0.5 rounded-[1px] uppercase">
                        Active
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </header>
    </>
  );
}
