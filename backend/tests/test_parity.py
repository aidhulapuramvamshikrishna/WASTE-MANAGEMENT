"""Parity test ensuring backend predictions match evaluate.py test_predictions.csv identically."""

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def test_backend_evaluate_parity(client: TestClient):
    """The backend's prediction for 20 fixed test images must match evaluate.py's test_predictions.csv exactly.

    Reads the pre-computed test_predictions.csv produced by evaluate.py, verifying top-1 label,
    stream, and calibrated probabilities match within 1e-4 tolerance without re-executing offline ML code.
    """
    model_name = settings.DEFAULT_MODEL  # mobilenet_v3
    csv_path = Path(settings.REPO_ROOT_DIR) / "ml" / "artifacts" / model_name / "test_predictions.csv"
    if not csv_path.exists():
        pytest.skip(f"Test predictions CSV not found: {csv_path}")

    # Read ground-truth predictions from evaluate.py output
    with open(csv_path, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    if not reader:
        pytest.skip("test_predictions.csv is empty")

    # Select 20 samples spread evenly across the test set
    step = len(reader) // 20
    test_rows = [reader[i * step] for i in range(20)]

    mismatches = []
    base_data_dir = Path(settings.REPO_ROOT_DIR) / "data" / "processed" / "waste12"

    for row in test_rows:
        rel_file = row["file"]
        img_path = base_data_dir / rel_file
        if not img_path.exists():
            continue

        with open(img_path, "rb") as f:
            file_bytes = f.read()

        expected_label = row["pred_class"]
        expected_stream = row["pred_stream"]
        expected_conf = float(row["confidence"])

        resp = client.post(
            "/api/v1/predict",
            params={"model": model_name, "explain": False},
            files={"file": (img_path.name, file_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200, f"Predict failed for {img_path.name}: {resp.text}"
        pred = resp.json()

        # 1. Check label parity
        if pred["label"] != expected_label:
            mismatches.append(
                f"{img_path.name}: label mismatch (backend={pred['label']}, evaluate.py CSV={expected_label})"
            )

        # 2. Check stream parity
        if pred["stream"] != expected_stream:
            mismatches.append(
                f"{img_path.name}: stream mismatch (backend={pred['stream']}, evaluate.py CSV={expected_stream})"
            )

        # 3. Check top-1 confidence parity within 1e-4
        conf_diff = abs(pred["confidence"] - expected_conf)
        if conf_diff > 1e-4:
            mismatches.append(
                f"{img_path.name}: confidence diff {conf_diff:.6f} > 1e-4 "
                f"(backend={pred['confidence']:.6f}, evaluate.py CSV={expected_conf:.6f})"
            )

        # 4. Check top-3 probabilities against corresponding class probabilities in the CSV
        for top_item in pred.get("top3", []):
            top_class = top_item["label"]
            col_name = f"prob_{top_class}"
            if col_name in row:
                csv_prob = float(row[col_name])
                if abs(top_item["confidence"] - csv_prob) > 1e-4:
                    mismatches.append(
                        f"{img_path.name}: top-3 prob mismatch for {top_class} "
                        f"(backend={top_item['confidence']:.6f}, CSV={csv_prob:.6f})"
                    )

    assert not mismatches, f"Parity failures on {len(mismatches)} samples:\n" + "\n".join(mismatches)
