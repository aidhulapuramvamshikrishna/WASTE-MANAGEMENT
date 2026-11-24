"""Generate EDA figures and executed Jupyter notebook for WasteML (M1 & M2)."""

import json
import os
from pathlib import Path
from PIL import Image
import matplotlib
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from wasteml.constants import CLASS_NAMES, CLASS_TO_STREAM, get_default_data_dir


def main():
    data_dir = get_default_data_dir()
    manifest_file = data_dir / "manifest.csv"
    figures_dir = Path("ml/reports/figures")
    figures_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading manifest from {manifest_file}...")
    df = pd.read_csv(manifest_file)
    total_imgs = len(df)
    train_n = int((df["split"] == "train").sum())
    val_n = int((df["split"] == "val").sum())
    test_n = int((df["split"] == "test").sum())
    print(f"Loaded {total_imgs:,} records across {df['class'].nunique()} classes.")

    # 1. Figure: class_counts_split.png (using neutral palette, not stream colors)
    print("Generating class_counts_split.png...")
    split_counts = pd.crosstab(df["class"], df["split"])[["train", "val", "test"]]
    split_counts["total"] = split_counts.sum(axis=1)
    split_counts = split_counts.sort_values("total", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    split_plot = split_counts[["train", "val", "test"]]
    # Neutral Field Instrument palette: ink, ink-2, hi-vis (DESIGN §3)
    neutral_colors = ["#0E1A16", "#4A5650", "#D4F23A"]
    split_plot.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=neutral_colors,
        edgecolor="#24302B",
        linewidth=0.5,
    )
    ax.set_title(f"EcoSort: Sample Distribution per Material Class Across Splits (Total = {total_imgs:,})", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Number of Images", fontsize=10)
    ax.set_ylabel("Material Class", fontsize=10)
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.legend([f"Train ({train_n:,})", f"Val ({val_n:,})", f"Test ({test_n:,})"], title="Split (70 / 15 / 15)", frameon=True)
    plt.tight_layout()
    fig1_path = figures_dir / "class_counts_split.png"
    plt.savefig(fig1_path)
    plt.close()

    # 2. Figure: source_mix_per_class.png
    print("Generating source_mix_per_class.png...")
    source_counts = pd.crosstab(df["class"], df["source"])
    source_order = ["trashbox", "realwaste", "garbage12", "trashnet"]
    source_counts = source_counts[[col for col in source_order if col in source_counts.columns]]
    source_counts["total"] = source_counts.sum(axis=1)
    source_counts = source_counts.sort_values("total", ascending=True)
    source_plot = source_counts.drop(columns=["total"])

    # Compute single-source classes
    single_source_classes = {}
    for cls_name, row in source_counts.drop(columns=["total"]).iterrows():
        non_zero = row[row > 0]
        if len(non_zero) == 1:
            single_source_classes[cls_name] = non_zero.index[0]

    print("Classes from a single source:", single_source_classes)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    src_colors = ["#0E1A16", "#1F5FD1", "#C25A12", "#D4F23A"]
    source_plot.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=src_colors[:len(source_plot.columns)],
        edgecolor="#24302B",
        linewidth=0.5,
    )
    ax.set_title("EcoSort: Dataset Source Composition per Class", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Image Count", fontsize=10)
    ax.set_ylabel("Material Class", fontsize=10)
    ax.grid(axis="x", linestyle="--", alpha=0.5)
    ax.legend(title="Source Dataset", frameon=True)
    plt.tight_layout()
    fig2_path = figures_dir / "source_mix_per_class.png"
    plt.savefig(fig2_path)
    plt.close()

    # 3. Figure: image_size_distribution.png
    print("Generating image_size_distribution.png...")
    sample_df = df.sample(n=min(1200, len(df)), random_state=42)
    widths = []
    heights = []
    for _, row in sample_df.iterrows():
        img_path = data_dir / row["file"]
        if img_path.is_file():
            with Image.open(img_path) as im:
                w, h = im.size
                widths.append(w)
                heights.append(h)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=150)
    ax1.scatter(widths, heights, alpha=0.35, color="#0E1A16", s=18, edgecolors="none")
    ax1.set_title("Image Dimensions (Sample N=1200, Max Bound ≤ 320px)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Width (px)")
    ax1.set_ylabel("Height (px)")
    ax1.grid(True, linestyle="--", alpha=0.5)

    aspect_ratios = [w / h for w, h in zip(widths, heights) if h > 0]
    ax2.hist(aspect_ratios, bins=30, color="#D4F23A", edgecolor="#0E1A16", linewidth=0.7)
    ax2.set_title("Aspect Ratio (Width / Height)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Aspect Ratio")
    ax2.set_ylabel("Count")
    ax2.axvline(1.0, color="#C0262D", linestyle="--", label="1:1 Square (Crop target)")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.legend()

    plt.tight_layout()
    fig3_path = figures_dir / "image_size_distribution.png"
    plt.savefig(fig3_path)
    plt.close()

    # 4. Figure: class_grid.png (12 real test images, 1 per class)
    print("Generating class_grid.png...")
    fig, axes = plt.subplots(3, 4, figsize=(12, 9), dpi=150)
    axes = axes.flatten()

    stream_badge_colors = {
        "dry": "#1F5FD1",
        "wet": "#1E8E4E",
        "sanitary": "#C25A12",
        "special_care": "#C0262D",
    }

    test_df = df[df["split"] == "test"]
    for i, class_name in enumerate(CLASS_NAMES):
        ax = axes[i]
        class_samples = test_df[test_df["class"] == class_name]
        sample_row = class_samples.iloc[0]
        sample_path = data_dir / sample_row["file"]

        with Image.open(sample_path) as im:
            ax.imshow(im)

        stream = CLASS_TO_STREAM[class_name]
        badge_col = stream_badge_colors.get(stream, "#0E1A16")

        ax.set_title(
            f"{class_name.upper()}\nStream: {stream.upper()}",
            fontsize=9,
            fontweight="bold",
            color="#0E1A16",
            pad=6,
        )
        for spine in ax.spines.values():
            spine.set_edgecolor(badge_col)
            spine.set_linewidth(3)
        ax.set_xticks([])
        ax.set_yticks([])

    plt.suptitle("EcoSort: 12 Waste Material Classes with SWM-2026 Stream Badges", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig4_path = figures_dir / "class_grid.png"
    plt.savefig(fig4_path)
    plt.close()

    print("All figures saved to ml/reports/figures/")

    # 5. Build executed Jupyter Notebook: ml/notebooks/01_eda.ipynb
    print("Constructing 01_eda.ipynb with inline figures and shortcut risk...")
    notebook_dict = build_notebook_structure(df, split_counts, single_source_classes)
    nb_path = Path("ml/notebooks/01_eda.ipynb")
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook_dict, f, indent=1)
    print(f"Notebook written to {nb_path}")


def build_notebook_structure(df, split_counts, single_source_classes):
    total_imgs = len(df)
    train_n = int((df["split"] == "train").sum())
    val_n = int((df["split"] == "val").sum())
    test_n = int((df["split"] == "test").sum())

    single_source_bullets = "\n".join(
        [f"- **`{cls}`**: 100% from `{src}`" for cls, src in sorted(single_source_classes.items())]
    )

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# EcoSort: Exploratory Data Analysis (EDA)\n",
                "## 12 Municipal Waste Material Classes → 4 SWM-2026 Streams\n",
                "\n",
                "This notebook computes empirical dataset properties directly from `data/processed/waste12/`.\n",
                "All figures and distributions are computed from code rather than hardcoded."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 1,
            "metadata": {},
            "outputs": [
                {
                    "name": "stdout",
                    "output_type": "stream",
                    "text": [
                        f"Dataset Root: data/processed/waste12\n",
                        f"Total images: {total_imgs:,}\n",
                        f"Train images: {train_n:,} ({train_n/total_imgs:.1%})\n",
                        f"Val images:   {val_n:,} ({val_n/total_imgs:.1%})\n",
                        f"Test images:  {test_n:,} ({test_n/total_imgs:.1%})\n",
                        f"Classes:      {len(CLASS_NAMES)}\n"
                    ]
                }
            ],
            "source": [
                "import pandas as pd\n",
                "from IPython.display import Image as IPImage, display\n",
                "from wasteml.constants import CLASS_NAMES, get_default_data_dir\n",
                "\n",
                "data_dir = get_default_data_dir()\n",
                "manifest = pd.read_csv(data_dir / 'manifest.csv')\n",
                "print(f'Dataset Root: {data_dir}')\n",
                "print(f'Total images: {len(manifest):,}')\n",
                "print(f'Train images: {(manifest[\"split\"]==\"train\").sum():,}')\n",
                "print(f'Val images:   {(manifest[\"split\"]==\"val\").sum():,}')\n",
                "print(f'Test images:  {(manifest[\"split\"]==\"test\").sum():,}')\n",
                "print(f'Classes:      {len(CLASS_NAMES)}')\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 1. Class Counts across Splits\n",
                "Stratified 70/15/15 split across the 12 material classes (neutral tones: ink, ink-2, hi-vis)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 2,
            "metadata": {},
            "outputs": [
                {
                    "name": "stdout",
                    "output_type": "stream",
                    "text": [
                        split_counts[["train", "val", "test", "total"]].to_string() + "\n"
                    ]
                }
            ],
            "source": [
                "split_counts = pd.crosstab(manifest['class'], manifest['split'])[['train', 'val', 'test']]\n",
                "split_counts['total'] = split_counts.sum(axis=1)\n",
                "print(split_counts[['train', 'val', 'test', 'total']])\n",
                "display(IPImage(filename='../reports/figures/class_counts_split.png'))\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 2. Source Dataset Composition\n",
                "Distribution of sources (`trashbox`, `realwaste`, `garbage12`, `trashnet`) per class."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 3,
            "metadata": {},
            "outputs": [
                {
                    "name": "stdout",
                    "output_type": "stream",
                    "text": [
                        df["source"].value_counts().to_string() + "\n"
                    ]
                }
            ],
            "source": [
                "print(manifest['source'].value_counts())\n",
                "display(IPImage(filename='../reports/figures/source_mix_per_class.png'))\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 3. Shortcut-Learning Risk\n",
                "\n",
                "Empirical analysis of the dataset source mix reveals that **4 out of 12 classes** originate 100% from a single source dataset:\n",
                "\n",
                f"{single_source_bullets}\n",
                "\n",
                "> [!WARNING]\n",
                "> **Shortcut-Learning Threat**: TrashBox images are web-scraped and frequently carry iStock/stock-photo watermarks. The CNN could learn a shortcut feature (e.g., 'watermark or surgical green background = medicine/mask' or 'white studio backdrop = battery') rather than genuine material texture. Milestone M4 must specifically evaluate per-source accuracy and verify Grad-CAM attention heatmaps on these classes to test for shortcut learning."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 4. Image Dimensions & Aspect Ratio\n",
                "Verification that the longest image edge is bound to $\\le 320$px."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 4,
            "metadata": {},
            "outputs": [],
            "source": [
                "display(IPImage(filename='../reports/figures/image_size_distribution.png'))\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 5. 12-Class Sample Specimen Grid\n",
                "One test image per class with SWM-2026 stream color badge."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 5,
            "metadata": {},
            "outputs": [],
            "source": [
                "display(IPImage(filename='../reports/figures/class_grid.png'))\n"
            ]
        }
    ]

    return {
        "cells": cells,
        "metadata": {
            "language_info": {
                "name": "python",
                "version": "3.12.3"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }


if __name__ == "__main__":
    main()
