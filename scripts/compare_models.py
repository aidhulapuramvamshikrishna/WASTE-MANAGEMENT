#!/usr/bin/env python3
"""Compare trained WasteML models on the test set.

Generates:
- ml/reports/model_comparison.json
- ml/reports/model_comparison.md
- McNemar tests with exact two-tailed p-values for:
  * wastenet vs mobilenet_v3
  * mobilenet_v3 vs efficientnet_b0
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats


def run_mcnemar_test(corr_a: np.ndarray, corr_b: np.ndarray) -> dict:
    """Calculate McNemar test contingency table, chi2, and two-tailed p-value."""
    # corr_a, corr_b are boolean arrays of shape (N,) indicating correct predictions
    n00 = int(np.sum((~corr_a) & (~corr_b)))  # Both wrong
    n01 = int(np.sum((~corr_a) & corr_b))    # A wrong, B correct (b)
    n10 = int(np.sum(corr_a & (~corr_b)))    # A correct, B wrong (c)
    n11 = int(np.sum(corr_a & corr_b))       # Both correct

    b = n01
    c = n10
    total_discordant = b + c

    # Exact binomial two-tailed p-value
    if total_discordant > 0:
        binom_res = stats.binomtest(min(b, c), total_discordant, 0.5, alternative="two-sided")
        p_exact = float(binom_res.pvalue)
    else:
        p_exact = 1.0

    # Edwards continuity-corrected Chi-Square
    if total_discordant > 0:
        chi2 = float((abs(b - c) - 1.0) ** 2 / total_discordant)
        p_chi2 = float(1.0 - stats.chi2.cdf(chi2, df=1))
    else:
        chi2 = 0.0
        p_chi2 = 1.0

    return {
        "contingency_table": {
            "both_wrong (n00)": n00,
            "a_wrong_b_correct (b/n01)": b,
            "a_correct_b_wrong (c/n10)": c,
            "both_correct (n11)": n11,
        },
        "discordant_pairs": total_discordant,
        "chi2_statistic": round(chi2, 4),
        "chi2_p_value": p_chi2,
        "exact_p_value": p_exact,
        "statistically_significant": bool(p_exact < 0.05),
    }


def main():
    root = Path(__file__).resolve().parent.parent
    artifacts_dir = root / "ml" / "artifacts"
    reports_dir = root / "ml" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    models = ["wastenet", "mobilenet_v3", "efficientnet_b0"]
    metrics_data = {}
    preds_data = {}

    for m in models:
        m_dir = artifacts_dir / m
        m_file = m_dir / "metrics.json"
        p_file = m_dir / "test_predictions.csv"

        if not m_file.exists():
            raise FileNotFoundError(f"Missing metrics.json for {m} at {m_file}")
        with open(m_file) as f:
            metrics_data[m] = json.load(f)

        if not p_file.exists():
            raise FileNotFoundError(f"Missing test_predictions.csv for {m} at {p_file}")
        preds_data[m] = pd.read_csv(p_file)

    # McNemar tests
    mcnemar_wastenet_vs_mobile = run_mcnemar_test(
        preds_data["wastenet"]["is_correct"].to_numpy(),
        preds_data["mobilenet_v3"]["is_correct"].to_numpy(),
    )
    mcnemar_mobile_vs_eff = run_mcnemar_test(
        preds_data["mobilenet_v3"]["is_correct"].to_numpy(),
        preds_data["efficientnet_b0"]["is_correct"].to_numpy(),
    )

    comparison_results = {
        "models": {m: metrics_data[m] for m in models},
        "mcnemar_tests": {
            "wastenet_vs_mobilenet_v3": mcnemar_wastenet_vs_mobile,
            "mobilenet_v3_vs_efficientnet_b0": mcnemar_mobile_vs_eff,
        },
    }

    # Save JSON
    json_path = reports_dir / "model_comparison.json"
    with open(json_path, "w") as f:
        json.dump(comparison_results, f, indent=2)
    print(f"Saved comparison JSON to {json_path}")

    # Generate Markdown Table and Report
    md_path = reports_dir / "model_comparison.md"
    with open(md_path, "w") as f:
        f.write("# EcoSort Model Comparison Report (Test Set Evaluation)\n\n")
        f.write("Evaluation conducted on the fixed, un-tuned 2,843 test images.\n\n")
        f.write("## 1. Overall Performance Summary\n\n")
        f.write("| Metric | WasteNet (Scratch) | MobileNetV3-Large (Transfer) | EfficientNet-B0 (Transfer) |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Architecture** | Custom 5-Block CNN | MobileNetV3-Large | EfficientNet-B0 |\n")
        f.write(f"| **Pretrained** | No (Kaiming init) | ImageNet-1K V2 | ImageNet-1K V1 |\n")
        f.write(f"| **Parameters** | {metrics_data['wastenet']['params']:,} | {metrics_data['mobilenet_v3']['params']:,} | {metrics_data['efficientnet_b0']['params']:,} |\n")
        f.write(f"| **Size (best.pt)** | {metrics_data['wastenet']['size_mb']:.1f} MB | {metrics_data['mobilenet_v3']['size_mb']:.1f} MB | {metrics_data['efficientnet_b0']['size_mb']:.1f} MB |\n")
        f.write(f"| **Test Accuracy** | **{metrics_data['wastenet']['accuracy']*100:.2f}%** | **{metrics_data['mobilenet_v3']['accuracy']*100:.2f}%** | **{metrics_data['efficientnet_b0']['accuracy']*100:.2f}%** |\n")
        f.write(f"| **Test Macro-F1** | {metrics_data['wastenet']['macro_f1']:.4f} | {metrics_data['mobilenet_v3']['macro_f1']:.4f} | {metrics_data['efficientnet_b0']['macro_f1']:.4f} |\n")
        f.write(f"| **95% CI (Acc)** | [{metrics_data['wastenet']['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {metrics_data['wastenet']['bootstrap_ci_95']['accuracy']['high']*100:.1f}%] | [{metrics_data['mobilenet_v3']['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {metrics_data['mobilenet_v3']['bootstrap_ci_95']['accuracy']['high']*100:.1f}%] | [{metrics_data['efficientnet_b0']['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {metrics_data['efficientnet_b0']['bootstrap_ci_95']['accuracy']['high']*100:.1f}%] |\n")
        f.write(f"| **95% CI (Macro-F1)** | [{metrics_data['wastenet']['bootstrap_ci_95']['macro_f1']['low']:.4f}, {metrics_data['wastenet']['bootstrap_ci_95']['macro_f1']['high']:.4f}] | [{metrics_data['mobilenet_v3']['bootstrap_ci_95']['macro_f1']['low']:.4f}, {metrics_data['mobilenet_v3']['bootstrap_ci_95']['macro_f1']['high']:.4f}] | [{metrics_data['efficientnet_b0']['bootstrap_ci_95']['macro_f1']['low']:.4f}, {metrics_data['efficientnet_b0']['bootstrap_ci_95']['macro_f1']['high']:.4f}] |\n")
        f.write(f"| **Top-3 Accuracy** | {metrics_data['wastenet']['top3_accuracy']*100:.2f}% | {metrics_data['mobilenet_v3']['top3_accuracy']*100:.2f}% | {metrics_data['efficientnet_b0']['top3_accuracy']*100:.2f}% |\n")
        f.write(f"| **Stream Accuracy** | {metrics_data['wastenet']['stream_accuracy']*100:.2f}% | {metrics_data['mobilenet_v3']['stream_accuracy']*100:.2f}% | {metrics_data['efficientnet_b0']['stream_accuracy']*100:.2f}% |\n")
        f.write(f"| **Hazard Miss Rate** | {metrics_data['wastenet']['hazard_miss_rate']*100:.2f}% ({metrics_data['wastenet']['hazard_miss_count']}/{metrics_data['wastenet']['hazard_total']}) | {metrics_data['mobilenet_v3']['hazard_miss_rate']*100:.2f}% ({metrics_data['mobilenet_v3']['hazard_miss_count']}/{metrics_data['mobilenet_v3']['hazard_total']}) | {metrics_data['efficientnet_b0']['hazard_miss_rate']*100:.2f}% ({metrics_data['efficientnet_b0']['hazard_miss_count']}/{metrics_data['efficientnet_b0']['hazard_total']}) |\n")
        f.write(f"| **Coverage @ Thresh** | {metrics_data['wastenet']['coverage_at_threshold']*100:.1f}% (thr={metrics_data['wastenet']['uncertain_threshold']:.2f}) | {metrics_data['mobilenet_v3']['coverage_at_threshold']*100:.1f}% (thr={metrics_data['mobilenet_v3']['uncertain_threshold']:.2f}) | {metrics_data['efficientnet_b0']['coverage_at_threshold']*100:.1f}% (thr={metrics_data['efficientnet_b0']['uncertain_threshold']:.2f}) |\n")
        f.write(f"| **Acc @ Thresh** | {metrics_data['wastenet']['accuracy_above_threshold']*100:.2f}% | {metrics_data['mobilenet_v3']['accuracy_above_threshold']*100:.2f}% | {metrics_data['efficientnet_b0']['accuracy_above_threshold']*100:.2f}% |\n")
        f.write(f"| **CPU Latency (p50)** | {metrics_data['wastenet']['cpu_latency_ms_p50']:.1f} ms | **{metrics_data['mobilenet_v3']['cpu_latency_ms_p50']:.1f} ms** | {metrics_data['efficientnet_b0']['cpu_latency_ms_p50']:.1f} ms |\n")
        f.write(f"| **CPU Latency (p95)** | {metrics_data['wastenet']['cpu_latency_ms_p95']:.1f} ms | {metrics_data['mobilenet_v3']['cpu_latency_ms_p95']:.1f} ms | {metrics_data['efficientnet_b0']['cpu_latency_ms_p95']:.1f} ms |\n\n")

        f.write("## 2. Statistical Significance (McNemar's Tests)\n\n")
        f.write("### WasteNet vs. MobileNetV3-Large\n")
        f.write(f"- Contingency Table:\n")
        f.write(f"  - Both correct ($n_{{11}}$): {mcnemar_wastenet_vs_mobile['contingency_table']['both_correct (n11)']}\n")
        f.write(f"  - WasteNet wrong, MobileNetV3 correct ($b$): {mcnemar_wastenet_vs_mobile['contingency_table']['a_wrong_b_correct (b/n01)']}\n")
        f.write(f"  - WasteNet correct, MobileNetV3 wrong ($c$): {mcnemar_wastenet_vs_mobile['contingency_table']['a_correct_b_wrong (c/n10)']}\n")
        f.write(f"  - Both wrong ($n_{{00}}$): {mcnemar_wastenet_vs_mobile['contingency_table']['both_wrong (n00)']}\n")
        f.write(f"- Discordant pairs ($b + c$): {mcnemar_wastenet_vs_mobile['discordant_pairs']}\n")
        f.write(f"- Continuity-corrected $\\chi^2$: {mcnemar_wastenet_vs_mobile['chi2_statistic']:.4f}\n")
        f.write(f"- Exact two-tailed p-value: **{mcnemar_wastenet_vs_mobile['exact_p_value']:.4e}** (Statistically significant: {mcnemar_wastenet_vs_mobile['statistically_significant']})\n\n")

        f.write("### MobileNetV3-Large vs. EfficientNet-B0\n")
        f.write(f"- Contingency Table:\n")
        f.write(f"  - Both correct ($n_{{11}}$): {mcnemar_mobile_vs_eff['contingency_table']['both_correct (n11)']}\n")
        f.write(f"  - MobileNetV3 wrong, EfficientNet-B0 correct ($b$): {mcnemar_mobile_vs_eff['contingency_table']['a_wrong_b_correct (b/n01)']}\n")
        f.write(f"  - MobileNetV3 correct, EfficientNet-B0 wrong ($c$): {mcnemar_mobile_vs_eff['contingency_table']['a_correct_b_wrong (c/n10)']}\n")
        f.write(f"  - Both wrong ($n_{{00}}$): {mcnemar_mobile_vs_eff['contingency_table']['both_wrong (n00)']}\n")
        f.write(f"- Discordant pairs ($b + c$): {mcnemar_mobile_vs_eff['discordant_pairs']}\n")
        f.write(f"- Continuity-corrected $\\chi^2$: {mcnemar_mobile_vs_eff['chi2_statistic']:.4f}\n")
        f.write(f"- Exact two-tailed p-value: **{mcnemar_mobile_vs_eff['exact_p_value']:.4e}** (Statistically significant: {mcnemar_mobile_vs_eff['statistically_significant']})\n\n")

        f.write("## 3. Per-Source Breakdown\n\n")
        f.write("| Source Dataset | WasteNet | MobileNetV3-Large | EfficientNet-B0 |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        sources = list(metrics_data['mobilenet_v3']['per_source_accuracy'].keys())
        for s in sources:
            w_acc = metrics_data['wastenet']['per_source_accuracy'].get(s, {}).get('accuracy', 0.0) * 100
            m_acc = metrics_data['mobilenet_v3']['per_source_accuracy'].get(s, {}).get('accuracy', 0.0) * 100
            e_acc = metrics_data['efficientnet_b0']['per_source_accuracy'].get(s, {}).get('accuracy', 0.0) * 100
            total_s = metrics_data['mobilenet_v3']['per_source_accuracy'].get(s, {}).get('total', 0)
            f.write(f"| **{s}** (N={total_s}) | {w_acc:.1f}% | {m_acc:.1f}% | {e_acc:.1f}% |\n")

    print(f"Saved comparison Markdown to {md_path}")


if __name__ == "__main__":
    main()
