#!/usr/bin/env python3
"""Update README.md with empirical model results from ml/artifacts/*/metrics.json.

Zero typed numbers: all figures are read directly from saved JSON metrics files.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"
README_PATH = REPO_ROOT / "README.md"

MODELS = [
    ("wastenet", "WasteNet (Scratch)", "Custom 5-Block CNN", "None (Kaiming init)"),
    ("mobilenet_v3", "MobileNetV3-Large (Transfer)", "MobileNetV3-Large", "ImageNet-1K V2"),
    ("efficientnet_b0", "EfficientNet-B0 (Transfer)", "EfficientNet-B0", "ImageNet-1K V1"),
]


def load_metrics(model_dir_name: str) -> dict:
    metrics_path = ARTIFACTS_DIR / model_dir_name / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Missing metrics file: {metrics_path}")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_results_markdown() -> str:
    metrics_map = {m[0]: load_metrics(m[0]) for m in MODELS}

    lines = [
        "<!-- RESULTS_START -->",
        "| Metric | WasteNet (Scratch) | MobileNetV3-Large (Transfer) | EfficientNet-B0 (Transfer) |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Architecture** | {MODELS[0][2]} | {MODELS[1][2]} | {MODELS[2][2]} |",
        f"| **Pretrained Weights** | {MODELS[0][3]} | {MODELS[1][3]} | {MODELS[2][3]} |",
    ]

    # Parameters
    p0 = f"{metrics_map['wastenet']['params']:,}"
    p1 = f"{metrics_map['mobilenet_v3']['params']:,}"
    p2 = f"{metrics_map['efficientnet_b0']['params']:,}"
    lines.append(f"| **Parameters** | {p0} | {p1} | {p2} |")

    # Size
    s0 = f"{metrics_map['wastenet']['size_mb']:.1f} MB"
    s1 = f"{metrics_map['mobilenet_v3']['size_mb']:.1f} MB"
    s2 = f"{metrics_map['efficientnet_b0']['size_mb']:.1f} MB"
    lines.append(f"| **Model Size** | {s0} | {s1} | {s2} |")

    # Accuracy
    a0 = f"{metrics_map['wastenet']['accuracy'] * 100:.2f}%"
    a1 = f"**{metrics_map['mobilenet_v3']['accuracy'] * 100:.2f}%**"
    a2 = f"{metrics_map['efficientnet_b0']['accuracy'] * 100:.2f}%"
    lines.append(f"| **Test Accuracy** | {a0} | {a1} | {a2} |")

    # Macro-F1
    f0 = f"{metrics_map['wastenet']['macro_f1'] * 100:.2f}%"
    f1 = f"**{metrics_map['mobilenet_v3']['macro_f1'] * 100:.2f}%**"
    f2 = f"{metrics_map['efficientnet_b0']['macro_f1'] * 100:.2f}%"
    lines.append(f"| **Test Macro-F1** | {f0} | {f1} | {f2} |")

    # 95% CIs
    ci_acc0 = f"[{metrics_map['wastenet']['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {metrics_map['wastenet']['bootstrap_ci_95']['accuracy']['high']*100:.1f}%]"
    ci_acc1 = f"[{metrics_map['mobilenet_v3']['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {metrics_map['mobilenet_v3']['bootstrap_ci_95']['accuracy']['high']*100:.1f}%]"
    ci_acc2 = f"[{metrics_map['efficientnet_b0']['bootstrap_ci_95']['accuracy']['low']*100:.1f}%, {metrics_map['efficientnet_b0']['bootstrap_ci_95']['accuracy']['high']*100:.1f}%]"
    lines.append(f"| **95% CI (Accuracy)** | {ci_acc0} | {ci_acc1} | {ci_acc2} |")

    ci_f1_0 = f"[{metrics_map['wastenet']['bootstrap_ci_95']['macro_f1']['low']*100:.1f}%, {metrics_map['wastenet']['bootstrap_ci_95']['macro_f1']['high']*100:.1f}%]"
    ci_f1_1 = f"[{metrics_map['mobilenet_v3']['bootstrap_ci_95']['macro_f1']['low']*100:.1f}%, {metrics_map['mobilenet_v3']['bootstrap_ci_95']['macro_f1']['high']*100:.1f}%]"
    ci_f1_2 = f"[{metrics_map['efficientnet_b0']['bootstrap_ci_95']['macro_f1']['low']*100:.1f}%, {metrics_map['efficientnet_b0']['bootstrap_ci_95']['macro_f1']['high']*100:.1f}%]"
    lines.append(f"| **95% CI (Macro-F1)** | {ci_f1_0} | {ci_f1_1} | {ci_f1_2} |")

    # Top-3 Accuracy
    t0 = f"{metrics_map['wastenet']['top3_accuracy'] * 100:.2f}%"
    t1 = f"{metrics_map['mobilenet_v3']['top3_accuracy'] * 100:.2f}%"
    t2 = f"{metrics_map['efficientnet_b0']['top3_accuracy'] * 100:.2f}%"
    lines.append(f"| **Top-3 Accuracy** | {t0} | {t1} | {t2} |")

    # Stream Accuracy
    sa0 = f"{metrics_map['wastenet']['stream_accuracy'] * 100:.2f}%"
    sa1 = f"**{metrics_map['mobilenet_v3']['stream_accuracy'] * 100:.2f}%**"
    sa2 = f"{metrics_map['efficientnet_b0']['stream_accuracy'] * 100:.2f}%"
    lines.append(f"| **Stream Accuracy (4 streams)** | {sa0} | {sa1} | {sa2} |")

    # Hazard Miss Rate
    hm0 = f"{metrics_map['wastenet']['hazard_miss_rate'] * 100:.2f}% ({metrics_map['wastenet']['hazard_miss_count']}/{metrics_map['wastenet']['hazard_total']})"
    hm1 = f"**{metrics_map['mobilenet_v3']['hazard_miss_rate'] * 100:.2f}%** ({metrics_map['mobilenet_v3']['hazard_miss_count']}/{metrics_map['mobilenet_v3']['hazard_total']})"
    hm2 = f"{metrics_map['efficientnet_b0']['hazard_miss_rate'] * 100:.2f}% ({metrics_map['efficientnet_b0']['hazard_miss_count']}/{metrics_map['efficientnet_b0']['hazard_total']})"
    lines.append(f"| **Hazard Miss Rate** | {hm0} | {hm1} | {hm2} |")

    # Uncertainty Coverage & Accuracy
    uc0 = f"{metrics_map['wastenet']['coverage_at_threshold'] * 100:.1f}% (thr={metrics_map['wastenet']['uncertain_threshold']:.2f})"
    uc1 = f"{metrics_map['mobilenet_v3']['coverage_at_threshold'] * 100:.1f}% (thr={metrics_map['mobilenet_v3']['uncertain_threshold']:.2f})"
    uc2 = f"{metrics_map['efficientnet_b0']['coverage_at_threshold'] * 100:.1f}% (thr={metrics_map['efficientnet_b0']['uncertain_threshold']:.2f})"
    lines.append(f"| **Coverage @ Threshold** | {uc0} | {uc1} | {uc2} |")

    ua0 = f"{metrics_map['wastenet']['accuracy_above_threshold'] * 100:.2f}%"
    ua1 = f"{metrics_map['mobilenet_v3']['accuracy_above_threshold'] * 100:.2f}%"
    ua2 = f"{metrics_map['efficientnet_b0']['accuracy_above_threshold'] * 100:.2f}%"
    lines.append(f"| **Accuracy @ Threshold** | {ua0} | {ua1} | {ua2} |")

    # CPU Latency (p50 / p95)
    l0 = f"{metrics_map['wastenet']['cpu_latency_ms_p50']:.1f} ms / {metrics_map['wastenet']['cpu_latency_ms_p95']:.1f} ms"
    l1 = f"{metrics_map['mobilenet_v3']['cpu_latency_ms_p50']:.1f} ms / {metrics_map['mobilenet_v3']['cpu_latency_ms_p95']:.1f} ms"
    l2 = f"{metrics_map['efficientnet_b0']['cpu_latency_ms_p50']:.1f} ms / {metrics_map['efficientnet_b0']['cpu_latency_ms_p95']:.1f} ms"
    lines.append(f"| **CPU Latency (p50 / p95)** | {l0} | {l1} | {l2} |")

    lines.append("<!-- RESULTS_END -->")
    return "\n".join(lines)


def update_readme() -> None:
    content = README_PATH.read_text(encoding="utf-8")
    table_md = generate_results_markdown()

    if "<!-- RESULTS_START -->" in content and "<!-- RESULTS_END -->" in content:
        start_idx = content.find("<!-- RESULTS_START -->")
        end_idx = content.find("<!-- RESULTS_END -->") + len("<!-- RESULTS_END -->")
        updated_content = content[:start_idx] + table_md + content[end_idx:]
    else:
        placeholder = "## Results\n_Filled in automatically from `ml/artifacts/*/metrics.json` by `scripts/update_readme_results.py` after M4. No numbers here until then._"
        if placeholder in content:
            updated_content = content.replace(placeholder, f"## Results\n\n{table_md}")
        else:
            # Fallback search for ## Results
            lines = content.split("\n")
            res_idx = -1
            for i, line in enumerate(lines):
                if line.strip() == "## Results":
                    res_idx = i
                    break
            if res_idx != -1:
                # Replace following line with table
                lines[res_idx + 1] = "\n" + table_md
                updated_content = "\n".join(lines)
            else:
                updated_content = content + "\n\n## Results\n\n" + table_md

    README_PATH.write_text(updated_content, encoding="utf-8")
    print(f"Updated {README_PATH} with empirical results from {ARTIFACTS_DIR}.")


if __name__ == "__main__":
    update_readme()
