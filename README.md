# EcoSort: Municipal Waste Classification using CNN

Photograph one waste item, and a CNN **we trained ourselves** (PyTorch) identifies its material (12 classes), maps it to India's **Solid Waste Management Rules 2026** four streams (wet · dry · sanitary · special care), explains its decision with a hand-built **Grad-CAM** heatmap, and says "not sure" when confidence is low.

> Individual college project · non-commercial academic use (see dataset licences in DATASET.md)

## Status
| Milestone | Description | Status |
|---|---|---|
| **M0–M1** | Scaffolding, EDA, and data pipeline (18,951 images, 12 classes) | ✅ Completed |
| **M2–M3** | CNN training: WasteNet (scratch), MobileNetV3, EfficientNet-B0 | ✅ Completed |
| **M4** | Evaluation, temperature scaling calibration, Grad-CAM hooks, model cards | ✅ Completed |
| **M5** | FastAPI backend, SQLite telemetry, rate limiting, and security hardening | ✅ Completed |
| **M6** | Next.js App Router frontend foundation, tokens, and offline fonts | ✅ Completed |
| **M7** | Viewfinder scanner, Grad-CAM interactive compare slider, and feedback | ✅ Completed |
| **M8** | History contact sheet, Insights charts, and Model diagnostic tabs | ✅ Completed |
| **M9** | Production hardening, offline build, report figures, and demo rehearsal | ✅ Completed |

## Run It in 3 Commands

Start the full system locally without manual configuration:

```bash
# 1. Start the FastAPI backend (terminal 1)
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000

# 2. Build and launch the production Next.js frontend (terminal 2)
cd frontend && pnpm build && pnpm start

# 3. Open the web instrument in your browser
open http://localhost:3000
# Alternatively, launch the automated demo runner: ./scripts/demo.sh
```

## 3-Minute Examiner Demonstration Script

Follow this structured rehearsal flow during the college project presentation:

1. **System Initialization (0:00 – 0:30):**
   - Cold start FastAPI backend (`:8000`) and Next.js production frontend (`:3000`). Show `http://localhost:8000/health/ready` returning `{"status": "ready"}` with eager model discovery.
2. **Scanner & Specimen Wall (0:30 – 1:15):**
   - Open `http://localhost:3000`. Point out the industrial field-instrument design (condensed Archivo display, mono telemetry, 4-stream color system, zero AI slop).
   - Click a confident dry-recyclable specimen (e.g. `cardboard` or `plastic`). Show instantaneous local CPU inference (~55 ms) and transition to `/scan/[id]`.
3. **Grad-CAM Explainability & Feedback (1:15 – 2:00):**
   - On the result page, drag the **Grad-CAM inspection slider** between raw photo and attention heatmap.
   - Explain how the CNN localized material-distinguishing features (corrugation, edges) rather than background noise.
   - Submit user feedback (confirming label correctness) and show instant persistence into SQLite.
4. **Safety Mechanisms & Uncertainty Flagging (2:00 – 2:30):**
   - Scan a hazardous item (`battery`) to show immediate mapping to the **Special Care** stream with safe disposal protocol.
   - Scan an ambiguous specimen to demonstrate the **Uncertainty Banner** ($threshold = 0.585$), flagging items for manual sorting rather than hallucinating classification.
5. **Model Evaluation & Research Transparency (2:30 – 3:00):**
   - Navigate to `/model`. Show the 3-architecture empirical comparison, McNemar hypothesis testing significance callouts ($p < 10^{-90}$ for MobileNet vs scratch), row-normalized confusion matrix, and calibration reliability diagram (ECE reduced from 14.5% to 7.9%).

## Results

<!-- RESULTS_START -->
| Metric | WasteNet (Scratch) | MobileNetV3-Large (Transfer) | EfficientNet-B0 (Transfer) |
| :--- | :--- | :--- | :--- |
| **Architecture** | Custom 5-Block CNN | MobileNetV3-Large | EfficientNet-B0 |
| **Pretrained Weights** | None (Kaiming init) | ImageNet-1K V2 | ImageNet-1K V1 |
| **Parameters** | 3,391,212 | 4,217,404 | 4,022,920 |
| **Model Size** | 13.0 MB | 16.3 MB | 15.6 MB |
| **Test Accuracy** | 75.87% | **92.44%** | 91.45% |
| **Test Macro-F1** | 74.41% | **91.81%** | 90.63% |
| **95% CI (Accuracy)** | [74.4%, 77.5%] | [91.4%, 93.4%] | [90.4%, 92.4%] |
| **95% CI (Macro-F1)** | [72.7%, 76.0%] | [90.7%, 92.8%] | [89.5%, 91.7%] |
| **Top-3 Accuracy** | 92.16% | 98.52% | 98.07% |
| **Stream Accuracy (4 streams)** | 88.32% | **97.75%** | 96.73% |
| **Hazard Miss Rate** | 17.36% (117/674) | **3.12%** (21/674) | 3.12% (21/674) |
| **Coverage @ Threshold** | 66.1% (thr=0.62) | 96.0% (thr=0.40) | 96.5% (thr=0.40) |
| **Accuracy @ Threshold** | 90.04% | 94.61% | 93.26% |
| **CPU Latency (p50 / p95)** | 8.5 ms / 10.5 ms | 55.5 ms / 58.7 ms | 115.4 ms / 134.9 ms |
<!-- RESULTS_END -->

## Tech stack
| Layer | Choice | Why |
|---|---|---|
| ML | PyTorch + torchvision | in the syllabus; full control for the from-scratch CNN and the hand-written Grad-CAM |
| Models | `wastenet` (custom CNN from scratch), MobileNetV3-Large, EfficientNet-B0 (fine-tuned) | baseline vs transfer learning comparison; both transfer models are light enough for CPU inference |
| Backend | FastAPI, SQLModel/SQLite, Pillow, slowapi | async, typed, auto docs at `/docs`; zero-ops DB |
| Frontend | Next.js 15, TypeScript, Tailwind v4, shadcn/ui, Recharts | modern, accessible components; server-rendered report pages |
| Testing | pytest, Playwright, axe-core, Lighthouse | Verification suite (unit, e2e, a11y, performance) |

## Repository map
See `ARCHITECTURE.md` §2. Key docs: `PRD.md` (what and why), `ARCHITECTURE.md` (how), `DATASET.md` (data), `SECURITY.md`, `DESIGN.md`, `implementation_plan.md`, `DECISION_LOG.md` (project memory).

## Quickstart (once built)
```bash
# No config needed: everything runs locally with built-in defaults.
# (Optional: cp .env.example .env to change ports/paths.)
# 1) ML
cd ml && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m wasteml.train --config configs/mobilenet_v3.yaml
python -m wasteml.calibrate --model mobilenet_v3 && python -m wasteml.evaluate --model mobilenet_v3
# 2) API → http://localhost:8000/docs
cd ../backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ../ml
uvicorn app.main:app --reload --port 8000
# 3) Web → http://localhost:3000
cd ../frontend && pnpm install && pnpm dev
```

## Train on Google Colab (if your laptop is slow)
1. Zip `data/processed/waste12` and the `ml/` folder, then upload both to Google Drive.
2. In Colab (GPU runtime): mount Drive, unzip, `pip install -e ml`, set `WASTE_DATA_DIR`, and run the same `python -m wasteml.train ...` commands.
3. Download `ml/artifacts/<model>/` back into the repo. The backend picks it up automatically.

## Dataset
18,951 images merged from RealWaste, TrashNet, Garbage Classification (12 classes) and TrashBox, then de-duplicated and split 70/15/15. Full details, citations and limitations are in `DATASET.md`. Rebuild with `scripts/build_dataset.py`.

## Credits
Dataset authors as cited in `DATASET.md`. ImageNet-pretrained weights from torchvision.
