"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import { ChevronDown, Filter, HelpCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { PredictionListItem, StreamType } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { getStreamMeta } from "@/components/ui/StreamBadge";
import { cn } from "@/lib/utils";

const STREAMS: Array<{ key: string; label: string; streamFilter?: StreamType }> = [
  { key: "all", label: "ALL" },
  { key: "wet", label: "WET", streamFilter: "wet" },
  { key: "dry", label: "DRY", streamFilter: "dry" },
  { key: "sanitary", label: "SANITARY", streamFilter: "sanitary" },
  { key: "special_care", label: "SPECIAL CARE", streamFilter: "special_care" },
];

interface HistoryClientProps {
  initialItems: PredictionListItem[];
}

export function HistoryClient({ initialItems }: HistoryClientProps) {
  const [selectedStream, setSelectedStream] = React.useState<string>("all");
  const [items, setItems] = React.useState<PredictionListItem[]>(initialItems);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const [hasMore, setHasMore] = React.useState(initialItems.length >= 24);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch items when filter changes
  const handleFilterChange = React.useCallback(async (streamKey: string) => {
    setSelectedStream(streamKey);
    setIsLoading(true);
    setError(null);
    try {
      const streamParam = streamKey === "all" ? undefined : streamKey;
      const res = await api.getPredictions({
        limit: 24,
        stream: streamParam,
      });
      setItems(res);
      setHasMore(res.length >= 24);
    } catch (err) {
      console.error("Failed to load history:", err);
      setError("Unable to load records from backend service.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Cursor-based pagination: fetch next 24 items using last item ID as cursor
  const handleLoadMore = React.useCallback(async () => {
    if (items.length === 0 || isLoadingMore || !hasMore) return;
    const lastItem = items[items.length - 1];
    setIsLoadingMore(true);
    setError(null);
    try {
      const streamParam = selectedStream === "all" ? undefined : selectedStream;
      const res = await api.getPredictions({
        limit: 24,
        cursor: lastItem.id,
        stream: streamParam,
      });
      if (res.length > 0) {
        setItems((prev) => [...prev, ...res]);
        setHasMore(res.length >= 24);
      } else {
        setHasMore(false);
      }
    } catch (err) {
      console.error("Failed to paginate history:", err);
      setError("Failed to load additional specimens.");
    } finally {
      setIsLoadingMore(false);
    }
  }, [items, isLoadingMore, hasMore, selectedStream]);

  // Format date helper
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-8">
      {/* Stream Filter Segmented Control */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--rule)] pb-6">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-[var(--ink-2)]" aria-hidden="true" />
          <span className="font-mono text-xs uppercase tracking-wider text-[var(--ink-2)] font-semibold">
            Filter Stream:
          </span>
        </div>

        <div
          role="tablist"
          aria-label="Filter predictions by municipal waste stream"
          className="inline-flex flex-wrap p-1 bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] gap-1"
        >
          {STREAMS.map((s) => {
            const isSelected = selectedStream === s.key;
            return (
              <button
                key={s.key}
                type="button"
                role="tab"
                aria-selected={isSelected}
                onClick={() => handleFilterChange(s.key)}
                className={cn(
                  "px-3 py-1.5 text-xs font-mono font-medium rounded-[2px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)]",
                  isSelected
                    ? "bg-[var(--ink)] text-[var(--paper)] font-bold shadow-xs"
                    : "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--paper)]"
                )}
              >
                {s.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          role="alert"
          className="p-4 border border-[var(--special)] bg-[var(--surface)] text-[var(--special)] font-mono text-xs rounded-[2px]"
        >
          {error}
        </div>
      )}

      {/* Loading Skeleton during filter switch */}
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {Array.from({ length: 12 }).map((_, idx) => (
            <div
              key={idx}
              className="bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-2 space-y-2 animate-pulse"
            >
              <div className="aspect-square bg-[var(--paper)] rounded-[2px]" />
              <div className="h-3 w-3/4 bg-[var(--paper)] rounded-[1px]" />
              <div className="h-2 w-1/2 bg-[var(--paper)] rounded-[1px]" />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        /* Empty State */
        <div className="p-12 text-center border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] max-w-xl mx-auto my-8">
          <HelpCircle className="w-10 h-10 text-[var(--ink-2)] mx-auto mb-4 stroke-1" aria-hidden="true" />
          <h3 className="font-sans font-bold text-lg text-[var(--ink)] uppercase mb-2">
            No Specimens Recorded
          </h3>
          <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-6">
            No classification records match the selected stream filter. Use the field scanner to process physical waste items.
          </p>
          <Button href="/#scanner-section" variant="primary" size="sm" withArrow>
            Open Scanner
          </Button>
        </div>
      ) : (
        /* Contact-Sheet Grid (DESIGN.md §6) */
        <>
          <div
            aria-label="Specimen classification archive"
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3"
          >
            {items.map((item) => {
              const meta = getStreamMeta(item.stream);
              const confPct = (item.confidence * 100).toFixed(1);

              return (
                <Link
                  key={item.id}
                  href={`/scan/${item.id}`}
                  className="group relative flex flex-col bg-[var(--surface)] border border-[var(--rule)] hover:border-[var(--ink)] rounded-[4px] overflow-hidden transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)]"
                >
                  {/* Square Specimen Thumbnail */}
                  <div className="relative aspect-square w-full bg-[var(--paper)] overflow-hidden">
                    <Image
                      src={api.getImageUrl(item.id)}
                      alt={`Specimen ${item.label} classified as ${item.stream}`}
                      fill
                      unoptimized
                      className="object-cover group-hover:scale-105 transition-transform duration-200"
                    />

                    {/* Uncertainty Banner Badge */}
                    {item.uncertain && (
                      <span className="absolute top-1.5 right-1.5 px-1.5 py-0.5 bg-[var(--panel-dark)] text-[#F5C451] border border-[#F5C451] font-mono text-[9px] font-bold uppercase rounded-[1px] tracking-wider shadow-xs">
                        Flagged
                      </span>
                    )}

                    {/* Grad-CAM Indicator */}
                    {item.gradcam_url && (
                      <span className="absolute top-1.5 left-1.5 px-1 py-0.5 bg-[var(--panel-dark)]/85 text-[var(--paper)] font-mono text-[8px] font-medium uppercase rounded-[1px] tracking-wider">
                        CAM
                      </span>
                    )}

                    {/* Bottom Stream Color Accent Border */}
                    <div
                      className="absolute bottom-0 left-0 w-full h-1"
                      style={{
                        backgroundColor:
                          item.stream === "wet"
                            ? "var(--wet)"
                            : item.stream === "dry"
                            ? "var(--dry)"
                            : item.stream === "sanitary"
                            ? "var(--sanitary)"
                            : "var(--special)",
                      }}
                      aria-hidden="true"
                    />
                  </div>

                  {/* Card Spec-Sheet Caption */}
                  <div className="p-2.5 flex flex-col justify-between flex-1">
                    <div>
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="font-sans font-extrabold text-xs uppercase text-[var(--ink)] truncate tracking-tight">
                          {item.label.replace(/_/g, " ")}
                        </span>
                        <span className="font-mono text-[10px] text-[var(--ink-2)] font-semibold shrink-0">
                          {confPct}%
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 mb-2">
                        <span
                          className="w-1.5 h-1.5 rounded-[0.5px] shrink-0"
                          style={{
                            backgroundColor:
                              item.stream === "wet"
                                ? "var(--wet)"
                                : item.stream === "dry"
                                ? "var(--dry)"
                                : item.stream === "sanitary"
                                ? "var(--sanitary)"
                                : "var(--special)",
                          }}
                          aria-hidden="true"
                        />
                        <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--ink-2)] truncate">
                          {meta.label}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-[var(--rule)] flex items-center justify-between font-mono text-[9px] text-[var(--ink-2)]">
                      <span className="truncate">{item.model}</span>
                      <span className="shrink-0">{formatDate(item.created_at)}</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* Pagination Controls */}
          <div className="pt-6 pb-12 flex flex-col items-center justify-center gap-3">
            {hasMore ? (
              <Button
                onClick={handleLoadMore}
                disabled={isLoadingMore}
                variant="outline"
                size="md"
                className="font-mono text-xs"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" aria-hidden="true" />
                    RETRIEVING SPECIMENS...
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5 mr-2" aria-hidden="true" />
                    LOAD MORE SPECIMENS (24)
                  </>
                )}
              </Button>
            ) : items.length > 0 ? (
              <div className="font-mono text-[11px] text-[var(--ink-2)] uppercase tracking-wider">
                — End of classification archive ({items.length} records) —
              </div>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
