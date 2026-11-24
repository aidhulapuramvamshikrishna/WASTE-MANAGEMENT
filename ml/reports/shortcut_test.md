# EcoSort: Quantitative Shortcut & Spatial Bias Analysis

Evaluates background, border, and artifact reliance across all 2,843 test images.

- **Random Chance Baseline:** 8.33% (1/12 classes)
- **Uniform Baseline for Outer 15% Border:** 51.0% of image area ($1 - 0.70^2 = 0.51$)
- **Border-60%:** Central 60% per side masked (36% area hidden, 64% border visible). Measures robustness to partial views + context, confounded by object parts in border.
- **Border-10% Control:** Central 80% per side masked (64% area hidden, only 10% perimeter frame remains).
- **Center-60%:** Outer 20% border on all sides masked (only central 36% area visible).
- **Grad-CAM Border Mass Ratio:** Observed border mass divided by 51.0% uniform baseline. Ratios < 1.0 prove attention is on average **more center-focused** on the object than chance.

## 1. Overall Model Comparison

| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WasteNet (Scratch)** | 75.87% | 15.65% | 29.26% | **17.31%** | 45.5% ± 31.7% | **0.89×** (Center-Focused) |
| **MobileNetV3-Large (Default)** | 92.44% | 79.07% | 82.48% | **62.33%** | 42.4% ± 17.2% | **0.83×** (Center-Focused) |
| **EfficientNet-B0** | 91.45% | 82.10% | 80.65% | **63.07%** | 42.3% ± 10.9% | **0.83×** (Center-Focused) |

## 2. Per-Source Breakdown

### Source: `garbage12` (web-scraped benchmark (Kaggle))

| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WasteNet (Scratch)** | 80.6% | 4.5% | 22.4% | **11.9%** | 55.7% ± 30.5% | **1.09×** |
| **MobileNetV3-Large (Default)** | 97.7% | 88.3% | 92.3% | **76.4%** | 40.6% ± 13.9% | **0.80×** |
| **EfficientNet-B0** | 96.5% | 86.5% | 92.3% | **73.8%** | 42.5% ± 7.7% | **0.83×** |

### Source: `realwaste` (photographed at a landfill site)

| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WasteNet (Scratch)** | 82.3% | 23.9% | 25.4% | **14.1%** | 47.9% ± 32.1% | **0.94×** |
| **MobileNetV3-Large (Default)** | 90.8% | 71.0% | 71.0% | **42.7%** | 40.9% ± 19.7% | **0.80×** |
| **EfficientNet-B0** | 88.9% | 79.1% | 67.6% | **44.6%** | 42.6% ± 12.5% | **0.84×** |

### Source: `trashbox` (web-scraped with stock watermarks)

| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WasteNet (Scratch)** | 65.7% | 13.2% | 31.1% | **18.8%** | 36.1% ± 30.1% | **0.71×** |
| **MobileNetV3-Large (Default)** | 90.4% | 78.6% | 82.8% | **65.1%** | 42.1% ± 16.6% | **0.83×** |
| **EfficientNet-B0** | 89.9% | 81.7% | 81.5% | **69.2%** | 40.9% ± 10.9% | **0.80×** |

### Source: `trashnet` (studio photos on white background)

| Model | Original Acc | Center-60% Acc | Border-60% Acc | Border-10% Frame | Grad-CAM Border Mass | Ratio vs. 51% Uniform |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WasteNet (Scratch)** | 82.7% | 26.8% | 43.8% | **29.4%** | 48.0% ± 30.5% | **0.94×** |
| **MobileNetV3-Large (Default)** | 91.6% | 79.3% | 85.8% | **66.9%** | 49.3% ± 17.7% | **0.97×** |
| **EfficientNet-B0** | 91.3% | 80.8% | 82.2% | **62.2%** | 45.0% ± 11.8% | **0.88×** |

