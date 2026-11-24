#!/usr/bin/env python3
"""EcoSort Demo Rehearsal Checklist & Timing Benchmark (M9 Milestone).

Executes and times each step of the 3-minute examiner demonstration:
1. Cold start of both servers (FastAPI backend + Next.js production frontend)
2. Scan 1: Confident item (cardboard)
3. Scan 2: Uncertain item (specimen below ui_uncertain_threshold)
4. Scan 3: Hazardous item (battery -> Special Care stream)
5. Grad-CAM inspection slider: fetch both original photo and attention heatmap
6. Feedback submission: submit agreement into database
7. Model page diagnostics: retrieve model cards and metrics
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = REPO_ROOT / "frontend" / "public" / "samples"


def wait_for_url(url: str, timeout: float = 30.0) -> float:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if resp.status == 200:
                    return time.perf_counter() - t0
        except Exception:
            pass
        time.sleep(0.2)
    raise TimeoutError(f"URL {url} did not become ready within {timeout}s")


def post_multipart_predict(image_path: Path, model: str = "mobilenet_v3") -> tuple[dict, float]:
    boundary = "----WebKitFormBoundaryRehearsalDemo"
    with open(image_path, "rb") as f:
        img_data = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{image_path.name}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: image/jpeg\r\n\r\n")
    body.extend(img_data)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="model"\r\n\r\n')
    body.extend(f"{model}\r\n".encode("utf-8"))
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        "http://127.0.0.1:3000/api/v1/predict",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        elapsed = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        return data, elapsed


def main():
    print("=" * 65)
    print("  EcoSort Demo Rehearsal & Timing Verification (M9)")
    print("=" * 65)

    timings = {}
    total_start = time.perf_counter()

    # Step 1: Cold start backend
    print("\n[Step 1a] Cold starting FastAPI backend on port 8000...")
    t0_be = time.perf_counter()
    uvicorn_bin = str(REPO_ROOT / "backend" / ".venv" / "bin" / "uvicorn")
    backend_proc = subprocess.Popen(
        [uvicorn_bin, "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=REPO_ROOT / "backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        be_time = wait_for_url("http://127.0.0.1:8000/api/v1/health/ready", timeout=20.0)
        timings["1a. Backend Cold Start"] = be_time
        print(f"  Backend ready in {be_time:.2f}s")

        # Step 1b: Cold start frontend
        print("\n[Step 1b] Cold starting Next.js production frontend on port 3000...")
        env = os.environ.copy()
        env["NODE_ENV"] = "production"
        frontend_proc = subprocess.Popen(
            ["pnpm", "start"],
            cwd=REPO_ROOT / "frontend",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            fe_time = wait_for_url("http://127.0.0.1:3000/", timeout=25.0)
            timings["1b. Frontend Cold Start"] = fe_time
            print(f"  Frontend ready in {fe_time:.2f}s")

            # Step 2: Confident Scan (cardboard)
            print("\n[Step 2] Executing Confident Scan (cardboard_1.jpg)...")
            cardboard_sample = SAMPLES_DIR / "cardboard_1.jpg"
            res_conf, t_conf = post_multipart_predict(cardboard_sample)
            timings["2. Confident Scan (cardboard)"] = t_conf
            print(f"  Result: Class={res_conf['label']}, Stream={res_conf['stream']}, Conf={res_conf['confidence']*100:.1f}%, Uncertain={res_conf['uncertain']} (Time: {t_conf*1000:.1f}ms)")
            assert res_conf["stream"] == "dry", f"Expected dry, got {res_conf['stream']}"
            pred_id_conf = res_conf["id"]

            # Step 3: Uncertain Scan (uncertain_sample.jpg)
            print("\n[Step 3] Executing Uncertain Scan (uncertain_sample.jpg)...")
            uncertain_sample = SAMPLES_DIR / "uncertain_sample.jpg"
            res_unc, t_unc = post_multipart_predict(uncertain_sample)
            timings["3. Uncertain Scan (safety gate)"] = t_unc
            print(f"  Result: Class={res_unc['label']}, Conf={res_unc['confidence']*100:.1f}%, Uncertain={res_unc['uncertain']} (Time: {t_unc*1000:.1f}ms)")
            assert res_unc["uncertain"] is True, f"Expected uncertain, got {res_unc['uncertain']}"

            # Step 4: Hazardous Scan (battery_1.jpg -> Special Care)
            print("\n[Step 4] Executing Hazardous Item Scan (battery_1.jpg)...")
            battery_sample = SAMPLES_DIR / "battery_1.jpg"
            res_haz, t_haz = post_multipart_predict(battery_sample)
            timings["4. Hazardous Scan (battery)"] = t_haz
            print(f"  Result: Class={res_haz['label']}, Stream={res_haz['stream']}, Conf={res_haz['confidence']*100:.1f}% (Time: {t_haz*1000:.1f}ms)")
            assert res_haz["stream"] == "special_care", f"Expected special_care, got {res_haz['stream']}"

            # Step 5: Grad-CAM slider image requests
            print("\n[Step 5] Fetching Grad-CAM Heatmap & Original Image...")
            t0_cam = time.perf_counter()
            with urllib.request.urlopen(f"http://127.0.0.1:3000/api/v1/predictions/{pred_id_conf}/image") as r1:
                assert r1.status == 200 and len(r1.read()) > 0
            with urllib.request.urlopen(f"http://127.0.0.1:3000/api/v1/predictions/{pred_id_conf}/gradcam") as r2:
                assert r2.status == 200 and len(r2.read()) > 0
            t_cam = time.perf_counter() - t0_cam
            timings["5. Heatmap & Photo Fetch"] = t_cam
            print(f"  Both original photo & heatmap delivered in {t_cam*1000:.1f}ms")

            # Step 6: User Feedback Submission
            print("\n[Step 6] Submitting User Feedback...")
            fb_payload = json.dumps({"correct_class": res_conf["label"], "comment": "Verified during demo"}).encode("utf-8")
            fb_req = urllib.request.Request(
                f"http://127.0.0.1:3000/api/v1/predictions/{pred_id_conf}/feedback",
                data=fb_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            t0_fb = time.perf_counter()
            with urllib.request.urlopen(fb_req) as fb_resp:
                assert fb_resp.status == 201
            t_fb = time.perf_counter() - t0_fb
            timings["6. Feedback Submission"] = t_fb
            print(f"  Feedback persisted in {t_fb*1000:.1f}ms (HTTP 201 Created)")

            # Step 7: Model Diagnostics Page & Metrics API
            print("\n[Step 7] Accessing /model Page & Model Metrics...")
            t0_mod = time.perf_counter()
            with urllib.request.urlopen("http://127.0.0.1:3000/model") as r_page:
                assert r_page.status == 200
            with urllib.request.urlopen("http://127.0.0.1:3000/api/v1/models/mobilenet_v3/metrics") as r_met:
                assert r_met.status == 200
            t_mod = time.perf_counter() - t0_mod
            timings["7. Model Diagnostics Navigation"] = t_mod
            print(f"  Model page & metrics API served in {t_mod*1000:.1f}ms")

        finally:
            frontend_proc.terminate()
            frontend_proc.wait(timeout=5)
    finally:
        backend_proc.terminate()
        backend_proc.wait(timeout=5)

    total_time = time.perf_counter() - total_start
    timings["Total Demonstration Runtime"] = total_time

    print("\n" + "=" * 65)
    print("  Demo Rehearsal Timing Summary")
    print("=" * 65)
    for step, sec in timings.items():
        if "Total" in step:
            print("-" * 65)
            print(f"  {step:38s}: {sec:.2f}s (Target: < 180s / 3 min)")
        elif sec < 1.0:
            print(f"  {step:38s}: {sec*1000:6.1f} ms")
        else:
            print(f"  {step:38s}: {sec:6.2f} s")
    print("=" * 65)

    # Save rehearsal log to ml/reports/demo_rehearsal.json
    out_file = REPO_ROOT / "ml" / "reports" / "demo_rehearsal.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(timings, f, indent=2)
    print(f"Saved rehearsal report to: {out_file}\n")


if __name__ == "__main__":
    main()
