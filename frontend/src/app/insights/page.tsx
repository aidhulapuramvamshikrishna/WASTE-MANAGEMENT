import * as React from "react";
import type { Metadata } from "next";
import { api } from "@/lib/api";
import type { StatsOut } from "@/lib/types";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Button } from "@/components/ui/button";
import { InsightsCharts } from "./InsightsCharts";

export const metadata: Metadata = {
  title: "Insights — EcoSort",
  description:
    "Municipal solid waste sorting analytics, stream composition ratios, daily volume, and citizen correction audits.",
};

export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  let stats: StatsOut = {
    total_predictions: 0,
    scans_per_day: [],
    stream_distribution: { wet: 0, dry: 0, sanitary: 0, special_care: 0 },
    class_distribution: {},
    total_feedback: 0,
    correction_rate: 0,
    top_confusions: [],
  };

  try {
    stats = await api.getStats(30);
  } catch (err) {
    console.error("InsightsPage getStats error:", err);
  }

  // Calculate municipal recovery / segregation rate (Wet + Dry / Total)
  const wetCount = stats.stream_distribution?.wet || 0;
  const dryCount = stats.stream_distribution?.dry || 0;
  const recoveryRate =
    stats.total_predictions > 0
      ? (((wetCount + dryCount) / stats.total_predictions) * 100).toFixed(1)
      : "—";

  return (
    <main id="main-content" className="flex-1 py-12 md:py-16 bg-[var(--paper)] transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Spec Eyebrow & Header */}
        <div className="mb-8 md:mb-12">
          <Eyebrow className="mb-3">02 — MUNICIPAL TELEMETRY</Eyebrow>
          <h1
            className="text-4xl sm:text-5xl md:text-6xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans mb-3"
            style={{ fontStretch: "75%" }}
          >
            Sorting Insights
          </h1>
          <p className="font-sans text-sm sm:text-base text-[var(--ink-2)] max-w-2xl">
            Real-time municipal telemetry across physical sorting streams, intake throughput, and citizen audit feedback under SWM Rules 2026.
          </p>
        </div>

        {/* Dark Control Room KPI Strip (DESIGN.md §5.8) */}
        <div className="mb-12 bg-[var(--panel-dark)] text-[var(--paper)] border border-[var(--rule)] rounded-[4px] p-6 md:p-8 shadow-xs">
          <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-6">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[var(--hivis)] animate-pulse" aria-hidden="true" />
              <span className="font-mono text-xs uppercase tracking-widest text-white/70 font-semibold">
                Control Room Telemetry · 30-Day Window
              </span>
            </div>
            <span className="font-mono text-xs text-white/50">
              SWM 2026 Monitored
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 divide-y md:divide-y-0 md:divide-x divide-white/10">
            {/* KPI 1 */}
            <div className="flex flex-col pt-3 md:pt-0">
              <span className="font-mono text-[11px] uppercase tracking-wider text-white/60 mb-1">
                Total Scans Logged
              </span>
              <span
                className="text-4xl sm:text-5xl font-extrabold tracking-tight text-[var(--hivis)] font-sans"
                style={{ fontStretch: "75%" }}
              >
                {stats.total_predictions.toLocaleString()}
              </span>
              <span className="font-mono text-[10px] text-white/50 mt-1">
                Physical waste captures
              </span>
            </div>

            {/* KPI 2 */}
            <div className="flex flex-col pt-3 md:pt-0 md:pl-6">
              <span className="font-mono text-[11px] uppercase tracking-wider text-white/60 mb-1">
                Recovery Stream Share
              </span>
              <span
                className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white font-sans"
                style={{ fontStretch: "75%" }}
              >
                {recoveryRate !== "—" ? `${recoveryRate}%` : "—"}
              </span>
              <span className="font-mono text-[10px] text-white/50 mt-1">
                Wet + Dry recyclables
              </span>
            </div>

            {/* KPI 3 */}
            <div className="flex flex-col pt-3 md:pt-0 md:pl-6">
              <span className="font-mono text-[11px] uppercase tracking-wider text-white/60 mb-1">
                Citizen Feedback
              </span>
              <span
                className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white font-sans"
                style={{ fontStretch: "75%" }}
              >
                {stats.total_feedback}
              </span>
              <span className="font-mono text-[10px] text-white/50 mt-1">
                Audited classifications
              </span>
            </div>

            {/* KPI 4 */}
            <div className="flex flex-col pt-3 md:pt-0 md:pl-6">
              <span className="font-mono text-[11px] uppercase tracking-wider text-white/60 mb-1">
                Field Correction Rate
              </span>
              <span
                className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white font-sans"
                style={{ fontStretch: "75%" }}
              >
                {stats.total_predictions > 0
                  ? `${(stats.correction_rate * 100).toFixed(1)}%`
                  : "0.0%"}
              </span>
              <span className="font-mono text-[10px] text-white/50 mt-1">
                Reported misclassifications
              </span>
            </div>
          </div>
        </div>

        {/* Visualizations and Audit Tables */}
        {stats.total_predictions === 0 ? (
          <div className="p-12 text-center border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] max-w-xl mx-auto my-8">
            <h3 className="font-sans font-bold text-lg text-[var(--ink)] uppercase mb-2">
              No Operational Telemetry Yet
            </h3>
            <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-6">
              The municipal insights dashboard populates as physical scans are classified and reviewed. Run a test item through the scanner.
            </p>
            <Button href="/#scanner-section" variant="primary" size="sm" withArrow>
              Open Scanner
            </Button>
          </div>
        ) : (
          <InsightsCharts stats={stats} />
        )}
      </div>
    </main>
  );
}
