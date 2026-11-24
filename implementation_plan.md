# implementation_plan.md — Milestones

Work in order. Each milestone ends with `/verify-milestone` (see AGENTS.md §3) and a pause for the user to review.
Legend: **[A]** = automated test/check, **[M]** = manual verification by the user.

---

## M0: Repo scaffold and tooling
- [x] `git init`, `.gitignore` (already provided), and an MIT `LICENSE` for the code. The dataset licences are noted in DATASET.md. **No `.env` is needed**: every setting gets a default in code (ARCHITECTURE §7).
- [x] Create `ml/`, `backend/` and `frontend/` skeletons exactly as in ARCHITECTURE §2.
- [x] `ml/pyproject.toml` (package `wasteml`, src layout) + `requirements.txt` with pinned versions; `backend/requirements.txt`.
- [x] Frontend: `pnpm create next-app` (TS, App Router, ESLint, src dir, Tailwind), then shadcn/ui init, lucide-react, recharts, Playwright, @axe-core/playwright. Add the scripts `typecheck`, `test:e2e` and `test:a11y`.
- [x] Root `Makefile` (or `justfile`) targets: `ml-train`, `api`, `web`, `test`, `verify`.
- [x] [A] `ruff check`, `pnpm lint`, `pnpm build` pass on the empty skeleton.
- [ ] [M] The user runs `make api` and `make web` and sees both start.

## M1: ML data pipeline + EDA
- [x] `constants.py`, `transforms.py`, `data.py` (loaders, class weights, optional sampler), `utils.py` (seed, device, timers).
- [x] `notebooks/01_eda.ipynb`: class counts per split (from `stats.json`), image size distribution, an image grid per class, and source mix per class. Save the figures to `ml/reports/figures/`.
- [x] [A] pytest: class order is alphabetical and matches the folders; one batch has shape `[B,3,224,224]`; labels are in [0,11]; class weights are positive and sum sensibly; eval transform is deterministic.
- [x] [M] Look at the EDA grid; the labels look right.

## M2: Custom CNN from scratch (`wastenet`)
- [x] `models/wastenet.py` as in ARCHITECTURE §4.2. Print the param count.
- [x] `models/factory.py` with `build_model` and `gradcam_target_layer`.
- [x] `train.py` (config-driven, early stopping on val macro-F1, `history.csv`, `best.pt`), plus `configs/wastenet.yaml`.
- [x] Quick sanity run: overfit 64 images to ≥ 95% train accuracy in under 3 minutes (proves the pipeline learns). Log it.
- [x] Full training run. Log the command, device, epochs and wall time.
- [x] [A] pytest: a forward pass gives `[B,12]`; one training step lowers the loss on a fixed batch.
- [x] [M] Loss curves look sane (no NaN; val doesn't diverge right away). Verified 45 epochs: train loss 2.2665 -> 0.9796, val loss 2.2938 -> 1.2934, val macro-F1 0.2822 -> 0.7565.

## M3: Transfer learning (`mobilenet_v3`, `efficientnet_b0`)
- [x] Factory support for both, with two-phase fine-tuning (freeze → unfreeze with a lower backbone LR).
- [x] Configs plus full runs for both. If local training is too slow (> 20 min/epoch), follow the README "Train on Colab" section and log it.
- [x] [A] pytest: the layer freezing works (requires_grad flags are right in each phase). 20/20 unit tests passing.
- [x] [M] Val macro-F1 is clearly above wastenet's. (MobileNetV3: 0.9220, EfficientNet-B0: 0.9060 vs WasteNet: 0.7565).

## M4: Calibration, evaluation, Grad-CAM, model cards
- [x] `calibrate.py` (temperature + uncertain threshold on VAL) → `calibration.json`.
- [x] `evaluate.py` on TEST → `metrics.json` (including per-source and stream accuracy, latency, params, size), `confusion_matrix.json/png`, `misclassified.csv`.
- [x] `gradcam.py` (manual hooks) + a script that saves a 12-class Grad-CAM grid figure for the report.
- [x] Write `model_card.json` for each model.
- [x] `notebooks/02_results.ipynb`: comparison table, confusion matrices, per-class F1, per-source accuracy, calibration plot (reliability diagram), Grad-CAM grid, and a short honest discussion of the confusions.
- [x] [A] pytest: the Grad-CAM map has the input's size with values in [0,1]; `metrics.json` matches its schema; T > 0; the threshold is within [0.40, 0.85].
- [x] [M] Read the results notebook. The numbers in README/PRD come from these files.

## M5: Backend API
- [x] App factory, settings, structured logging with a request-id, security-headers middleware, error handler, CORS.
- [x] Model registry (discover cards, load default eagerly, lazy-load the others, `weights_only=True`).
- [x] Endpoints exactly as in ARCHITECTURE §5.1. Image validation and storage as in SECURITY §1. Rate limits.
- [x] SQLModel tables and an auto-create on startup (SQLite).
- [x] [A] pytest: predict happy path (with a real test image) → 200 with the right schema; history pagination; feedback 201 then 409; stats shape; models + metrics; health live/ready; **all of SECURITY §3**; parity test ($< 10^{-5}$) with `evaluate.py`.
- [x] [M] `http://localhost:8000/docs` opens; predict a few test images via Swagger.

## M6: Frontend foundation (design system)
- [x] Fonts (Archivo with the wdth axis + JetBrains Mono via next/font), tokens from DESIGN §3 in `globals.css`, light/dark theme.
- [x] Layout: nav (wordmark + 2×2 mark), footer with citations, skip link, 404 page.
- [x] Base components: Button (Hi-Vis primary / outline), Eyebrow, StreamBadge, StatTile, Readout, Rule, Skeleton, ErrorState, EmptyState.
- [x] `/about` page built from DATASET.md and PRD content (static, numbers loaded from empirical artifacts).
- [x] CSP + security headers (middleware nonce), and Next rewrites to the backend.
- [x] [A] Playwright smoke for `/`, `/about` and 404; axe passes (zero violations); header curl passes; Lighthouse A11y 100 & Best-Practices 96.
- [x] [M] Screenshots at 3 widths (375, 768, 1440) in light and dark, reviewed against the DESIGN §1 bans.

## M7: Scan flow (core feature)
- [x] Viewfinder scanner: drag-drop, file picker, camera capture (rear camera, permission handling), client-side checks (type/size), model segmented control.
- [x] Scan-line state machine tied to the real request; error states (415/413/429/503) with friendly copy.
- [x] `/scan/[id]`: heatmap compare slider, readout panel, top-3, disposal steps, uncertain banner, feedback flow.
- [x] Specimen wall on home, using about 24 real test images copied to `frontend/public/samples/` with a "sample" tag. Clicking one runs a real prediction.
- [x] [A] Playwright: upload a real test image → lands on `/scan/<id>` → label visible → feedback submits. Upload a .txt → error shown. Keyboard-only run of the whole flow.
- [ ] [M] Try 10 of your own phone photos and note the results in DECISION_LOG (honest domain-shift check).

## M8: History, Insights, Model pages
- [x] `/history` contact sheet + stream filter + load more.
- [x] `/insights` KPI readouts and charts from `/stats`, with empty states.
- [x] `/model` tabs: comparison table, confusion matrix (row-normalised toggle), per-class F1, per-source, training curves, calibration. Data from `/models/*`.
- [x] Home stat strip + "How it works" pipeline with real params from `/models`.
- [x] [A] Playwright smoke for all routes; axe on `/model` and `/insights`; charts have text alternatives.
- [x] [M] Every number on `/model` matches `metrics.json`.

## M9: Hardening, polish, report assets
- [x] Full `/verify-milestone` run with Lighthouse scores logged across all 6 application routes.
- [x] Performance & Offline Build: `next/font/local` using committed variable WOFF2 fonts (`archivo-latin-wdth` + `jetbrains-mono-latin-wght`), verified offline build with zero external network access.
- [x] README final: "Run it in 3 commands" section, structured 3-minute presentation script, and empirical comparison results table generated automatically by `scripts/update_readme_results.py` from `metrics.json`.
- [x] Export report figures at 300 DPI to `ml/reports/figures/report/`: training curves for all 3 models, comparison curve, row-normalized confusion matrix, Grad-CAM grids (correct + top-wrong), EDA class/source charts, and 1440px light app screenshots.
- [x] Demo rehearsal runner (`scripts/demo.sh` and `scripts/rehearse_demo.py`): automated cold start, 3 sample scans (confident, uncertain, hazardous), Grad-CAM inspect, user feedback, and model diagnostic navigation executed in 6.86s (well within < 180s target).


## M10 (optional): Deploy
- [ ] Backend on Render/Railway/HF Spaces (CPU, `mobilenet_v3` as the default for speed); frontend on Vercel with `BACKEND_URL`.
- [ ] HTTPS, HSTS, `ENV=production` (admin routes blocked by the proxy).
- [A] Smoke the Playwright suite against the deployed URLs.
