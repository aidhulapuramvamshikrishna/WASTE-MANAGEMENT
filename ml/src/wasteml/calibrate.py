"""Post-hoc temperature scaling and uncertainty threshold calibration on validation set.

Implements:
- Temperature scaling parameter T optimized by L-BFGS on validation NLL loss.
- Expected Calibration Error (ECE) before and after calibration using 15 equal-width bins.
- Uncertain threshold search: lowest max-softmax value where kept validation accuracy >= 90% (clamped to [0.40, 0.85]).
- Coverage and accuracy reporting.
- Reliability diagram plotting saved to ml/artifacts/<model>/calibration.png.
- Calibration parameters written to ml/artifacts/<model>/calibration.json.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from wasteml.data import build_dataloaders
from wasteml.models.factory import build_model
from wasteml.utils import get_device


class ModelWithTemperature(nn.Module):
    """Wrapper that scales logits with a learned scalar temperature parameter."""

    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.model(x)
        return self.temperature_scale(logits)

    def temperature_scale(self, logits: torch.Tensor) -> torch.Tensor:
        # Expand temperature to match logits shape
        temperature = self.temperature.unsqueeze(1).expand(logits.size(0), logits.size(1))
        return logits / temperature


def compute_ece(probs: np.ndarray, targets: np.ndarray, n_bins: int = 15) -> tuple[float, list[dict[str, Any]]]:
    """Compute Expected Calibration Error (ECE) across n_bins equal-width confidence intervals."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == targets).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    bin_details = []

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = float(np.mean(in_bin))

        if prop_in_bin > 0:
            accuracy_in_bin = float(np.mean(accuracies[in_bin]))
            avg_confidence_in_bin = float(np.mean(confidences[in_bin]))
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
            bin_details.append({
                "bin_lower": bin_lower,
                "bin_upper": bin_upper,
                "count": int(np.sum(in_bin)),
                "accuracy": accuracy_in_bin,
                "confidence": avg_confidence_in_bin,
            })
        else:
            bin_details.append({
                "bin_lower": bin_lower,
                "bin_upper": bin_upper,
                "count": 0,
                "accuracy": 0.0,
                "confidence": (bin_lower + bin_upper) / 2.0,
            })

    return float(ece), bin_details


def collect_val_logits(
    model: nn.Module,
    val_loader: DataLoader,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Collect raw logits and labels from the validation set."""
    model.eval()
    logits_list = []
    labels_list = []

    with torch.no_grad():
        for images, targets in val_loader:
            images = images.to(device)
            logits = model(images)
            logits_list.append(logits.cpu())
            labels_list.append(targets.cpu())

    return torch.cat(logits_list, dim=0), torch.cat(labels_list, dim=0)


def optimize_temperature(
    logits: torch.Tensor,
    labels: torch.Tensor,
    max_iter: int = 50,
) -> float:
    """Optimize temperature T using L-BFGS on validation negative log-likelihood (NLL)."""
    # Optimize log_temperature for unconstrained positive temperature
    log_temp = nn.Parameter(torch.zeros(1, dtype=torch.float32))
    nll_criterion = nn.CrossEntropyLoss()

    optimizer = torch.optim.LBFGS([log_temp], lr=0.01, max_iter=max_iter)

    def eval_loss() -> torch.Tensor:
        optimizer.zero_grad()
        t = torch.exp(log_temp)
        loss = nll_criterion(logits / t, labels)
        loss.backward()
        return loss

    optimizer.step(eval_loss)
    temperature = float(torch.exp(log_temp).item())
    return max(0.01, temperature)


def find_uncertain_threshold(
    calibrated_probs: np.ndarray,
    labels: np.ndarray,
    target_accuracy: float = 0.90,
    min_threshold: float = 0.40,
    max_threshold: float = 0.85,
) -> tuple[float, float, float]:
    """Find the lowest max-softmax threshold where accuracy of kept predictions >= target_accuracy."""
    max_conf = np.max(calibrated_probs, axis=1)
    preds = np.argmax(calibrated_probs, axis=1)
    correct = (preds == labels)

    best_thresh = max_threshold
    best_acc = 0.0

    # Search from min_threshold to max_threshold in 0.005 steps
    candidate_thresholds = np.linspace(min_threshold, max_threshold, 91)
    found = False

    for thresh in candidate_thresholds:
        kept = max_conf >= thresh
        if np.sum(kept) == 0:
            continue
        acc = float(np.mean(correct[kept]))

        if acc >= target_accuracy and not found:
            best_thresh = float(thresh)
            found = True
            break
        elif acc > best_acc:
            best_acc = acc
            best_thresh = float(thresh)

    # Clamp strictly to [min_threshold, max_threshold]
    clamped_thresh = float(np.clip(best_thresh, min_threshold, max_threshold))
    kept = max_conf >= clamped_thresh
    final_acc = float(np.mean(correct[kept])) if np.sum(kept) > 0 else 0.0
    final_cov = float(np.mean(kept))

    return clamped_thresh, final_acc, final_cov


def plot_reliability_diagram(
    bins_before: list[dict[str, Any]],
    bins_after: list[dict[str, Any]],
    ece_before: float,
    ece_after: float,
    temperature: float,
    model_name: str,
    output_png: Path,
) -> None:
    """Plot reliability diagram comparing before and after calibration."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=200)
    fig.patch.set_facecolor("#FAFAF7")

    for ax, bins, ece, title in [
        (ax1, bins_before, ece_before, f"{model_name} — Uncalibrated (ECE: {ece_before:.2%})"),
        (ax2, bins_after, ece_after, f"{model_name} — Calibrated (T = {temperature:.3f}, ECE: {ece_after:.2%})"),
    ]:
        ax.set_facecolor("#FFFFFF")

        # Perfect calibration diagonal
        ax.plot([0, 1], [0, 1], linestyle="--", color="#9CA3AF", linewidth=1.5, label="Perfect calibration")

        # Bars
        bin_width = 1.0 / len(bins)
        bar_centers = [(b["bin_lower"] + b["bin_upper"]) / 2 for b in bins]
        bin_accs = [b["accuracy"] for b in bins]

        ax.bar(bar_centers, bin_accs, width=bin_width * 0.85, color="#107569", alpha=0.7, edgecolor="#0E1A16", label="Outputs")

        # Gap bars
        for b in bins:
            if b["count"] > 0:
                mid = (b["bin_lower"] + b["bin_upper"]) / 2
                ax.plot([mid, mid], [b["accuracy"], b["confidence"]], color="#DC2626", linewidth=1.8)

        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Confidence", fontsize=9)
        ax.set_ylabel("Accuracy", fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(True, color="#E5E5DF", linestyle=":", linewidth=0.8)
        ax.legend(loc="upper left", frameon=True, facecolor="#FAFAF7", edgecolor="#E5E5DF")

    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, bbox_inches="tight")
    plt.close()
    print(f"Saved reliability diagram to: {output_png}")


def calibrate_model(
    model_name: str,
    artifacts_dir: Path | None = None,
    device_str: str = "auto",
) -> dict[str, Any]:
    """Run full calibration pipeline on validation set for a given model."""
    device = get_device(device_str)
    if artifacts_dir is None:
        artifacts_dir = Path("artifacts") / model_name
        if not artifacts_dir.is_dir():
            alt_dir = Path("ml/artifacts") / model_name
            if alt_dir.is_dir():
                artifacts_dir = alt_dir

    best_pt = artifacts_dir / "best.pt"
    if not best_pt.is_file():
        raise FileNotFoundError(f"Model checkpoint not found: {best_pt}")

    print("\n=======================================================")
    print(f"Calibrating Model: {model_name} on VALIDATION split")
    print(f"Loading weights from: {best_pt}")
    print("=======================================================")

    # 1. Load model with weights_only=True
    model = build_model(model_name, num_classes=12, pretrained=False)
    state_dict = torch.load(best_pt, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    # 2. Build validation loader (num_workers=0 avoids macOS shared memory IPC restrictions)
    _, val_loader, _, _ = build_dataloaders(batch_size=64, num_workers=0, use_sampler=False)

    # 3. Collect validation logits and true targets
    print(f"Collecting validation logits across {len(val_loader.dataset)} images...")
    logits, labels = collect_val_logits(model, val_loader, device)

    # 4. Compute uncalibrated probabilities and ECE
    uncalibrated_probs = torch.softmax(logits, dim=1).numpy()
    labels_np = labels.numpy()
    ece_before, bins_before = compute_ece(uncalibrated_probs, labels_np, n_bins=15)
    raw_val_acc = float((uncalibrated_probs.argmax(axis=1) == labels_np).mean())
    print(f"Uncalibrated Val Accuracy: {raw_val_acc:.2%}")
    print(f"Uncalibrated ECE (15 bins): {ece_before:.4f} ({ece_before:.2%})")

    # 5. Optimize temperature T on NLL
    print("Optimizing scalar temperature T via L-BFGS on validation NLL...")
    temperature = optimize_temperature(logits, labels)
    print(f"Optimized Temperature T: {temperature:.4f}")

    # 6. Compute calibrated probabilities and ECE
    calibrated_logits = logits / temperature
    calibrated_probs = torch.softmax(calibrated_logits, dim=1).numpy()
    ece_after, bins_after = compute_ece(calibrated_probs, labels_np, n_bins=15)
    print(f"Calibrated ECE (15 bins):   {ece_after:.4f} ({ece_after:.2%})")
    print(f"ECE Reduction:              {ece_before - ece_after:+.4f} ({(ece_before - ece_after) / ece_before:+.1%})")

    # 7. Find uncertain threshold on validation set
    uncertain_thresh, acc_at_thresh, cov_at_thresh = find_uncertain_threshold(
        calibrated_probs=calibrated_probs,
        labels=labels_np,
        target_accuracy=0.90,
        min_threshold=0.40,
        max_threshold=0.85,
    )
    print(f"Uncertain Threshold (clamped to [0.40, 0.85]): {uncertain_thresh:.4f}")
    print(f"Validation Coverage at Threshold:              {cov_at_thresh:.2%}")
    print(f"Validation Accuracy on Kept Predictions:       {acc_at_thresh:.2%}")

    # 8. Save reliability diagram
    diag_png = artifacts_dir / "calibration.png"
    plot_reliability_diagram(
        bins_before=bins_before,
        bins_after=bins_after,
        ece_before=ece_before,
        ece_after=ece_after,
        temperature=temperature,
        model_name=model_name,
        output_png=diag_png,
    )

    # 9. Save calibration.json
    calib_data = {
        "model_name": model_name,
        "temperature": round(temperature, 4),
        "uncertain_threshold": round(uncertain_thresh, 4),
        "ece_before": round(ece_before, 4),
        "ece_after": round(ece_after, 4),
        "coverage_at_threshold": round(cov_at_thresh, 4),
        "val_acc_at_threshold": round(acc_at_thresh, 4),
        "val_total_samples": len(labels_np),
        "n_bins": 15,
    }

    calib_json = artifacts_dir / "calibration.json"
    with open(calib_json, "w") as f:
        json.dump(calib_data, f, indent=2)
    print(f"Saved calibration data to: {calib_json}")

    return calib_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate model on validation set.")
    parser.add_argument("--model", type=str, default="all", help="Model name ('wastenet', 'mobilenet_v3', 'efficientnet_b0', or 'all')")
    parser.add_argument("--artifacts-dir", type=str, default=None, help="Directory containing model artifacts")
    parser.add_argument("--device", type=str, default="auto", help="Compute device (auto, cuda, mps, cpu)")
    args = parser.parse_args()

    models = ["wastenet", "mobilenet_v3", "efficientnet_b0"] if args.model == "all" else [args.model]

    for m in models:
        art_dir = Path(args.artifacts_dir) if args.artifacts_dir else None
        calibrate_model(model_name=m, artifacts_dir=art_dir, device_str=args.device)


if __name__ == "__main__":
    main()
