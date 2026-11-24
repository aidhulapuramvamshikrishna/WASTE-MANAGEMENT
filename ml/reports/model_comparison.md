# EcoSort Model Comparison Report (Test Set Evaluation)

Evaluation conducted on the fixed, un-tuned 2,843 test images.

## 1. Overall Performance Summary

| Metric | WasteNet (Scratch) | MobileNetV3-Large (Transfer) | EfficientNet-B0 (Transfer) |
| :--- | :--- | :--- | :--- |
| **Architecture** | Custom 5-Block CNN | MobileNetV3-Large | EfficientNet-B0 |
| **Pretrained** | No (Kaiming init) | ImageNet-1K V2 | ImageNet-1K V1 |
| **Parameters** | 3,391,212 | 4,217,404 | 4,022,920 |
| **Size (best.pt)** | 13.0 MB | 16.3 MB | 15.6 MB |
| **Test Accuracy** | **75.87%** | **92.44%** | **91.45%** |
| **Test Macro-F1** | 0.7441 | 0.9181 | 0.9063 |
| **95% CI (Acc)** | [74.4%, 77.5%] | [91.4%, 93.4%] | [90.4%, 92.4%] |
| **95% CI (Macro-F1)** | [0.7272, 0.7599] | [0.9074, 0.9284] | [0.8946, 0.9168] |
| **Top-3 Accuracy** | 92.16% | 98.52% | 98.07% |
| **Stream Accuracy** | 88.32% | 97.75% | 96.73% |
| **Hazard Miss Rate** | 17.36% (117/674) | 3.12% (21/674) | 3.12% (21/674) |
| **Coverage @ Thresh** | 66.1% (thr=0.62) | 96.0% (thr=0.40) | 96.5% (thr=0.40) |
| **Acc @ Thresh** | 90.04% | 94.61% | 93.26% |
| **CPU Latency (p50)** | 8.5 ms | **54.5 ms** | 115.4 ms |
| **CPU Latency (p95)** | 10.5 ms | 61.8 ms | 134.9 ms |

## 2. Statistical Significance (McNemar's Tests)

### WasteNet vs. MobileNetV3-Large
- Contingency Table:
  - Both correct ($n_{11}$): 2086
  - WasteNet wrong, MobileNetV3 correct ($b$): 542
  - WasteNet correct, MobileNetV3 wrong ($c$): 71
  - Both wrong ($n_{00}$): 144
- Discordant pairs ($b + c$): 613
- Continuity-corrected $\chi^2$: 360.3589
- Exact two-tailed p-value: **9.5094e-91** (Statistically significant: True)

### MobileNetV3-Large vs. EfficientNet-B0
- Contingency Table:
  - Both correct ($n_{11}$): 2515
  - MobileNetV3 wrong, EfficientNet-B0 correct ($b$): 85
  - MobileNetV3 correct, EfficientNet-B0 wrong ($c$): 113
  - Both wrong ($n_{00}$): 130
- Discordant pairs ($b + c$): 198
- Continuity-corrected $\chi^2$: 3.6818
- Exact two-tailed p-value: **5.4734e-02** (Statistically significant: False)

## 3. Per-Source Breakdown

| Source Dataset | WasteNet | MobileNetV3-Large | EfficientNet-B0 |
| :--- | :--- | :--- | :--- |
| **garbage12** (N=691) | 80.6% | 97.7% | 96.5% |
| **realwaste** (N=731) | 82.3% | 90.8% | 88.9% |
| **trashbox** (N=1040) | 65.7% | 90.4% | 89.9% |
| **trashnet** (N=381) | 82.7% | 91.6% | 91.3% |
