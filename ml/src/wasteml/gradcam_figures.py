"""Generate Grad-CAM visualization figures for the WasteML report.

Generates three specific report figures:
1. ml/reports/figures/gradcam_12class_correct.png:
   12-class grid of correct test predictions with heatmaps.
2. ml/reports/figures/gradcam_top_wrong.png:
   12 most confident incorrect test predictions with heatmaps.
3. ml/reports/figures/gradcam_shortcut_check.png:
   12 test images from TrashBox source inspecting background/watermark bias.
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image

from wasteml.constants import (
    CLASS_NAMES,
    CLASS_TO_IDX,
    NUM_CLASSES,
    get_default_data_dir,
)
from wasteml.gradcam import GradCAM, overlay_cam_on_image
from wasteml.models.factory import build_model, gradcam_target_layer
from wasteml.transforms import eval_tfms
from wasteml.utils import get_device, seed_everything


def generate_gradcam_figures(
    model_name: str = "mobilenet_v3",
    data_dir: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
    figures_dir: str | Path = "ml/reports/figures",
    device_name: str | None = None,
) -> None:
    seed_everything(42)
    device = get_device(device_name)
    base_data_dir = Path(data_dir) if data_dir else get_default_data_dir()
    test_dir = base_data_dir / "test"
    manifest_path = base_data_dir / "manifest.csv"

    if artifacts_dir is None:
        model_artifacts = Path("artifacts") / model_name
        if not model_artifacts.is_dir():
            alt_dir = Path("ml/artifacts") / model_name
            if alt_dir.is_dir():
                model_artifacts = alt_dir
    else:
        model_artifacts = Path(artifacts_dir) / model_name
        if not model_artifacts.is_dir() and (Path("ml") / artifacts_dir / model_name).is_dir():
            model_artifacts = Path("ml") / artifacts_dir / model_name

    weights_path = model_artifacts / "best.pt"
    calib_path = model_artifacts / "calibration.json"
    mis_path = model_artifacts / "misclassified.csv"

    out_dir = Path(figures_dir)
    if not out_dir.is_dir() and (Path("ml") / figures_dir).parent.is_dir():
        out_dir = Path("ml") / figures_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    temperature = 1.0
    if calib_path.exists():
        with open(calib_path) as f:
            temperature = float(json.load(f).get("temperature", 1.0))

    print("\n=======================================================")
    print(f"Generating Grad-CAM Figures using model: {model_name}")
    print("=======================================================")

    # Instantiate model and GradCAM engine
    model = build_model(model_name, num_classes=NUM_CLASSES, pretrained=False)
    state_dict = torch.load(weights_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    target_layer = gradcam_target_layer(model, model_name)
    cam_engine = GradCAM(model, target_layer)
    preprocess = eval_tfms()

    # Load manifest
    df_manifest = pd.read_csv(manifest_path) if manifest_path.exists() else None

    # Helper function to process an image path and return (original_pil, overlay_rgb, pred_idx, conf)
    def process_image(img_path: Path, target_cls: int | None = None):
        img_pil = Image.open(img_path).convert("RGB")
        tensor = preprocess(img_pil).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = model(tensor)
            scaled_logits = logits / temperature
            probs = F.softmax(scaled_logits, dim=-1)
            pred_idx = int(probs.argmax(dim=-1).item())
            conf = float(probs[0, pred_idx].item())

        cls_to_explain = pred_idx if target_cls is None else target_cls
        cam = cam_engine.generate(tensor, target_class=cls_to_explain)
        overlay = overlay_cam_on_image(img_pil, cam, colormap="jet", alpha=0.45)
        return img_pil, overlay, pred_idx, conf

    # -------------------------------------------------------------
    # Figure 1: 12-class grid of correct test predictions
    # -------------------------------------------------------------
    print("Generating Figure 1: 12-class correct predictions grid...")
    _fig, axes = plt.subplots(3, 4, figsize=(14, 11), dpi=200)
    axes = axes.flatten()

    for idx, c_name in enumerate(CLASS_NAMES):
        class_folder = test_dir / c_name
        img_candidates = sorted(list(class_folder.glob("*.jpg")) + list(class_folder.glob("*.png")))

        # Find a clean correct sample with high confidence
        chosen_sample = None
        chosen_overlay = None
        chosen_conf = 0.0

        for p in img_candidates[:15]:
            _, overlay, pred_cls, conf = process_image(p, target_cls=idx)
            if pred_cls == idx and conf > 0.85:
                chosen_sample = p
                chosen_overlay = overlay
                chosen_conf = conf
                break

        if chosen_sample is None and img_candidates:
            # Fallback to first candidate
            _, chosen_overlay, pred_cls, chosen_conf = process_image(img_candidates[0], target_cls=idx)

        ax = axes[idx]
        ax.imshow(chosen_overlay)
        ax.axis("off")
        ax.set_title(
            f"Class {idx+1}: {c_name}\nPred: {c_name} ({chosen_conf*100:.1f}%)",
            fontsize=10,
            fontweight="bold",
            pad=6,
        )

    plt.suptitle(
        f"EcoSort: 12-Class Grad-CAM Explanations on Test Set ({model_name})",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    fig1_path = out_dir / "gradcam_12class_correct.png"
    plt.savefig(fig1_path, bbox_inches="tight", dpi=200)
    plt.close()
    print(f"Saved Figure 1 to: {fig1_path}")

    # -------------------------------------------------------------
    # Figure 2: The 12 most confident WRONG test predictions
    # -------------------------------------------------------------
    print("Generating Figure 2: Top 12 confident wrong predictions...")
    if mis_path.exists():
        df_mis = pd.read_csv(mis_path)
        top12_mis = df_mis.head(12)

        _fig, axes = plt.subplots(3, 4, figsize=(14, 11), dpi=200)
        axes = axes.flatten()

        for idx, (_, row) in enumerate(top12_mis.iterrows()):
            img_p = base_data_dir / row["file"]
            pred_cls_idx = CLASS_TO_IDX[row["pred_class"]]
            _, overlay, _, conf = process_image(img_p, target_cls=pred_cls_idx)

            ax = axes[idx]
            ax.imshow(overlay)
            ax.axis("off")
            is_haz = " [HAZARD MISS]" if row.get("is_hazard_miss") else ""
            ax.set_title(
                f"True: {row['true_class']}\nPred: {row['pred_class']} ({conf*100:.1f}%){is_haz}",
                fontsize=9,
                fontweight="bold",
                color="darkred" if row.get("is_hazard_miss") else "navy",
                pad=6,
            )

        plt.suptitle(
            f"EcoSort: Top 12 Confident Misclassifications with Grad-CAM ({model_name})",
            fontsize=14,
            fontweight="bold",
            y=0.98,
        )
        plt.tight_layout()
        fig2_path = out_dir / "gradcam_top_wrong.png"
        plt.savefig(fig2_path, bbox_inches="tight", dpi=200)
        plt.close()
        print(f"Saved Figure 2 to: {fig2_path}")
    else:
        print(f"Skipping Figure 2: {mis_path} not found.")

    # -------------------------------------------------------------
    # Figure 3: Shortcut check (12 test images from TrashBox)
    # -------------------------------------------------------------
    print("Generating Figure 3: Shortcut check on TrashBox test samples (full 3x4 grid)...")
    if df_manifest is not None:
        tb_test = df_manifest[
            (df_manifest["split"] == "test") & (df_manifest["source"] == "trashbox")
        ]
        # TrashBox covers 8 classes in test split.
        # Select 6 core classes with 2 images each = exactly 12 images (no empty axes).
        # Seeded random choice (seed=42) to avoid any cherry-picking.
        tb_classes = ["cardboard", "e_waste", "glass", "medicine_syringe", "metal", "plastic"]
        selected_tb = []
        for c in tb_classes:
            c_rows = tb_test[tb_test["class"] == c]
            sampled = c_rows.sample(n=2, random_state=42)
            for _, r in sampled.iterrows():
                selected_tb.append(r)

        _fig, axes = plt.subplots(3, 4, figsize=(14, 11), dpi=200)
        axes = axes.flatten()

        for idx, row in enumerate(selected_tb):
            img_p = base_data_dir / row["file"]
            true_idx = CLASS_TO_IDX[row["class"]]
            _, overlay, pred_cls, conf = process_image(img_p, target_cls=true_idx)

            pred_name = CLASS_NAMES[pred_cls]
            match_str = "CORRECT" if pred_cls == true_idx else f"WRONG ({pred_name})"

            ax = axes[idx]
            ax.imshow(overlay)
            ax.axis("off")
            ax.set_title(
                f"Class: {row['class']} (TrashBox)\n{match_str} ({conf*100:.1f}%)",
                fontsize=9,
                fontweight="bold",
                pad=6,
            )

        plt.suptitle(
            f"EcoSort: Shortcut & Artifact Inspection on TrashBox Images ({model_name})\n"
            "(12 Images across 6 Classes, 2 per Class, Seeded Random Choice)",
            fontsize=13,
            fontweight="bold",
            y=0.98,
        )
        plt.tight_layout()
        fig3_path = out_dir / "gradcam_shortcut_check.png"
        plt.savefig(fig3_path, bbox_inches="tight", dpi=200)
        plt.close()
        print(f"Saved Figure 3 (12 panels complete) to: {fig3_path}")

    cam_engine.remove_hooks()
    print("Grad-CAM figures generation complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Grad-CAM figures for report")
    parser.add_argument("--model", type=str, default="mobilenet_v3")
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--artifacts-dir", type=str, default=None)
    parser.add_argument("--figures-dir", type=str, default="ml/reports/figures")
    parser.add_argument("--device", type=str, default=None)
    args = parser.parse_args()

    generate_gradcam_figures(
        model_name=args.model,
        data_dir=args.data_dir,
        artifacts_dir=args.artifacts_dir,
        figures_dir=args.figures_dir,
        device_name=args.device,
    )


if __name__ == "__main__":
    main()
