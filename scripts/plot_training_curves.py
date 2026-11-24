"""Plot training curves from history.csv according to DESIGN.md tokens."""

import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def plot_curves(history_csv: Path, output_png: Path, model_name: str = "WasteNet") -> None:
    df = pd.read_csv(history_csv)

    fig, axs = plt.subplots(2, 2, figsize=(12, 8), dpi=200)
    fig.patch.set_facecolor("#FAFAF7")

    colors = {
        "train": "#0E1A16",
        "val": "#107569",
        "f1": "#059669",
        "lr_head": "#D97706",
        "lr_bb": "#4338CA",
        "grid": "#E5E5DF",
        "phase": "#9CA3AF",
    }

    has_phase = "phase" in df.columns
    phase2_start = None
    if has_phase and (df["phase"] == 2).any():
        phase2_start = int(df.loc[df["phase"] == 2, "epoch"].min())

    # 1. Loss
    ax = axs[0, 0]
    ax.set_facecolor("#FFFFFF")
    ax.plot(df["epoch"], df["train_loss"], label="Train Loss", color=colors["train"], linewidth=2)
    ax.plot(df["epoch"], df["val_loss"], label="Val Loss", color=colors["val"], linewidth=2, linestyle="--")
    if phase2_start:
        ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2 (Unfreeze)")
    ax.set_title(f"{model_name} — Cross Entropy Loss", fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel("Epoch", fontsize=9)
    ax.set_ylabel("Loss", fontsize=9)
    ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
    ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

    # 2. Accuracy
    ax = axs[0, 1]
    ax.set_facecolor("#FFFFFF")
    ax.plot(df["epoch"], df["train_acc"] * 100, label="Train Acc", color=colors["train"], linewidth=2)
    ax.plot(df["epoch"], df["val_acc"] * 100, label="Val Acc", color=colors["val"], linewidth=2, linestyle="--")
    if phase2_start:
        ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2")
    ax.set_title(f"{model_name} — Accuracy (%)", fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel("Epoch", fontsize=9)
    ax.set_ylabel("Accuracy (%)", fontsize=9)
    ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
    ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

    # 3. Macro-F1
    ax = axs[1, 0]
    ax.set_facecolor("#FFFFFF")
    ax.plot(df["epoch"], df["val_macro_f1"], label="Val Macro-F1", color=colors["f1"], linewidth=2)
    best_f1_idx = df["val_macro_f1"].idxmax()
    best_epoch = int(df.loc[best_f1_idx, "epoch"])
    best_f1 = df.loc[best_f1_idx, "val_macro_f1"]
    ax.scatter([best_epoch], [best_f1], color="#DC2626", s=60, zorder=5, label=f"Best: {best_f1:.4f} (ep {best_epoch})")
    if phase2_start:
        ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2")
    ax.set_title(f"{model_name} — Validation Macro-F1", fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel("Epoch", fontsize=9)
    ax.set_ylabel("Macro-F1", fontsize=9)
    ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
    ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

    # 4. Learning Rate
    ax = axs[1, 1]
    ax.set_facecolor("#FFFFFF")
    if "lr_head" in df.columns and "lr_backbone" in df.columns:
        ax.plot(df["epoch"], df["lr_head"], label="LR Head", color=colors["lr_head"], linewidth=2)
        ax.plot(df["epoch"], df["lr_backbone"], label="LR Backbone", color=colors["lr_bb"], linewidth=2, linestyle="--")
    elif "lr" in df.columns:
        ax.plot(df["epoch"], df["lr"], label="Learning Rate", color=colors["lr_head"], linewidth=2)

    if phase2_start:
        ax.axvline(x=phase2_start - 0.5, color=colors["phase"], linestyle=":", linewidth=1.5, label="Phase 2")
    ax.set_title(f"{model_name} — Learning Rate Schedule", fontsize=11, fontweight="bold", pad=8)
    ax.set_xlabel("Epoch", fontsize=9)
    ax.set_ylabel("Learning Rate", fontsize=9)
    ax.set_yscale("log")
    ax.grid(True, color=colors["grid"], linestyle=":", linewidth=0.8)
    ax.legend(frameon=True, facecolor="#FAFAF7", edgecolor=colors["grid"])

    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, bbox_inches="tight")
    plt.close()
    print(f"Saved curves figure to: {output_png}")


def plot_comparison_curves(output_png: Path) -> None:
    """Plot comparison of all 3 architectures on Val Macro-F1 and Accuracy."""
    artifacts = {
        "WasteNet (from scratch)": Path("ml/artifacts/wastenet/history.csv"),
        "MobileNetV3 (transfer)": Path("ml/artifacts/mobilenet_v3/history.csv"),
        "EfficientNet-B0 (transfer)": Path("ml/artifacts/efficientnet_b0/history.csv"),
    }

    colors = {
        "WasteNet (from scratch)": "#6B7280",      # Neutral Gray
        "MobileNetV3 (transfer)": "#107569",       # Deep Teal
        "EfficientNet-B0 (transfer)": "#2563EB",   # Blue
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=200)
    fig.patch.set_facecolor("#FAFAF7")

    for name, path in artifacts.items():
        if not path.is_file():
            continue
        df = pd.read_csv(path)
        ax1.plot(df["epoch"], df["val_macro_f1"], label=name, color=colors[name], linewidth=2.2)
        ax2.plot(df["epoch"], df["val_acc"] * 100, label=name, color=colors[name], linewidth=2.2)

        # Mark best
        best_f1_idx = df["val_macro_f1"].idxmax()
        ax1.scatter([df.loc[best_f1_idx, "epoch"]], [df.loc[best_f1_idx, "val_macro_f1"]],
                    color=colors[name], s=50, zorder=5)

    ax1.set_facecolor("#FFFFFF")
    ax1.set_title("Architecture Comparison — Validation Macro-F1", fontsize=11, fontweight="bold", pad=8)
    ax1.set_xlabel("Epoch", fontsize=9)
    ax1.set_ylabel("Validation Macro-F1", fontsize=9)
    ax1.grid(True, color="#E5E5DF", linestyle=":", linewidth=0.8)
    ax1.legend(frameon=True, facecolor="#FAFAF7", edgecolor="#E5E5DF")

    ax2.set_facecolor("#FFFFFF")
    ax2.set_title("Architecture Comparison — Validation Accuracy (%)", fontsize=11, fontweight="bold", pad=8)
    ax2.set_xlabel("Epoch", fontsize=9)
    ax2.set_ylabel("Validation Accuracy (%)", fontsize=9)
    ax2.grid(True, color="#E5E5DF", linestyle=":", linewidth=0.8)
    ax2.legend(frameon=True, facecolor="#FAFAF7", edgecolor="#E5E5DF")

    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, bbox_inches="tight")
    plt.close()
    print(f"Saved comparison curves figure to: {output_png}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot model training curves from history.csv")
    parser.add_argument("--history", type=Path, default=Path("ml/artifacts/wastenet/history.csv"))
    parser.add_argument("--output", type=Path, default=Path("ml/reports/figures/wastenet_curves.png"))
    parser.add_argument("--model", type=str, default="WasteNet")
    parser.add_argument("--all", action="store_true", help="Plot all individual models and comparison figure")
    args = parser.parse_args()

    if args.all:
        models = [
            ("WasteNet", Path("ml/artifacts/wastenet/history.csv"), Path("ml/reports/figures/wastenet_curves.png")),
            ("MobileNetV3", Path("ml/artifacts/mobilenet_v3/history.csv"), Path("ml/reports/figures/mobilenet_v3_curves.png")),
            ("EfficientNet-B0", Path("ml/artifacts/efficientnet_b0/history.csv"), Path("ml/reports/figures/efficientnet_b0_curves.png")),
        ]
        for name, hist, out in models:
            if hist.is_file():
                plot_curves(hist, out, name)
        plot_comparison_curves(Path("ml/reports/figures/model_comparison_curves.png"))
    else:
        plot_curves(args.history, args.output, args.model)


if __name__ == "__main__":
    main()
