"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Top3Item(BaseModel):
    label: str
    confidence: float


class PredictionOut(BaseModel):
    id: str
    created_at: datetime
    model: str
    label: str
    stream: str
    confidence: float
    uncertain: bool
    uncertain_threshold: float = 0.585
    top3: list[Top3Item]
    disposal: str
    image_url: str
    gradcam_url: str | None = None
    latency_ms: float


class PredictionListItem(BaseModel):
    id: str
    created_at: datetime
    model: str
    label: str
    stream: str
    confidence: float
    uncertain: bool
    image_url: str
    gradcam_url: str | None = None


class FeedbackCreate(BaseModel):
    correct_class: str
    comment: str | None = Field(default=None, max_length=280)


class FeedbackOut(BaseModel):
    id: str
    prediction_id: str
    created_at: datetime
    correct_class: str
    comment: str | None = None


class ClassInfoOut(BaseModel):
    name: str
    stream: str
    disposal: str


class ModelSummaryOut(BaseModel):
    name: str
    display_name: str
    trained_from_scratch: bool
    is_default: bool
    metrics_summary: dict[str, Any]


class StatsOut(BaseModel):
    total_predictions: int
    scans_per_day: list[dict[str, Any]]
    stream_distribution: dict[str, int]
    class_distribution: dict[str, int]
    total_feedback: int
    correction_rate: float
    top_confusions: list[dict[str, Any]]
