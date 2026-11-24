"""Quantitative shortcut learning and spatial bias evaluation for WasteML.

Evaluates on the full 2,843 test images:
1. Border-60% accuracy: Central 60% per side masked with dataset mean colour (36% area masked, 64% visible).
   Measures robustness to partial views and surrounding context, confounded by object extent into the border.
2. Border-10% accuracy: Central 80% per side masked with dataset mean colour (64% area masked, only a 10% outer frame remains).
   Strict control isolating perimeter/background features.
3. Center-60% accuracy: Outer 20% border on all sides masked with dataset mean colour (only central 36% area visible).
4. Grad-CAM border mass: Average share of activation energy in the outer 15% perimeter (covers 51% of pixels).
   Compared against the 51% uniform baseline (observed / 51%). Ratios < 1.0 show attention is more center-focused on the object.
5. Per-source breakdown: trashbox, garbage12, realwaste, trashnet.

Outputs:
- ml/reports/shortcut_test.json
- ml/reports/shortcut_test.md
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from wasteml.constants import (
    NUM_CLASSES,
    get_default_data_dir,
)
from wasteml.models.factory import SUPPORTED_MODELS, build_model, gradcam_target_layer
from wasteml.transforms import eval_tfms
from wasteml.utils import get_device, seed_everything

UNIFORM_BORDER_15_BASELINE = 0.5100  # 1 - 0.70^2 = 51% of pixels in outer 15% perimeter


def save_reports(all_results: dict, out_dir: Path) -> None:
    """Save both JSON and Markdown summaries from current results dictionary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "shortcut_test.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Updated shortcut test JSON at: {json_path}", flush=True)

    md_path = out_dir / "shortcut_test.md"
    names = {
        "wastenet": "WasteNet (Scratch)",
        "mobilenet_v3": "MobileNetV3-Large (Default)",
        "efficientnet_b0": "EfficientNet-B0",
    }
    with open(md_path, "w") as f:
        f.write("# EcoSort: Quantitative Shortcut & Spatial Bias Analysis\n\n")
        f.write("Evaluates background, border, and artifact reliance across all 2,843 test images.\n\n")
        f.write("- **Random Chance Baseline:** 8.33% (1/12 classes)\n")
        f.write("- **Uniform Baseline for Outer 15% Border:** 51.0% of image area ($1 - 0.70^2 = 0.51$)\n")
        f.write("- **Border-60%:** Central 60% per side masked (36% area hidden, 64% border visible). Measures robustness to partial views + context, confounded by object parts in border.\n")
        f.write("- **Border-10% Control:** Central 80% per side masked (64% area hidden, only 10% perimeter frame remains).\n")
        f.write("- **Center-60%:** Outer 20% border on all sides masked (only central 36% area visible).\n")
        f.write("- **Grad-CAM Border Mass Ratio:** Observed border mass divided by 51.0% uniform baseline. Ratios < 1.0 prove attention is on average **more center-focused** on the object than chance.\n\n")

        f.write("## 1. Overall Model Comparison\n\n")
        f.write("| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for m in SUPPORTED_MODELS:
            if m in all_results:
                ov = all_results[m]["overall"]
                c60 = ov.get("center_60_acc", ov.get("center_only_acc", 0.0))
                b60 = ov.get("border_60_acc", ov.get("border_only_acc", 0.0))
                b10_str = f"{ov['border_10_acc']*100:.2f}%" if "border_10_acc" in ov else "N/A"
                ratio_val = ov.get("gradcam_border_ratio", ov["gradcam_border_mass_mean"] / 0.51)
                f.write(
                    f"| **{names[m]}** | {ov['original_acc']*100:.2f}% | "
                    f"{c60*100:.2f}% | "
                    f"{b60*100:.2f}% | "
                    f"**{b10_str}** | "
                    f"{ov['gradcam_border_mass_mean']*100:.1f}% ± {ov['gradcam_border_mass_std']*100:.1f}% | "
                    f"**{ratio_val:.2f}×** ({'Center-Focused' if ratio_val < 1.0 else 'Border-Biased'}) |\n"
                )

        f.write("\n## 2. Per-Source Breakdown\n\n")
        first_m = next(iter(all_results.keys()), None)
        if first_m:
            sources = list(all_results[first_m]["per_source"].keys())
            source_desc = {
                "garbage12": "web-scraped benchmark (Kaggle)",
                "realwaste": "photographed at a landfill site",
                "trashbox": "web-scraped with stock watermarks",
                "trashnet": "studio photos on white background",
            }
            for s in sources:
                f.write(f"### Source: `{s}` ({source_desc.get(s, '')})\n\n")
                f.write("| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for m in SUPPORTED_MODELS:
                    if m in all_results and s in all_results[m]["per_source"]:
                        s_data = all_results[m]["per_source"][s]
                        s_c60 = s_data.get("center_60_acc", s_data.get("center_only_acc", 0.0))
                        s_b60 = s_data.get("border_60_acc", s_data.get("border_only_acc", 0.0))
                        b10_str = f"{s_data['border_10_acc']*100:.1f}%" if "border_10_acc" in s_data else "N/A"
                        ratio_val = s_data.get("gradcam_border_ratio", s_data["gradcam_border_mass_mean"] / 0.51)
                        f.write(
                            f"| **{names[m]}** | {s_data['original_acc']*100:.1f}% | "
                            f"{s_c60*100:.1f}% | "
                            f"{s_b60*100:.1f}% | "
                            f"**{b10_str}** | "
                            f"{s_data['gradcam_border_mass_mean']*100:.1f}% ± {s_data['gradcam_border_mass_std']*100:.1f}% | "
                            f"**{ratio_val:.2f}×** |\n"
                        )
                f.write("\n")

    print(f"Updated shortcut test Markdown at: {md_path}", flush=True)


def run_shortcut_evaluation(
    model_name: str,
    data_dir: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
    device_name: str | None = None,
    batch_size: int = 64,
) -> dict:
    seed_everything(42)
    torch.set_num_threads(4)
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
    if not weights_path.exists():
        raise FileNotFoundError(f"Missing weights for {model_name} at {weights_path}")

    print("\n=======================================================", flush=True)
    print(f"Running Shortcut & Spatial Bias Test: {model_name}", flush=True)
    print(f"Loading weights from: {weights_path}", flush=True)
    print("=======================================================", flush=True)

    model = build_model(model_name, num_classes=NUM_CLASSES, pretrained=False)
    state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    # Freeze model weights so backward does not compute unnecessary weight gradients
    for p in model.parameters():
        p.requires_grad = False

    # Hook target layer for fast activation-level Grad-CAM
    target_layer = gradcam_target_layer(model, model_name)
    acts_buffer = []

    def fwd_hook(mod, inp, out):
        out.requires_grad_(True)
        out.retain_grad()
        acts_buffer.append(out)

    hook_handle = target_layer.register_forward_hook(fwd_hook)

    # Load test dataset
    test_dataset = ImageFolder(str(test_dir), transform=eval_tfms())
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # Manifest mapping
    manifest_map = {}
    if manifest_path.exists():
        df_manifest = pd.read_csv(manifest_path)
        for _, row in df_manifest.iterrows():
            manifest_map[row["file"]] = row["source"]

    sample_sources = []
    for path, _ in test_dataset.samples:
        rel_p = str(Path(path).relative_to(base_data_dir))
        sample_sources.append(manifest_map.get(rel_p, "unknown"))

    sources_arr = np.array(sample_sources)

    correct_orig = []
    correct_border_60 = []
    correct_border_10 = []
    correct_center_60 = []
    border_mass_fractions = []

    t0 = time.time()
    for batch_idx, (images, targets) in enumerate(test_loader):
        images = images.to(device)
        targets = targets.to(device)
        b = images.shape[0]

        # 1. Forward pass for original predictions + activation hook
        acts_buffer.clear()
        logits_orig = model(images)
        preds_orig = logits_orig.argmax(dim=-1)
        correct_orig.extend((preds_orig == targets).cpu().tolist())

        # 2. Grad-CAM backward on target layer activations only
        act = acts_buffer[0]
        scores = logits_orig[torch.arange(b, device=device), preds_orig]
        model.zero_grad(set_to_none=True)
        scores.sum().backward()
        grad = act.grad

        weights = torch.mean(grad, dim=(2, 3), keepdim=True)
        cam = F.relu(torch.sum(weights * act, dim=1))  # (B, H, W)

        # Outer 1-pixel perimeter of the spatial grid (e.g. 7x7 outer border = 1/7 = 14.3% approx 15%)
        h_dim, w_dim = cam.shape[1], cam.shape[2]
        border_mask = torch.ones((h_dim, w_dim), dtype=torch.bool, device=device)
        border_mask[1:h_dim - 1, 1:w_dim - 1] = False

        tot_energy = cam.sum(dim=(1, 2))
        b_energy = (cam * border_mask).sum(dim=(1, 2))
        fracs = (b_energy / torch.clamp(tot_energy, min=1e-8)).detach().cpu().tolist()
        border_mass_fractions.extend(fracs)

        # 3. Masked evaluation variants
        # Variant A: Border-60% (mask central 60% per side: indices 45:179 -> 36% area hidden, 64% visible)
        images_b60 = images.clone()
        images_b60[:, :, 45:179, 45:179] = 0.0

        # Variant B: Border-10% (mask central 80% per side: indices 22:202 -> 64.5% area hidden, only 10% frame visible)
        images_b10 = images.clone()
        images_b10[:, :, 22:202, 22:202] = 0.0

        # Variant C: Center-60% (mask outer 20% border on all sides -> only central 36% area visible)
        images_c60 = torch.zeros_like(images)
        images_c60[:, :, 45:179, 45:179] = images[:, :, 45:179, 45:179]

        images_cat = torch.cat([images_b60, images_b10, images_c60], dim=0)
        with torch.inference_mode():
            logits_cat = model(images_cat)
            preds_b60 = logits_cat[:b].argmax(dim=-1)
            preds_b10 = logits_cat[b:2 * b].argmax(dim=-1)
            preds_c60 = logits_cat[2 * b:].argmax(dim=-1)
            correct_border_60.extend((preds_b60 == targets).cpu().tolist())
            correct_border_10.extend((preds_b10 == targets).cpu().tolist())
            correct_center_60.extend((preds_c60 == targets).cpu().tolist())

        if (batch_idx + 1) % 10 == 0 or (batch_idx + 1) == len(test_loader):
            print(f"Processed batch {batch_idx+1}/{len(test_loader)} ({len(correct_orig)}/{len(test_dataset)} samples)...", flush=True)

    hook_handle.remove()
    elapsed = time.time() - t0
    print(f"Evaluation finished for {model_name} in {elapsed:.1f}s.", flush=True)

    corr_orig_np = np.array(correct_orig, dtype=bool)
    corr_b60_np = np.array(correct_border_60, dtype=bool)
    corr_b10_np = np.array(correct_border_10, dtype=bool)
    corr_c60_np = np.array(correct_center_60, dtype=bool)
    bm_np = np.array(border_mass_fractions, dtype=np.float64)

    mean_bm = float(np.mean(bm_np))
    std_bm = float(np.std(bm_np))

    # Overall metrics
    n_total = len(corr_orig_np)
    overall_res = {
        "n_samples": n_total,
        "original_acc": round(float(np.mean(corr_orig_np)), 4),
        "center_60_acc": round(float(np.mean(corr_c60_np)), 4),
        "border_60_acc": round(float(np.mean(corr_b60_np)), 4),
        "border_10_acc": round(float(np.mean(corr_b10_np)), 4),
        "gradcam_border_mass_mean": round(mean_bm, 4),
        "gradcam_border_mass_std": round(std_bm, 4),
        "gradcam_border_uniform_baseline": UNIFORM_BORDER_15_BASELINE,
        "gradcam_border_ratio": round(mean_bm / UNIFORM_BORDER_15_BASELINE, 4),
    }

    # Per-source metrics
    per_source_res = {}
    sources = sorted(set(sample_sources))
    for s in sources:
        mask = sources_arr == s
        s_n = int(np.sum(mask))
        s_mean_bm = float(np.mean(bm_np[mask]))
        s_std_bm = float(np.std(bm_np[mask]))
        per_source_res[s] = {
            "n_samples": s_n,
            "original_acc": round(float(np.mean(corr_orig_np[mask])), 4),
            "center_60_acc": round(float(np.mean(corr_c60_np[mask])), 4),
            "border_60_acc": round(float(np.mean(corr_b60_np[mask])), 4),
            "border_10_acc": round(float(np.mean(corr_b10_np[mask])), 4),
            "gradcam_border_mass_mean": round(s_mean_bm, 4),
            "gradcam_border_mass_std": round(s_std_bm, 4),
            "gradcam_border_uniform_baseline": UNIFORM_BORDER_15_BASELINE,
            "gradcam_border_ratio": round(s_mean_bm / UNIFORM_BORDER_15_BASELINE, 4),
        }

    return {
        "model_name": model_name,
        "overall": overall_res,
        "per_source": per_source_res,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate shortcut learning on test set")
    parser.add_argument("--model", type=str, default="all", choices=SUPPORTED_MODELS + ["all"])
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--artifacts-dir", type=str, default=None)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    out_dir = Path("ml/reports")
    json_path = out_dir / "shortcut_test.json"
    all_results = {}
    if json_path.exists():
        try:
            with open(json_path) as f:
                all_results = json.load(f)
        except (json.JSONDecodeError, OSError):
            all_results = {}

    models_to_test = SUPPORTED_MODELS if args.model == "all" else [args.model]

    for m in models_to_test:
        res = run_shortcut_evaluation(
            model_name=m,
            data_dir=args.data_dir,
            artifacts_dir=args.artifacts_dir,
            device_name=args.device,
            batch_size=args.batch_size,
        )
        all_results[m] = res
        save_reports(all_results, out_dir)


if __name__ == "__main__":
    main()
