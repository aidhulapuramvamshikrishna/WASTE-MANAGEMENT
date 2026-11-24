"""Generate ml/notebooks/02_results.ipynb using standard json module."""

import json
from pathlib import Path


def make_notebook():
    cells = []

    def md_cell(source: str):
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in source.split("\n")]
        }

    def code_cell(source: str):
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in source.split("\n")]
        }

    # Title & Metadata
    cells.append(
        md_cell(
            "# EcoSort: Model Evaluation & Results Analysis\n"
            "## 12 Municipal Material Classes → 4 Solid Waste Management (SWM) 2026 Streams\n\n"
            "This notebook presents empirical evaluation on the held-out **2,843 test images**.\n"
            "All metrics and figures are loaded directly from generated artifacts:\n"
            "- `ml/artifacts/wastenet/` (Custom 5-Block CNN from scratch)\n"
            "- `ml/artifacts/mobilenet_v3/` (MobileNetV3-Large transfer learning)\n"
            "- `ml/artifacts/efficientnet_b0/` (EfficientNet-B0 transfer learning)\n"
            "- `ml/reports/figures/` (Confusion matrices, Reliability diagrams, and Grad-CAM grids)"
        )
    )

    # Imports & Setup
    cells.append(
        code_cell(
            "import json\n"
            "from pathlib import Path\n"
            "import matplotlib.pyplot as plt\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from IPython.display import Image as IPImage, display, Markdown\n\n"
            "# Define paths\n"
            "ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
            "ARTIFACTS_DIR = ROOT / 'ml' / 'artifacts'\n"
            "REPORTS_DIR = ROOT / 'ml' / 'reports'\n"
            "FIGURES_DIR = REPORTS_DIR / 'figures'\n\n"
            "print('Artifacts Directory:', ARTIFACTS_DIR)\n"
            "print('Figures Directory:  ', FIGURES_DIR)"
        )
    )

    # 1. Performance Summary Table
    cells.append(
        md_cell(
            "## 1. Overall Performance Comparison on Unseen Test Split\n\n"
            "Evaluation conducted on 2,843 held-out test images across all three models.\n"
            "Per Decision **D-16**, MobileNetV3-Large was pre-selected as the serving model "
            "prior to test evaluation based on validation macro-F1."
        )
    )

    cells.append(
        code_cell(
            "with open(REPORTS_DIR / 'model_comparison.json') as f:\n"
            "    comp = json.load(f)\n\n"
            "models = ['wastenet', 'mobilenet_v3', 'efficientnet_b0']\n"
            "names = ['WasteNet (Scratch)', 'MobileNetV3-Large (Transfer)', 'EfficientNet-B0 (Transfer)']\n\n"
            "rows = []\n"
            "for m, name in zip(models, names):\n"
            "    data = comp['models'][m]\n"
            "    rows.append({\n"
            "        'Model': name,\n"
            "        'Test Acc': f\"{data['accuracy']*100:.2f}%\",\n"
            "        'Macro-F1': f\"{data['macro_f1']:.4f}\",\n"
            "        '95% CI (Acc)': f\"[{data['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {data['bootstrap_ci_95']['accuracy']['high']*100:.1f}%]\",\n"
            "        'Stream Acc': f\"{data['stream_accuracy']*100:.2f}%\",\n"
            "        'Hazard Miss Rate': f\"{data['hazard_miss_rate']*100:.2f}% ({data['hazard_miss_count']}/{data['hazard_total']})\",\n"
            "        'Coverage @ Thresh': f\"{data['coverage_at_threshold']*100:.1f}% (thr={data['uncertain_threshold']:.2f})\",\n"
            "        'Acc @ Thresh': f\"{data['accuracy_above_threshold']*100:.2f}%\",\n"
            "        'CPU Latency p50': f\"{data['cpu_latency_ms_p50']:.1f} ms\",\n"
            "        'Params': f\"{data['params']:,}\",\n"
            "        'Size': f\"{data['size_mb']:.1f} MB\",\n"
            "    })\n\n"
            "df_summary = pd.DataFrame(rows)\n"
            "display(df_summary)"
        )
    )

    # 2. McNemar's Statistical Significance
    cells.append(
        md_cell(
            "## 2. Statistical Significance: McNemar's Test\n\n"
            "We conduct McNemar's test with continuity correction and exact two-tailed binomial p-values "
            "on paired binary test predictions ($N=2,843$)."
        )
    )

    cells.append(
        code_cell(
            "mc = comp['mcnemar_tests']\n"
            "print('=== WasteNet vs. MobileNetV3-Large ===')\n"
            "w_vs_m = mc['wastenet_vs_mobilenet_v3']\n"
            "print('Contingency Table:', w_vs_m['contingency_table'])\n"
            "print(f\"Discordant pairs: {w_vs_m['discordant_pairs']}\")\n"
            "print(f\"Chi-Square:       {w_vs_m['chi2_statistic']:.4f}\")\n"
            "print(f\"Exact p-value:    {w_vs_m['exact_p_value']:.4e} (Significant: {w_vs_m['statistically_significant']})\")\n\n"
            "print('\\n=== MobileNetV3-Large vs. EfficientNet-B0 ===')\n"
            "m_vs_e = mc['mobilenet_v3_vs_efficientnet_b0']\n"
            "print('Contingency Table:', m_vs_e['contingency_table'])\n"
            "print(f\"Discordant pairs: {m_vs_e['discordant_pairs']}\")\n"
            "print(f\"Chi-Square:       {m_vs_e['chi2_statistic']:.4f}\")\n"
            "print(f\"Exact p-value:    {m_vs_e['exact_p_value']:.4e} (Significant: {m_vs_e['statistically_significant']})\")"
        )
    )

    # 3. Confusion Matrix Heatmaps
    cells.append(
        md_cell(
            "## 3. Confusion Matrix Heatmaps (12 Material Classes)\n\n"
            "Comparing classification patterns across all three architectures."
        )
    )

    cells.append(
        code_cell(
            "fig, axes = plt.subplots(1, 3, figsize=(20, 6), dpi=150)\n"
            "for ax, m, name in zip(axes, models, names):\n"
            "    cm_data = json.load(open(ARTIFACTS_DIR / m / 'confusion_matrix.json'))\n"
            "    cm = np.array(cm_data['matrix'])\n"
            "    cm_norm = cm.astype('float') / np.maximum(cm.sum(axis=1)[:, np.newaxis], 1)\n"
            "    cax = ax.imshow(cm_norm, cmap='Blues')\n"
            "    ax.set_title(f\"{name}\\nAcc: {comp['models'][m]['accuracy']*100:.1f}%\", fontsize=11, fontweight='bold')\n"
            "    ax.set_xticks(range(12))\n"
            "    ax.set_xticklabels(cm_data['classes'], rotation=45, ha='right', fontsize=7)\n"
            "    ax.set_yticks(range(12))\n"
            "    ax.set_yticklabels(cm_data['classes'], fontsize=7)\n"
            "    ax.set_xlabel('Predicted')\n"
            "    ax.set_ylabel('True')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        )
    )

    # 4. Per-Class F1 Analysis
    cells.append(
        md_cell(
            "## 4. Per-Class F1 Breakdown & Top Material Confusions"
        )
    )

    cells.append(
        code_cell(
            "classes = list(comp['models']['mobilenet_v3']['per_class'].keys())\n"
            "f1_w = [comp['models']['wastenet']['per_class'][c]['f1'] for c in classes]\n"
            "f1_m = [comp['models']['mobilenet_v3']['per_class'][c]['f1'] for c in classes]\n"
            "f1_e = [comp['models']['efficientnet_b0']['per_class'][c]['f1'] for c in classes]\n\n"
            "x = np.arange(len(classes))\n"
            "width = 0.28\n\n"
            "plt.figure(figsize=(14, 5), dpi=150)\n"
            "plt.bar(x - width, f1_w, width, label='WasteNet (Scratch)', color='#718096')\n"
            "plt.bar(x, f1_m, width, label='MobileNetV3 (Default)', color='#2B6CB0')\n"
            "plt.bar(x + width, f1_e, width, label='EfficientNet-B0', color='#319795')\n"
            "plt.xticks(x, classes, rotation=35, ha='right', fontweight='bold')\n"
            "plt.ylabel('F1-Score', fontweight='bold')\n"
            "plt.title('Per-Class F1-Score Comparison across 12 Municipal Waste Classes', fontweight='bold')\n"
            "plt.legend()\n"
            "plt.grid(axis='y', linestyle='--', alpha=0.5)\n"
            "plt.tight_layout()\n"
            "plt.show()"
        )
    )

    # 5. Domain Generalization & Per-Source Gap
    cells.append(
        md_cell(
            "## 5. Domain Shift & Per-Source Breakdown\n\n"
            "We inspect performance across the 4 aggregated constituent datasets:\n"
            "- `garbage12`: Curated web-scraped waste image benchmark (Kaggle)\n"
            "- `realwaste`: Landfill and sorting facility photos under uneven real-world lighting\n"
            "- `trashbox`: Web-scraped e-waste, hazardous, and municipal items featuring stock watermarks (e.g. Shutterstock, Getty) and varied camera angles\n"
            "- `trashnet`: Classic laboratory-style photos on uniform white background"
        )
    )

    cells.append(
        code_cell(
            "sources = list(comp['models']['mobilenet_v3']['per_source_accuracy'].keys())\n"
            "src_rows = []\n"
            "for s in sources:\n"
            "    src_rows.append({\n"
            "        'Source Dataset': s,\n"
            "        'Test Count': comp['models']['mobilenet_v3']['per_source_accuracy'][s]['total'],\n"
            "        'WasteNet (Scratch)': f\"{comp['models']['wastenet']['per_source_accuracy'][s]['accuracy']*100:.1f}%\",\n"
            "        'MobileNetV3 (Default)': f\"{comp['models']['mobilenet_v3']['per_source_accuracy'][s]['accuracy']*100:.1f}%\",\n"
            "        'EfficientNet-B0': f\"{comp['models']['efficientnet_b0']['per_source_accuracy'][s]['accuracy']*100:.1f}%\",\n"
            "    })\n"
            "display(pd.DataFrame(src_rows))"
        )
    )

    # 6. Reliability Diagrams & Calibration
    cells.append(
        md_cell(
            "## 6. Model Calibration & Reliability Diagrams (15 Equal-Width Bins)\n\n"
            "Displaying calibration diagrams before and after temperature scaling on validation."
        )
    )

    cells.append(
        code_cell(
            "for m, name in zip(models, names):\n"
            "    print(f'=== {name} Reliability Diagram ===')\n"
            "    display(IPImage(filename=str(ARTIFACTS_DIR / m / 'calibration.png')))"
        )
    )

    # 7. Grad-CAM Explainability & Shortcut Audit
    cells.append(
        md_cell(
            "## 7. Explainability & Shortcut Learning Audit (Hand-Written Grad-CAM)\n\n"
            "Inspecting convolutional feature attention using manual forward/backward PyTorch hooks."
        )
    )

    cells.append(
        md_cell(
            "### 7.1 Twelve-Class Correct Prediction Heatmaps\n"
            "Verifying that the model activates on salient item geometry across all 12 classes."
        )
    )
    cells.append(
        code_cell(
            "display(IPImage(filename=str(FIGURES_DIR / 'gradcam_12class_correct.png')))"
        )
    )

    cells.append(
        md_cell(
            "### 7.2 Top 12 Confident Misclassifications with Grad-CAM\n"
            "Inspecting the most confident failure cases and hazardous miss errors.\n\n"
            "> **Key Observation:** In the top confident misclassifications (`gradcam_top_wrong.png`), "
            "note the `paper → cardboard` misclassification. The Grad-CAM heatmap intensity is concentrated "
            "in the bottom-right corner where a **shutterstock.com watermark** is printed, rather than on the paper item."
        )
    )
    cells.append(
        code_cell(
            "display(IPImage(filename=str(FIGURES_DIR / 'gradcam_top_wrong.png')))"
        )
    )

    cells.append(
        md_cell(
            "### 7.3 Shortcut & Watermark Bias Audit (TrashBox Test Samples)\n"
            "Empirical check across 12 TrashBox test images (2 per class across 6 classes: "
            "`cardboard`, `e_waste`, `glass`, `medicine_syringe`, `metal`, `plastic`):\n"
            "Does the model focus on the physical object or latch onto web watermarks, borders, and corners?\n\n"
            "> **Visual Findings:** While central item geometry triggers high gradient energy in cases like "
            "syringes and circuit boards, several images display prominent heat on border edges (e.g. mobile phone left edge) "
            "and image corners (e.g. metal item corner), confirming partial reliance on border/watermark context."
        )
    )
    cells.append(
        code_cell(
            "display(IPImage(filename=str(FIGURES_DIR / 'gradcam_shortcut_check.png')))"
        )
    )

    cells.append(
        md_cell(
            "### 7.4 Quantitative Shortcut & Spatial Bias Evaluation\n\n"
            "To quantitatively measure shortcut reliance and spatial bias beyond visual spot-checks, we evaluate all 2,843 test images under:\n"
            "1. **Border-60% Accuracy:** Central 60% per side masked (36% area hidden, 64% border visible). Measures robustness to partial views + context, confounded by object parts in border.\n"
            "2. **Border-10% Control:** Central 80% per side masked (64% area hidden, only a 10% perimeter frame remains visible). Isolates thin border context.\n"
            "3. **Center-60% Accuracy:** Outer 20% border on all sides masked with dataset mean colour (only central 36% area visible).\n"
            "4. **Grad-CAM Border Mass Ratio:** The outer 15% perimeter covers $1 - 0.70^2 = 51.0\\%$ of image area. "
            "We compare observed border mass against this 51.0% uniform baseline. Ratios $< 1.0$ indicate that attention is on average "
            "**more center-focused** on the object than uniform chance."
        )
    )
    cells.append(
        code_cell(
            "shortcut_json_path = REPORTS_DIR / 'shortcut_test.json'\n"
            "if shortcut_json_path.exists():\n"
            "    with open(shortcut_json_path) as f:\n"
            "        sdata = json.load(f)\n\n"
            "    s_rows = []\n"
            "    for m, name in zip(models, names):\n"
            "        if m in sdata:\n"
            "            ov = sdata[m]['overall']\n"
            "            b10_str = f\"{ov['border_10_acc']*100:.2f}%\" if 'border_10_acc' in ov else 'N/A'\n"
            "            ratio_val = ov.get('gradcam_border_ratio', ov['gradcam_border_mass_mean']/0.51)\n"
            "            s_rows.append({\n"
            "                'Model': name,\n"
            "                'Original Acc': f\"{ov['original_acc']*100:.2f}%\",\n"
            "                'Center-60% Acc': f\"{ov['center_60_acc']*100:.2f}%\",\n"
            "                'Border-60% Acc': f\"{ov['border_60_acc']*100:.2f}%\",\n"
            "                'Border-10% Frame': b10_str,\n"
            "                'Grad-CAM Border Mass': f\"{ov['gradcam_border_mass_mean']*100:.1f}% ± {ov['gradcam_border_mass_std']*100:.1f}%\",\n"
            "                'Ratio vs 51% Uniform': f\"{ratio_val:.2f}x ({'Center-Focused' if ratio_val < 1.0 else 'Border-Biased'})\"\n"
            "            })\n"
            "    display(pd.DataFrame(s_rows))\n"
            "else:\n"
            "    print('shortcut_test.json not yet generated.')"
        )
    )

    # 8. Honest Discussion
    cells.append(
        md_cell(
            "## 8. Honest Academic Discussion & Engineering Findings\n\n"
            "### 8.1 Key Findings\n"
            "1. **Transfer Learning vs. From-Scratch:** Pretrained ImageNet representations provide a decisive advantage "
            "(+16.57 percentage points in accuracy, +0.1740 in macro-F1 over WasteNet). "
            "McNemar's test confirms this difference is overwhelmingly statistically significant ($p = 9.51 \\times 10^{-91}$).\n\n"
            "2. **Serving Model Selection:** MobileNetV3-Large was pre-selected per Decision **D-16** based on validation macro-F1 (0.922 vs 0.906) "
            "and its 2.1× CPU inference speed advantage (54.5 ms vs 115.4 ms). On the test set, MobileNetV3 achieves 92.44% accuracy vs 91.45% for EfficientNet-B0. "
            "A paired McNemar test reveals **$p = 0.0547$**, which is **not statistically significant** at $\\alpha = 0.05$. "
            "Therefore, the serving decision rests appropriately on validation performance and computational efficiency rather than post-hoc test tuning.\n\n"
            "3. **Hazard Miss Rate & Stream Routing:** Under SWM Rules 2026, hazardous materials (`sanitary` and `special_care`) must not leak "
            "into `wet` or `dry` municipal streams. MobileNetV3 and EfficientNet-B0 reduce hazard leakage to **3.12%** (21/674), "
            "down from 17.36% (117/674) in WasteNet. Overall stream-level classification accuracy reaches **97.82%**.\n\n"
            "4. **Shortcut Learning & Attention Distribution:**\n"
            "   - **Border Test Nuance:** Blanking the central 60% per side covers only 36% of the image area, leaving 64% visible. "
            "Because physical waste items often extend beyond this central box, the 82% border-60% accuracy partly reflects partial object visibility "
            "and context rather than pure shortcut reliance. The cleaner **Border-10% control** (masking the central 80% per side) provides a strict perimeter assessment.\n"
            "   - **Grad-CAM Border Mass vs. Uniform Baseline:** The outer 15% perimeter covers $1 - 0.70^2 = 51.0\\%$ of the image. "
            "Transfer learning models exhibit an average border mass of $\\approx 42\\%$, which is *below* uniform chance (ratio $\\approx 0.83$). "
            "Thus, on average, model attention is **mostly object-centered**, accompanied by isolated individual cases of watermark or border reliance (e.g., the `shutterstock.com` watermark corner activation in `paper → cardboard`).\n\n"
            "5. **Error Audit: Hazard Misses vs. Ambiguous Annotations:**\n"
            "   - **Model Hazard Miss:** The confident misclassification of a copper wire coil as `metal` rather than `e_waste` is a genuine model hazard miss. "
            "TrashBox explicitly defines e-waste to include electrical wires, cords, and cables (Special Care stream); misrouting it to dry metal is a model classification failure under SWM Rules 2026.\n"
            "   - **Ambiguous Annotations:** Other confident errors, such as transparent jars, reflect visual ambiguity between glass and clear rigid plastic in low-resolution web imagery.\n\n"
            "6. **Confidence Thresholding Limitation:** The optimal uncertainty rejection threshold sits at the clamp floor ($p_{max} \\ge 0.40$), "
            "retaining 96.0% coverage while elevating kept accuracy to 94.61%. This reflects that temperature-scaled probabilities remain relatively sharp after label smoothing."
        )
    )

    notebook_dict = {
        "cells": cells,
        "metadata": {
            "language_info": {
                "name": "python",
                "version": "3.11"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    out_path = Path("ml/notebooks/02_results.ipynb")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(notebook_dict, f, indent=1)
    print(f"Successfully generated {out_path}")


if __name__ == "__main__":
    make_notebook()
