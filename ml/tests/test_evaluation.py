"""Tests for M4 evaluation, calibration, Grad-CAM, and model card artifacts."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from wasteml.constants import CLASS_NAMES, NUM_CLASSES
from wasteml.gradcam import GradCAM, overlay_cam_on_image
from wasteml.models.factory import SUPPORTED_MODELS, build_model, gradcam_target_layer


def get_artifact_dir(model_name: str) -> Path:
    p1 = Path("ml/artifacts") / model_name
    if p1.is_dir():
        return p1
    p2 = Path("artifacts") / model_name
    if p2.is_dir():
        return p2
    return p1


@pytest.mark.parametrize("model_name", SUPPORTED_MODELS)
def test_gradcam_output_shape_and_range(model_name: str):
    """Grad-CAM map must match input spatial dimensions and lie strictly in [0, 1]."""
    model = build_model(model_name, num_classes=NUM_CLASSES, pretrained=False)
    layer = gradcam_target_layer(model, model_name)
    cam_engine = GradCAM(model, layer)

    h, w = 224, 224
    dummy_input = torch.randn(1, 3, h, w)
    cam = cam_engine.generate(dummy_input, target_class=0)
    cam_engine.remove_hooks()

    assert isinstance(cam, np.ndarray), f"Expected np.ndarray, got {type(cam)}"
    assert cam.shape == (h, w), f"Expected shape ({h}, {w}), got {cam.shape}"
    assert not np.isnan(cam).any(), "Grad-CAM map contains NaNs"
    assert not np.isinf(cam).any(), "Grad-CAM map contains Infs"
    assert cam.min() >= 0.0, f"Grad-CAM min is negative: {cam.min()}"
    assert cam.max() <= 1.0, f"Grad-CAM max exceeds 1.0: {cam.max()}"

    # Test overlay blending
    dummy_img = np.zeros((h, w, 3), dtype=np.uint8)
    overlay = overlay_cam_on_image(dummy_img, cam, colormap="jet", alpha=0.45)
    assert overlay.shape == (h, w, 3)
    assert overlay.dtype == np.uint8


@pytest.mark.parametrize("model_name", SUPPORTED_MODELS)
def test_calibration_artifact_bounds(model_name: str):
    """Calibration artifact must exist, have T > 0, and threshold within [0.40, 0.85]."""
    artifact_path = get_artifact_dir(model_name) / "calibration.json"
    if not artifact_path.exists():
        pytest.skip(f"Artifact {artifact_path} does not exist yet.")

    with open(artifact_path) as f:
        calib = json.load(f)

    temp = calib.get("temperature")
    thresh = calib.get("uncertain_threshold")

    assert temp is not None and temp > 0.0, f"Invalid temperature: {temp}"
    assert thresh is not None, "Missing uncertain_threshold in calibration.json"
    assert 0.40 <= thresh <= 0.85, f"Uncertain threshold {thresh} out of bounds [0.40, 0.85]"


@pytest.mark.parametrize("model_name", SUPPORTED_MODELS)
def test_metrics_json_schema_and_values(model_name: str):
    """Metrics artifact must exist, follow schema, and have valid values."""
    metrics_path = get_artifact_dir(model_name) / "metrics.json"
    if not metrics_path.exists():
        pytest.skip(f"Metrics artifact {metrics_path} does not exist yet.")

    with open(metrics_path) as f:
        m = json.load(f)

    required_keys = [
        "model_name",
        "n_test",
        "accuracy",
        "macro_f1",
        "weighted_f1",
        "top3_accuracy",
        "bootstrap_ci_95",
        "stream_accuracy",
        "hazard_miss_rate",
        "hazard_miss_count",
        "hazard_total",
        "cpu_latency_ms_p50",
        "cpu_latency_ms_p95",
        "params",
        "size_mb",
        "per_class",
        "per_source_accuracy",
    ]
    for k in required_keys:
        assert k in m, f"Missing key '{k}' in {metrics_path}"

    assert m["n_test"] == 2843, f"Expected 2843 test samples, got {m['n_test']}"
    assert 0.0 <= m["accuracy"] <= 1.0
    assert 0.0 <= m["macro_f1"] <= 1.0
    assert 0.0 <= m["stream_accuracy"] <= 1.0
    assert 0.0 <= m["hazard_miss_rate"] <= 1.0
    assert m["cpu_latency_ms_p50"] > 0.0
    assert m["params"] > 0

    ci = m["bootstrap_ci_95"]
    assert "accuracy" in ci and "macro_f1" in ci
    assert ci["accuracy"]["low"] <= ci["accuracy"]["high"]
    assert ci["macro_f1"]["low"] <= ci["macro_f1"]["high"]

    assert len(m["per_class"]) == NUM_CLASSES
    for c_name in CLASS_NAMES:
        assert c_name in m["per_class"]
        cls_m = m["per_class"][c_name]
        for field in ["precision", "recall", "f1", "support"]:
            assert field in cls_m


@pytest.mark.parametrize("model_name", SUPPORTED_MODELS)
def test_model_card_schema_and_class_names(model_name: str):
    """Model card must exist, have class_names == CLASS_NAMES, and match ARCHITECTURE §4.6."""
    card_path = get_artifact_dir(model_name) / "model_card.json"
    if not card_path.exists():
        pytest.skip(f"Model card {card_path} does not exist yet.")

    with open(card_path) as f:
        card = json.load(f)

    required_fields = [
        "name",
        "display_name",
        "arch",
        "num_classes",
        "class_names",
        "img_size",
        "mean",
        "std",
        "gradcam_layer",
        "weights_file",
        "trained_from_scratch",
        "created_at",
        "temperature",
        "uncertain_threshold",
        "test_accuracy",
        "test_macro_f1",
    ]
    for field in required_fields:
        assert field in card, f"Missing field '{field}' in {card_path}"

    assert card["class_names"] == CLASS_NAMES, "Class names in model card do not match CLASS_NAMES"
    assert card["num_classes"] == NUM_CLASSES
    assert card["img_size"] == 224
    assert card["weights_file"] == "best.pt"
