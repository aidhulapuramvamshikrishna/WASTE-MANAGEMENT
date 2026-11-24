"use client";

import * as React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Download, Info, ShieldCheck, Table as TableIcon } from "lucide-react";
import type { StatsOut } from "@/lib/types";
import { Button } from "@/components/ui/button";

const emptySubscribe = () => () => {};

const STREAM_COLORS: Record<string, string> = {
  wet: "var(--wet, #1E8E4E)",
  dry: "var(--dry, #1F5FD1)",
  sanitary: "var(--sanitary, #C25A12)",
  special_care: "var(--special, #C0262D)",
};

interface InsightsChartsProps {
  stats: StatsOut;
}

export function InsightsCharts({ stats }: InsightsChartsProps) {
  const [showDataTables, setShowDataTables] = React.useState(false);
  const mounted = React.useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );

  // Format stream distribution data for Donut Chart
  const streamData = React.useMemo(() => {
    const raw = stats.stream_distribution || {};
    return Object.entries(raw).map(([key, count]) => {
      const label =
        key === "wet"
          ? "Wet Waste"
          : key === "dry"
          ? "Dry Waste"
          : key === "sanitary"
          ? "Sanitary"
          : key === "special_care"
          ? "Special Care"
          : key;
      return {
        key,
        name: label,
        value: count,
        color: STREAM_COLORS[key] || "var(--ink-2)",
      };
    });
  }, [stats.stream_distribution]);

  // Format daily volume data for Area Chart
  const dailyData = React.useMemo(() => {
    return (stats.scans_per_day || []).map((item) => ({
      date: item.date.slice(5), // MM-DD
      fullDate: item.date,
      scans: item.count,
    }));
  }, [stats.scans_per_day]);

  // Format class distribution for Bar Chart (sorted descending)
  const classData = React.useMemo(() => {
    const raw = stats.class_distribution || {};
    return Object.entries(raw)
      .map(([name, count]) => ({
        name: name.replace(/_/g, " "),
        count,
      }))
      .sort((a, b) => b.count - a.count);
  }, [stats.class_distribution]);

  if (!mounted) {
    return (
      <div className="p-12 text-center border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] font-mono text-xs text-[var(--ink-2)]">
        INITIALIZING ANALYTICS ENGINE...
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* Table Toggle / Export Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--rule)] pb-4">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setShowDataTables((prev) => !prev)}
            className="font-mono text-xs flex items-center gap-1.5"
            aria-expanded={showDataTables}
          >
            <TableIcon className="w-3.5 h-3.5" aria-hidden="true" />
            {showDataTables ? "HIDE DATA TABLES" : "ACCESSIBLE DATA TABLES"}
          </Button>
        </div>

        <a
          href="/api/v1/admin/feedback.csv"
          download="feedback_export.csv"
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-[var(--surface)] border border-[var(--rule)] hover:border-[var(--ink)] text-[var(--ink)] font-mono text-xs rounded-[2px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)]"
        >
          <Download className="w-3.5 h-3.5 text-[var(--ink-2)]" aria-hidden="true" />
          EXPORT AUDIT CSV (LOCAL ONLY)
        </a>
      </div>

      {/* Grid: 2 Column Analytics Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Chart 1: Stream Distribution Donut (5 Cols) */}
        <section
          aria-labelledby="heading-stream-dist"
          className="lg:col-span-5 flex flex-col bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6"
        >
          <div className="mb-4">
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
              01 / SEGREGATION RATIO
            </span>
            <h2 id="heading-stream-dist" className="font-sans font-bold text-lg text-[var(--ink)]">
              Stream Composition
            </h2>
          </div>

          <figure className="flex-1 flex flex-col justify-between">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={streamData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="var(--paper)"
                    strokeWidth={2}
                  >
                    {streamData.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--panel-dark)",
                      borderColor: "var(--rule)",
                      borderRadius: "2px",
                      color: "var(--paper)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                    }}
                    itemStyle={{ color: "var(--paper)" }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconType="square"
                    wrapperStyle={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      paddingTop: "16px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <figcaption className="mt-4 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink-2)]">
              Total volume across {stats.total_predictions} scans divided into 4 statutory municipal streams.
            </figcaption>

            {/* Accessible Table Alternative */}
            {showDataTables && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border border-[var(--rule)]">
                  <caption className="sr-only">Stream Composition Data Table</caption>
                  <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)]">
                    <tr>
                      <th className="p-2">Stream</th>
                      <th className="p-2 text-right">Scans</th>
                      <th className="p-2 text-right">Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
                    {streamData.map((d) => (
                      <tr key={d.key}>
                        <td className="p-2">{d.name}</td>
                        <td className="p-2 text-right">{d.value}</td>
                        <td className="p-2 text-right">
                          {stats.total_predictions > 0
                            ? `${((d.value / stats.total_predictions) * 100).toFixed(1)}%`
                            : "0%"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </figure>
        </section>

        {/* Chart 2: Daily Scan Activity Area Chart (7 Cols) */}
        <section
          aria-labelledby="heading-daily-volume"
          className="lg:col-span-7 flex flex-col bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6"
        >
          <div className="mb-4">
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
              02 / TEMPORAL THROUGHPUT
            </span>
            <h2 id="heading-daily-volume" className="font-sans font-bold text-lg text-[var(--ink)]">
              Daily Ingestion Volume
            </h2>
          </div>

          <figure className="flex-1 flex flex-col justify-between">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={dailyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="date"
                    stroke="var(--ink-2)"
                    tick={{ fill: "var(--ink-2)", fontSize: 10, fontFamily: "var(--font-mono)" }}
                    tickLine={{ stroke: "var(--rule)" }}
                  />
                  <YAxis
                    stroke="var(--ink-2)"
                    tick={{ fill: "var(--ink-2)", fontSize: 10, fontFamily: "var(--font-mono)" }}
                    tickLine={{ stroke: "var(--rule)" }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--panel-dark)",
                      borderColor: "var(--rule)",
                      borderRadius: "2px",
                      color: "var(--paper)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "12px",
                    }}
                    itemStyle={{ color: "var(--paper)" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="scans"
                    stroke="var(--ink)"
                    strokeWidth={2}
                    fill="var(--hivis)"
                    fillOpacity={0.25}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <figcaption className="mt-4 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink-2)]">
              Daily frequency of physical waste classifications registered in the active monitoring period.
            </figcaption>

            {/* Accessible Table Alternative */}
            {showDataTables && (
              <div className="mt-4 max-h-48 overflow-y-auto">
                <table className="w-full text-left font-mono text-xs border border-[var(--rule)]">
                  <caption className="sr-only">Daily Ingestion Volume Data Table</caption>
                  <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)]">
                    <tr>
                      <th className="p-2">Date</th>
                      <th className="p-2 text-right">Scans</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
                    {dailyData.map((d) => (
                      <tr key={d.fullDate}>
                        <td className="p-2">{d.fullDate}</td>
                        <td className="p-2 text-right">{d.scans}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </figure>
        </section>
      </div>

      {/* Row 2: 12 Material Classes Horizontal Bar Chart */}
      <section
        aria-labelledby="heading-class-breakdown"
        className="bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6"
      >
        <div className="mb-4">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
            03 / MATERIAL INVENTORY
          </span>
          <h2 id="heading-class-breakdown" className="font-sans font-bold text-lg text-[var(--ink)]">
            Classification Volume by Material
          </h2>
        </div>

        <figure>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={classData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
              >
                <XAxis
                  type="number"
                  stroke="var(--ink-2)"
                  tick={{ fill: "var(--ink-2)", fontSize: 10, fontFamily: "var(--font-mono)" }}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke="var(--ink-2)"
                  tick={{ fill: "var(--ink)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                  width={110}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--panel-dark)",
                    borderColor: "var(--rule)",
                    borderRadius: "2px",
                    color: "var(--paper)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "12px",
                  }}
                  itemStyle={{ color: "var(--paper)" }}
                />
                <Bar dataKey="count" fill="var(--ink)" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <figcaption className="mt-4 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink-2)]">
            Distribution across all 12 trained material classes, ordered from highest to lowest intake.
          </figcaption>

          {/* Accessible Table Alternative */}
          {showDataTables && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left font-mono text-xs border border-[var(--rule)]">
                <caption className="sr-only">Material Inventory Data Table</caption>
                <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)]">
                  <tr>
                    <th className="p-2">Material</th>
                    <th className="p-2 text-right">Scans</th>
                    <th className="p-2 text-right">Proportion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
                  {classData.map((d) => (
                    <tr key={d.name}>
                      <td className="p-2 capitalize">{d.name}</td>
                      <td className="p-2 text-right">{d.count}</td>
                      <td className="p-2 text-right">
                        {stats.total_predictions > 0
                          ? `${((d.count / stats.total_predictions) * 100).toFixed(1)}%`
                          : "0%"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </figure>
      </section>

      {/* Row 3: Citizen Feedback & Confusion Pairs Audit */}
      <section
        aria-labelledby="heading-citizen-audit"
        className="bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
              04 / CITIZEN AUDIT & GROUND TRUTH
            </span>
            <h2 id="heading-citizen-audit" className="font-sans font-bold text-lg text-[var(--ink)]">
              Field Feedback & Confusion Pairs
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px] font-mono text-xs text-[var(--ink)]">
              <ShieldCheck className="w-3.5 h-3.5 text-[var(--wet)]" aria-hidden="true" />
              {stats.total_feedback} verified reviews
            </span>
          </div>
        </div>

        {stats.top_confusions && stats.top_confusions.length > 0 ? (
          <div className="overflow-x-auto border border-[var(--rule)] rounded-[2px]">
            <table className="w-full text-left font-mono text-xs">
              <caption className="sr-only">Top Misclassified Pairs Reported by Citizens</caption>
              <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)]">
                <tr>
                  <th className="p-3">Rank</th>
                  <th className="p-3">Predicted by Model</th>
                  <th className="p-3">Reported by Citizen</th>
                  <th className="p-3 text-right">Corrections</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
                {stats.top_confusions.map((c, idx) => (
                  <tr key={`${c.predicted}-${c.actual}`} className="hover:bg-[var(--paper)] transition-colors">
                    <td className="p-3 text-[var(--ink-2)] font-bold">{idx + 1}</td>
                    <td className="p-3 capitalize font-semibold">{c.predicted.replace(/_/g, " ")}</td>
                    <td className="p-3 capitalize text-[var(--caution)] font-semibold">
                      {c.actual.replace(/_/g, " ")}
                    </td>
                    <td className="p-3 text-right font-bold">{c.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6 text-center border border-[var(--rule)] bg-[var(--paper)] rounded-[2px] font-mono text-xs text-[var(--ink-2)]">
            NO CORRECTIONS SUBMITTED YET — ALL REVIEWED SPECIMENS VERIFIED AS CORRECT
          </div>
        )}

        <div className="mt-4 flex items-start gap-2 text-[var(--ink-2)] font-mono text-[11px] leading-relaxed">
          <Info className="w-3.5 h-3.5 text-[var(--ink-2)] shrink-0 mt-0.5" aria-hidden="true" />
          <span>
            Citizen feedback provides an empirical feedback loop for continual model validation and post-deployment retraining datasets.
          </span>
        </div>
      </section>
    </div>
  );
}
