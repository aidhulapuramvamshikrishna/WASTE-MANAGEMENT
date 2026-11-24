"use client";

import * as React from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Scale,
  Table as TableIcon,
} from "lucide-react";
import type { ModelFullMetricsOut, ModelSummaryOut } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ModelViewProps {
  modelSummaries: ModelSummaryOut[];
  modelsFullData: Record<string, ModelFullMetricsOut>;
}

export function ModelView({ modelSummaries, modelsFullData }: ModelViewProps) {
  const [selectedModel, setSelectedModel] = React.useState<string>("mobilenet_v3");
  const [matrixMode, setMatrixMode] = React.useState<"normalized" | "raw">("normalized");
  const [hoveredCell, setHoveredCell] = React.useState<{
    actual: string;
    predicted: string;
    count: number;
    pct: number;
  } | null>(null);
  const [showDataTables, setShowDataTables] = React.useState(false);

  const activeFull = modelsFullData[selectedModel] || Object.values(modelsFullData)[0];
  const activeMetrics = activeFull?.metrics ?? null;
  const activeCalib = activeFull?.calibration ?? null;
  const activeMatrix = activeFull?.confusion_matrix ?? null;

  // 12 Classes in exact ImageFolder / test order
  const classes = activeMatrix?.classes || [
    "battery",
    "cardboard",
    "e_waste",
    "glass",
    "mask_glove",
    "medicine_syringe",
    "metal",
    "misc_trash",
    "organic",
    "paper",
    "plastic",
    "textile",
  ];

  // Compute row-normalized confusion matrix
  const { rawMatrix, normMatrix } = React.useMemo(() => {
    const raw = activeMatrix?.matrix || [];
    const sums: number[] = raw.map((row) => row.reduce((a, b) => a + b, 0));
    const norm = raw.map((row, i) => {
      const sum = sums[i] || 1;
      return row.map((val) => (val / sum) * 100);
    });
    return { rawMatrix: raw, normMatrix: norm };
  }, [activeMatrix]);

  // Format training history for Recharts
  const historyData = React.useMemo(() => {
    const historyList = activeFull?.history || [];
    return historyList.map((h) => ({
      epoch: h.epoch,
      phase: h.phase ?? (h.epoch <= 3 ? 1 : 2),
      train_loss: Number(h.train_loss?.toFixed(3)),
      val_loss: Number(h.val_loss?.toFixed(3)),
      val_macro_f1: Number(((h.val_macro_f1 ?? 0) * 100).toFixed(1)),
      val_acc: Number(((h.val_acc ?? 0) * 100).toFixed(1)),
    }));
  }, [activeFull?.history]);

  return (
    <div className="space-y-16">
      {/* ==================================================================== */}
      {/* 01 ARCHITECTURE COMPARISON TABLE (DESIGN.md §5.7)                     */}
      {/* ==================================================================== */}
      <section aria-labelledby="heading-comparison" className="space-y-4">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
            01 / BENCHMARK SYNTHESIS
          </span>
          <h2 id="heading-comparison" className="font-sans font-extrabold text-2xl uppercase tracking-tight text-[var(--ink)]">
            Architecture Comparison
          </h2>
          <p className="font-sans text-xs text-[var(--ink-2)] mt-1">
            Empirical evaluation across 2,843 held-out test specimens. Dot (<span className="inline-block w-2 h-2 rounded-full bg-[var(--hivis)] mx-0.5" />) denotes top performer per metric.
          </p>
        </div>

        <div className="overflow-x-auto border border-[var(--rule)] bg-[var(--surface)] rounded-[4px]">
          <table className="w-full text-left font-mono text-xs">
            <caption className="sr-only">Model Architecture Comparison Table</caption>
            <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)]">
              <tr>
                <th className="p-3">Architecture</th>
                <th className="p-3">Method</th>
                <th className="p-3 text-right">Test Accuracy</th>
                <th className="p-3 text-right">Macro-F1</th>
                <th className="p-3 text-right">Stream Acc</th>
                <th className="p-3 text-right">Hazard Miss</th>
                <th className="p-3 text-right">Latency p50</th>
                <th className="p-3 text-right">Params</th>
                <th className="p-3 text-right">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
              {modelSummaries.map((m) => {
                const full = modelsFullData[m.name];
                const metrics = full?.metrics || {};
                const acc = metrics.accuracy ? (metrics.accuracy * 100).toFixed(2) : "—";
                const accCI = metrics.bootstrap_ci_95?.accuracy;
                const f1 = metrics.macro_f1 ? (metrics.macro_f1 * 100).toFixed(2) : "—";
                const f1CI = metrics.bootstrap_ci_95?.macro_f1;
                const streamAcc = metrics.stream_accuracy
                  ? `${(metrics.stream_accuracy * 100).toFixed(1)}%`
                  : "—";
                const hazardRate = metrics.hazard_miss_rate !== undefined
                  ? `${(metrics.hazard_miss_rate * 100).toFixed(1)}%`
                  : "—";
                const hazardCount = metrics.hazard_miss_count !== undefined
                  ? `(${metrics.hazard_miss_count}/${metrics.hazard_total ?? 674})`
                  : "";
                const latency = metrics.cpu_latency_ms_p50
                  ? `${metrics.cpu_latency_ms_p50.toFixed(1)} ms`
                  : "—";
                const params = metrics.params
                  ? `${(metrics.params / 1_000_000).toFixed(2)}M`
                  : "—";
                const size = metrics.size_mb ? `${metrics.size_mb.toFixed(1)} MB` : "—";

                const isBestAcc = m.name === "mobilenet_v3";
                const isBestF1 = m.name === "mobilenet_v3";
                const isBestStream = m.name === "mobilenet_v3";
                const isBestHazard = m.name === "mobilenet_v3" || m.name === "efficientnet_b0";
                const isBestLatency = m.name === "wastenet";
                const isBestParams = m.name === "wastenet";
                const isBestSize = m.name === "wastenet";

                return (
                  <tr
                    key={m.name}
                    className={cn(
                      "hover:bg-[var(--paper)] transition-colors",
                      m.name === selectedModel && "bg-[var(--paper)]/60 font-semibold"
                    )}
                  >
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className="font-sans font-bold text-sm text-[var(--ink)]">
                          {m.display_name}
                        </span>
                        {m.is_default && (
                          <span className="px-1.5 py-0.5 bg-[var(--hivis)] text-[var(--ink)] font-mono text-[9px] font-extrabold uppercase rounded-[1px]">
                            DEFAULT
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-[var(--ink-2)] font-mono">
                        {m.name}
                      </span>
                    </td>
                    <td className="p-3 text-[var(--ink-2)]">
                      {m.trained_from_scratch ? (
                        <span className="px-1.5 py-0.5 bg-[var(--paper)] border border-[var(--rule)] rounded-[1px] text-[10px]">
                          Scratch
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 bg-[var(--surface)] border border-[var(--rule)] rounded-[1px] text-[10px]">
                          Transfer (ImageNet)
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      {isBestAcc && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      <span className="font-bold">{acc}%</span>
                      {accCI && (
                        <span className="block text-[10px] text-[var(--ink-2)]">
                          [{ (accCI.low * 100).toFixed(1) }, { (accCI.high * 100).toFixed(1) }]
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      {isBestF1 && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      <span className="font-bold">{f1}%</span>
                      {f1CI && (
                        <span className="block text-[10px] text-[var(--ink-2)]">
                          [{ (f1CI.low * 100).toFixed(1) }, { (f1CI.high * 100).toFixed(1) }]
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      {isBestStream && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      {streamAcc}
                    </td>
                    <td className="p-3 text-right">
                      {isBestHazard && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      <span className={cn(metrics.hazard_miss_rate && metrics.hazard_miss_rate > 0.1 ? "text-[var(--special)] font-bold" : "")}>
                        {hazardRate}
                      </span>
                      <span className="block text-[10px] text-[var(--ink-2)]">
                        {hazardCount}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      {isBestLatency && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      {latency}
                    </td>
                    <td className="p-3 text-right">
                      {isBestParams && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      {params}
                    </td>
                    <td className="p-3 text-right">
                      {isBestSize && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--hivis)] mr-1" />}
                      {size}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Statistical Rigor Callout */}
        <div className="p-4 bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] font-mono text-xs text-[var(--ink-2)] space-y-1 leading-relaxed">
          <div className="font-bold text-[var(--ink)] flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5 text-[var(--ink)]" aria-hidden="true" />
            Hypothesis Testing & Significance Analysis
          </div>
          <div>
            • <strong>Transfer Learning vs Scratch:</strong> McNemar test yields χ² = 360.36, p = 9.51 × 10⁻⁹¹ (overwhelmingly significant advantage for pretrained representations).
          </div>
          <div>
            • <strong>MobileNetV3 vs EfficientNet-B0:</strong> McNemar test yields χ² = 3.68, p = 0.055 (not statistically significant at α = 0.05). Selection of MobileNetV3 as default rests on validation macro-F1 and 2.1× faster CPU inference latency (55.5 ms vs 115.4 ms).
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* 02 ARCHITECTURE SELECTOR TABS                                        */}
      {/* ==================================================================== */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--rule)] pb-4">
        <div>
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
            INSPECT ARCHITECTURE TELEMETRY
          </span>
          <h3 className="font-sans font-bold text-lg text-[var(--ink)]">
            Detailed Diagnostic Telemetry
          </h3>
        </div>

        <div
          role="tablist"
          aria-label="Select model architecture for detailed telemetry"
          className="inline-flex p-1 bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] gap-1"
        >
          {modelSummaries.map((m) => (
            <button
              key={m.name}
              role="tab"
              aria-selected={selectedModel === m.name}
              onClick={() => setSelectedModel(m.name)}
              className={cn(
                "px-3 py-1.5 text-xs font-mono font-medium rounded-[2px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)]",
                selectedModel === m.name
                  ? "bg-[var(--ink)] text-[var(--paper)] font-bold shadow-xs"
                  : "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--paper)]"
              )}
            >
              {m.display_name}
            </button>
          ))}
        </div>
      </div>

      {/* ==================================================================== */}
      {/* 03 CONFUSION MATRIX HEATMAP (12×12 Grid)                            */}
      {/* ==================================================================== */}
      <section aria-labelledby="heading-matrix" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
              02 / CLASSIFICATION ALIGNMENT
            </span>
            <h2 id="heading-matrix" className="font-sans font-extrabold text-xl uppercase tracking-tight text-[var(--ink)]">
              Confusion Matrix ({classes.length} × {classes.length})
            </h2>
            <p className="font-sans text-xs text-[var(--ink-2)] mt-0.5">
              Vertical axis represents True ground truth; horizontal axis represents Model Prediction.
            </p>
          </div>

          <div className="inline-flex p-1 bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] gap-1">
            <button
              type="button"
              onClick={() => setMatrixMode("normalized")}
              className={cn(
                "px-2.5 py-1 text-xs font-mono rounded-[2px] transition-colors",
                matrixMode === "normalized"
                  ? "bg-[var(--ink)] text-[var(--paper)] font-bold"
                  : "text-[var(--ink-2)] hover:text-[var(--ink)]"
              )}
            >
              ROW-NORMALIZED (%)
            </button>
            <button
              type="button"
              onClick={() => setMatrixMode("raw")}
              className={cn(
                "px-2.5 py-1 text-xs font-mono rounded-[2px] transition-colors",
                matrixMode === "raw"
                  ? "bg-[var(--ink)] text-[var(--paper)] font-bold"
                  : "text-[var(--ink-2)] hover:text-[var(--ink)]"
              )}
            >
              RAW COUNTS (N)
            </button>
          </div>
        </div>

        {/* Hover Readout Bar */}
        <div className="p-2.5 bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] font-mono text-xs flex items-center justify-between min-h-[38px]">
          {hoveredCell ? (
            <div className="flex items-center gap-2">
              <span className="font-bold text-[var(--ink)] uppercase">
                TRUE: {hoveredCell.actual.replace(/_/g, " ")}
              </span>
              <span className="text-[var(--ink-2)]">→</span>
              <span className="font-bold text-[var(--ink)] uppercase">
                PRED: {hoveredCell.predicted.replace(/_/g, " ")}
              </span>
              <span className="text-[var(--ink-2)] ml-2">
                [{hoveredCell.count} specimens · {hoveredCell.pct.toFixed(1)}%]
              </span>
            </div>
          ) : (
            <span className="text-[var(--ink-2)] italic">
              Hover over matrix cells to inspect specimen count and alignment percentage.
            </span>
          )}
        </div>

        {/* Matrix Grid Container */}
        <div className="overflow-x-auto border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] p-4">
          <div className="min-w-[640px]">
            {/* Header Column Labels */}
            <div className="grid grid-cols-[110px_repeat(12,1fr)] gap-1 mb-1">
              <div className="font-mono text-[9px] uppercase tracking-wider text-[var(--ink-2)] flex items-end justify-end pr-2 pb-1">
                TRUE \ PRED
              </div>
              {classes.map((cls) => (
                <div
                  key={cls}
                  className="font-mono text-[9px] uppercase tracking-tight text-[var(--ink-2)] text-center truncate py-1 rotate-[-35deg] origin-bottom-left"
                  title={cls}
                >
                  {cls.slice(0, 5)}
                </div>
              ))}
            </div>

            {/* Matrix Rows */}
            <div className="space-y-1">
              {rawMatrix.map((row, rowIdx) => {
                const actualClass = classes[rowIdx] || `class_${rowIdx}`;
                return (
                  <div key={actualClass} className="grid grid-cols-[110px_repeat(12,1fr)] gap-1 items-center">
                    {/* Row Label */}
                    <div
                      className="font-mono text-[10px] uppercase font-bold text-[var(--ink)] truncate pr-2 text-right"
                      title={actualClass}
                    >
                      {actualClass.replace(/_/g, " ")}
                    </div>

                    {/* Cells */}
                    {row.map((val, colIdx) => {
                      const predClass = classes[colIdx] || `class_${colIdx}`;
                      const isDiagonal = rowIdx === colIdx;
                      const normVal = normMatrix[rowIdx]?.[colIdx] ?? 0;
                      const intensity = Math.min(Math.round(normVal), 100);

                      return (
                        <div
                          key={`${rowIdx}-${colIdx}`}
                          onMouseEnter={() =>
                            setHoveredCell({
                              actual: actualClass,
                              predicted: predClass,
                              count: val,
                              pct: normVal,
                            })
                          }
                          onMouseLeave={() => setHoveredCell(null)}
                          className={cn(
                            "aspect-square flex items-center justify-center font-mono text-[10px] rounded-[1px] cursor-pointer transition-colors select-none",
                            isDiagonal
                              ? intensity > 85
                                ? "bg-[var(--ink)] text-[var(--paper)] font-bold ring-1 ring-[var(--hivis)]/50"
                                : "bg-[var(--ink)]/80 text-[var(--paper)] font-semibold"
                              : val > 0
                              ? "bg-[var(--caution)]/20 text-[var(--caution)] font-bold hover:bg-[var(--caution)]/40"
                              : "bg-[var(--paper)]/40 text-transparent hover:text-[var(--ink-2)]"
                          )}
                          title={`${actualClass} -> ${predClass}: ${val} (${normVal.toFixed(1)}%)`}
                        >
                          {matrixMode === "normalized" ? (
                            normVal > 0 ? `${Math.round(normVal)}` : "·"
                          ) : (
                            val > 0 ? `${val}` : "·"
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* 04 PER-CLASS SPECIFICATIONS & GENERALIZATION                          */}
      {/* ==================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Per-Class F1 Table (7 Cols) */}
        <section
          aria-labelledby="heading-per-class"
          className="lg:col-span-7 bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6 space-y-4"
        >
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
              03 / CLASS GRANULARITY
            </span>
            <h2 id="heading-per-class" className="font-sans font-bold text-lg text-[var(--ink)]">
              Per-Class Performance
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <caption className="sr-only">Per-Class Precision, Recall, and F1 Metrics</caption>
              <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)]">
                <tr>
                  <th className="p-2">Material</th>
                  <th className="p-2 text-right">Precision</th>
                  <th className="p-2 text-right">Recall</th>
                  <th className="p-2 text-right">F1 Score</th>
                  <th className="p-2 text-right">Support</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
                {classes.map((cls) => {
                  const m = activeMetrics?.per_class?.[cls];
                  const prec = m ? `${(m.precision * 100).toFixed(1)}%` : "—";
                  const rec = m ? `${(m.recall * 100).toFixed(1)}%` : "—";
                  const f1 = m ? `${(m.f1 * 100).toFixed(1)}%` : "—";
                  const supp = m ? m.support : "—";

                  return (
                    <tr key={cls} className="hover:bg-[var(--paper)] transition-colors">
                      <td className="p-2 capitalize font-semibold flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-[0.5px] bg-[var(--ink)]" aria-hidden="true" />
                        {cls.replace(/_/g, " ")}
                      </td>
                      <td className="p-2 text-right">{prec}</td>
                      <td className="p-2 text-right">{rec}</td>
                      <td className="p-2 text-right font-bold">{f1}</td>
                      <td className="p-2 text-right text-[var(--ink-2)]">{supp}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Dataset Generalization & Calibration (5 Cols) */}
        <div className="lg:col-span-5 space-y-8">
          {/* Source Generalization */}
          <section
            aria-labelledby="heading-sources"
            className="bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6 space-y-4"
          >
            <div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
                04 / CROSS-DATASET GENERALIZATION
              </span>
              <h2 id="heading-sources" className="font-sans font-bold text-lg text-[var(--ink)]">
                Source Dataset Accuracy
              </h2>
            </div>

            <div className="space-y-3">
              {activeMetrics?.per_source_accuracy &&
                Object.entries(activeMetrics.per_source_accuracy).map(([src, d]) => {
                  const accPct = (d.accuracy * 100).toFixed(1);
                  return (
                    <div key={src} className="p-3 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px]">
                      <div className="flex items-center justify-between font-mono text-xs mb-1">
                        <span className="font-bold uppercase text-[var(--ink)]">{src}</span>
                        <span className="font-bold text-[var(--ink)]">{accPct}%</span>
                      </div>
                      <div className="w-full bg-[var(--rule)] h-1.5 rounded-[1px] overflow-hidden mb-1">
                        <div
                          className="bg-[var(--ink)] h-full rounded-[1px]"
                          style={{ width: `${accPct}%` }}
                        />
                      </div>
                      <div className="flex justify-between font-mono text-[10px] text-[var(--ink-2)]">
                        <span>{d.correct} / {d.total} correct</span>
                        <span>Held-out test split</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </section>

          {/* Calibration & Sharpness */}
          <section
            aria-labelledby="heading-calib"
            className="bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6 space-y-4"
          >
            <div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
                05 / PROBABILITY CALIBRATION
              </span>
              <h2 id="heading-calib" className="font-sans font-bold text-lg text-[var(--ink)]">
                Temperature Scaling & ECE
              </h2>
            </div>

            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="p-3 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px]">
                <span className="text-[10px] text-[var(--ink-2)] uppercase block mb-1">
                  Temperature (T)
                </span>
                <span className="text-xl font-bold text-[var(--ink)]">
                  {typeof activeCalib?.temperature === "number" ? activeCalib.temperature.toFixed(4) : "—"}
                </span>
                <span className="text-[9px] text-[var(--ink-2)] block mt-0.5">
                  T &lt; 1.0 sharpens logits
                </span>
              </div>

              <div className="p-3 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px]">
                <span className="text-[10px] text-[var(--ink-2)] uppercase block mb-1">
                  ECE (Pre → Post)
                </span>
                <span className="text-xl font-bold text-[var(--wet)]">
                  {typeof activeCalib?.ece_after === "number" ? `${(activeCalib.ece_after * 100).toFixed(1)}%` : "—"}
                </span>
                <span className="text-[9px] text-[var(--ink-2)] block mt-0.5">
                  Down from {typeof activeCalib?.ece_before === "number" ? `${(activeCalib.ece_before * 100).toFixed(1)}%` : "—"}
                </span>
              </div>
            </div>

            <div className="p-3 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px] font-mono text-xs">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] uppercase text-[var(--ink-2)]">UI Uncertainty Gate:</span>
                <span className="font-bold text-[var(--ink)]">
                  {activeCalib?.ui_uncertain_threshold ?? activeCalib?.uncertain_threshold ?? 0.585}
                </span>
              </div>
              <p className="text-[11px] text-[var(--ink-2)] leading-relaxed">
                Validation-calibrated threshold to flag ambiguous specimens. Retains 88.2% automated throughput with 97.2% unflagged precision.
              </p>
            </div>
          </section>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* 05 TRAINING DYNAMICS (history.csv Recharts Curve)                     */}
      {/* ==================================================================== */}
      {historyData.length > 0 && (
        <section
          aria-labelledby="heading-training"
          className="bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] p-6 space-y-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--ink-2)] font-semibold">
                06 / CONVERGENCE TRAJECTORY
              </span>
              <h2 id="heading-training" className="font-sans font-extrabold text-xl uppercase tracking-tight text-[var(--ink)]">
                Training & Validation Dynamics ({historyData.length} Epochs)
              </h2>
              <p className="font-sans text-xs text-[var(--ink-2)] mt-0.5">
                Two-stage training: Phase 1 (Frozen Backbone, Epochs 1–3) → Phase 2 (Differential Learning Rate Fine-tuning).
              </p>
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowDataTables((prev) => !prev)}
              className="font-mono text-xs flex items-center gap-1.5"
              aria-expanded={showDataTables}
            >
              <TableIcon className="w-3.5 h-3.5" aria-hidden="true" />
              {showDataTables ? "HIDE EPOCH TABLE" : "ACCESSIBLE EPOCH TABLE"}
            </Button>
          </div>

          <figure className="space-y-4">
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--rule)" />
                  <XAxis
                    dataKey="epoch"
                    stroke="var(--ink-2)"
                    tick={{ fill: "var(--ink-2)", fontSize: 10, fontFamily: "var(--font-mono)" }}
                  />
                  <YAxis
                    stroke="var(--ink-2)"
                    tick={{ fill: "var(--ink-2)", fontSize: 10, fontFamily: "var(--font-mono)" }}
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
                  <Legend
                    verticalAlign="top"
                    wrapperStyle={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      paddingBottom: "12px",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="val_macro_f1"
                    name="Val Macro-F1 (%)"
                    stroke="var(--hivis)"
                    strokeWidth={2}
                    dot={{ r: 2 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="train_loss"
                    name="Train Loss"
                    stroke="var(--ink-2)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="val_loss"
                    name="Val Loss"
                    stroke="var(--ink)"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <figcaption className="pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink-2)]">
              Convergence curves recorded across training runs, showing smooth validation loss minimization without catastrophic overfitting.
            </figcaption>

            {showDataTables && (
              <div className="max-h-60 overflow-y-auto border border-[var(--rule)] rounded-[2px]">
                <table className="w-full text-left font-mono text-xs">
                  <caption className="sr-only">Epoch-by-Epoch Training Log Table</caption>
                  <thead className="bg-[var(--paper)] text-[var(--ink-2)] border-b border-[var(--rule)] sticky top-0">
                    <tr>
                      <th className="p-2">Epoch</th>
                      <th className="p-2">Phase</th>
                      <th className="p-2 text-right">Train Loss</th>
                      <th className="p-2 text-right">Val Loss</th>
                      <th className="p-2 text-right">Val Acc (%)</th>
                      <th className="p-2 text-right">Val Macro-F1 (%)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--rule)] text-[var(--ink)]">
                    {historyData.map((h) => (
                      <tr key={h.epoch} className="hover:bg-[var(--paper)]">
                        <td className="p-2 font-bold">{h.epoch}</td>
                        <td className="p-2">{h.phase === 1 ? "Phase 1 (Head)" : "Phase 2 (Full)"}</td>
                        <td className="p-2 text-right">{h.train_loss}</td>
                        <td className="p-2 text-right">{h.val_loss}</td>
                        <td className="p-2 text-right">{h.val_acc}%</td>
                        <td className="p-2 text-right font-bold text-[var(--ink)]">{h.val_macro_f1}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </figure>
        </section>
      )}
    </div>
  );
}
