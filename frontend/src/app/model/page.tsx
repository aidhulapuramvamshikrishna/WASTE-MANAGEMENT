import * as React from "react";
import type { Metadata } from "next";
import { api } from "@/lib/api";
import type { ModelFullMetricsOut, ModelSummaryOut } from "@/lib/types";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { ModelView } from "./ModelView";

export const metadata: Metadata = {
  title: "Model Telemetry — EcoSort",
  description:
    "Engineering benchmarks, McNemar hypothesis testing, 12x12 confusion matrices, calibration ECE, and training dynamics across all CNN architectures.",
};

export const dynamic = "force-dynamic";

export default async function ModelPage() {
  let modelSummaries: ModelSummaryOut[] = [];
  const modelsFullData: Record<string, ModelFullMetricsOut> = {};

  try {
    modelSummaries = await api.getModels();
    // Fetch full metrics for each discovered model
    await Promise.all(
      modelSummaries.map(async (m) => {
        try {
          const full = await api.getModelMetrics(m.name);
          modelsFullData[m.name] = full;
        } catch (err) {
          console.error(`Failed to load metrics for ${m.name}:`, err);
        }
      })
    );
  } catch (err) {
    console.error("ModelPage getModels error:", err);
  }

  return (
    <main id="main-content" className="flex-1 py-12 md:py-16 bg-[var(--paper)] transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Spec Eyebrow & Header */}
        <div className="mb-8 md:mb-12">
          <Eyebrow className="mb-3">03 — EVALUATION BENCHMARK</Eyebrow>
          <h1
            className="text-4xl sm:text-5xl md:text-6xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans mb-3"
            style={{ fontStretch: "75%" }}
          >
            Model Diagnostic Telemetry
          </h1>
          <p className="font-sans text-sm sm:text-base text-[var(--ink-2)] max-w-2xl">
            Exhaustive empirical analysis across pretrained transfer learning and from-scratch CNN architectures. Zero simulated metrics.
          </p>
        </div>

        {modelSummaries.length === 0 ? (
          <div className="p-12 text-center border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] font-mono text-xs text-[var(--ink-2)]">
            NO CNN MODELS LOADED OR BACKEND REGISTRY OFFLINE
          </div>
        ) : (
          <ModelView modelSummaries={modelSummaries} modelsFullData={modelsFullData} />
        )}
      </div>
    </main>
  );
}
