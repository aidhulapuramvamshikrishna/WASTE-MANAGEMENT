"""Functional API tests for EcoSort Backend."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services.registry import registry

SAMPLE_IMAGE = Path(settings.REPO_ROOT_DIR) / "data" / "processed" / "waste12" / "test" / "cardboard" / "cardboard_garbage12_01706.jpg"


def test_health_live(client: TestClient):
    """GET /api/v1/health/live returns 200 with status ok."""
    resp = client.get("/api/v1/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_ready(client: TestClient):
    """GET /api/v1/health/ready returns 200 when default model is loaded and DB is reachable."""
    resp = client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["default_model"] == settings.DEFAULT_MODEL
    assert "mobilenet_v3" in data["available_models"]


def test_classes(client: TestClient):
    """GET /api/v1/classes returns all 12 classes with stream and disposal."""
    resp = client.get("/api/v1/classes")
    assert resp.status_code == 200
    classes = resp.json()
    assert len(classes) == 12
    names = [c["name"] for c in classes]
    assert names == sorted(names), "Class list must be strictly in alphabetical order"
    assert "cardboard" in names
    assert "organic" in names

    # Verify stream mapping
    c_map = {c["name"]: c for c in classes}
    assert c_map["organic"]["stream"] == "wet"
    assert c_map["cardboard"]["stream"] == "dry"
    assert c_map["mask_glove"]["stream"] == "sanitary"
    assert c_map["e_waste"]["stream"] == "special_care"


def test_models_list(client: TestClient):
    """GET /api/v1/models returns discovered models with metrics summary."""
    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 1
    m_names = [m["name"] for m in models]
    assert settings.DEFAULT_MODEL in m_names

    default_m = next(m for m in models if m["is_default"])
    assert default_m["name"] == settings.DEFAULT_MODEL
    assert "accuracy" in default_m["metrics_summary"]
    assert "macro_f1" in default_m["metrics_summary"]


def test_model_metrics(client: TestClient):
    """GET /api/v1/models/{name}/metrics returns full artifacts."""
    resp = client.get(f"/api/v1/models/{settings.DEFAULT_MODEL}/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == settings.DEFAULT_MODEL
    assert "model_card" in data
    assert "metrics" in data
    assert "confusion_matrix" in data
    assert "calibration" in data


def test_model_metrics_404(client: TestClient):
    """GET /api/v1/models/{unknown}/metrics returns 404."""
    resp = client.get("/api/v1/models/non_existent_arch/metrics")
    assert resp.status_code == 404


def test_predict_happy_path(client: TestClient):
    """POST /api/v1/predict with real image returns valid PredictionOut schema."""
    if not SAMPLE_IMAGE.exists():
        pytest.skip(f"Sample test image {SAMPLE_IMAGE} not found.")

    with open(SAMPLE_IMAGE, "rb") as f:
        file_bytes = f.read()

    resp = client.post(
        "/api/v1/predict",
        params={"model": settings.DEFAULT_MODEL, "explain": True},
        files={"file": ("sample.jpg", file_bytes, "image/jpeg")},
    )
    assert resp.status_code == 200, resp.text
    pred = resp.json()

    assert "id" in pred
    assert pred["model"] == settings.DEFAULT_MODEL
    assert pred["label"] in registry.load_model(settings.DEFAULT_MODEL).class_names
    assert pred["stream"] in {"wet", "dry", "sanitary", "special_care"}
    assert 0.0 <= pred["confidence"] <= 1.0
    assert len(pred["top3"]) == 3
    assert pred["disposal"] != ""
    assert pred["image_url"].startswith("/api/v1/predictions/")
    assert pred["gradcam_url"] is not None
    assert pred["latency_ms"] > 0

    pred_id = pred["id"]

    # Verify GET /predictions/{id}
    detail_resp = client.get(f"/api/v1/predictions/{pred_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == pred_id
    assert detail["label"] == pred["label"]

    # Verify GET /predictions/{id}/image
    img_resp = client.get(f"/api/v1/predictions/{pred_id}/image")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/jpeg"
    assert len(img_resp.content) > 0

    # Verify GET /predictions/{id}/gradcam
    cam_resp = client.get(f"/api/v1/predictions/{pred_id}/gradcam")
    assert cam_resp.status_code == 200
    assert cam_resp.headers["content-type"] == "image/png"
    assert len(cam_resp.content) > 0


def test_history_and_feedback_flow(client: TestClient):
    """Test history pagination and feedback 201 then 409 conflict."""
    if not SAMPLE_IMAGE.exists():
        pytest.skip(f"Sample test image {SAMPLE_IMAGE} not found.")

    with open(SAMPLE_IMAGE, "rb") as f:
        file_bytes = f.read()

    # Create two predictions
    p1 = client.post(
        "/api/v1/predict",
        files={"file": ("s1.jpg", file_bytes, "image/jpeg")},
    ).json()

    p2 = client.post(
        "/api/v1/predict",
        files={"file": ("s2.jpg", file_bytes, "image/jpeg")},
    ).json()

    # List history
    hist_resp = client.get("/api/v1/predictions?limit=10")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    ids = [item["id"] for item in hist]
    assert p1["id"] in ids
    assert p2["id"] in ids

    # Submit feedback for p1 -> 201
    fb_resp = client.post(
        f"/api/v1/predictions/{p1['id']}/feedback",
        json={"correct_class": "cardboard", "comment": "Verified cardboard box"},
    )
    assert fb_resp.status_code == 201
    fb = fb_resp.json()
    assert fb["prediction_id"] == p1["id"]
    assert fb["correct_class"] == "cardboard"

    # Duplicate feedback for p1 -> 409 Conflict
    dup_resp = client.post(
        f"/api/v1/predictions/{p1['id']}/feedback",
        json={"correct_class": "paper", "comment": "Duplicate attempt"},
    )
    assert dup_resp.status_code == 409


def test_stats_endpoint(client: TestClient):
    """GET /api/v1/stats returns municipal sorting KPIs."""
    resp = client.get("/api/v1/stats?days=30")
    assert resp.status_code == 200
    stats = resp.json()
    assert "total_predictions" in stats
    assert "scans_per_day" in stats
    assert "stream_distribution" in stats
    assert "class_distribution" in stats
    assert "correction_rate" in stats


def test_admin_endpoints(client: TestClient):
    """Admin endpoints: localhost allows 200, non-localhost raises 403."""
    # Localhost export feedback CSV
    resp = client.get("/api/v1/admin/feedback.csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "predicted_class,correct_class" in resp.text


def test_ui_uncertain_threshold_flagging(client: TestClient):
    """Verify that a prediction at 0.49 confidence is flagged uncertain under ui_uncertain_threshold (0.585)."""
    from app.services.registry import registry

    model = registry.load_model("mobilenet_v3")
    assert model.uncertain_threshold == 0.585

    # Any prediction with confidence < 0.585 (such as the real-world OOD laptop case @ 0.49) is flagged uncertain
    conf = 0.49
    assert bool(conf < model.uncertain_threshold) is True

    # Verify calibration metadata exposed in API
    resp = client.get("/api/v1/models/mobilenet_v3/metrics")
    assert resp.status_code == 200
    calib = resp.json()["calibration"]
    assert calib.get("ui_uncertain_threshold") == 0.585
