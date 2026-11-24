/**
 * TypeScript type definitions mirroring backend schemas (backend/app/api/v1/schemas.py).
 * Pure source of truth for all API payloads and municipal sorting domain models.
 */

export type StreamType = "wet" | "dry" | "sanitary" | "special_care";

export interface Top3Item {
  label: string;
  confidence: number;
}

export interface PredictionOut {
  id: string;
  created_at: string;
  model: string;
  label: string;
  stream: StreamType | string;
  confidence: number;
  uncertain: boolean;
  uncertain_threshold?: number;
  top3: Top3Item[];
  disposal: string;
  image_url: string;
  gradcam_url: string | null;
  latency_ms: number;
}

export interface PredictionListItem {
  id: string;
  created_at: string;
  model: string;
  label: string;
  stream: StreamType | string;
  confidence: number;
  uncertain: boolean;
  image_url: string;
  gradcam_url: string | null;
}

export interface FeedbackCreate {
  correct_class: string;
  comment?: string | null;
}

export interface FeedbackOut {
  id: string;
  prediction_id: string;
  created_at: string;
  correct_class: string;
  comment: string | null;
}

export interface ClassInfoOut {
  name: string;
  stream: StreamType | string;
  disposal: string;
}

export interface ModelSummaryOut {
  name: string;
  display_name: string;
  trained_from_scratch: boolean;
  is_default: boolean;
  metrics_summary: {
    accuracy?: number;
    test_accuracy?: number;
    macro_f1?: number;
    stream_accuracy?: number;
    hazard_miss_rate?: number;
    cpu_latency_ms_p50?: number;
    latency_ms_cpu_p50?: number;
    params?: number;
    size_mb?: number;
    model_size_mb?: number;
    temperature?: number;
    uncertain_threshold?: number;
    [key: string]: unknown;
  };
}

export interface ModelFullMetricsOut {
  name: string;
  model_card?: {
    model_name?: string;
    display_name?: string;
    architecture?: string;
    trained_from_scratch?: boolean;
    num_classes?: number;
    class_names?: string[];
    weights_file?: string;
    uncertain_threshold?: number;
    ui_uncertain_threshold?: number;
    [key: string]: unknown;
  };
  metrics?: {
    model_name?: string;
    n_test?: number;
    accuracy?: number;
    macro_f1?: number;
    weighted_f1?: number;
    top3_accuracy?: number;
    stream_accuracy?: number;
    hazard_miss_rate?: number;
    hazard_miss_count?: number;
    hazard_total?: number;
    uncertain_threshold?: number;
    temperature?: number;
    coverage_at_threshold?: number;
    accuracy_above_threshold?: number;
    params?: number;
    size_mb?: number;
    cpu_latency_ms_p50?: number;
    cpu_latency_ms_p95?: number;
    bootstrap_ci_95?: {
      accuracy?: { low: number; high: number };
      macro_f1?: { low: number; high: number };
    };
    ui_threshold_eval_test?: {
      threshold: number;
      coverage: number;
      accuracy_above_threshold: number;
      note?: string;
    };
    per_class?: Record<
      string,
      { precision: number; recall: number; f1: number; support: number }
    >;
    per_source_accuracy?: Record<
      string,
      { accuracy: number; correct: number; total: number }
    >;
    [key: string]: unknown;
  } | null;
  confusion_matrix?: {
    classes: string[];
    matrix: number[][];
    [key: string]: unknown;
  } | null;
  calibration?: {
    model_name?: string;
    temperature: number;
    uncertain_threshold: number;
    ui_uncertain_threshold?: number;
    ui_threshold_rule?: string;
    ece_before: number;
    ece_after: number;
    coverage_at_threshold?: number;
    val_acc_at_threshold?: number;
    val_total_samples?: number;
    n_bins?: number;
    [key: string]: unknown;
  } | null;
  history?: Array<{
    epoch: number;
    phase?: number;
    train_loss: number;
    train_acc: number;
    val_loss: number;
    val_acc: number;
    val_macro_f1: number;
    lr_backbone?: number;
    lr_head?: number;
    seconds?: number;
    [key: string]: unknown;
  }> | null;
}

export interface StatsOut {
  total_predictions: number;
  scans_per_day: Array<{ date: string; count: number }>;
  stream_distribution: Record<string, number>;
  class_distribution: Record<string, number>;
  total_feedback: number;
  correction_rate: number;
  top_confusions: Array<{
    predicted: string;
    actual: string;
    count: number;
    share?: number;
  }>;
}

export interface HealthReadyOut {
  status: string;
  default_model: string;
  loaded_models: string[];
  db: string;
}
