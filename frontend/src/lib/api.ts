/**
 * Typed API client for EcoSort Backend.
 * Seamlessly routes requests through Next.js rewrite (/api/v1) on the client,
 * or directly to BACKEND_URL on the server.
 */

import type {
  ClassInfoOut,
  FeedbackCreate,
  FeedbackOut,
  HealthReadyOut,
  ModelFullMetricsOut,
  ModelSummaryOut,
  PredictionListItem,
  PredictionOut,
  StatsOut,
} from "./types";

function getBaseUrl(): string {
  if (typeof window !== "undefined") {
    // In browser: use relative URL to leverage Next.js rewrite and avoid CORS
    return "";
  }
  return process.env.BACKEND_URL || "http://127.0.0.1:8000";
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.error?.message) {
        errorDetail = errorJson.error.message;
      } else if (typeof errorJson.detail === "string") {
        errorDetail = errorJson.detail;
      } else if (errorJson.error) {
        errorDetail = String(errorJson.error);
      }
    } catch {
      // Keep default error text
    }
    throw new Error(errorDetail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Check backend liveness probe */
  async getHealthLive(): Promise<{ status: string }> {
    const res = await fetch(`${getBaseUrl()}/api/v1/health/live`, {
      cache: "no-store",
    });
    return handleResponse<{ status: string }>(res);
  },

  /** Check backend readiness probe (checks default model loaded & DB connection) */
  async getHealthReady(): Promise<HealthReadyOut> {
    const res = await fetch(`${getBaseUrl()}/api/v1/health/ready`, {
      cache: "no-store",
    });
    return handleResponse<HealthReadyOut>(res);
  },

  /** Retrieve 12 municipal classes with stream mappings and disposal instructions */
  async getClasses(): Promise<ClassInfoOut[]> {
    const res = await fetch(`${getBaseUrl()}/api/v1/classes`, {
      next: { revalidate: 3600 },
    });
    return handleResponse<ClassInfoOut[]>(res);
  },

  /** Retrieve list of available CNN model architectures */
  async getModels(): Promise<ModelSummaryOut[]> {
    const res = await fetch(`${getBaseUrl()}/api/v1/models`, {
      next: { revalidate: 60 },
    });
    return handleResponse<ModelSummaryOut[]>(res);
  },

  /** Retrieve full evaluation metrics, confusion matrix, calibration, and training history for a model */
  async getModelMetrics(name: string): Promise<ModelFullMetricsOut> {
    const res = await fetch(`${getBaseUrl()}/api/v1/models/${encodeURIComponent(name)}/metrics`, {
      next: { revalidate: 60 },
    });
    return handleResponse<ModelFullMetricsOut>(res);
  },

  /** Submit an image for CNN inference and Grad-CAM explanation */
  async predict(
    file: File | Blob,
    options?: { model?: string; explain?: boolean }
  ): Promise<PredictionOut> {
    const formData = new FormData();
    const filename = file instanceof File ? file.name : "upload.jpg";
    formData.append("file", file, filename);

    const params = new URLSearchParams();
    if (options?.model) params.set("model", options.model);
    if (options?.explain !== undefined) params.set("explain", String(options.explain));

    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${getBaseUrl()}/api/v1/predict${qs}`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<PredictionOut>(res);
  },

  /** Retrieve paginated prediction history */
  async getPredictions(options?: {
    limit?: number;
    cursor?: string;
    stream?: string;
  }): Promise<PredictionListItem[]> {
    const params = new URLSearchParams();
    if (options?.limit) params.set("limit", String(options.limit));
    if (options?.cursor) params.set("cursor", options.cursor);
    if (options?.stream) params.set("stream", options.stream);

    const qs = params.toString() ? `?${params.toString()}` : "";
    const res = await fetch(`${getBaseUrl()}/api/v1/predictions${qs}`, {
      cache: "no-store",
    });
    return handleResponse<PredictionListItem[]>(res);
  },

  /** Retrieve a single prediction by ID */
  async getPrediction(id: string): Promise<PredictionOut> {
    const res = await fetch(`${getBaseUrl()}/api/v1/predictions/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    return handleResponse<PredictionOut>(res);
  },

  /** Submit citizen feedback / correction for a prediction */
  async submitFeedback(id: string, body: FeedbackCreate): Promise<FeedbackOut> {
    const res = await fetch(`${getBaseUrl()}/api/v1/predictions/${encodeURIComponent(id)}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return handleResponse<FeedbackOut>(res);
  },

  /** Retrieve municipal sorting KPIs, daily counts, and confusion breakdowns */
  async getStats(days = 30): Promise<StatsOut> {
    const res = await fetch(`${getBaseUrl()}/api/v1/stats?days=${days}`, {
      next: { revalidate: 30 },
    });
    return handleResponse<StatsOut>(res);
  },

  /** Construct sanitized URL for original prediction image (always relative for browser same-origin request) */
  getImageUrl(id: string): string {
    return `/api/v1/predictions/${encodeURIComponent(id)}/image`;
  },

  /** Construct sanitized URL for Grad-CAM overlay image (always relative for browser same-origin request) */
  getGradcamUrl(id: string): string {
    return `/api/v1/predictions/${encodeURIComponent(id)}/gradcam`;
  },
};
