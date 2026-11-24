"use client";

import * as React from "react";
import Image from "next/image";
import { SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

interface HeatmapCompareProps {
  imageUrl: string;
  gradcamUrl: string | null;
  label: string;
  className?: string;
}

export function HeatmapCompare({
  imageUrl,
  gradcamUrl,
  label,
  className,
}: HeatmapCompareProps) {
  // Slider position from 0 to 100%
  const [sliderPos, setSliderPos] = React.useState<number>(50);
  const [isDragging, setIsDragging] = React.useState<boolean>(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  const handleMove = React.useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSliderPos(Math.round(pct));
    },
    []
  );

  const handleMouseDown = () => setIsDragging(true);
  const handleTouchStart = () => setIsDragging(true);

  React.useEffect(() => {
    const handleMouseUp = () => setIsDragging(false);
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) handleMove(e.clientX);
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (isDragging && e.touches.length > 0) handleMove(e.touches[0].clientX);
    };

    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
      window.addEventListener("touchmove", handleTouchMove);
      window.addEventListener("touchend", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleMouseUp);
    };
  }, [isDragging, handleMove]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
      e.preventDefault();
      setSliderPos((prev) => Math.max(0, prev - 5));
    } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
      e.preventDefault();
      setSliderPos((prev) => Math.min(100, prev + 5));
    } else if (e.key === "Home") {
      e.preventDefault();
      setSliderPos(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setSliderPos(100);
    }
  };

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* Visual Header */}
      <div className="flex items-center justify-between font-mono text-xs text-[var(--ink-2)]">
        <span className="flex items-center gap-1.5 uppercase tracking-wider font-semibold">
          <SlidersHorizontal className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Grad-CAM Visual Explanation</span>
        </span>
        <span className="text-[11px] font-mono">
          {sliderPos}% OVERLAY
        </span>
      </div>

      {/* 4:3 Compare Viewport */}
      <div
        ref={containerRef}
        role="slider"
        tabIndex={0}
        aria-label="Grad-CAM overlay comparison slider"
        aria-valuenow={sliderPos}
        aria-valuemin={0}
        aria-valuemax={100}
        onKeyDown={handleKeyDown}
        className="relative aspect-[4/3] bg-black/10 dark:bg-black/50 border border-[var(--rule)] rounded-[4px] overflow-hidden select-none touch-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-ew-resize"
      >
        {/* Layer 1: Base original image */}
        <div className="absolute inset-0">
          <Image
            src={imageUrl}
            alt={`Specimen photo classified as ${label}`}
            fill
            sizes="(max-width: 768px) 100vw, 50vw"
            className="object-cover"
            priority
            unoptimized
          />
          <div className="absolute top-2.5 left-2.5 font-mono text-[10px] uppercase font-bold tracking-wider bg-black/75 text-white/90 px-1.5 py-0.5 rounded-[1px] z-10 pointer-events-none">
            PHOTO
          </div>
        </div>

        {/* Layer 2: Grad-CAM Overlay with Clip Path */}
        {gradcamUrl && (
          <div
            className="absolute inset-0 transition-none pointer-events-none"
            style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}
          >
            <Image
              src={gradcamUrl}
              alt={`Grad-CAM activation heatmap for ${label}`}
              fill
              sizes="(max-width: 768px) 100vw, 50vw"
              className="object-cover"
              priority
              unoptimized
            />
            <div className="absolute top-2.5 right-2.5 font-mono text-[10px] uppercase font-bold tracking-wider bg-[var(--hivis)] text-[#0E1A16] px-1.5 py-0.5 rounded-[1px] z-10 pointer-events-none">
              GRAD-CAM
            </div>
          </div>
        )}

        {/* Vertical Divider Line with Grab Handle */}
        {gradcamUrl && (
          <div
            className="absolute top-0 bottom-0 w-[2px] bg-[var(--hivis)] shadow-[0_0_8px_rgba(0,0,0,0.5)] z-20 pointer-events-none"
            style={{ left: `${sliderPos}%` }}
          >
            <div
              onMouseDown={handleMouseDown}
              onTouchStart={handleTouchStart}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-[var(--hivis)] border-2 border-[#0E1A16] shadow-md flex items-center justify-center pointer-events-auto cursor-ew-resize hover:scale-110 active:scale-95 transition-transform"
              aria-hidden="true"
            >
              <div className="w-1.5 h-1.5 bg-[#0E1A16] rounded-full" />
            </div>
          </div>
        )}
      </div>

      {/* Explanatory Caption */}
      <p className="font-sans text-xs text-[var(--ink-2)] leading-relaxed">
        Grad-CAM highlights spatial pixel regions that most heavily activated the convolutional layers during classification. Drag slider or use Left / Right arrows to inspect features.
      </p>
    </div>
  );
}
