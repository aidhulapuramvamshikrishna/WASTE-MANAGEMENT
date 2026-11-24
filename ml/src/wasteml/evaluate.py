"""Model evaluation pipeline on TEST split for WasteML.

Computes comprehensive metrics:
- Overall test accuracy, macro-F1, weighted-F1, top-3 accuracy
- 95% bootstrap confidence intervals for accuracy and macro-F1 (1,000 resamples)
- Per-class precision, recall, F1, and support (12 classes)
- 4-stream accuracy and 4x4 stream confusion matrix (SWM-2026)
- Hazard miss rate (share of true sanitary/special_care predicted as wet/dry)
- Per-source accuracy (joined with manifest.csv: trashbox, realwaste, garbage12, trashnet)
- Coverage and accuracy above uncertainty threshold (calibrated)
- Single-image CPU inference latency benchmark (p50 and p95 across 200 runs, 50 warmup)
- Writes metrics.json, confusion_matrix.json/png, misclassified.csv, and model_card.json.
"""

import argparse
import json
import platform
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from wasteml.constants import (
    CLASS_NAMES,
    CLASS_TO_STREAM,
    IMAGENET_MEAN,
    IMAGENET_STD,
    IMG_SIZE,
    NUM_CLASSES,
    STREAMS,
    get_default_data_dir,
)
from wasteml.models.factory import SUPPORTED_MODELS, build_model
from wasteml.transforms import eval_tfms
from wasteml.utils import get_device, seed_everything


def get_git_commit() -> str:
    """Return short git commit hash or 'unknown'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def get_cpu_info() -> str:
    """Return descriptive CPU model string."""
    try:
        if platform.system() == "Darwin":
            res = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=True,
            )
            return res.stdout.strip()
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
    except (subprocess.SubprocessError, OSError, UnicodeDecodeError):
        pass
    return platform.processor() or "CPU"


def measure_cpu_latency(
    model: torch.nn.Module,
    input_shape: tuple[int, int, int, int] = (1, 3, 224, 224),
    warmup_runs: int = 50,
    timed_runs: int = 200,
    num_threads: int = 4,
) -> tuple[float, float]:
    """Measure single-image CPU inference latency (p50 and p95 in milliseconds)."""
    torch.set_num_threads(num_threads)
    cpu_model = model.to("cpu")
    cpu_model.eval()

    dummy_input = torch.randn(*input_shape, device="cpu")

    # Warmup
    with torch.no_grad():
        for _ in range(warmup_runs):
            _ = cpu_model(dummy_input)

    # Timed runs
    latencies: list[float] = []
    with torch.no_grad():
        for _ in range(timed_runs):
            t0 = time.perf_counter()
            _ = cpu_model(dummy_input)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)

    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    return p50, p95


def bootstrap_confidence_intervals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_resamples: int = 1000,
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    """Compute 95% bootstrap confidence intervals for accuracy and macro-F1."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    acc_samples = np.empty(n_resamples, dtype=np.float64)
    f1_samples = np.empty(n_resamples, dtype=np.float64)

    for i in range(n_resamples):
        idx = rng.choice(n, size=n, replace=True)
        yt_sample = y_true[idx]
        yp_sample = y_pred[idx]
        acc_samples[i] = accuracy_score(yt_sample, yp_sample)
        f1_samples[i] = precision_recall_fscore_support(
            yt_sample, yp_sample, average="macro", zero_division=0
        )[2]

    return {
        "accuracy": {
            "low": round(float(np.percentile(acc_samples, 2.5)), 4),
            "high": round(float(np.percentile(acc_samples, 97.5)), 4),
        },
        "macro_f1": {
            "low": round(float(np.percentile(f1_samples, 2.5)), 4),
            "high": round(float(np.percentile(f1_samples, 97.5)), 4),
        },
    }


def plot_and_save_confusion_matrix(
    cm: np.ndarray,
    classes: list[str],
    output_path: Path,
    title: str = "Test Confusion Matrix",
) -> None:
    """Plot and save 12x12 confusion matrix with counts and row normalized percentages."""
    _fig, ax = plt.subplots(figsize=(10, 8), dpi=200)

    # Normalize by row (true class support)
    cm_norm = cm.astype("float") / np.maximum(cm.sum(axis=1)[:, np.newaxis], 1)

    cax = ax.imshow(cm_norm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.colorbar(cax, fraction=0.046, pad=0.04)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    tick_marks = np.arange(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(classes, rotation=45, ha="right", fontsize=9)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(classes, fontsize=9)

    ax.set_xlabel("Predicted Label", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("True Label", fontsize=11, fontweight="bold", labelpad=8)

    # Annotate counts inside cells
    thresh = cm_norm.max() / 2.0
    for i in range(len(classes)):
        for j in range(len(classes)):
            color = "white" if cm_norm[i, j] > thresh else "black"
            ax.text(
                j,
                i,
                f"{cm[i, j]}",
                ha="center",
                va="center",
                color=color,
                fontsize=8,
            )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200)
    plt.close()


def evaluate_model(
    model_name: str,
    data_dir: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
    device_name: str | None = None,
    batch_size: int = 64,
) -> dict:
    """Evaluate a trained model on the TEST split and export all artifacts."""
    seed_everything(42)
    device = get_device(device_name)
    base_data_dir = Path(data_dir) if data_dir else get_default_data_dir()
    test_dir = base_data_dir / "test"
    manifest_path = base_data_dir / "manifest.csv"

    if artifacts_dir is None:
        model_dir = Path("artifacts") / model_name
        if not model_dir.is_dir():
            alt_dir = Path("ml/artifacts") / model_name
            if alt_dir.is_dir():
                model_dir = alt_dir
    else:
        model_dir = Path(artifacts_dir) / model_name
        if not model_dir.is_dir() and (Path("ml") / artifacts_dir / model_name).is_dir():
            model_dir = Path("ml") / artifacts_dir / model_name

    weights_path = model_dir / "best.pt"
    calib_path = model_dir / "calibration.json"

    if not weights_path.exists():
        raise FileNotFoundError(f"Trained checkpoint not found at: {weights_path}")

    # Load calibration parameters
    temperature = 1.0
    uncertain_threshold = 0.5
    if calib_path.exists():
        with open(calib_path) as f:
            calib_data = json.load(f)
            temperature = float(calib_data.get("temperature", 1.0))
            uncertain_threshold = float(calib_data.get("uncertain_threshold", 0.5))
    else:
        print(f"Warning: {calib_path} not found. Using default T={temperature}, threshold={uncertain_threshold}")

    print("\n=======================================================")
    print(f"Evaluating Model on TEST split: {model_name}")
    print(f"Loading weights from: {weights_path}")
    print(f"Using Temperature T={temperature:.4f}, Uncertain Threshold={uncertain_threshold:.4f}")
    print("=======================================================")

    # Build model
    model = build_model(model_name, num_classes=NUM_CLASSES, pretrained=False)
    state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    num_params = sum(p.numel() for p in model.parameters())
    size_mb = round(weights_path.stat().st_size / (1024 * 1024), 2)

    # Load test dataset
    test_dataset = ImageFolder(str(test_dir), transform=eval_tfms())
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,  # 0 for safety in sandbox
    )

    all_logits = []
    all_targets = []
    all_top3_matches = []

    with torch.no_grad():
        for images, targets in test_loader:
            images = images.to(device)
            logits = model(images)
            all_logits.append(logits.cpu())
            all_targets.append(targets)

            # Top-3 computation
            top3_preds = logits.topk(3, dim=-1).indices.cpu()
            matches = top3_preds.eq(targets.unsqueeze(1)).any(dim=-1)
            all_top3_matches.extend(matches.tolist())

    logits_tensor = torch.cat(all_logits, dim=0)
    y_true = torch.cat(all_targets, dim=0).numpy()

    # Temperature scaling
    scaled_logits = logits_tensor / temperature
    probabilities = F.softmax(scaled_logits, dim=-1).numpy()
    y_pred = probabilities.argmax(axis=-1)
    max_confidences = probabilities.max(axis=-1)

    # Core metrics
    n_test = len(y_true)
    acc = round(float(accuracy_score(y_true, y_pred)), 4)
    _prec_macro, _rec_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    _prec_weighted, _rec_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    top3_acc = round(float(sum(all_top3_matches) / len(all_top3_matches)), 4)

    # 95% Bootstrap Confidence Intervals
    bootstrap_ci = bootstrap_confidence_intervals(y_true, y_pred, n_resamples=1000, seed=42)

    # Per-class metrics
    p_class, r_class, f1_class, sup_class = precision_recall_fscore_support(
        y_true, y_pred, average=None, zero_division=0
    )
    per_class_metrics = {}
    for i, c_name in enumerate(CLASS_NAMES):
        per_class_metrics[c_name] = {
            "precision": round(float(p_class[i]), 4),
            "recall": round(float(r_class[i]), 4),
            "f1": round(float(f1_class[i]), 4),
            "support": int(sup_class[i]),
        }

    # Confusion matrix (12x12)
    cm_12x12 = np.zeros((NUM_CLASSES, NUM_CLASSES), dtype=int)
    for yt, yp in zip(y_true, y_pred):
        cm_12x12[yt, yp] += 1

    # Four-stream mapping
    stream_to_idx = {name: i for i, name in enumerate(STREAMS)}
    true_streams = np.array([stream_to_idx[CLASS_TO_STREAM[CLASS_NAMES[yt]]] for yt in y_true])
    pred_streams = np.array([stream_to_idx[CLASS_TO_STREAM[CLASS_NAMES[yp]]] for yp in y_pred])
    stream_acc = round(float(accuracy_score(true_streams, pred_streams)), 4)

    stream_cm = np.zeros((len(STREAMS), len(STREAMS)), dtype=int)
    for st, sp in zip(true_streams, pred_streams):
        stream_cm[st, sp] += 1

    # Hazard miss rate: share of true sanitary / special_care items predicted as wet or dry
    # sanitary=2, special_care=3; wet=0, dry=1
    hazard_indices = {stream_to_idx["sanitary"], stream_to_idx["special_care"]}
    non_hazard_indices = {stream_to_idx["wet"], stream_to_idx["dry"]}

    is_true_hazard = np.isin(true_streams, list(hazard_indices))
    hazard_total = int(np.sum(is_true_hazard))
    hazard_miss_count = int(
        np.sum(is_true_hazard & np.isin(pred_streams, list(non_hazard_indices)))
    )
    hazard_miss_rate = round(float(hazard_miss_count / max(hazard_total, 1)), 4)

    # Per-source accuracy using manifest.csv
    per_source_acc = {}
    manifest_map = {}
    if manifest_path.exists():
        df_manifest = pd.read_csv(manifest_path)
        for _, row in df_manifest.iterrows():
            manifest_map[row["file"]] = row["source"]

    # Map dataset sample relative paths
    sample_sources = []
    sample_rel_paths = []
    for path, _ in test_dataset.samples:
        rel_p = str(Path(path).relative_to(base_data_dir))
        sample_rel_paths.append(rel_p)
        sample_sources.append(manifest_map.get(rel_p, "unknown"))

    sources_arr = np.array(sample_sources)
    unique_sources = sorted(set(sample_sources))
    for src in unique_sources:
        src_mask = sources_arr == src
        src_total = int(np.sum(src_mask))
        src_correct = int(np.sum((y_true == y_pred) & src_mask))
        per_source_acc[src] = {
            "accuracy": round(float(src_correct / max(src_total, 1)), 4),
            "correct": src_correct,
            "total": src_total,
        }

    # Coverage and Accuracy at Uncertainty Threshold
    kept_mask = max_confidences >= uncertain_threshold
    kept_count = int(np.sum(kept_mask))
    coverage_at_thresh = round(float(kept_count / n_test), 4)
    acc_above_thresh = (
        round(float(accuracy_score(y_true[kept_mask], y_pred[kept_mask])), 4)
        if kept_count > 0
        else 0.0
    )

    # Measure CPU latency (benchmarked on CPU with 4 threads)
    print("Measuring single-image CPU latency (batch 1, 50 warmup + 200 timed runs)...")
    cpu_p50, cpu_p95 = measure_cpu_latency(
        model=model,
        input_shape=(1, 3, IMG_SIZE, IMG_SIZE),
        warmup_runs=50,
        timed_runs=200,
        num_threads=4,
    )
    cpu_model_str = get_cpu_info()
    print(f"CPU Latency on {cpu_model_str}: p50={cpu_p50:.2f}ms, p95={cpu_p95:.2f}ms")

    # Assemble metrics dict
    metrics = {
        "model_name": model_name,
        "n_test": n_test,
        "accuracy": acc,
        "macro_f1": round(float(f1_macro), 4),
        "weighted_f1": round(float(f1_weighted), 4),
        "top3_accuracy": top3_acc,
        "bootstrap_ci_95": bootstrap_ci,
        "stream_accuracy": stream_acc,
        "hazard_miss_rate": hazard_miss_rate,
        "hazard_miss_count": hazard_miss_count,
        "hazard_total": hazard_total,
        "uncertain_threshold": uncertain_threshold,
        "temperature": temperature,
        "coverage_at_threshold": coverage_at_thresh,
        "accuracy_above_threshold": acc_above_thresh,
        "cpu_latency_ms_p50": round(cpu_p50, 2),
        "cpu_latency_ms_p95": round(cpu_p95, 2),
        "cpu_benchmark_info": {
            "cpu_model": cpu_model_str,
            "torch_version": torch.__version__,
            "threads": 4,
            "warmup_runs": 50,
            "timed_runs": 200,
        },
        "params": num_params,
        "size_mb": size_mb,
        "per_class": per_class_metrics,
        "per_source_accuracy": per_source_acc,
        "git_commit": get_git_commit(),
        "timestamp": datetime.now(UTC).isoformat(),
        "device": str(device),
    }

    # Save metrics.json
    metrics_path = model_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics to: {metrics_path}")

    # Save confusion_matrix.json
    cm_json_path = model_dir / "confusion_matrix.json"
    with open(cm_json_path, "w") as f:
        json.dump(
            {
                "classes": CLASS_NAMES,
                "matrix": cm_12x12.tolist(),
                "streams": STREAMS,
                "stream_matrix": stream_cm.tolist(),
            },
            f,
            indent=2,
        )
    print(f"Saved confusion matrix JSON to: {cm_json_path}")

    # Save confusion_matrix.png
    cm_png_path = model_dir / "confusion_matrix.png"
    plot_and_save_confusion_matrix(
        cm_12x12,
        CLASS_NAMES,
        cm_png_path,
        title=f"{model_name} Test Confusion Matrix (Acc: {acc*100:.1f}%, F1: {f1_macro:.4f})",
    )
    print(f"Saved confusion matrix PNG to: {cm_png_path}")

    # Save misclassified.csv (sorted descending by confidence)
    misclassified_rows = []
    all_pred_rows = []
    for i in range(n_test):
        yt_name = CLASS_NAMES[y_true[i]]
        yp_name = CLASS_NAMES[y_pred[i]]
        st_name = CLASS_TO_STREAM[yt_name]
        sp_name = CLASS_TO_STREAM[yp_name]
        is_correct = bool(y_true[i] == y_pred[i])
        is_haz_miss = bool((st_name in ["sanitary", "special_care"]) and (sp_name in ["wet", "dry"]))
        row_data = {
            "file": sample_rel_paths[i],
            "source": sample_sources[i],
            "true_class": yt_name,
            "pred_class": yp_name,
            "confidence": round(float(max_confidences[i]), 6),
            "true_stream": st_name,
            "pred_stream": sp_name,
            "is_correct": is_correct,
            "is_hazard_miss": is_haz_miss,
        }
        for c_idx, c_name in enumerate(CLASS_NAMES):
            row_data[f"prob_{c_name}"] = float(probabilities[i, c_idx])
        all_pred_rows.append(row_data)
        if not is_correct:
            misclassified_rows.append(row_data)

    # Save full sample-level test predictions for McNemar tests and auditing
    df_all_preds = pd.DataFrame(all_pred_rows)
    all_preds_path = model_dir / "test_predictions.csv"
    df_all_preds.to_csv(all_preds_path, index=False)
    print(f"Saved full test predictions to: {all_preds_path}")

    misclassified_rows.sort(key=lambda r: r["confidence"], reverse=True)
    mis_df = pd.DataFrame(misclassified_rows)
    mis_csv_path = model_dir / "misclassified.csv"
    mis_df.to_csv(mis_csv_path, index=False)
    print(f"Saved {len(misclassified_rows)} misclassified samples to: {mis_csv_path}")

    # Generate model_card.json (ARCHITECTURE §4.6)
    arch_info = {
        "wastenet": {
            "display_name": "WasteNet (from scratch)",
            "arch": "WasteNet-5B",
            "trained_from_scratch": True,
            "gradcam_layer": "block5.conv2",
        },
        "mobilenet_v3": {
            "display_name": "MobileNetV3-Large",
            "arch": "MobileNetV3-Large (Transfer)",
            "trained_from_scratch": False,
            "gradcam_layer": "features[-1]",
        },
        "efficientnet_b0": {
            "display_name": "EfficientNet-B0",
            "arch": "EfficientNet-B0 (Transfer)",
            "trained_from_scratch": False,
            "gradcam_layer": "features[-1]",
        },
    }[model_name]

    model_card = {
        "name": model_name,
        "display_name": arch_info["display_name"],
        "arch": arch_info["arch"],
        "num_classes": NUM_CLASSES,
        "class_names": CLASS_NAMES,
        "img_size": IMG_SIZE,
        "mean": IMAGENET_MEAN,
        "std": IMAGENET_STD,
        "gradcam_layer": arch_info["gradcam_layer"],
        "weights_file": "best.pt",
        "trained_from_scratch": arch_info["trained_from_scratch"],
        "created_at": datetime.now(UTC).isoformat(),
        "temperature": temperature,
        "uncertain_threshold": uncertain_threshold,
        "test_accuracy": acc,
        "test_macro_f1": round(float(f1_macro), 4),
        "params": num_params,
        "size_mb": size_mb,
        "cpu_latency_ms_p50": round(cpu_p50, 2),
    }

    card_path = model_dir / "model_card.json"
    with open(card_path, "w") as f:
        json.dump(model_card, f, indent=2)
    print(f"Saved model card to: {card_path}")

    print(
        f"\nSUMMARY ({model_name}): Test Acc={acc*100:.2f}%, Macro-F1={f1_macro:.4f}, "
        f"Stream Acc={stream_acc*100:.2f}%, Hazard Miss Rate={hazard_miss_rate*100:.2f}%, "
        f"CPU p50={cpu_p50:.2f}ms"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate WasteML model on TEST split")
    parser.add_argument(
        "--model",
        type=str,
        default="all",
        choices=SUPPORTED_MODELS + ["all"],
        help="Model name to evaluate or 'all'",
    )
    parser.add_argument("--data-dir", type=str, default=None, help="Dataset directory")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Artifacts directory")
    parser.add_argument("--device", type=str, default=None, help="Device (mps/cuda/cpu)")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size for test evaluation")
    args = parser.parse_args()

    models_to_eval = SUPPORTED_MODELS if args.model == "all" else [args.model]
    for m in models_to_eval:
        evaluate_model(
            model_name=m,
            data_dir=args.data_dir,
            artifacts_dir=args.artifacts_dir,
            device_name=args.device,
            batch_size=args.batch_size,
        )


if __name__ == "__main__":
    main()
