import * as React from "react";
import type { Metadata } from "next";
import { api } from "@/lib/api";
import type { PredictionListItem } from "@/lib/types";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { HistoryClient } from "./HistoryClient";

export const metadata: Metadata = {
  title: "History — EcoSort",
  description:
    "Chronological archive of physical waste scans classified by PyTorch CNN models into municipal segregation streams.",
};

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  let initialItems: PredictionListItem[] = [];
  try {
    initialItems = await api.getPredictions({ limit: 24 });
  } catch (err) {
    console.error("HistoryPage server fetch error:", err);
  }

  return (
    <main id="main-content" className="flex-1 py-12 md:py-16 bg-[var(--paper)] transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Spec Eyebrow & Header */}
        <div className="mb-8 md:mb-12">
          <Eyebrow className="mb-3">01 — ARCHIVE</Eyebrow>
          <h1
            className="text-4xl sm:text-5xl md:text-6xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans mb-3"
            style={{ fontStretch: "75%" }}
          >
            Classification History
          </h1>
          <p className="font-sans text-sm sm:text-base text-[var(--ink-2)] max-w-2xl">
            Chronological contact sheet of physical waste scans processed by local models. Filter by municipal stream or inspect individual activation heatmaps.
          </p>
        </div>

        {/* Interactive Client View */}
        <HistoryClient initialItems={initialItems} />
      </div>
    </main>
  );
}
