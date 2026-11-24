"use client";

import * as React from "react";
import { Check, CheckCircle2, MessageSquare, ThumbsDown, ThumbsUp } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const CLASSES_12 = [
  { name: "battery", label: "Battery", stream: "special_care", streamColor: "var(--special)" },
  { name: "cardboard", label: "Cardboard", stream: "dry", streamColor: "var(--dry)" },
  { name: "e_waste", label: "E-Waste", stream: "special_care", streamColor: "var(--special)" },
  { name: "glass", label: "Glass", stream: "dry", streamColor: "var(--dry)" },
  { name: "mask_glove", label: "Mask / Glove", stream: "sanitary", streamColor: "var(--sanitary)" },
  { name: "medicine_syringe", label: "Medicine / Syringe", stream: "special_care", streamColor: "var(--special)" },
  { name: "metal", label: "Metal", stream: "dry", streamColor: "var(--dry)" },
  { name: "misc_trash", label: "Misc Trash", stream: "dry", streamColor: "var(--dry)" },
  { name: "organic", label: "Organic", stream: "wet", streamColor: "var(--wet)" },
  { name: "paper", label: "Paper", stream: "dry", streamColor: "var(--dry)" },
  { name: "plastic", label: "Plastic", stream: "dry", streamColor: "var(--dry)" },
  { name: "textile", label: "Textile", stream: "dry", streamColor: "var(--dry)" },
];

interface FeedbackFlowProps {
  predictionId: string;
  initialLabel: string;
}

export function FeedbackFlow({ predictionId, initialLabel }: FeedbackFlowProps) {
  const [status, setStatus] = React.useState<"idle" | "picking" | "submitting" | "done">("idle");
  const [selectedClass, setSelectedClass] = React.useState<string>(initialLabel);
  const [comment, setComment] = React.useState<string>("");
  const [feedbackMessage, setFeedbackMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const handleConfirmCorrect = async () => {
    setStatus("submitting");
    setError(null);
    try {
      await api.submitFeedback(predictionId, {
        correct_class: initialLabel,
        comment: "User verified as correct",
      });
      setStatus("done");
      setFeedbackMessage("Thank you! Verification recorded to municipal audit log.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      if (msg.includes("409") || msg.toLowerCase().includes("already")) {
        setStatus("done");
        setFeedbackMessage("Feedback has already been submitted for this specimen.");
      } else {
        setStatus("idle");
        setError(msg);
      }
    }
  };

  const handleSubmitCorrection = async () => {
    if (!selectedClass) return;
    setStatus("submitting");
    setError(null);
    try {
      await api.submitFeedback(predictionId, {
        correct_class: selectedClass,
        comment: comment.trim() || undefined,
      });
      setStatus("done");
      setFeedbackMessage(`Correction logged as ${selectedClass.replace("_", " ").toUpperCase()}. Thank you!`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      if (msg.includes("409") || msg.toLowerCase().includes("already")) {
        setStatus("done");
        setFeedbackMessage("Feedback has already been submitted for this specimen.");
      } else {
        setStatus("picking");
        setError(msg);
      }
    }
  };

  if (status === "done") {
    return (
      <div className="p-4 bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] flex items-center gap-3 text-xs font-sans text-[var(--ink)]">
        <CheckCircle2 className="w-5 h-5 text-[var(--wet)] shrink-0" aria-hidden="true" />
        <span className="font-medium">{feedbackMessage}</span>
      </div>
    );
  }

  return (
    <div className="p-6 bg-[var(--surface)] border border-[var(--rule)] rounded-[4px] transition-colors">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-2)] font-semibold mb-1">
            Was this right?
          </div>
          <h2 className="font-sans font-bold text-base text-[var(--ink)]">
            Help verify this scan for municipal sorting accuracy
          </h2>
        </div>

        {status === "idle" && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleConfirmCorrect}
              className="px-4 py-2 bg-[var(--hivis)] text-[#0E1A16] font-mono text-xs font-bold rounded-[2px] flex items-center gap-1.5 hover:brightness-105 active:scale-95 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink)] cursor-pointer"
            >
              <ThumbsUp className="w-3.5 h-3.5" aria-hidden="true" />
              <span>YES, CORRECT</span>
            </button>

            <button
              type="button"
              onClick={() => setStatus("picking")}
              className="px-4 py-2 bg-[var(--surface)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--ink)] font-mono text-xs font-semibold rounded-[2px] flex items-center gap-1.5 active:scale-95 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-pointer"
            >
              <ThumbsDown className="w-3.5 h-3.5" aria-hidden="true" />
              <span>NO, CHANGE MATERIAL</span>
            </button>
          </div>
        )}
      </div>

      {error && (
        <div role="alert" className="p-2.5 bg-red-950/15 border border-red-500/30 text-red-600 dark:text-red-400 font-sans text-xs rounded-[2px] mb-4">
          {error}
        </div>
      )}

      {/* 12-Class Picker Grid when user selects NO */}
      {status === "picking" && (
        <div className="pt-4 border-t border-[var(--rule)] space-y-4">
          <p className="font-sans text-xs text-[var(--ink-2)]">
            Select the true physical material to help train the next model iteration:
          </p>

          <div
            role="radiogroup"
            aria-label="Select true waste material"
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2"
          >
            {CLASSES_12.map((c) => {
              const isSelected = selectedClass === c.name;
              return (
                <button
                  key={c.name}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  onClick={() => setSelectedClass(c.name)}
                  className={cn(
                    "p-2.5 text-left rounded-[2px] border transition-all flex items-center justify-between text-xs font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)] cursor-pointer",
                    isSelected
                      ? "border-[var(--ink)] bg-[var(--paper)] font-bold text-[var(--ink)] ring-1 ring-[var(--ink)]"
                      : "border-[var(--rule)] bg-[var(--surface)] text-[var(--ink-2)] hover:border-[var(--ink-2)]"
                  )}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span
                      className="w-2 h-2 rounded-[1px] shrink-0"
                      style={{ backgroundColor: c.streamColor }}
                      aria-hidden="true"
                    />
                    <span className="truncate">{c.label}</span>
                  </div>
                  {isSelected && <Check className="w-3.5 h-3.5 text-[var(--ink)] shrink-0" />}
                </button>
              );
            })}
          </div>

          {/* Optional Comment Input */}
          <div className="space-y-1.5">
            <label htmlFor="feedback-comment" className="font-mono text-[11px] uppercase tracking-wider text-[var(--ink-2)] block">
              Optional Comment (Max 280 chars)
            </label>
            <div className="relative">
              <input
                id="feedback-comment"
                type="text"
                maxLength={280}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="e.g. Broken screen with Li-ion battery inside"
                className="w-full px-3 py-2 bg-[var(--paper)] border border-[var(--rule)] rounded-[2px] text-xs font-sans text-[var(--ink)] placeholder:text-[var(--ink-2)]/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--hivis)]"
              />
              <MessageSquare className="w-3.5 h-3.5 text-[var(--ink-2)] absolute right-3 top-2.5 pointer-events-none" />
            </div>
          </div>

          {/* Submission Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setStatus("idle")}
              className="px-3 py-1.5 text-xs font-mono text-[var(--ink-2)] hover:text-[var(--ink)] cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmitCorrection}
              disabled={!selectedClass}
              className="px-4 py-2 bg-[var(--hivis)] text-[#0E1A16] font-mono text-xs font-bold rounded-[2px] hover:brightness-105 active:scale-95 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ink)] cursor-pointer"
            >
              SUBMIT CORRECTION
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
