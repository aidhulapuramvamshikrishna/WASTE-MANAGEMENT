"use client";

import * as React from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { cn } from "@/lib/utils";

interface SpecimenItem {
  filename: string;
  class: string;
  stream: string;
  original_file: string;
}

export function SpecimenWall() {
  const router = useRouter();
  const [samples, setSamples] = React.useState<SpecimenItem[]>([]);
  const [loadingFile, setLoadingFile] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    fetch("/samples/samples.json")
      .then((res) => res.json())
      .then((data) => setSamples(data))
      .catch((err) => console.error("Failed to load specimen samples", err));
  }, []);

  const handleSelectSample = async (item: SpecimenItem) => {
    setLoadingFile(item.filename);
    setError(null);
    try {
      // 1. Fetch real blob from public samples
      const resBlob = await fetch(`/samples/${item.filename}`);
      if (!resBlob.ok) throw new Error("Could not load sample image file");
      const blob = await resBlob.blob();

      // 2. Submit real prediction to backend API
      const pred = await api.predict(blob, { explain: true });
      // 3. Navigate to result readout
      router.push(`/scan/${pred.id}`);
    } catch (err: unknown) {
      console.error("Failed to classify sample:", err);
      setError("Failed to run sample prediction. Please ensure backend is reachable.");
      setLoadingFile(null);
    }
  };

  if (samples.length === 0) {
    return null;
  }

  return (
    <section className="py-16 md:py-24 border-b border-[var(--rule)] bg-[var(--paper)] transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 gap-4">
          <div>
            <Eyebrow className="mb-2">02 — SPECIMEN BENCHMARK</Eyebrow>
            <h2
              className="text-3xl sm:text-4xl md:text-5xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans"
              style={{ fontStretch: "75%" }}
            >
              Test Set Specimen Wall
            </h2>
            <p className="font-sans text-sm text-[var(--ink-2)] mt-2 max-w-2xl">
              24 real held-out test specimens across all 12 municipal categories. Click any sample to run live inference and view Grad-CAM explainability.
            </p>
          </div>
          <div className="font-mono text-xs text-[var(--ink-2)] uppercase shrink-0">
            24 / 24 VERIFIED TEST IMAGES
          </div>
        </div>

        {error && (
          <div role="alert" className="p-3 bg-red-950/20 border border-red-500/40 text-red-600 dark:text-red-400 font-sans text-xs rounded-[2px] mb-6">
            {error}
          </div>
        )}

        {/* 12-class x 2 grid: responsive 2 to 6 columns */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {samples.map((item) => {
            const isLoading = loadingFile === item.filename;
            const streamFormatted = item.stream.replace("_", " ").toUpperCase();
            const classFormatted = item.class.replace("_", " ").toUpperCase();

            return (
              <button
                key={item.filename}
                type="button"
                onClick={() => handleSelectSample(item)}
                disabled={loadingFile !== null}
                className={cn(
                  "group relative aspect-square bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] overflow-hidden p-1 text-left flex flex-col justify-between transition-all hover:border-[var(--ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-pointer select-none",
                  isLoading && "ring-2 ring-[var(--hivis)]"
                )}
              >
                {/* Image thumb */}
                <div className="relative w-full h-full bg-black/5 dark:bg-white/5 rounded-[1px] overflow-hidden">
                  <Image
                    src={`/samples/${item.filename}`}
                    alt={`Sample photo of ${item.class}`}
                    fill
                    sizes="(max-width: 768px) 50vw, (max-width: 1200px) 25vw, 16vw"
                    className="object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />

                  {/* "Sample" Watermark Tag */}
                  <span className="absolute top-1.5 left-1.5 font-mono text-[9px] uppercase tracking-wider font-bold bg-black/75 text-white/90 px-1 py-0.5 rounded-[1px] z-10">
                    SAMPLE
                  </span>

                  {/* Loading Spinner Overlay */}
                  {isLoading && (
                    <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center gap-1 z-20 text-white font-mono text-[10px] font-bold">
                      <RefreshCw className="w-4 h-4 animate-spin text-[var(--hivis)]" />
                      <span>INFERRING</span>
                    </div>
                  )}
                </div>

                {/* Bottom mono metadata bar */}
                <div className="mt-1.5 px-0.5 flex items-center justify-between font-mono text-[10px] text-[var(--ink-2)] truncate">
                  <span className="font-bold text-[var(--ink)] truncate">{classFormatted}</span>
                  <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--ink-2)] shrink-0 ml-1">
                    {streamFormatted}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
