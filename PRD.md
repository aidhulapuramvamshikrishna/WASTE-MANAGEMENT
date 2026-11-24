# PRD.md — EcoSort: Municipal Waste Classification using CNN

**Type:** individual college project (B.Tech/BE final-year level) · **Framework:** PyTorch · **Status:** dataset ready, build not started

## 1. Problem
Since **1 April 2026**, India's Solid Waste Management Rules 2026 require households and institutions to separate waste at source into four streams: **wet, dry, sanitary and special care**. People often don't know which stream an item belongs to (a tetra pak, a used mask, a dead battery, a syringe), and mixed waste ruins composting and recycling. Municipal staff also have no simple data on what residents are throwing away.

## 2. Solution
A web app where a user photographs or uploads one waste item. A **CNN we trained ourselves** then:
1. identifies the **material** (12 classes),
2. maps it to the **SWM-2026 stream** and shows disposal instructions,
3. shows **why** it decided, with a Grad-CAM heatmap,
4. says "not sure" when confidence is low instead of guessing.

Scans and user corrections are stored and summarised on a municipal-style **insights dashboard**. A **model page** compares a from-scratch CNN with fine-tuned MobileNetV3 and EfficientNet-B0 using real test-set metrics.

## 3. Users
- **Resident/student:** "Which bin does this go in?"
- **Municipal/ward officer (demo persona):** "What are people scanning, and where does the model get it wrong?"
- **Examiner/faculty:** "Did you actually train and evaluate a model, and do you understand it?"

## 4. Scope
### Must have (MVP)
- M1 Three trained models: `wastenet` (custom CNN from scratch), `mobilenet_v3`, `efficientnet_b0`.
- M2 Evaluation on the held-out test set: accuracy, macro-F1, per-class P/R/F1, confusion matrix, stream-level accuracy, per-source accuracy, latency, model size.
- M3 Calibration: temperature scaling and an "uncertain" threshold tuned on the validation set.
- M4 FastAPI backend: predict, history, feedback, stats, models/metrics, health.
- M5 Next.js frontend: scanner (upload + camera), result with Grad-CAM, history, insights, model comparison, about.
- M6 Grad-CAM implemented by hand (hooks), not from a library.
- M7 Tests: pytest (ml + backend), Playwright smoke tests on every route, accessibility checks.

### Should have
- Model switcher in the UI (compare live predictions between models).
- Feedback export (CSV) for retraining, plus a documented retrain loop.
- PWA manifest so it installs on a phone.
- Hindi labels for stream names (i18n-ready strings).

### Won't do (explicitly out of scope)
- Calling any external AI or vision API.
- Multi-object detection (YOLO). Listed as future work.
- User accounts, logins, API keys or tokens. Admin actions only work from the local machine.
- Collecting real municipal data or locations.

## 5. Core user flows and acceptance criteria
**F1: Scan an item**
- Given the app is open, when I drop or pick a JPG/PNG/WebP ≤ 8 MB or take a camera photo, then within ~2 s on a laptop CPU I'm taken to `/scan/{id}`, which shows the label, stream, confidence, top-3 and disposal text.
- Non-image files, files that are too large, or corrupt files show a clear inline error. Nothing is saved.
- If `p_max < uncertain_threshold`, a banner says "Not sure — top guesses: …", and the stream badge is shown as tentative.

**F2: Understand the decision**
- The Grad-CAM overlay can be toggled or slid over the photo. The text explains what the heatmap means.

**F3: Correct the model**
- "Was this right?" Yes, or No → pick the correct class → saved (one per scan). The confirmation is visible.
- From the local machine, the user can download `feedback.csv` (via a link on `/insights`, shown only in development).

**F4: Browse history**
- `/history` shows scans newest first, can filter by stream, and links to each result.

**F5: Municipal insights**
- `/insights` shows stream share, scans per day, class counts, correction rate and top corrected pairs, all from real stored data, with empty states when there's none.

**F6: Model comparison**
- `/model` shows the three models side by side with metrics read from `metrics.json`, the confusion matrix, per-class F1, per-source accuracy and training curves.
- An untrained model shows "Not trained yet", never placeholder numbers.

## 6. Success metrics (targets, not results)
These are *goals*. The real numbers come only from `evaluate.py`:
- EfficientNet-B0 / MobileNetV3: test accuracy ≥ 85%, macro-F1 ≥ 0.82.
- wastenet (from scratch): ≥ 65% accuracy (it's a baseline; the gap is a finding, not a failure).
- Stream-level accuracy ≥ 92% for the best model.
- CPU latency p50 ≤ 150 ms per image for the best model (batch 1, laptop).
- Lighthouse accessibility ≥ 95 on `/` and `/model`.

## 7. Feature checklist vs industry (from research)
| Capability | AMP Robotics / Greyparrot / Recycleye / TOMRA (industrial) | EcoSort (ours) |
|---|---|---|
| Material recognition by camera + CNN | ✔ (conveyor belts at MRFs) | ✔ (single item, phone/laptop) |
| Robotic picking | ✔ | ✘ (out of scope) |
| Composition analytics dashboard | ✔ (Greyparrot) | ✔ (`/insights`, small-scale) |
| Household-level guidance | ✘ | ✔ **differentiator** |
| India SWM-2026 four-stream mapping | ✘ | ✔ **differentiator** |
| Explainability shown to the user (Grad-CAM) | ✘ (not user-facing) | ✔ **differentiator** |
| "I'm not sure" calibrated fallback | ? | ✔ |
| Feedback loop for retraining | internal | ✔ (CSV export + retrain doc) |

## 8. Risks
| Risk | Mitigation |
|---|---|
| Sanitary stream covered only by masks/gloves | Stated in the UI About page and the report; optional extra class from your own photos |
| Web-scraped images make test accuracy look too good | Report per-source accuracy; RealWaste/TrashNet subsets are the realistic number |
| Training too slow on a laptop | MobileNetV3 first; Colab GPU path in README; fewer epochs for wastenet |
| Agent invents metrics or UI numbers | AGENTS.md rule: no numbers that don't come from artifacts; verified in review |
