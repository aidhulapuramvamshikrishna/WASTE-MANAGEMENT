"""SQLModel database entities for EcoSort."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


class Prediction(SQLModel, table=True):
    __tablename__ = "predictions"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    model: str = Field(index=True)
    label: str = Field(index=True)
    stream: str = Field(index=True)
    confidence: float
    uncertain: bool = Field(default=False, index=True)
    top3_json: str  # JSON array string: [{"label": "...", "confidence": 0.95}, ...]
    disposal: str
    image_path: str
    gradcam_path: str | None = None
    latency_ms: float


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    prediction_id: str = Field(unique=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    correct_class: str
    comment: str | None = Field(default=None, max_length=280)
