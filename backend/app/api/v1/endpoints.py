"""API endpoints for EcoSort Backend."""

import csv
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlmodel import Session, col, func, select

from app.api.v1.schemas import (
    ClassInfoOut,
    FeedbackCreate,
    FeedbackOut,
    ModelSummaryOut,
    PredictionListItem,
    PredictionOut,
    StatsOut,
)
from app.config import settings
from app.core.security import limiter, verify_localhost_admin
from app.db.models import Feedback, Prediction
from app.db.session import get_session
from app.services.inference import run_prediction, validate_and_process_upload
from app.services.registry import registry

router = APIRouter()


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------

@router.get("/health/live", tags=["health"])
async def health_live():
    """Liveness probe: always 200 when the server process is alive."""
    return {"status": "ok"}


@router.get("/health/ready", tags=["health"])
async def health_ready(session: Session = Depends(get_session)):
    """Readiness probe: 200 when default model is loaded and DB is reachable (503 otherwise)."""
    # 1. Check Model Registry
    if not registry.is_ready or settings.DEFAULT_MODEL not in registry._cache:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": "Default model not loaded or registry unavailable",
                "default_model": settings.DEFAULT_MODEL,
            },
        )

    # 2. Check Database Connectivity
    try:
        session.exec(select(func.count(Prediction.id))).first()
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": f"Database unreachable: {e}",
            },
        )

    return {
        "status": "ready",
        "default_model": settings.DEFAULT_MODEL,
        "available_models": list(registry.available_models.keys()),
    }


# ---------------------------------------------------------------------------
# Classes & Models
# ---------------------------------------------------------------------------

@router.get("/classes", response_model=list[ClassInfoOut], tags=["metadata"])
async def get_classes():
    """Return all 12 municipal classes with SWM 2026 stream and disposal guidelines."""
    return registry.get_classes()


@router.get("/models", response_model=list[ModelSummaryOut], tags=["models"])
async def get_models():
    """Return discovered models with high-level test metrics."""
    summaries = []
    for name in sorted(registry.available_models.keys()):
        s = registry.get_model_summary(name)
        if s:
            summaries.append(s)
    return summaries


@router.get("/models/{name}/metrics", tags=["models"])
async def get_model_metrics(name: str):
    """Return comprehensive metrics, confusion matrix, calibration, and training history."""
    data = registry.get_full_metrics(name)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{name}' not found. Available: {list(registry.available_models.keys())}",
        )
    return data


# ---------------------------------------------------------------------------
# Prediction & Inference
# ---------------------------------------------------------------------------

@router.post(
    "/predict",
    response_model=PredictionOut,
    tags=["prediction"],
)
@limiter.limit(settings.RATE_LIMIT_PREDICT)
async def predict_waste(
    request: Request,
    model: str = Query(default=settings.DEFAULT_MODEL, description="Model architecture name"),
    explain: bool = Query(default=True, description="Generate Grad-CAM activation heatmap"),
    file: UploadFile = File(..., description="Waste item image (JPEG, PNG, or WebP)"),
    session: Session = Depends(get_session),
):
    """Classify an uploaded image into one of 12 classes and 4 SWM streams with Grad-CAM."""
    # Validate model selection against allowlist
    model_name = model.lower().strip()
    if model_name not in registry.available_models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown model '{model}'. Available: {list(registry.available_models.keys())}",
        )

    if not registry.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model serving is not ready. No model loaded.",
        )

    try:
        loaded_model = registry.load_model(model_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to load model '{model_name}': {e}",
        ) from e

    # Read and stream-validate uploaded file bytes
    try:
        raw_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {e}") from e

    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload.")

    # Validate image format, bomb safety, downscale, and strip EXIF
    try:
        pil_img, clean_jpeg_bytes = validate_and_process_upload(raw_bytes)
    except ValueError as e:
        err_msg = str(e)
        if "Payload too large" in err_msg:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=err_msg) from e
        elif "Unsupported format" in err_msg or "Invalid image file" in err_msg:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=err_msg) from e
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg) from e

    # Run inference + calibration + Grad-CAM
    pred_res = run_prediction(loaded_model, pil_img, explain=explain)

    # Save processed image to disk using uuid filename (SECURITY.md T4)
    pred_id = uuid4().hex
    storage_path = Path(settings.STORAGE_DIR)
    img_rel_path = f"uploads/{pred_id}.jpg"
    img_full_path = storage_path / img_rel_path
    with open(img_full_path, "wb") as f:
        f.write(clean_jpeg_bytes)

    # Save Grad-CAM if generated
    cam_rel_path = None
    if pred_res["gradcam_png_bytes"]:
        cam_rel_path = f"gradcam/{pred_id}.png"
        cam_full_path = storage_path / cam_rel_path
        with open(cam_full_path, "wb") as f:
            f.write(pred_res["gradcam_png_bytes"])

    # Persist in DB
    db_pred = Prediction(
        id=pred_id,
        created_at=datetime.now(UTC),
        model=model_name,
        label=pred_res["label"],
        stream=pred_res["stream"],
        confidence=pred_res["confidence"],
        uncertain=pred_res["uncertain"],
        top3_json=json.dumps(pred_res["top3"]),
        disposal=pred_res["disposal"],
        image_path=img_rel_path,
        gradcam_path=cam_rel_path,
        latency_ms=pred_res["latency_ms"],
    )
    session.add(db_pred)
    session.commit()
    session.refresh(db_pred)

    return PredictionOut(
        id=db_pred.id,
        created_at=db_pred.created_at,
        model=db_pred.model,
        label=db_pred.label,
        stream=db_pred.stream,
        confidence=db_pred.confidence,
        uncertain=db_pred.uncertain,
        uncertain_threshold=pred_res.get("uncertain_threshold", loaded_model.uncertain_threshold),
        top3=pred_res["top3"],
        disposal=db_pred.disposal,
        image_url=f"/api/v1/predictions/{db_pred.id}/image",
        gradcam_url=f"/api/v1/predictions/{db_pred.id}/gradcam" if cam_rel_path else None,
        latency_ms=db_pred.latency_ms,
    )


# ---------------------------------------------------------------------------
# History & Image Serving
# ---------------------------------------------------------------------------

@router.get("/predictions", response_model=list[PredictionListItem], tags=["history"])
async def list_predictions(
    limit: int = Query(default=24, ge=1, le=100),
    cursor: str | None = Query(default=None, description="Prediction ID for pagination"),
    stream: str | None = Query(default=None, description="Filter by stream (wet/dry/sanitary/special_care)"),
    session: Session = Depends(get_session),
):
    """Retrieve history of predictions with cursor-based pagination."""
    stmt = select(Prediction).order_by(col(Prediction.created_at).desc(), col(Prediction.id).desc())

    if stream:
        stmt = stmt.where(Prediction.stream == stream.lower().strip())

    if cursor:
        cursor_pred = session.get(Prediction, cursor)
        if cursor_pred:
            stmt = stmt.where(
                (Prediction.created_at < cursor_pred.created_at)
                | ((Prediction.created_at == cursor_pred.created_at) & (Prediction.id < cursor_pred.id))
            )

    stmt = stmt.limit(limit)
    rows = session.exec(stmt).all()

    out = []
    for r in rows:
        out.append(
            PredictionListItem(
                id=r.id,
                created_at=r.created_at,
                model=r.model,
                label=r.label,
                stream=r.stream,
                confidence=r.confidence,
                uncertain=r.uncertain,
                image_url=f"/api/v1/predictions/{r.id}/image",
                gradcam_url=f"/api/v1/predictions/{r.id}/gradcam" if r.gradcam_path else None,
            )
        )
    return out


@router.get("/predictions/{id}", response_model=PredictionOut, tags=["history"])
async def get_prediction(id: str, session: Session = Depends(get_session)):
    """Fetch details of a specific prediction by UUID."""
    pred = session.get(Prediction, id)
    if not pred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found.")

    top3 = json.loads(pred.top3_json) if pred.top3_json else []
    try:
        model_obj = registry.load_model(pred.model)
        thresh = model_obj.uncertain_threshold
    except Exception:
        thresh = 0.585

    return PredictionOut(
        id=pred.id,
        created_at=pred.created_at,
        model=pred.model,
        label=pred.label,
        stream=pred.stream,
        confidence=pred.confidence,
        uncertain=pred.uncertain,
        uncertain_threshold=thresh,
        top3=top3,
        disposal=pred.disposal,
        image_url=f"/api/v1/predictions/{pred.id}/image",
        gradcam_url=f"/api/v1/predictions/{pred.id}/gradcam" if pred.gradcam_path else None,
        latency_ms=pred.latency_ms,
    )


@router.get("/predictions/{id}/image", tags=["assets"])
async def get_prediction_image(id: str, session: Session = Depends(get_session)):
    """Serve uploaded specimen image bytes by prediction ID (SECURITY.md T4)."""
    pred = session.get(Prediction, id)
    if not pred or not pred.image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")

    full_path = Path(settings.STORAGE_DIR) / pred.image_path
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file missing on disk.")

    return FileResponse(full_path, media_type="image/jpeg")


@router.get("/predictions/{id}/gradcam", tags=["assets"])
async def get_prediction_gradcam(id: str, session: Session = Depends(get_session)):
    """Serve Grad-CAM heatmap overlay bytes by prediction ID."""
    pred = session.get(Prediction, id)
    if not pred or not pred.gradcam_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grad-CAM overlay not found.")

    full_path = Path(settings.STORAGE_DIR) / pred.gradcam_path
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grad-CAM file missing on disk.")

    return FileResponse(full_path, media_type="image/png")


# ---------------------------------------------------------------------------
# Feedback & Stats
# ---------------------------------------------------------------------------

@router.post(
    "/predictions/{id}/feedback",
    response_model=FeedbackOut,
    status_code=status.HTTP_201_CREATED,
    tags=["feedback"],
)
async def submit_feedback(
    id: str,
    body: FeedbackCreate,
    session: Session = Depends(get_session),
):
    """Submit user feedback / correction on a scan. Exactly one feedback per prediction."""
    pred = session.get(Prediction, id)
    if not pred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found.")

    # Check if feedback already submitted (409 Conflict)
    existing = session.exec(select(Feedback).where(Feedback.prediction_id == id)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already submitted for this prediction.",
        )

    # Sanitize comment: strip control characters, limit 280 chars (SECURITY.md T8)
    clean_comment = None
    if body.comment:
        clean_comment = "".join(ch for ch in body.comment[:280] if ch.isprintable())

    fb = Feedback(
        id=uuid4().hex,
        prediction_id=id,
        created_at=datetime.now(UTC),
        correct_class=body.correct_class.strip(),
        comment=clean_comment,
    )
    session.add(fb)
    session.commit()
    session.refresh(fb)

    return FeedbackOut(
        id=fb.id,
        prediction_id=fb.prediction_id,
        created_at=fb.created_at,
        correct_class=fb.correct_class,
        comment=fb.comment,
    )


@router.get("/stats", response_model=StatsOut, tags=["stats"])
async def get_stats(
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """Aggregate municipal sorting KPIs, daily scan counts, and confusion rates."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    preds = session.exec(select(Prediction).where(Prediction.created_at >= cutoff)).all()
    feedbacks = session.exec(select(Feedback).where(Feedback.created_at >= cutoff)).all()

    total_preds = len(preds)
    total_fb = len(feedbacks)

    # Scans per day
    daily_counts: dict[str, int] = {}
    stream_dist: dict[str, int] = {"wet": 0, "dry": 0, "sanitary": 0, "special_care": 0}
    class_dist: dict[str, int] = {}

    pred_map = {p.id: p for p in preds}

    for p in preds:
        d_str = p.created_at.strftime("%Y-%m-%d")
        daily_counts[d_str] = daily_counts.get(d_str, 0) + 1
        stream_dist[p.stream] = stream_dist.get(p.stream, 0) + 1
        class_dist[p.label] = class_dist.get(p.label, 0) + 1

    scans_per_day = [{"date": d, "count": count} for d, count in sorted(daily_counts.items())]

    # Corrections
    corrections_count = 0
    confusion_pairs: dict[tuple[str, str], int] = {}
    for fb in feedbacks:
        p = pred_map.get(fb.prediction_id) or session.get(Prediction, fb.prediction_id)
        if p and p.label != fb.correct_class:
            corrections_count += 1
            pair = (p.label, fb.correct_class)
            confusion_pairs[pair] = confusion_pairs.get(pair, 0) + 1

    correction_rate = round(corrections_count / total_preds, 4) if total_preds > 0 else 0.0

    top_confusions = [
        {"predicted": pair[0], "actual": pair[1], "count": count}
        for pair, count in sorted(confusion_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return StatsOut(
        total_predictions=total_preds,
        scans_per_day=scans_per_day,
        stream_distribution=stream_dist,
        class_distribution=class_dist,
        total_feedback=total_fb,
        correction_rate=correction_rate,
        top_confusions=top_confusions,
    )


# ---------------------------------------------------------------------------
# Admin Endpoints (Localhost Only, SECURITY.md T7)
# ---------------------------------------------------------------------------

@router.get(
    "/admin/feedback.csv",
    tags=["admin"],
    dependencies=[Depends(verify_localhost_admin)],
)
async def export_feedback_csv(session: Session = Depends(get_session)):
    """Export feedback dataset for retraining (localhost-only)."""
    feedbacks = session.exec(select(Feedback).order_by(col(Feedback.created_at).desc())).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "prediction_id", "created_at", "predicted_class", "correct_class", "comment", "image_url"])

    for fb in feedbacks:
        pred = session.get(Prediction, fb.prediction_id)
        pred_label = pred.label if pred else "unknown"
        img_url = f"/api/v1/predictions/{fb.prediction_id}/image" if pred else ""
        writer.writerow([
            fb.id,
            fb.prediction_id,
            fb.created_at.isoformat(),
            pred_label,
            fb.correct_class,
            fb.comment or "",
            img_url,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=feedback_export.csv"},
    )


@router.delete(
    "/admin/predictions/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["admin"],
    dependencies=[Depends(verify_localhost_admin)],
)
async def delete_prediction(id: str, session: Session = Depends(get_session)):
    """Delete a prediction, associated feedback, and images from disk (localhost-only)."""
    pred = session.get(Prediction, id)
    if not pred:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found.")

    storage_path = Path(settings.STORAGE_DIR)
    if pred.image_path:
        f = storage_path / pred.image_path
        if f.exists():
            f.unlink()

    if pred.gradcam_path:
        f = storage_path / pred.gradcam_path
        if f.exists():
            f.unlink()

    # Delete feedback if any
    fb = session.exec(select(Feedback).where(Feedback.prediction_id == id)).first()
    if fb:
        session.delete(fb)

    session.delete(pred)
    session.commit()
    return None
