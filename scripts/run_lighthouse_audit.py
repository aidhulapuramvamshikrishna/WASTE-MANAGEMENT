#!/usr/bin/env python3
"""Run mobile Lighthouse audits across all 6 EcoSort routes and export scores.

Routes audited:
- /
- /about
- /scan/<id>
- /model
- /insights
- /history
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = REPO_ROOT / "ml" / "reports" / "lighthouse_m9.json"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Fetch or verify a valid scan ID from backend
def get_sample_scan_id() -> str:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/predictions?limit=1") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and "items" in data and len(data["items"]) > 0:
                return data["items"][0]["id"]
    except Exception as e:
        print(f"Failed to query backend predictions: {e}")
    # Fallback to known scanned id
    return "928ea886b904493c9d82a4f109db3086"


def run_audit(url: str, output_json: Path) -> dict:
    cmd = [
        "pnpm",
        "lighthouse",
        url,
        "--output=json",
        f"--output-path={output_json}",
        "--form-factor=mobile",
        "--screenEmulation.mobile=true",
        '--chrome-flags=--headless --no-sandbox',
        "--only-categories=performance,accessibility,best-practices,seo",
    ]
    print(f"Auditing {url}...")
    proc = subprocess.run(cmd, cwd=REPO_ROOT / "frontend", capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Error auditing {url}: {proc.stderr}")
        return {}

    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    cats = data["categories"]
    return {
        "performance": round(cats["performance"]["score"] * 100),
        "accessibility": round(cats["accessibility"]["score"] * 100),
        "best_practices": round(cats["best-practices"]["score"] * 100),
        "seo": round(cats["seo"]["score"] * 100),
    }


def main():
    scan_id = get_sample_scan_id()
    routes = [
        ("/", "/ (Home Viewfinder)"),
        ("/about", "/about (System & Dataset)"),
        (f"/scan/{scan_id}", f"/scan/{scan_id[:8]}... (Grad-CAM Result)"),
        ("/model", "/model (Model Comparison)"),
        ("/insights", "/insights (Municipal Insights)"),
        ("/history", "/history (Specimen History)"),
    ]

    results = {}
    tmp_out = Path("/tmp/lh_single_report.json")

    for path, label in routes:
        url = f"http://127.0.0.1:3000{path}"
        scores = run_audit(url, tmp_out)
        results[path] = {
            "label": label,
            "url": url,
            "scores": scores,
        }

    # Save to ml/reports/lighthouse_m9.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print markdown table
    print("\n" + "=" * 65)
    print("  Lighthouse Mobile Audit Summary (M9 Milestone)")
    print("=" * 65)
    print("| Route | Performance | Accessibility | Best Practices | SEO |")
    print("| :--- | :---: | :---: | :---: | :---: |")
    for path, data in results.items():
        s = data["scores"]
        print(f"| `{path}` | {s.get('performance', '-')} | {s.get('accessibility', '-')} | {s.get('best_practices', '-')} | {s.get('seo', '-')} |")
    print("=" * 65)
    print(f"Saved full audit JSON to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
