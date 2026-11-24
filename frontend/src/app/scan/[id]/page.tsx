import * as React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { HeatmapCompare } from "@/components/scan/HeatmapCompare";
import { ReadoutPanel } from "@/components/scan/ReadoutPanel";
import { FeedbackFlow } from "@/components/scan/FeedbackFlow";

export const dynamic = "force-dynamic";

interface ScanResultPageProps {
  params: Promise<{ id: string }>;
}

export default async function ScanResultPage({ params }: ScanResultPageProps) {
  const { id } = await params;

  let prediction;
  try {
    prediction = await api.getPrediction(id);
  } catch (err) {
    console.error("Failed to fetch prediction:", err);
    notFound();
  }

  if (!prediction) {
    notFound();
  }

  const imageUrl = api.getImageUrl(prediction.id);
  const gradcamUrl = prediction.gradcam_url ? api.getGradcamUrl(prediction.id) : null;

  return (
    <main id="main-content" className="flex-1 py-10 md:py-16 bg-[var(--paper)] transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        {/* Navigation Breadcrumb & Back Link (Responsive: stack on mobile to prevent collision, row on desktop) */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 sm:pb-6 mb-8 border-b border-[var(--rule)]">
          <Link
            href="/"
            className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-[var(--ink-2)] hover:text-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] rounded-[2px]"
          >
            <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
            <span>RETURN TO SCANNER</span>
          </Link>

          <Eyebrow>
            01 — CLASSIFICATION RESULT
          </Eyebrow>
        </div>

        {/* 7/5 Asymmetric Grid (DESIGN §6) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start mb-10">
          {/* Left 7 Columns: Heatmap Comparison Viewport */}
          <div className="lg:col-span-7">
            <HeatmapCompare
              imageUrl={imageUrl}
              gradcamUrl={gradcamUrl}
              label={prediction.label}
            />
          </div>

          {/* Right 5 Columns: Spec Sheet Readout Panel */}
          <div className="lg:col-span-5">
            <ReadoutPanel prediction={prediction} />
          </div>
        </div>

        {/* Citizen Feedback Flow Section */}
        <div className="max-w-3xl">
          <FeedbackFlow
            predictionId={prediction.id}
            initialLabel={prediction.label}
          />
        </div>
      </div>
    </main>
  );
}
