"use client";

import * as React from "react";
import {
  AlertTriangle,
  Leaf,
  Package,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import type { PredictionOut } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ReadoutPanelProps {
  prediction: PredictionOut;
}

export function ReadoutPanel({ prediction }: ReadoutPanelProps) {
  const {
    id,
    model,
    label,
    stream,
    confidence,
    uncertain,
    top3,
    disposal,
    latency_ms,
  } = prediction;

  const labelFormatted = label.replace("_", " ").toUpperCase();
  const streamFormatted = stream.replace("_", " ").toUpperCase();

  // Confidence meter percentage & calibrated threshold from API response
  const confPct = Math.round(confidence * 100);
  const thresholdExact = prediction.uncertain_threshold ?? 0.585;
  const thresholdPct = Math.round(thresholdExact * 100);

  // Stream icon and destination mapping
  const streamConfig: Record<
    string,
    { icon: React.ElementType; colorVar: string; destination: string; label: string }
  > = {
    wet: {
      icon: Leaf,
      colorVar: "var(--wet)",
      destination: "Decentralized Composting / Biomethanation",
      label: "WET WASTE",
    },
    dry: {
      icon: Package,
      colorVar: "var(--dry)",
      destination: "Material Recovery Facility (MRF)",
      label: "DRY WASTE",
    },
    sanitary: {
      icon: ShieldAlert,
      colorVar: "var(--sanitary)",
      destination: "Wrapped Securely & Stored Separately",
      label: "SANITARY WASTE",
    },
    special_care: {
      icon: TriangleAlert,
      colorVar: "var(--special)",
      destination: "Authorised Agencies / Designated Collection Centres",
      label: "SPECIAL CARE HAZARDOUS",
    },
  };

  const currentStream = streamConfig[stream.toLowerCase()] || {
    icon: Package,
    colorVar: "var(--ink)",
    destination: "Municipal SWM Rules 2026 Segregation",
    label: streamFormatted,
  };

  const StreamIcon = currentStream.icon;

  return (
    <div className="flex flex-col border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] p-6 sm:p-8 transition-colors">
      {/* 1. Spec Sheet Eyebrow Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[var(--rule)] mb-6 font-mono text-[11px] text-[var(--ink-2)]">
        <span className="uppercase tracking-wider font-semibold">
          Prediction Result
        </span>
        <span className="uppercase tracking-wider">
          ID: {id.slice(0, 8)}
        </span>
      </div>

      {/* 2. Primary Classification Label (Condensed Uppercase Display) */}
      <div className="mb-4">
        <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-2)] mb-1">
          Identified Material
        </div>
        <h1
          className="text-5xl sm:text-6xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans leading-none"
          style={{ fontStretch: "75%" }}
        >
          {labelFormatted}
        </h1>
      </div>

      {/* 3. Statutory Stream Bar with Icon & Destination */}
      {uncertain ? (
        <div className="p-4 rounded-[2px] mb-6 flex items-start sm:items-center gap-3 border border-[var(--caution)] bg-[var(--caution)]/10 text-[var(--ink)]">
          <div className="p-2 rounded-[2px] bg-[var(--caution)] text-[#0E1A16] shrink-0">
            <AlertTriangle className="w-5 h-5" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="font-mono text-xs uppercase font-extrabold tracking-wider text-[var(--ink)]">
              POSSIBLY: {currentStream.label}
            </div>
            <div className="font-sans text-xs sm:text-sm font-semibold text-[var(--ink-2)] leading-snug">
              Check the top-3 guesses before disposing.
            </div>
          </div>
        </div>
      ) : (
        <div
          className="p-4 rounded-[2px] mb-6 flex items-start sm:items-center gap-3 border"
          style={{
            borderColor: currentStream.colorVar,
            backgroundColor: `color-mix(in srgb, ${currentStream.colorVar} 12%, transparent)`,
          }}
        >
          <div
            className="p-2 rounded-[2px] text-white shrink-0"
            style={{ backgroundColor: currentStream.colorVar }}
          >
            <StreamIcon className="w-5 h-5" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div
              className="font-mono text-xs uppercase font-extrabold tracking-wider"
              style={{ color: currentStream.colorVar }}
            >
              {currentStream.label}
            </div>
            <div className="font-sans text-xs sm:text-sm font-semibold text-[var(--ink)] leading-snug">
              {currentStream.destination}
            </div>
          </div>
        </div>
      )}

      {/* 4. Uncertain Warning Banner (if confidence < threshold) */}
      {uncertain && (
        <div
          role="alert"
          className="p-3.5 bg-[var(--caution)]/15 border-l-4 border-[var(--caution)] rounded-[2px] mb-6 flex items-start gap-3 text-xs font-sans text-[var(--ink)]"
        >
          <AlertTriangle className="w-4 h-4 text-[var(--caution)] shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <strong className="font-mono uppercase tracking-wider text-[var(--ink)] block mb-0.5">
              Uncertain Flagged ({(confidence * 100).toFixed(1)}% &lt; {(thresholdExact * 100).toFixed(1)}%)
            </strong>
            <span>
              Prediction is below the calibrated confidence threshold. Verify material manually before routing into bins.
            </span>
          </div>
        </div>
      )}

      {/* 5. Calibrated Confidence Meter with Threshold Tick */}
      <div className="mb-6 p-4 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px]">
        <div className="flex items-center justify-between mb-2 font-mono text-xs">
          <span className="text-[var(--ink-2)] uppercase">Calibrated Confidence</span>
          <span className="text-[var(--ink)] font-extrabold text-sm">{confPct}%</span>
        </div>

        {/* Meter Track */}
        <div className="relative h-2 w-full bg-[var(--surface)] border border-[var(--rule)] rounded-[1px] overflow-hidden">
          {/* Fill */}
          <div
            className="h-full bg-[var(--hivis)] transition-all duration-500"
            style={{ width: `${confPct}%` }}
          />
          {/* Threshold Tick Line */}
          <div
            className="absolute top-0 bottom-0 w-[2px] bg-[var(--special)] z-10"
            style={{ left: `${thresholdPct}%` }}
            title={`Threshold: ${(thresholdExact * 100).toFixed(1)}%`}
          />
        </div>

        <div className="flex items-center justify-between mt-2 font-mono text-[10px] text-[var(--ink-2)]">
          <span>0%</span>
          <span className="text-[var(--ink)] font-bold">
            TICK: {(thresholdExact * 100).toFixed(1)}% THRESHOLD
          </span>
          <span>100%</span>
        </div>
      </div>

      {/* 6. Top-3 Probabilities Breakdown */}
      {top3 && top3.length > 0 && (
        <div className="mb-6">
          <div className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-2)] font-semibold mb-3">
            Top-3 Softmax Distribution
          </div>
          <div className="space-y-2 font-mono text-xs">
            {top3.map((item, idx) => {
              const itemPct = Math.round(item.confidence * 100);
              const isTop = idx === 0;
              return (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className={cn(isTop ? "font-bold text-[var(--ink)]" : "text-[var(--ink-2)]")}>
                      0{idx + 1} · {item.label.replace("_", " ").toUpperCase()}
                    </span>
                    <span className="font-semibold text-[var(--ink)]">{itemPct}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-[var(--paper)] rounded-[1px] overflow-hidden border border-[var(--rule)]">
                    <div
                      className={cn("h-full transition-all duration-300", isTop ? "bg-[var(--hivis)]" : "bg-[var(--rule)]")}
                      style={{ width: `${itemPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 7. Disposal Instructions */}
      <div className="mb-6 pt-4 border-t border-[var(--rule)]">
        <div className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-2)] font-semibold mb-2">
          Disposal Protocol
        </div>
        <p className="font-sans text-xs text-[var(--ink)] leading-relaxed bg-[var(--paper)] p-3 border border-[var(--rule)] rounded-[2px]">
          {disposal}
        </p>
      </div>

      {/* 8. Technical Metadata Row */}
      <div className="mt-auto pt-4 border-t border-[var(--rule)] flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-[var(--ink-2)]">
        <span>MODEL: {model}</span>
        <span>SERVER TIME INCL. GRAD-CAM: {latency_ms.toFixed(1)} MS</span>
        <span>SCALE: 224×224 RGB</span>
      </div>
    </div>
  );
}
