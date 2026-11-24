#!/usr/bin/env python3
"""Export high-resolution (300 DPI) figures for the project report into ml/reports/figures/report/.

Covers:
1. Training curves for all 3 models (WasteNet, MobileNetV3, EfficientNet-B0) + comparison curve
2. MobileNetV3 confusion matrix (row-normalized with exact percentages and counts)
3. Grad-CAM correct 12-class grid and top-wrong misclassification grid
4. EDA class distribution and source mix charts
5. Application screenshots at 1440px light (Home scanner, Scan result with heatmap, Uncertain scan, Model page)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import matplotlib
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "ml" / "reports" / "figures" / "report"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Training Curves (300 DPI)
# ---------------------------------------------------------------------------
def export_training_curves():
    print("Generating training curves at 300 DPI...")
    models = [
        ("wastenet", "WasteNet (Scratch)", REPO_ROOT / "ml" / "artifacts" / "wastenet" / "history.csv"),
        ("mobilenet_v3", "MobileNetV3-Large (Transfer)", REPO_ROOT / "ml" / "artifacts" / "mobilenet_v3" / "history.csv"),
        ("efficientnet_b0", "EfficientNet-B0 (Transfer)", REPO_ROOT / "ml" / "artifacts" / "efficientnet_b0" / "history.csv"),
    ]

    colors = {
        "train": "#0E1A16",
        "val": "#107569",
        "f1": "#059669",
        "phase": "#9CA3AF",
        "grid": "#E5E5DF",
    }

    dfs = {}
    for key, name, hist_path in models:
        if not hist_path.exists():
            continue
        df = pd.read_csv(hist_path)
        dfs[key] = (name, df)

        fig, axs = plt.subplots(2, 2, figsize=(11, 7.5), dpi=300)
        fig.patch.set_facecolor("#FAFAF7")

        has_phase = "phase" in df.columns
        phase2_start = None
        if has_phase and (df["phase"] == 2).any():
            phase2_start = int(df.loc[df["phase"] == 2, "epoch"].min())

        # Loss
        ax = axs[0, 0]
        ax.set_facecolor("#FFFFFF")
        ax.plot(df["epoch"], df["train_loss"], label="Train Loss", color=colors["train"], linewidth=2)
        ax.plot(df["epoch"], df["val_loss"], label="Val Loss", color=colors["val"], linewidth=2, linestyle="--")
        if phase2_start:
            ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2 (Fine-tune)")
        ax.set_title(f"{name} — Cross Entropy Loss", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Epoch", fontsize=9)
        ax.set_ylabel("Loss", fontsize=9)
        ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
        ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

        # Accuracy
        ax = axs[0, 1]
        ax.set_facecolor("#FFFFFF")
        ax.plot(df["epoch"], df["train_acc"] * 100, label="Train Acc", color=colors["train"], linewidth=2)
        ax.plot(df["epoch"], df["val_acc"] * 100, label="Val Acc", color=colors["val"], linewidth=2, linestyle="--")
        if phase2_start:
            ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2")
        ax.set_title(f"{name} — Accuracy (%)", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Epoch", fontsize=9)
        ax.set_ylabel("Accuracy (%)", fontsize=9)
        ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
        ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

        # Macro-F1
        ax = axs[1, 0]
        ax.set_facecolor("#FFFFFF")
        ax.plot(df["epoch"], df["val_macro_f1"] * 100, label="Val Macro-F1", color=colors["f1"], linewidth=2)
        if phase2_start:
            ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2")
        ax.set_title(f"{name} — Validation Macro-F1 (%)", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Epoch", fontsize=9)
        ax.set_ylabel("Macro-F1 (%)", fontsize=9)
        ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
        ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

        # Learning Rate
        ax = axs[1, 1]
        ax.set_facecolor("#FFFFFF")
        if "lr" in df.columns:
            ax.plot(df["epoch"], df["lr"], label="Learning Rate", color="#D97706", linewidth=2)
        elif "lr_head" in df.columns:
            ax.plot(df["epoch"], df["lr_head"], label="LR Head", color="#D97706", linewidth=2)
            if "lr_backbone" in df.columns:
                ax.plot(df["epoch"], df["lr_backbone"], label="LR Backbone", color="#4338CA", linewidth=1.5, linestyle="--")
        ax.set_title(f"{name} — Learning Rate Schedule", fontsize=11, fontweight="bold", pad=8)
        ax.set_xlabel("Epoch", fontsize=9)
        ax.set_ylabel("Learning Rate", fontsize=9)
        ax.set_yscale("log")
        ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
        ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

        plt.tight_layout()
        out_path = OUTPUT_DIR / f"training_curves_{key}.png"
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  Saved {out_path.name}")

    # Architecture Comparison Figure
    if len(dfs) >= 2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
        fig.patch.set_facecolor("#FAFAF7")
        model_styles = {
            "wastenet": {"color": "#6B7280", "ls": ":", "label": "WasteNet (Scratch)"},
            "mobilenet_v3": {"color": "#0E1A16", "ls": "-", "label": "MobileNetV3-Large"},
            "efficientnet_b0": {"color": "#107569", "ls": "--", "label": "EfficientNet-B0"},
        }
        for k, (name, df) in dfs.items():
            sty = model_styles.get(k, {"color": "#000", "ls": "-", "label": name})
            ax1.plot(df["epoch"], df["val_macro_f1"] * 100, linewidth=2, color=sty["color"], linestyle=sty["ls"], label=sty["label"])
            ax2.plot(df["epoch"], df["val_acc"] * 100, linewidth=2, color=sty["color"], linestyle=sty["ls"], label=sty["label"])

        ax1.set_facecolor("#FFFFFF")
        ax1.set_title("Architecture Comparison — Val Macro-F1 (%)", fontsize=11, fontweight="bold", pad=8)
        ax1.set_xlabel("Epoch", fontsize=9)
        ax1.set_ylabel("Val Macro-F1 (%)", fontsize=9)
        ax1.grid(True, color="#E5E5DF", linestyle=":", linewidth=0.8)
        ax1.legend(frameon=True, facecolor="#FAFAF7", edgecolor="#E5E5DF")

        ax2.set_facecolor("#FFFFFF")
        ax2.set_title("Architecture Comparison — Val Accuracy (%)", fontsize=11, fontweight="bold", pad=8)
        ax2.set_xlabel("Epoch", fontsize=9)
        ax2.set_ylabel("Val Accuracy (%)", fontsize=9)
        ax2.grid(True, color="#E5E5DF", linestyle=":", linewidth=0.8)
        ax2.legend(frameon=True, facecolor="#FAFAF7", edgecolor="#E5E5DF")

        plt.tight_layout()
        out_comp = OUTPUT_DIR / "training_curves_comparison.png"
        plt.savefig(out_comp, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"  Saved {out_comp.name}")


# ---------------------------------------------------------------------------
# 2. Row-Normalized Confusion Matrix (300 DPI)
# ---------------------------------------------------------------------------
def export_confusion_matrix():
    print("Generating MobileNetV3 row-normalized confusion matrix at 300 DPI...")
    cm_path = REPO_ROOT / "ml" / "artifacts" / "mobilenet_v3" / "confusion_matrix.json"
    if not cm_path.exists():
        print("  Warning: confusion_matrix.json not found")
        return

    with open(cm_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    classes = data["classes"]
    cm = np.array(data["matrix"])
    cm_norm = cm.astype("float") / np.maximum(cm.sum(axis=1)[:, np.newaxis], 1)

    fig, ax = plt.subplots(figsize=(10.5, 9), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")

    cax = ax.imshow(cm_norm, interpolation="nearest", cmap=plt.cm.Blues, vmin=0, vmax=1)
    cbar = plt.colorbar(cax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Recall / Row-Normalized Proportion", rotation=-90, va="bottom", fontsize=10, fontweight="bold")

    ax.set_title("MobileNetV3-Large Test Confusion Matrix (Row-Normalized)", fontsize=13, fontweight="bold", pad=14)
    tick_marks = np.arange(len(classes))
    clean_classes = [c.replace("_", " ") for c in classes]
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(clean_classes, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(clean_classes, fontsize=9)

    ax.set_xlabel("Predicted Label", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_ylabel("True Ground Truth Label", fontsize=11, fontweight="bold", labelpad=10)

    # Annotate counts and percentages inside cells
    thresh = 0.5
    for i in range(len(classes)):
        for j in range(len(classes)):
            val_pct = cm_norm[i, j] * 100
            val_count = cm[i, j]
            text_color = "white" if cm_norm[i, j] > thresh else "#0E1A16"
            label = f"{val_count}\n({val_pct:.1f}%)" if val_count > 0 else "0"
            ax.text(
                j,
                i,
                label,
                ha="center",
                va="center",
                color=text_color,
                fontsize=7.5,
                fontweight="medium" if cm_norm[i, j] > thresh else "normal",
            )

    plt.tight_layout()
    out_path = OUTPUT_DIR / "mobilenet_v3_confusion_matrix_row_norm.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved {out_path.name}")


# ---------------------------------------------------------------------------
# 3. Grad-CAM Grids (300 DPI)
# ---------------------------------------------------------------------------
def export_gradcam_grids():
    print("Exporting Grad-CAM grids at 300 DPI...")
    src_correct = REPO_ROOT / "ml" / "reports" / "figures" / "gradcam_12class_correct.png"
    src_wrong = REPO_ROOT / "ml" / "reports" / "figures" / "gradcam_top_wrong.png"

    if src_correct.exists():
        im = Image.open(src_correct)
        out = OUTPUT_DIR / "gradcam_12class_correct.png"
        im.save(out, dpi=(300, 300))
        print(f"  Saved {out.name}")

    if src_wrong.exists():
        im = Image.open(src_wrong)
        out = OUTPUT_DIR / "gradcam_top_wrong.png"
        im.save(out, dpi=(300, 300))
        print(f"  Saved {out.name}")


# ---------------------------------------------------------------------------
# 4. EDA Class Distribution & Source Mix Charts (300 DPI)
# ---------------------------------------------------------------------------
def export_eda_charts():
    print("Generating EDA charts at 300 DPI...")
    manifest_path = REPO_ROOT / "data" / "processed" / "waste12" / "manifest.csv"
    if not manifest_path.exists():
        # Fallback to copying existing figures
        for fname in ["class_counts_split.png", "source_mix_per_class.png"]:
            src = REPO_ROOT / "ml" / "reports" / "figures" / fname
            if src.exists():
                im = Image.open(src)
                out = OUTPUT_DIR / fname
                im.save(out, dpi=(300, 300))
                print(f"  Saved {out.name} (from existing)")
        return

    df = pd.read_csv(manifest_path)
    total_imgs = len(df)

    # 1. Class counts per split
    split_counts = pd.crosstab(df["class"], df["split"])[["train", "val", "test"]]
    split_counts["total"] = split_counts.sum(axis=1)
    split_counts = split_counts.sort_values("total", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    split_plot = split_counts[["train", "val", "test"]]
    neutral_colors = ["#0E1A16", "#4A5650", "#D4F23A"]
    split_plot.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=neutral_colors,
        edgecolor="#24302B",
        linewidth=0.5,
    )
    ax.set_title(f"EcoSort Dataset: Distribution per Material Class Across Splits (N = {total_imgs:,})", fontsize=11, fontweight="bold", pad=12)
    ax.set_xlabel("Number of Images", fontsize=9, fontweight="bold")
    ax.set_ylabel("Material Class", fontsize=9, fontweight="bold")
    clean_yticks = [c.replace("_", " ") for c in split_counts.index]
    ax.set_yticklabels(clean_yticks, fontsize=8.5)
    ax.legend(["Train (70%)", "Val (15%)", "Test (15%)"], frameon=True, loc="lower right", facecolor="#FAFAF7", edgecolor="#D9D8CF")
    ax.grid(axis="x", color="#E5E5DF", linestyle=":", linewidth=0.8)

    plt.tight_layout()
    out_counts = OUTPUT_DIR / "class_counts_split.png"
    plt.savefig(out_counts, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved {out_counts.name}")

    # 2. Source mix per class
    src_counts = pd.crosstab(df["class"], df["source"])
    src_pct = src_counts.div(src_counts.sum(axis=1), axis=0) * 100
    src_pct = src_pct.loc[split_counts.index]

    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    source_palette = ["#107569", "#1F5FD1", "#C25A12", "#D4F23A"]
    src_pct.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=source_palette,
        edgecolor="#24302B",
        linewidth=0.5,
    )
    ax.set_title("EcoSort: Underlying Dataset Source Composition per Class (%)", fontsize=11, fontweight="bold", pad=12)
    ax.set_xlabel("Proportion of Class Images (%)", fontsize=9, fontweight="bold")
    ax.set_ylabel("Material Class", fontsize=9, fontweight="bold")
    ax.set_yticklabels(clean_yticks, fontsize=8.5)
    ax.legend(title="Source Dataset", frameon=True, loc="lower right", facecolor="#FAFAF7", edgecolor="#D9D8CF")
    ax.grid(axis="x", color="#E5E5DF", linestyle=":", linewidth=0.8)

    plt.tight_layout()
    out_src = OUTPUT_DIR / "source_mix_per_class.png"
    plt.savefig(out_src, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved {out_src.name}")


# ---------------------------------------------------------------------------
# 5. Application Screenshots at 1440px Light (300 DPI)
# ---------------------------------------------------------------------------
def export_app_screenshots():
    print("Exporting application screenshots at 1440px light (300 DPI)...")
    screenshots = [
        ("home_1440_light.png", "app_home_scanner_1440_light.png"),
        ("scan_1440_light.png", "app_result_heatmap_1440_light.png"),
        ("scan_uncertain_1440_light.png", "app_result_uncertain_1440_light.png"),
        ("model_1440_light.png", "app_model_benchmarks_1440_light.png"),
    ]

    for src_name, target_name in screenshots:
        src = REPO_ROOT / "frontend" / "tests" / "screenshots" / src_name
        if src.exists():
            im = Image.open(src)
            out = OUTPUT_DIR / target_name
            # Save at 300 DPI resolution metadata
            im.save(out, dpi=(300, 300))
            print(f"  Saved {out.name} ({im.width}x{im.height}px @ 300 DPI)")
        else:
            print(f"  Warning: {src_name} not found")


def main():
    print(f"Exporting report figures to: {OUTPUT_DIR}")
    export_training_curves()
    export_confusion_matrix()
    export_gradcam_grids()
    export_eda_charts()
    export_app_screenshots()
    print("All report figures exported successfully.")


if __name__ == "__main__":
    main()
