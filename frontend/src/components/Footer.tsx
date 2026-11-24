import * as React from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-[var(--rule)] bg-[var(--paper)] mt-auto transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 md:py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Col 1: Identification */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-2">
              <span
                className="font-sans font-extrabold text-base tracking-tight uppercase text-[var(--ink)]"
                style={{ fontStretch: "75%" }}
              >
                EcoSort
              </span>
              <span className="font-mono text-[10px] text-[var(--ink-2)] border border-[var(--rule)] px-1.5 py-0.5 rounded-[2px] uppercase">
                v0.1.0
              </span>
            </div>
            <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed max-w-sm mb-4">
              Municipal Solid Waste classification system aligning 12 physical material categories into 4 segregation streams under India Solid Waste Management Rules 2026.
            </p>
            <div className="font-mono text-[11px] text-[var(--ink-2)]">
              College Capstone Project · Academic Non-Commercial Use Only
            </div>
          </div>

          {/* Col 2: Benchmark Datasets & Citations */}
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink)] font-semibold mb-3">
              Data Citations
            </div>
            <ul className="space-y-2 text-xs font-sans text-[var(--ink-2)]">
              <li>
                <a
                  href="https://www.kaggle.com/datasets/asdasdasasdas/garbage-classification"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-[var(--ink)] inline-flex items-center gap-1 hover:underline"
                >
                  <span>Garbage12 (Kaggle)</span>
                  <ArrowUpRight className="w-3 h-3 text-[var(--ink-2)]" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/AgaMiko/waste-datasets-review"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-[var(--ink)] inline-flex items-center gap-1 hover:underline"
                >
                  <span>RealWaste (Landfill)</span>
                  <ArrowUpRight className="w-3 h-3 text-[var(--ink-2)]" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/nikhilvenkatkumsetty/TrashBox"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-[var(--ink)] inline-flex items-center gap-1 hover:underline"
                >
                  <span>TrashBox (E-Waste/Hazard)</span>
                  <ArrowUpRight className="w-3 h-3 text-[var(--ink-2)]" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/garythung/trashnet"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-[var(--ink)] inline-flex items-center gap-1 hover:underline"
                >
                  <span>TrashNet (Thung & Yang)</span>
                  <ArrowUpRight className="w-3 h-3 text-[var(--ink-2)]" />
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Navigation */}
          <div>
            <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink)] font-semibold mb-3">
              Navigation
            </div>
            <ul className="space-y-2 text-xs font-sans text-[var(--ink-2)]">
              <li>
                <Link href="/" className="hover:text-[var(--ink)] hover:underline">
                  01 — Viewfinder Scan
                </Link>
              </li>
              <li>
                <Link href="/history" className="hover:text-[var(--ink)] hover:underline">
                  02 — Contact Sheet History
                </Link>
              </li>
              <li>
                <Link href="/insights" className="hover:text-[var(--ink)] hover:underline">
                  03 — Operational Insights
                </Link>
              </li>
              <li>
                <Link href="/model" className="hover:text-[var(--ink)] hover:underline">
                  04 — Model Benchmarks & CAM
                </Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-[var(--ink)] hover:underline">
                  05 — Methodology & Limitations
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-6 border-t border-[var(--rule)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] font-mono text-[var(--ink-2)]">
          <div>
            PyTorch CNN · Temperature Scaled · Grad-CAM Explainable AI
          </div>
          <div>
            Zero external AI APIs · 100% locally trained weights
          </div>
        </div>
      </div>
    </footer>
  );
}
