import * as React from "react";
import {
  ArrowRight,
  CheckCircle2,
  Leaf,
  Package,
  ShieldAlert,
  TriangleAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { StatTile } from "@/components/ui/StatTile";
import { Scanner } from "@/components/scanner/Scanner";
import { SpecimenWall } from "@/components/home/SpecimenWall";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  // Attempt to fetch model summaries from backend
  let defaultModelAcc: number | null = 92.44;
  let defaultModelParams = "4.22M";
  let defaultModelLatency = "55.5 ms";
  let defaultModelName = "MobileNetV3";
  try {
    const models = await api.getModels();
    const defaultModel = models.find((m) => m.is_default) || models[0];
    if (defaultModel) {
      const summary = defaultModel.metrics_summary;
      const acc = summary?.accuracy ?? summary?.test_accuracy;
      if (typeof acc === "number") {
        defaultModelAcc = Math.round(acc * 1000) / 10;
      }
      if (typeof summary?.params === "number") {
        defaultModelParams = `${(summary.params / 1_000_000).toFixed(2)}M`;
      }
      const lat = summary?.cpu_latency_ms_p50 ?? summary?.latency_ms_cpu_p50;
      if (typeof lat === "number") {
        defaultModelLatency = `${lat.toFixed(1)} ms`;
      }
      if (defaultModel.display_name) {
        defaultModelName = defaultModel.display_name;
      }
    }
  } catch {
    // If backend is momentarily unreachable, defaultModelAcc stays fallback
  }

  return (
    <main id="main-content" className="flex-1 flex flex-col">
      {/* ==================================================================== */}
      {/* 01 HERO SECTION: Asymmetric 5/7 Split with Interactive Scanner       */}
      {/* ==================================================================== */}
      <section className="border-b border-[var(--rule)] bg-[var(--paper)] py-12 md:py-20 transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
            {/* Left 5 Cols: Spec & Title */}
            <div className="lg:col-span-5 flex flex-col justify-center">
              <Eyebrow className="mb-4">
                01 — SCAN
              </Eyebrow>

              <h1
                className="text-6xl sm:text-7xl lg:text-8xl font-extrabold uppercase tracking-tight text-[var(--ink)] leading-[0.9] font-sans mb-6"
                style={{ fontStretch: "75%" }}
              >
                WHICH BIN?
              </h1>

              <p className="font-sans text-base sm:text-lg text-[var(--ink-2)] font-medium leading-relaxed mb-4">
                Know in a second. Automated waste sorting instrument classifying physical scrap into four municipal segregation streams.
              </p>

              <div className="p-3.5 bg-[var(--surface)] border border-[var(--rule)] rounded-[2px] mb-8">
                <div className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-2)] font-semibold mb-1">
                  SWM Rules 2026 Mandate
                </div>
                <p className="font-sans text-xs text-[var(--ink-2)] leading-normal">
                  Source-segregation of municipal solid waste into Wet, Dry, Sanitary, and Special Care streams before collection.
                </p>
              </div>

              {/* Primary Action Button: Scan an item scrolls to / focuses the scanner */}
              <div className="flex flex-wrap items-center gap-3">
                <Button href="#scanner-section" variant="primary" size="md" withArrow>
                  Scan an item
                </Button>
                <Button href="/about" variant="outline" size="md">
                  Read the method
                </Button>
              </div>
            </div>

            {/* Right 7 Cols: Interactive Viewfinder Scanner Component */}
            <div className="lg:col-span-7">
              <Scanner initialModel="mobilenet_v3" />
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* 02 SPECIMEN WALL: 24 Real Held-Out Test Set Images (DESIGN §5)       */}
      {/* ==================================================================== */}
      <SpecimenWall />

      {/* ==================================================================== */}
      {/* 03 FOUR-STREAM REGULATORY LEGEND (DESIGN.md §5)                       */}
      {/* ==================================================================== */}
      <section className="py-16 md:py-24 border-b border-[var(--rule)] bg-[var(--paper)] transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="mb-10">
            <Eyebrow className="mb-2">
              03 — STREAMS
            </Eyebrow>
            <h2
              className="text-3xl sm:text-4xl md:text-5xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans"
              style={{ fontStretch: "75%" }}
            >
              The Four Municipal Streams
            </h2>
            <p className="font-sans text-sm text-[var(--ink-2)] mt-2 max-w-2xl">
              Under SWM Rules 2026, citizen segregation separates 12 physical material categories into 4 statutory destination streams.
            </p>
          </div>

          {/* 4 Tall Columns Separated by Hairline Rules */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] overflow-hidden divide-y md:divide-y-0 md:divide-x divide-[var(--rule)] mb-4">
            {/* Stream 1: Wet */}
            <div className="p-6 flex flex-col justify-between">
              <div>
                <div className="h-1.5 w-full bg-[var(--wet)] rounded-[1px] mb-4" />
                <div className="flex items-center gap-2 mb-2">
                  <Leaf className="w-5 h-5 text-[var(--wet)]" aria-hidden="true" />
                  <h3 className="font-sans font-bold text-lg text-[var(--ink)]">
                    Wet Waste
                  </h3>
                </div>
                <div className="font-mono text-xs text-[var(--ink-2)] uppercase tracking-wider mb-4">
                  <span className="text-[var(--ink)] font-bold">Commonly Green Bin</span> · Compost
                </div>
                <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-4">
                  Biodegradable organic matter suitable for biological decomposition and nutrient recovery.
                </p>
                <div className="space-y-1.5 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                  <div>• Food & kitchen scraps</div>
                  <div>• Fruit & vegetable peel</div>
                  <div>• Tea leaves & coffee grounds</div>
                  <div>• Garden biomass</div>
                </div>
              </div>
              <div className="mt-6 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                Mandate: Decentralized Composting / Biomethanation
              </div>
            </div>

            {/* Stream 2: Dry */}
            <div className="p-6 flex flex-col justify-between">
              <div>
                <div className="h-1.5 w-full bg-[var(--dry)] rounded-[1px] mb-4" />
                <div className="flex items-center gap-2 mb-2">
                  <Package className="w-5 h-5 text-[var(--dry)]" aria-hidden="true" />
                  <h3 className="font-sans font-bold text-lg text-[var(--ink)]">
                    Dry Waste
                  </h3>
                </div>
                <div className="font-mono text-xs text-[var(--ink-2)] uppercase tracking-wider mb-4">
                  <span className="text-[var(--ink)] font-bold">Commonly Blue Bin</span> · Recycling
                </div>
                <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-4">
                  Non-biodegradable recyclable packaging materials kept clean and dry.
                </p>
                <div className="space-y-1.5 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                  <div>• Paper, books & newspaper</div>
                  <div>• Cardboard boxes & cartons</div>
                  <div>• PET, HDPE & rigid plastics</div>
                  <div>• Steel, aluminum & tin cans</div>
                </div>
              </div>
              <div className="mt-6 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                Mandate: Material Recovery Facility (MRF)
              </div>
            </div>

            {/* Stream 3: Sanitary */}
            <div className="p-6 flex flex-col justify-between">
              <div>
                <div className="h-1.5 w-full bg-[var(--sanitary)] rounded-[1px] mb-4" />
                <div className="flex items-center gap-2 mb-2">
                  <ShieldAlert className="w-5 h-5 text-[var(--sanitary)]" aria-hidden="true" />
                  <h3 className="font-sans font-bold text-lg text-[var(--ink)]">
                    Sanitary
                  </h3>
                </div>
                <div className="font-mono text-xs text-[var(--ink-2)] uppercase tracking-wider mb-2">
                  <span className="text-[var(--ink)] font-bold">Secure Paper Wrap</span> · Hygiene
                </div>
                <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-3">
                  Personal hygiene and medical protection items wrapped securely in paper or designated pouches.
                </p>
                <div className="p-2 bg-[var(--sanitary)]/10 text-[var(--ink)] border-l-2 border-[var(--sanitary)] font-medium text-[11px] rounded-[2px] mb-3 leading-tight font-sans">
                  EcoSort recognises: face masks, gloves. Not yet recognised: diapers, sanitary napkins (no public open-access training data).
                </div>
                <div className="space-y-1.5 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                  <div>• Face masks & latex gloves</div>
                  <div>• Personal protective gear</div>
                </div>
              </div>
              <div className="mt-6 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                Mandate: Wrapped securely and stored separately
              </div>
            </div>

            {/* Stream 4: Special Care */}
            <div className="p-6 flex flex-col justify-between">
              <div>
                <div className="h-1.5 w-full bg-[var(--special)] rounded-[1px] mb-4" />
                <div className="flex items-center gap-2 mb-2">
                  <TriangleAlert className="w-5 h-5 text-[var(--special)]" aria-hidden="true" />
                  <h3 className="font-sans font-bold text-lg text-[var(--ink)]">
                    Special Care
                  </h3>
                </div>
                <div className="font-mono text-xs text-[var(--ink-2)] uppercase tracking-wider mb-4">
                  <span className="text-[var(--ink)] font-bold">Designated Drop Point</span> · Hazardous
                </div>
                <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed mb-4">
                  Domestic hazardous chemicals, electrical components, and heavy metal e-waste.
                </p>
                <div className="space-y-1.5 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                  <div>• Alkaline & Li-ion batteries</div>
                  <div>• Broken phones & electronics</div>
                  <div>• Syringes & expired medicine</div>
                  <div>• Aerosol cans & fluorescent tubes</div>
                </div>
              </div>
              <div className="mt-6 pt-3 border-t border-[var(--rule)] font-mono text-[11px] text-[var(--ink)]">
                Mandate: Authorised agencies / designated collection centres
              </div>
            </div>
          </div>

          <div className="text-[11px] font-mono text-[var(--ink-2)] italic">
            * Note: Card colours (green, blue, orange, red) are a design choice for visual clarity, not statutory container colours.
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* 04 INFERENCE PIPELINE DIAGRAM (DESIGN.md §6 Continuous Hairline Flow) */}
      {/* ==================================================================== */}
      <section className="py-16 md:py-24 border-b border-[var(--rule)] bg-[var(--paper)] transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="mb-10">
            <Eyebrow className="mb-2">
              04 — PIPELINE
            </Eyebrow>
            <h2
              className="text-3xl sm:text-4xl md:text-5xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans"
              style={{ fontStretch: "75%" }}
            >
              How It Works
            </h2>
            <p className="font-sans text-sm text-[var(--ink-2)] mt-2 max-w-2xl">
              From raw camera capture to calibrated municipal routing and gradient visual explanation.
            </p>
          </div>

          {/* Continuous Horizontal Pipeline Drawn with 1px Rules & Connecting Arrows */}
          <div className="border border-[var(--rule)] bg-[var(--surface)] rounded-[4px] overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-6 divide-y md:divide-y-0 md:divide-x divide-[var(--rule)]">
              {/* Step 1 */}
              <div className="p-4 flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-[var(--ink-2)] uppercase tracking-widest font-semibold">
                      01 / CAPTURE
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-[var(--ink-2)] hidden md:block shrink-0" aria-hidden="true" />
                  </div>
                  <div className="font-sans font-bold text-sm text-[var(--ink)] mb-1">
                    Photo Input
                  </div>
                  <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
                    Camera sensor or image upload
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-[var(--rule)] font-mono text-[10px] text-[var(--ink-2)]">
                  RGB 3-channel
                </div>
              </div>

              {/* Step 2 */}
              <div className="p-4 flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-[var(--ink-2)] uppercase tracking-widest font-semibold">
                      02 / PREPROCESS
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-[var(--ink-2)] hidden md:block shrink-0" aria-hidden="true" />
                  </div>
                  <div className="font-sans font-bold text-sm text-[var(--ink)] mb-1">
                    Sanitization
                  </div>
                  <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
                    EXIF stripped, 224×224 normalized
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-[var(--rule)] font-mono text-[10px] text-[var(--ink-2)]">
                  ImageNet stats
                </div>
              </div>

              {/* Step 3 */}
              <div className="p-4 flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-[var(--ink-2)] uppercase tracking-widest font-semibold">
                      03 / INFERENCE
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-[var(--ink-2)] hidden md:block shrink-0" aria-hidden="true" />
                  </div>
                  <div className="font-sans font-bold text-sm text-[var(--ink)] mb-1">
                    PyTorch CNN
                  </div>
                  <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
                    {defaultModelName} {defaultModelParams} parameters
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-[var(--rule)] font-mono text-[10px] text-[var(--ink-2)]">
                  ~{defaultModelLatency} CPU p50
                </div>
              </div>

              {/* Step 4 */}
              <div className="p-4 flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-[var(--ink-2)] uppercase tracking-widest font-semibold">
                      04 / CALIBRATE
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-[var(--ink-2)] hidden md:block shrink-0" aria-hidden="true" />
                  </div>
                  <div className="font-sans font-bold text-sm text-[var(--ink)] mb-1">
                    Temperature
                  </div>
                  <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
                    Post-hoc scaling (T = 0.8392)
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-[var(--rule)] font-mono text-[10px] text-[var(--ink-2)]">
                  val ECE after calibration: 0.0795
                </div>
              </div>

              {/* Step 5 */}
              <div className="p-4 flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-[var(--ink-2)] uppercase tracking-widest font-semibold">
                      05 / ROUTING
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-[var(--ink-2)] hidden md:block shrink-0" aria-hidden="true" />
                  </div>
                  <div className="font-sans font-bold text-sm text-[var(--ink)] mb-1">
                    Stream Map
                  </div>
                  <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
                    12 classes mapped to 4 streams
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-[var(--rule)] font-mono text-[10px] text-[var(--ink-2)]">
                  SWM Rules 2026
                </div>
              </div>

              {/* Step 6 */}
              <div className="p-4 flex flex-col justify-between relative group bg-[var(--hivis)]/10">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[10px] text-[var(--ink)] uppercase tracking-widest font-bold">
                      06 / EXPLAIN
                    </span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-[var(--ink)] shrink-0" aria-hidden="true" />
                  </div>
                  <div className="font-sans font-bold text-sm text-[var(--ink)] mb-1">
                    Grad-CAM
                  </div>
                  <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
                    Spatial saliency heatmap overlay
                  </p>
                </div>
                <div className="mt-4 pt-2 border-t border-[var(--rule)] font-mono text-[10px] text-[var(--ink)] font-bold">
                  Layer 16 Hooks
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ==================================================================== */}
      {/* 05 STAT STRIP: Greyparrot-style Big Numbers (DESIGN.md §5)           */}
      {/* ==================================================================== */}
      <section className="py-16 md:py-24 bg-[var(--paper)] transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="mb-10">
            <Eyebrow className="mb-2">
              05 — BENCHMARKS
            </Eyebrow>
            <h2
              className="text-3xl sm:text-4xl md:text-5xl font-extrabold uppercase tracking-tight text-[var(--ink)] font-sans"
              style={{ fontStretch: "75%" }}
            >
              System Scale & Metrics
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatTile
              value="18,951"
              label="Standardized Images"
              sublabel="Train / Val / Test (70/15/15 Split)"
            />
            <StatTile
              value="12"
              label="Physical Materials"
              sublabel="Plastic, Cardboard, E-Waste, etc."
            />
            <StatTile
              value="4"
              label="Segregation Streams"
              sublabel="India SWM Rules 2026 Mandate"
            />
            {defaultModelAcc !== null && (
              <StatTile
                value={`${defaultModelAcc}%`}
                label="TEST ACCURACY · 2,843 held-out images"
                sublabel="MobileNetV3 · 95% CI: [91.4%, 93.4%]"
                highlight
              />
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
