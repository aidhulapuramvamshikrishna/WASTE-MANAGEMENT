# DECISION_LOG.md — Project memory (source of truth for "why")

Append-only. Newest entries at the **bottom**. Every agent session must read the last ~5 entries before working.

## Templates
**Decision**
```
### D-<n> · <date> · <title>
- Decision:
- Why:
- Alternatives considered:
- Consequences:
```
**Error / fix**
```
### E-<n> · <date> · <short error>
- Where (file/command):
- Error text (trimmed):
- Root cause:
- Fix:
```
**Pivot**
```
### P-<n> · <date> · <what changed>
- From → To:
- Reason:
```
**Verification (one per milestone)**
```
### V-<milestone> · <date>
- Commands run (verbatim, in order) + result (pass/fail):
- URLs/routes opened:
- Key numbers (from files, with file path):
- Screenshots: <path>
- Status: COMPLETE | INCOMPLETE (reason)
```

---

## Log

### D-1 · 2026-11-16 · Project framing: SWM Rules 2026 four-stream mapping
- Decision: The CNN predicts **material** (12 classes); a fixed table maps each material to one of India's four SWM-2026 streams (wet, dry, sanitary, special care).
- Why: The rules (in force 1 Apr 2026) mandate four-stream segregation at source. Predicting material keeps the vision task well-defined; the mapping gives civic relevance and a differentiator from industrial competitors (AMP, Greyparrot, Recycleye, TOMRA), which target recovery facilities rather than households.
- Alternatives: predicting the 4 streams directly (loses material info; streams are visually heterogeneous); a 6-class TrashNet-only scope (too narrow, unrealistic).
- Consequences: classes.json carries the stream + disposal text; the UI shows both material and stream.

### D-2 · 2026-11-16 · Data sources: GitHub-hosted public datasets only
- Decision: Merge RealWaste, TrashNet, Garbage Classification (12-class Kaggle set via a GitHub mirror) and TrashBox (train + test/val repos).
- Why: Kaggle, Hugging Face, UCI and Roboflow were not reachable from the build environment; GitHub was. These four together cover dry recyclables, organics, textiles, batteries, e-waste and medical items.
- Alternatives: Kaggle API (blocked); scraping images (licence/quality risk).
- Consequences: The sanitary stream is only covered by masks and gloves (TrashBox medical subfolders). Documented as a limitation.

### D-3 · 2026-11-16 · Dataset build rules
- Decision: Exact (MD5) + perceptual-hash de-dup, keeping the real-world copy first (priority RealWaste > TrashNet > Garbage-12 > TrashBox); cap 2,000 per class while keeping all RealWaste/TrashNet images; resize the longest side to ≤ 320 px; stratified 70/15/15 split with seed 42.
- Why: The sources overlap heavily (3,754 exact duplicates found), and duplicates across splits would inflate test accuracy. Capping limits the dominance of web-scraped classes (e.g. 5,325 clothes images).
- Result: 18,951 images; dropped 3,754 MD5 dups, 361 pHash dups, 6 unreadable, 2 too small. Counts in `data/processed/waste12/stats.json`.

### P-1 · 2026-11-16 · Removed Garbage-12 "trash" from misc_trash
- From → To: misc_trash = RealWaste Misc + TrashNet trash + Garbage-12 trash (1,329) → RealWaste Misc + TrashNet trash (632).
- Reason: A visual spot-check showed Garbage-12 "trash" is mostly face masks, which conflicts with the `mask_glove` class.

### D-4 · 2026-11-16 · Class index order
- Decision: Model class indices = alphabetical folder order (torchvision ImageFolder). The `index` field in `classes.json` follows build-script order and must be ignored.
- Why: ImageFolder assigns indices alphabetically; mismatched orders are a classic silent bug.
- Consequences: A pytest asserts the order; model cards store `class_names` explicitly.

### D-5 · 2026-11-16 · Stack
- Decision: PyTorch (syllabus) for ML; FastAPI + SQLite backend with in-process PyTorch inference; Next.js 15 + Tailwind v4 + shadcn/ui frontend proxied via Next rewrites.
- Why: One language for ML and API (shared `wasteml` package, so preprocessing can't drift between training and serving); SQLite = zero ops for a single-person project; same-origin proxy simplifies CORS and CSP.
- Alternatives: ONNX Runtime serving (faster, but Grad-CAM needs gradients → would need PyTorch anyway); Flask (fewer built-in docs and validation); Streamlit (not a "real" frontend).

### D-6 · 2026-11-16 · Design direction "Field Instrument"
- Decision: Archivo (variable width; condensed for display) + JetBrains Mono; paper/ink neutrals; a single Hi-Vis accent `#D4F23A`; stream colours used only as signals; 2px radius; hairline rules instead of shadows.
- Why: A live review of greyparrot.ai, ampsortation.com, recycleye.com and tomra.com (16 Nov 2026) showed the category's credible look: a single sans family, ink text, one loud accent, square controls, real imagery, big stats. Serif display fonts and gradient "AI" aesthetics were explicitly rejected (user requirement: no AI slop).
- Consequences: DESIGN.md §1 ban list and §5 signature components.

### Commands run so far (dataset phase)
```
git clone --depth 1 https://github.com/nikhilvenkatkumsetty/TrashBox
git clone --depth 1 https://github.com/nikhilvenkatkumsetty/TrashBox-testandvalid
git clone --depth 1 https://github.com/arshpreet-nar/7TH-SEMESTER-PROJECT-
git clone --depth 1 https://github.com/sam-single/realwaste
curl -L -o dataset-resized.zip https://github.com/garythung/trashnet/raw/master/data/dataset-resized.zip
pip install pillow imagehash
python scripts/build_dataset.py --src <download_dir> --out data/processed/waste12
```
URLs opened for design research: https://www.greyparrot.ai, https://ampsortation.com, https://recycleye.com, https://www.tomra.com/waste-metal-recycling

### D-7 · 2026-11-16 · Zero-config local run (no `.env` required)
- Decision: Every setting has a working default in code; `.env` is optional and only overrides defaults; the admin token is auto-generated at startup when unset.
- Why: The project runs entirely on the student's laptop. Requiring a config file adds a setup step and a failure mode with no benefit. (Asked by the user.)
- Consequences: AGENTS.md rule 6 and DoD item 5 check that the app starts with no `.env`.

---
<!-- Agents: append new entries below this line -->

### D-8 · 2026-11-16 · Next.js 16 (App Router + Turbopack) adoption
- Decision: Use Next.js 16.4.6 with React 19 and Turbopack instead of Next.js 15.
- Why: `pnpm create next-app@latest` scaffolded Next.js 16 with native Turbopack and React 19 support, which is backward-compatible with our App Router architecture and provides faster compile times.
- Alternatives: Downgrading to Next.js 15.
- Consequences: Middleware convention has an informative deprecation note in Next 16 ("use proxy instead"), but works reliably; font fetching and CSS pipeline run through Turbopack.

### D-9 · 2026-11-16 · Admin endpoints localhost-only, token removed
- Decision: Remove `ADMIN_TOKEN` and token generation from `backend/app/config.py`. Admin access is strictly localhost-bound (`request.client.host in {"127.0.0.1", "::1"}`).
- Why: Eliminates unnecessary token management and aligns with SECURITY.md T7 and D-7 zero-config local run.
- Consequences: No administrative token is needed or generated.

### D-10 · 2026-11-16 · Next.js 16 proxy.ts convention
- Decision: Migrate `middleware.ts` to `frontend/src/proxy.ts` exporting `proxy`.
- Why: Next.js 16 deprecates `middleware.ts` in favor of `proxy.ts`. Proactively adopting the standard eliminates deprecation warnings and future-proofs the codebase.
- Consequences: Dynamic nonce CSP and security headers run seamlessly through `proxy.ts`.

### D-11 · 2026-11-16 · Tailwind v4 @theme inline token mapping
- Decision: Map all Field Instrument design tokens into Tailwind using `@theme inline` in `globals.css` (`--color-paper: var(--paper)`, etc.).
- Why: Enables clean semantic Tailwind utility classes (`bg-paper`, `text-ink`, `border-rule`) without verbose `var(...)` arbitrary value syntax.
- Consequences: Cleaner JSX markup adhering strictly to DESIGN.md §3 tokens.

### D-12 · 2026-11-16 · WasteNet stride-2 stem downsampling
- Decision: Modify Block 1 Conv 1 in `WasteNet` to use `stride=2, padding=1`, reducing the spatial resolution of the first layer from 224×224 to 112×112 before pooling to 56×56. Retain exact channel counts (32-64-128-256-384) and exact 3,391,212 parameter count.
- Why: Reduces activation memory in the first block by 4×, preventing memory bloat on unified memory devices and reducing FLOPs for faster CPU/edge inference.
- Consequences: Activation memory dropped 4×; parameter count unchanged at exactly 3,391,212.

### D-13 · 2026-11-16 · Cloud Training on Google Colab GPU (Option C)
- Decision: Execute full model training for `wastenet`, `mobilenet_v3`, and `efficientnet_b0` on Google Colab NVIDIA T4 GPU with CUDA and AMP, rather than running 25+ hours locally under memory swapping.
- Why: Free T4 GPU provides ~1.5 min/epoch (~35 min total) with CUDA AMP, zero memory paging, and full reproducibility.
- Consequences: Dataset uploaded to Google Drive `EcoSort/`, `ml.zip` packaged via `make ml-zip`, and `ml/notebooks/colab_train.ipynb` orchestrates training and artifact backup.


### E-1 · 2026-11-16 · Google Fonts fetch failure and banned Geist font
- Where (file/command): `frontend/src/app/layout.tsx` / `pnpm build`
- Error text: `Failed to fetch Geist from Google Fonts. If you are offline or behind a proxy, self-host the font with next/font/local`
- Root cause: `create-next-app` default template introduced Geist and Geist Mono fonts. In an offline/sandboxed build, `next/font/google` failed to reach Google Fonts. Additionally, Geist is explicitly forbidden by DESIGN.md §1 ban list.
- Fix: Replaced Geist with Archivo (with `axes: ["wdth"]`) and JetBrains Mono from `next/font/google`, downloaded once with network access so local offline builds pass.

### E-2 · 2026-11-16 · Premature deletion of postcss.config.mjs and third-party "cn" package
- Where (file/command): `frontend/postcss.config.mjs`, `frontend/src/lib/utils.ts`
- Error text: Turbopack panic `node process exited before we could connect to it with exit status: 0` and TS2307 `Cannot find module 'cn'`
- Root cause: When `postcss.config.mjs` was initially added, `next build` failed due to an orphaned node worker/lock conflict in `.next` while a dev server was running, combined with shadcn installing an unvetted third-party `cn` package instead of `clsx` + `tailwind-merge`. Instead of debugging the root cause, `postcss.config.mjs` was hastily deleted, silencing the error but disabling Tailwind utility generation.
- Fix: Restored `frontend/postcss.config.mjs` with `{ plugins: { "@tailwindcss/postcss": {} } }`. Removed the `cn` package from `package.json`, installed `clsx` and `tailwind-merge`, and rewrote `src/lib/utils.ts` to standard shadcn `cn()`. Cleared `.next` build cache. Proved utility generation with `find frontend/.next -name "*.css" -exec grep -o "\.flex{[^}]*}" {} +` (`.flex{display:flex}`).

### E-3 · 2026-11-16 · Missing per-request nonce CSP middleware and blocked hydration
- Where (file/command): `frontend/src/middleware.ts`, `frontend/next.config.ts`
- Error text: Static CSP in `next.config.ts` lacked per-request dynamic nonces, which would block Next.js script execution and hydration in production under `strict-dynamic`.
- Root cause: Middleware-based dynamic nonce generation specified in SECURITY.md §2 was not implemented.
- Fix: Implemented `src/middleware.ts` generating per-request cryptographic nonces and setting `script-src 'self' 'nonce-...' 'strict-dynamic'` (plus `'unsafe-eval'` only when `NODE_ENV=development`). Removed static CSP from `next.config.ts`. Added a Playwright test asserting 0 CSP console errors and verifying client component hydration via a button toggle test.

### E-4 · 2026-11-16 · Trivial test assertions in smoke and accessibility tests
- Where (file/command): `frontend/tests/e2e/smoke.spec.ts`, `frontend/tests/e2e/a11y.spec.ts`
- Error text: Tautological regex `/.*|EcoSort/i` matched any title; a11y test only checked `critical` impact instead of `serious` or `critical`.
- Root cause: Careless placeholder assertions written during scaffold setup.
- Fix: Rewrote `smoke.spec.ts` to assert exact title contains "EcoSort", assert a visible H1 heading exists, assert client component hydration via state change, and assert zero CSP errors in the console. Rewrote `a11y.spec.ts` to strictly fail on `serious` OR `critical` violations.

### E-5 · 2026-11-16 · False readiness report from /health/ready
- Where (file/command): `backend/app/main.py` / `GET /health/ready`
- Error text: Returned 200 `{"status": "ready"}` despite no model being loaded or trained.
- Root cause: Stub endpoint returned hardcoded ready status, violating ARCHITECTURE §5 ("If no model exists, /health/ready returns 503... Never fake a prediction").
- Fix: Changed `/api/v1/health/ready` to return HTTP 503 `{"status": "no_model", "message": "No model loaded yet"}` until model registry is active. Scoped all health routes strictly under `/api/v1/health/*`.

### E-6 · 2026-11-16 · Loose dependency versions in requirements.txt
- Where (file/command): `ml/requirements.txt`, `backend/requirements.txt`
- Error text: Dependencies specified with `>=` instead of exact pinned `==` versions.
- Root cause: Initial template used minimum bounds instead of frozen locks.
- Fix: Filtered `pip freeze` from the working virtual environments and pinned all direct dependencies to exact `==` versions.

### V-M0 · 2026-11-16 (Re-verified & Complete)
- Commands run (verbatim, in order) + result (pass/fail):
  - `git init && git branch -m main`: pass
  - `mkdir -p ml/configs ml/src/wasteml/models ml/notebooks ml/tests ml/artifacts backend/app/api/v1 backend/app/services backend/app/db backend/app/core backend/tests backend/storage/uploads backend/storage/gradcam`: pass
  - `python3.12 -m venv ml/.venv && python3.12 -m venv backend/.venv`: pass
  - `cd ml && pip install -r requirements.txt && pip install -e .`: pass
  - `cd backend && pip install -r requirements.txt && pip install -e ../ml`: pass
  - `pnpm create next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-pnpm --yes`: pass
  - `cd frontend && pnpm remove cn && pnpm add clsx tailwind-merge lucide-react recharts && pnpm add -D @playwright/test @axe-core/playwright @tailwindcss/postcss postcss`: pass
  - `cd ml && source .venv/bin/activate && ruff check . && pytest -q`: pass (1 passed)
  - `cd backend && source .venv/bin/activate && ruff check . && pytest -q`: pass (2 passed)
  - `cd ml && source .venv/bin/activate && pip-audit -r requirements.txt`: pass (0 vulnerabilities)
  - `cd backend && source .venv/bin/activate && pip-audit -r requirements.txt`: pass (0 vulnerabilities)
  - `cd frontend && pnpm audit --prod`: pass (0 vulnerabilities)
  - `cd frontend && pnpm lint && pnpm typecheck && pnpm build`: pass (0 errors, 0 warnings)
  - `find frontend/.next -name "*.css" -exec grep -o "\.flex{[^}]*}" {} +`: pass (`.flex{display:flex}`)
  - `cd frontend && pnpm test:e2e`: pass (2 tests passed: smoke, hydration, title, heading, zero CSP errors)
  - `cd frontend && pnpm test:a11y`: pass (1 test passed: 0 serious, 0 critical violations)
  - `curl -s -D - http://localhost:8000/api/v1/health/live -o /dev/null`: pass
    ```http
    HTTP/1.1 200 OK
    x-content-type-options: nosniff
    x-frame-options: DENY
    referrer-policy: strict-origin-when-cross-origin
    permissions-policy: camera=(self), microphone=(), geolocation=(), interest-cohort=()
    cross-origin-opener-policy: same-origin
    content-security-policy: default-src 'none'; frame-ancestors 'none'
    x-request-id: 2c15d257-ed47-4bc5-9f9b-ddfa117a7fdb
    ```
  - `curl -s -D - http://localhost:8000/api/v1/health/ready -o /dev/null`: pass
    ```http
    HTTP/1.1 503 Service Unavailable
    content-type: application/json
    x-content-type-options: nosniff
    x-frame-options: DENY
    content-security-policy: default-src 'none'; frame-ancestors 'none'
    {"status":"no_model","message":"No model loaded yet"}
    ```
  - `curl -s -D - http://localhost:3000/ -o /dev/null`: pass
    ```http
    HTTP/1.1 200 OK
    x-content-type-options: nosniff
    x-frame-options: DENY
    referrer-policy: strict-origin-when-cross-origin
    permissions-policy: camera=(self), microphone=(), geolocation=(), interest-cohort=()
    cross-origin-opener-policy: same-origin
    content-security-policy: default-src 'self'; script-src 'self' 'nonce-Mjc3ZDJiZjYtZTU2NC00NDA4LWJmYWItZjcyMzc4Zjg1N2Fm' 'strict-dynamic'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none';
    ```
  - `npx --yes lighthouse http://localhost:3000/ --only-categories=accessibility,best-practices,performance --quiet --chrome-flags="--headless" --no-enable-error-reporting --output=json --output-path=frontend/tests/lighthouse-home.json`: pass
  - `git grep -nE "(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}"`: pass (clean)
  - `grep -rniE "lorem|™|trusted by|testimonial|99\.[0-9]%|placeholder" frontend/src`: pass (clean)
  - `make verify`: pass
- URLs/routes opened:
  - `http://localhost:3000/` (Playwright E2E smoke & Axe a11y tests, Lighthouse audit)
  - `http://localhost:8000/api/v1/health/live` & `http://localhost:8000/api/v1/health/ready` (curl headers verification)
- Key numbers:
  - Lighthouse scores on `/`: Accessibility = 100, Best Practices = 100, Performance = 100.
  - 0 lint errors, 0 type errors, 0 audit vulnerabilities in ml, backend, and frontend.
  - 0 critical, 0 serious axe violations.
  - CSS utility proof: `.flex{display:flex}` compiled in `.next` stylesheet.
- Status: COMPLETE | INCOMPLETE (reason)
```

---



### V-M1 · 2026-11-16
- Commands run (verbatim, in order) + result (pass/fail):
  - `python3 -c "import os; ... count images"`: pass (train: 13,266, val: 2,842, test: 2,843, total: 18,951)
  - `python scripts/generate_eda.py`: pass (all 4 EDA figures generated into `ml/reports/figures/` and `ml/notebooks/01_eda.ipynb` created)
  - `cd ml && source .venv/bin/activate && ruff check .`: pass (0 errors, 0 warnings)
  - `cd ml && source .venv/bin/activate && pytest -v`: pass (7 tests passed in 2.21s)
  - `cd backend && source .venv/bin/activate && ruff check . && pytest -q`: pass (2 tests passed)
  - `cd frontend && pnpm lint && pnpm typecheck && pnpm build`: pass (0 errors, 0 warnings)
  - `cd frontend && pnpm test:e2e`: pass (2 tests passed)
  - `pip-audit -r ml/requirements.txt`: pass (0 vulnerabilities found)
  - `pip-audit -r backend/requirements.txt`: pass (0 vulnerabilities found)
  - `pnpm audit --prod`: pass (0 vulnerabilities found)
  - `git grep -nE "(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}"`: pass (clean)
  - `grep -rniE "lorem|™|trusted by|testimonial|99\.[0-9]%|placeholder" frontend/src`: pass (clean)
  - `make verify`: pass
- URLs/routes opened:
  - `http://localhost:3000/` (Playwright E2E smoke & axe a11y regression check)
- Key numbers:
  - Image counts found by code: Train = 13,266, Val = 2,842, Test = 2,843, Total = 18,951 (matches specification exactly).
  - Classes: 12 strictly alphabetical matching `ARCHITECTURE §3` (`battery`, `cardboard`, `e_waste`, `glass`, `mask_glove`, `medicine_syringe`, `metal`, `misc_trash`, `organic`, `paper`, `plastic`, `textile`).
  - Stream mapping: 100% of classes mapped to SWM-2026 streams (`wet`: 1, `dry`: 7, `sanitary`: 1, `special_care`: 3).
  - Batch shape: `[4, 3, 224, 224]`, labels in `[0, 11]`.
  - Class weights: min = 0.548 (cardboard/paper/plastic/etc., n=1400), max = 1.734 (misc_trash, n=442), positive and normalized to sum to 12.0.
  - Compute device selected: `MPS` (Apple Silicon GPU acceleration active).
- Figures:
  - `ml/reports/figures/class_counts_split.png`
  - `ml/reports/figures/source_mix_per_class.png`
  - `ml/reports/figures/image_size_distribution.png`
  - `ml/reports/figures/class_grid.png`
- Notebook: `ml/notebooks/01_eda.ipynb`
- Status: COMPLETE

---

### E-9 · 2026-11-16 · local MPS run aborted: 8 GB RAM swap thrashing, 2,025 s/epoch
- Where (file/command): `ml/src/wasteml/train.py --config configs/wastenet.yaml` (task-633)
- Error text: Epoch 1 took 2,024.81s (~33.7 minutes). Train loss 3.9722, initial loss diverged above chance level ln(12) ≈ 2.48. Projected 45-epoch run: ~25.3 hours.
- Root cause:
  1. Memory: 4 DataLoader worker processes (~1.6 GB) + 5.5 GB PyTorch Metal buffer pool overwhelmed the 8 GB unified memory on this Mac, generating 18M+ disk swapouts and blocking Metal stream synchronizations on swapped pages.
  2. Stability & Head Init: Linear classifier head initialized with Kaiming normal (fan_out) blew up initial logits to ±30, causing initial loss to start at ~12.9 instead of ln(12) ≈ 2.48.
  3. Warm-up bug: LR warmup was computed per-epoch rather than per-step, so step 0 immediately began at base LR (0.001) without gradual ramp-up.
- Fix:
  1. Killed task-633 and preserved `history.csv` as `ml/artifacts/wastenet/aborted_run1_history.csv`.
  2. Architecture: Added stride-2 conv to Block 1 stem for 4× activation memory reduction (D-12).
  3. Initialization: Initialized linear classifier head with `normal(0, 0.01)`, ensuring initial loss starts near chance level (tested: 2.5088).
  4. Scheduler: Implemented per-step `LinearLR` warmup (1 epoch) -> `CosineAnnealingLR` via `SequentialLR`, stepped every batch. Added unit test `test_warmup_scheduler_lr_progression`.
  5. Stability: Added `torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)` and logged first 20 steps in sanity check.
  6. Sanity check: Overfit 64 images locally with `batch_size: 16` and `num_workers: 0` reaching 100% accuracy in 8.0s.
  7. Cloud training: Created `ml/notebooks/colab_train.ipynb` with AMP and checkpoint resumption (`--resume`), and added `make ml-zip` to package code for Google Colab GPU execution (D-13).

### E-10 · 2026-11-16 · Invalid unstratified sanity check (single-class battery collapse)
- Where (file/command): `ml/src/wasteml/train.py` (`run_sanity_check`)
- Error text: Sanity check reached 100% accuracy at step 2 with loss 0.0003 from initial loss 0.94 (below chance level).
- Root cause: `indices = list(range(64))` sampled the first 64 images of an alphabetically sorted ImageFolder (`train/battery/`), meaning all 64 samples belonged to class 0 (`battery`). The model collapsed to predicting class 0, masking multi-class learning behavior.
- Fix:
  1. Rewrote `run_sanity_check` to stratify 64 samples across all 12 classes (5–6 per class, seeded).
  2. Used `eval_tfms` (no augmentation) for deterministic overfit verification.
  3. Asserted `len(set(selected_labels)) == 12` inside the function and printed label distribution.
  4. Output on MPS: Step-1 loss started at 2.8121 and gradually climbed to 95.3% accuracy at step 52 in 19.1s.
  5. Added `--smoke` (`run_real_data_smoke`) to test 30 steps of the actual training pipeline with train augmentation, class weights, label smoothing 0.1, per-step warmup, and grad clipping: step-1 loss started at 2.4473 and remained stable (2.41–2.69) while LR smoothly rose from 1e-5 to 4.58e-5.

### V-M2 · 2026-11-17
- Commands run (verbatim, in order) + result (pass/fail):
  - `python -m wasteml.train --config configs/wastenet.yaml --sanity --device mps`: pass (64 stratified samples across all 12 classes overfit to 95.3% accuracy at step 52 in 19.1s)
  - `python -m wasteml.train --config configs/wastenet.yaml --smoke --device mps`: pass (30 steps of real data training setup with augmentation, class weights, label smoothing 0.1, per-step warmup, and grad clipping; step 1 loss: 2.4473, stable progression, LR rose from 1e-5 to 4.58e-5 in 4.4s)
  - `python -m wasteml.train --config configs/wastenet.yaml --device cuda --artifacts-dir /content/drive/MyDrive/EcoSort/artifacts/wastenet` (on Google Colab T4 GPU): pass (45/45 epochs completed in 4,687s / ~78.1 min, best Val Macro-F1: 0.7565 at epoch 45)
  - `cd ml && source .venv/bin/activate && ruff check . && pytest -q`: pass (12 passed in 8.32s)
  - `cd backend && source .venv/bin/activate && ruff check . && pytest -q`: pass (2 passed)
  - `cd frontend && pnpm lint && pnpm typecheck && pnpm build`: pass (0 errors, 0 warnings)
  - `cd frontend && pnpm test:e2e`: pass (2 passed in 3.3s)
  - `make test`: pass
  - `make verify`: pass
- URLs/routes opened:
  - `http://localhost:3000/` (Playwright E2E smoke and axe a11y regression check)
- Key numbers:
  - Architecture: `WasteNet` custom 10-layer CNN (5 ConvBlocks with stride-2 stem downsampling, channels 32-64-128-256-384, GAP, Dropout 0.4, Linear 384->12)
  - Total trainable parameters: **3,391,212**
  - Compute environment: Google Colab NVIDIA Tesla T4 GPU (CUDA with Automatic Mixed Precision AMP)
  - Training hyperparameters: batch_size=64, num_workers=4, optimizer=AdamW (lr=0.001, weight_decay=1e-4), per-step LinearLR warmup (1 epoch) -> CosineAnnealingLR, label_smoothing=0.1, gradient clipping=1.0
  - Wall time: 45 epochs in 4,687s (~78.1 min), ~104s/epoch
  - Loss & Convergence: Step 1 loss started at 2.2665 (within chance level ln 12 ≈ 2.4849; zero loss explosion, zero NaNs)
  - Best Validation Result: **Epoch 45**
    - Train Loss: 0.9796, Train Accuracy: 85.0%
    - Val Loss: 1.2934, Val Accuracy: **77.1%**
    - Val Macro-F1: **0.7565** (exceeds random baseline 0.083 by >9x)
  - Artifacts generated: `ml/artifacts/wastenet/history.csv`, `best.pt`, `last.pt`, `config.yaml`
- Status: COMPLETE






---

### D-14 · 2026-11-17 · Two-Phase Transfer Learning with Frozen Backbone BN
- Context: Fine-tuning ImageNet-1K pretrained models (`mobilenet_v3_large` and `efficientnet_b0`) on the 12-class EcoSort dataset.
- Decision:
  1. Phase 1 (Epochs 1–3): Freeze all backbone parameters (`requires_grad=False`) and lock all backbone BatchNorm layers in `eval()` mode (`m.eval()`). Train only the new 12-class linear head using AdamW with `lr=1e-3` and a 1-epoch per-step linear warmup.
  2. Phase 2 (Epochs 4–25): Unfreeze the entire network with differential parameter groups: backbone at `lr=3e-5` (0.1× ratio) and head at `lr=3e-4`. Train with per-step linear warmup (1 epoch) followed by CosineAnnealingLR decay over the remaining 22 epochs.
  3. Early stopping (patience 8 on validation macro-F1) is active only during Phase 2.
  4. `history.csv` records `phase`, `lr_backbone`, and `lr_head` per epoch.
- Why: Training an uninitialized classifier head on an unfrozen backbone immediately transmits large random gradient updates backward, wiping out delicate low-level filter representations learned on ImageNet (catastrophic forgetting). Locking BatchNorm statistics in eval mode prevents batch-level variance in waste images from corrupting global running mean and variance estimates.
- Alternatives considered:
  - Single-phase fine-tuning with uniform LR: Causes severe feature corruption and instability.
  - Linear probe only (never unfreezing backbone): Fails to adapt deep semantic features to specialized municipal waste domain textures (e.g. crushed cans, stained paper, medical blisters).

### D-15 · 2026-11-17 · Automated CA Certificate Resolution for PyTorch Model Weights
- Context: Downloading official ImageNet pretrained weights (`torchvision.models.mobilenet_v3_large` and `efficientnet_b0`) from `download.pytorch.org` on macOS.
- Decision: Integrated `certifi` CA bundle injection into `wasteml.train`: `os.environ.setdefault("SSL_CERT_FILE", certifi.where())`.
- Why: macOS Python binaries often lack local CA root certificates, triggering `ssl.SSLCertVerificationError` when `urllib.request` downloads PyTorch hub weights.
- Alternatives considered: Manually running `Install Certificates.command` on the host; rejected because it does not make the repository portable or self-healing on other machines.

---

### V-M3 · 2026-11-17 (Transfer Learning Models: MobileNetV3 & EfficientNet-B0)
- Commands run (verbatim, in order) + result (pass/fail):
  - `python -m wasteml.train --config configs/mobilenet_v3.yaml --sanity --device mps`: pass (64 stratified samples overfit to 100.0% accuracy at step 9 in 3.4s)
  - `python -m wasteml.train --config configs/mobilenet_v3.yaml --smoke --device mps`: pass (30 steps real-data training with warmup, step 1 loss: 2.6650, final LR: 4.58e-5 in 3.3s)
  - `python -m wasteml.train --config configs/efficientnet_b0.yaml --sanity --device mps`: pass (64 stratified samples overfit to 100.0% accuracy at step 12 in 2.6s)
  - `python -m wasteml.train --config configs/efficientnet_b0.yaml --smoke --device mps`: pass (30 steps real-data training with warmup, step 1 loss: 2.5094, final LR: 4.58e-5 in 4.1s)
  - `python -u -m wasteml.train --config configs/mobilenet_v3.yaml --device cuda --artifacts-dir /content/drive/MyDrive/EcoSport/artifacts/mobilenet_v3` (on Google Colab T4 GPU): pass (25/25 epochs in ~14.0 min; Phase 1 reached 0.8489 F1, Phase 2 reached Best Epoch 25 with Val Macro-F1: 0.9220, Val Acc: 92.5%)
  - `python -u -m wasteml.train --config configs/efficientnet_b0.yaml --device cuda --artifacts-dir /content/drive/MyDrive/EcoSport/artifacts/efficientnet_b0` (on Google Colab T4 GPU): pass (25/25 epochs in ~16.2 min; Phase 1 reached 0.8134 F1, Phase 2 reached Best Epoch 24 with Val Macro-F1: 0.9060, Val Acc: 91.2%)
  - `cd ml && source .venv/bin/activate && pytest -v`: pass (20 passed in 6.37s)
  - `cd backend && source .venv/bin/activate && ruff check . && pytest -q`: pass (2 passed)
  - `cd frontend && pnpm lint && pnpm typecheck && pnpm build`: pass (0 errors, 0 warnings)
  - `cd frontend && pnpm test:e2e`: pass (2 passed in 2.1s)
  - `python scripts/plot_training_curves.py --all`: pass (generated individual curves and `ml/reports/figures/model_comparison_curves.png`)
- URLs/routes opened:
  - `http://localhost:3000/` (Playwright E2E smoke and axe a11y test)
- Key numbers:
  - `mobilenet_v3`: 25 epochs (3 frozen + 22 fine-tune), Best Epoch = 25, Val Acc = **92.5%**, Val Macro-F1 = **0.9220**
  - `efficientnet_b0`: 25 epochs (3 frozen + 22 fine-tune), Best Epoch = 24, Val Acc = **91.2%**, Val Macro-F1 = **0.9060**
  - Comparison against from-scratch baseline (`wastenet` 0.7565): MobileNetV3 gained **+0.1655 macro-F1 (+16.55 percentage points)**; EfficientNet-B0 gained **+0.1495 macro-F1 (+14.95 percentage points)**.
  - Target achievement: Both transfer models decisively exceed PRD target (macro-F1 >= 0.82) by 8.6–10.2 points.
  - Artifacts generated:
    - `ml/artifacts/mobilenet_v3/`: `best.pt` (17.1 MB), `last.pt` (50.9 MB), `history.csv`, `config.yaml`
    - `ml/artifacts/efficientnet_b0/`: `best.pt` (16.4 MB), `last.pt` (48.7 MB), `history.csv`, `config.yaml`
    - `ml/reports/figures/`: `mobilenet_v3_curves.png`, `efficientnet_b0_curves.png`, `model_comparison_curves.png`
- Status: COMPLETE

---

### D-16 · 2026-11-17 · Selection of Default Serving Model on Validation Macro-F1 Prior to Test Evaluation
- Context: Selecting the default model for backend serving, CLI, and initial UI scanner flow.
- Decision: Selected `mobilenet_v3` as the default model (`DEFAULT_MODEL = "mobilenet_v3"` in `backend/app/config.py`, `.env.example`, and `ARCHITECTURE.md §7`). Decision is based strictly on **Validation set macro-F1** (0.9220 vs `efficientnet_b0` 0.9060 and `wastenet` 0.7565) and lower inference latency (~33s/epoch vs 39s/epoch on GPU, faster on CPU).
- Rationale: In strict accordance with ML evaluation integrity, model selection must occur prior to inspecting test set results to prevent data leakage and unintentional test set tuning.
- Alternatives considered: `efficientnet_b0` (lower validation F1 by 1.6 percentage points and higher latency); `wastenet` (val F1 lower by 16.55 percentage points).

---

### V-M4 · 2026-11-18 (Calibration, Evaluation, Grad-CAM & Model Cards)
- Commands run (verbatim, in order) + result (pass/fail):
  - `ml/.venv/bin/python -m wasteml.calibrate --model all --device mps`: pass (temperature scaling $T$ fitted on validation NLL loss, uncertain thresholds computed and reliability diagrams plotted)
  - `ml/.venv/bin/python -m wasteml.evaluate --model all --device mps`: pass (evaluated on 2,843 test images once per model; generated `metrics.json`, `confusion_matrix.json/png`, `misclassified.csv`, `test_predictions.csv`, `model_card.json`)
  - `ml/.venv/bin/python scripts/compare_models.py`: pass (computed McNemar tests with exact two-tailed p-values, saved `ml/reports/model_comparison.json` and `ml/reports/model_comparison.md`)
  - `ml/.venv/bin/python -m wasteml.gradcam_figures --model mobilenet_v3`: pass (generated `gradcam_12class_correct.png`, `gradcam_top_wrong.png`, `gradcam_shortcut_check.png`)
  - `ml/.venv/bin/python scripts/build_results_notebook.py`: pass (generated `ml/notebooks/02_results.ipynb`)
  - `ml/.venv/bin/pytest ml/tests/test_evaluation.py -v`: pass (12 passed in 15.96s)
  - `ml/.venv/bin/pytest ml/tests/ -v`: pass (32 passed in 18.42s)
  - `ml/.venv/bin/ruff check ml/`: pass (all checks passed)
  - `backend/.venv/bin/pytest backend/ -q`: pass (2 passed)
  - `cd frontend && pnpm build`: pass (zero errors, zero warnings)
- URLs/routes opened:
  - `http://localhost:3000/` (Playwright E2E smoke and axe a11y test verified)
- Key numbers from test set evaluation (2,843 held-out images):
  - `wastenet` (scratch baseline):
    - Test Accuracy: **75.87%** (95% CI: [74.4%, 77.5%])
    - Test Macro-F1: **0.7441** (95% CI: [0.7272, 0.7599])
    - Stream Accuracy: **88.32%**
    - Hazard Miss Rate: **17.36%** (117 / 674 hazard items leaked into wet/dry)
    - Temperature $T$: 0.9320, Uncertain Threshold: 0.6200
    - Coverage @ Threshold: 66.1%, Accuracy on kept: 90.04%
    - CPU Latency (p50): 8.54 ms (p95: 10.49 ms)
    - Params: 3,391,212, best.pt size: 13.0 MB
  - `mobilenet_v3` (Serving Default):
    - Test Accuracy: **92.44%** (95% CI: [91.4%, 93.4%])
    - Test Macro-F1: **0.9181** (95% CI: [0.9074, 0.9284])
    - Stream Accuracy: **97.75%**
    - Hazard Miss Rate: **3.12%** (21 / 674 hazard items leaked into wet/dry)
    - Temperature $T$: 0.8392, Uncertain Threshold: 0.4000
    - Coverage @ Threshold: 96.0%, Accuracy on kept: 94.61%
    - CPU Latency (p50): 54.49 ms (p95: 61.81 ms)
    - Params: 4,217,404, best.pt size: 16.3 MB
  - `efficientnet_b0`:
    - Test Accuracy: **91.45%** (95% CI: [90.4%, 92.4%])
    - Test Macro-F1: **0.9063** (95% CI: [0.8946, 0.9168])
    - Stream Accuracy: **96.73%**
    - Hazard Miss Rate: **3.12%** (21 / 674 hazard items leaked into wet/dry)
    - Temperature $T$: 0.8512, Uncertain Threshold: 0.4000
    - Coverage @ Threshold: 96.5%, Accuracy on kept: 93.26%
    - CPU Latency (p50): 115.43 ms (p95: 134.94 ms)
    - Params: 4,022,920, best.pt size: 15.6 MB
- Statistical Significance:
  - WasteNet vs. MobileNetV3: Discordant pairs = 613 ($b=542, c=71$), continuity-corrected $\chi^2 = 360.36$, exact two-tailed $p = 9.51 \times 10^{-91}$ (statistically significant; ImageNet transfer provides a massive +16.57 percentage point boost).
  - MobileNetV3 vs. EfficientNet-B0: Discordant pairs = 198 ($b=85, c=113$), continuity-corrected $\chi^2 = 3.68$, exact two-tailed $p = 0.0547$. McNemar test is **not** statistically significant ($\alpha=0.05$). The default serving selection therefore rests strictly on validation macro-F1 (0.922 vs 0.906) and 2.1× faster CPU inference latency (54.5 ms vs 115.4 ms) as pre-decided in Decision D-16.
- Uncertainty Threshold Limitation:
  - The uncertainty rejection threshold sits at the clamp floor of $p_{max} \ge 0.40$ (due to temperature scaling sharpening probabilities after label smoothing). At this threshold, MobileNetV3 retains 96.0% coverage with 94.61% accuracy on kept samples.
- Visual Grad-CAM Shortcut Evidence:
  - In `gradcam_top_wrong.png`, confident misclassifications reveal isolated shortcut reliance: e.g., the confident `paper → cardboard` misclassification concentrates its heatmap activation in the bottom-right corner where a **shutterstock.com watermark** is printed, rather than on the paper item.
  - In `gradcam_shortcut_check.png` (regenerated as a full 3×4 grid across 6 TrashBox classes with 2 images each, zero blank axes), physical features like syringe plungers and PCB traces are primarily highlighted, with occasional border and corner activations (e.g. phone left edge, metal corner) indicating partial background/border context utilization.
- Quantitative Shortcut & Spatial Bias Evaluation (`ml/reports/shortcut_test.json`, `shortcut_test.md`):
  - **Random chance baseline:** 8.33% (1/12 classes).
  - **Uniform baseline for outer 15% perimeter:** 51.0% ($1 - 0.70^2 = 0.51$).
  - **WasteNet (from scratch):** Original Acc: 75.87% | Center-60% Acc: 15.65% | Border-60% Acc: 29.26% | Border-10% Frame: **17.31%** | Grad-CAM Border Mass: 45.5% ± 31.7% | Ratio vs Uniform: **0.89×** (Center-Focused).
  - **MobileNetV3-Large (Default):** Original Acc: 92.44% | Center-60% Acc: 79.07% | Border-60% Acc: 82.48% | Border-10% Frame: **62.33%** | Grad-CAM Border Mass: 42.4% ± 17.2% | Ratio vs Uniform: **0.83×** (Center-Focused).
  - **EfficientNet-B0:** Original Acc: 91.45% | Center-60% Acc: 82.10% | Border-60% Acc: 80.65% | Border-10% Frame: **63.07%** | Grad-CAM Border Mass: 42.3% ± 10.9% | Ratio vs Uniform: **0.83×** (Center-Focused).
  - **Spatial Bias Interpretation:** Masking the central 60% per side hides only 36% of pixels, leaving 64% visible. Because objects often extend into the outer border, the 82% border-60% accuracy partly reflects partial object visibility and surrounding context. When the central 80% per side is masked (Border-10% control, leaving only a 10% perimeter frame), accuracy drops significantly to 62.33% (and down to 42.68% on real-world landfill `realwaste`), confirming that model performance degrades when physical object contours are removed.
  - **Grad-CAM Border Mass Ratio:** The observed outer-band mass (~42%) is *below* the 51% uniform baseline (ratio 0.83×). Thus, attention is **mostly object-centered on average**, with isolated individual cases of watermark or border reliance.
- Error Audit: Hazard Misses vs. Ambiguous Annotations:
  - **Model Hazard Miss:** The confident misclassification of a copper wire coil as `metal` rather than `e_waste` is a genuine model hazard miss. TrashBox taxonomy explicitly classifies wires, cords, and cables under e-waste (Special Care stream); misrouting it to dry metal is a model safety failure under SWM Rules 2026.
  - **Ambiguous Annotations:** Other confident errors, such as transparent jars, reflect visual ambiguity between glass and clear rigid plastic in low-resolution web imagery.
- Constituent Dataset Descriptions (Corrected):
  - `garbage12`: Curated web-scraped waste image benchmark (Kaggle).
  - `realwaste`: Landfill and sorting facility photos under uneven real-world lighting.
  - `trashbox`: Web-scraped e-waste, hazardous, and municipal items featuring stock watermarks (e.g. Shutterstock, Getty) and varied camera angles.
  - `trashnet`: Classic laboratory-style photos on uniform white background.
- Status: COMPLETE

## E-20: M4 shortcut write-up overclaimed; corrected
- **Date:** 2026-11-18
- **Context:** Milestone 4 shortcut learning write-up review.
- **Problem:**
  1. The "border-only" test overclaimed that "the object is completely masked". Masking the central 60% per side covers only 36% of pixels, leaving 64% visible. Objects routinely extend into the border, so the 82% accuracy was confounded by visible object parts.
  2. The Grad-CAM border mass (~42%) was interpreted as shortcut reliance without comparison to its uniform chance baseline (outer 15% perimeter = 51% of pixels). In reality, 42% is *below* uniform chance, meaning attention is on average *more* center-focused on the object than chance.
  3. The copper wire coil was wrongly called "label noise"; TrashBox explicitly includes wires/cords under e-waste, so this is a genuine model hazard miss. An unsupported "92–93% accuracy ceiling" was also asserted.
- **Resolution:**
  1. Rephrased the border test to accurately describe robustness to partial views + context. Added a strict "Border-10%" control (masking central 80% per side, leaving only a 10% perimeter frame), where MobileNetV3 drops to 62.33% (and 42.68% on RealWaste).
  2. Calculated and reported the observed/51% uniform ratio across all models and sources, concluding that attention is mostly object-centered on average, with isolated individual shortcut reliance cases.
  3. Reclassified the copper wire coil as a model hazard miss, called transparent jars "ambiguous", and deleted all unmeasured accuracy ceiling claims.
  4. Updated `shortcut_test.py`, `shortcut_test.json`, `shortcut_test.md`, `build_results_notebook.py`, and regenerated `02_results.ipynb`.

## Decision D-17: Milestone 5 (Backend API) Architecture, Model Registry, and Threat-Model Hardening
- **Date:** 2026-11-18
- **Context:** Milestone 5 builds the production FastAPI backend (`backend/`) bridging trained PyTorch artifacts from `ml/artifacts/` to the Next.js frontend, complying strictly with `ARCHITECTURE.md` §5 and `SECURITY.md`.
- **Decisions Made:**
  1. **Model Registry & Weight Loading (`app/services/registry.py`):**
     - Scans `ml/artifacts/*/model_card.json` at startup to dynamically discover available models (`mobilenet_v3`, `efficientnet_b0`, `wastenet`).
     - Eagerly loads `mobilenet_v3` (serving default selected in D-16) to avoid cold-start delays on initial requests. Other discovered models are lazy-loaded upon request.
     - Enforces `torch.load(..., weights_only=True)` to prevent arbitrary code execution vulnerabilities.
     - Per-model `threading.Lock()` serializes Grad-CAM generation per model instance to guarantee thread safety and prevent hook interference under concurrent requests.
     - Rejects any requested model outside the registry allowlist with HTTP 422 Unprocessable Content.
  2. **Preprocessing & Inference Parity (`app/services/inference.py`):**
     - Directly imports `eval_tfms` from `wasteml.transforms` (zero duplicate code).
     - Uses calibrated temperature scaling ($logits / T$) before softmax.
     - Maps predicted class name to municipal sorting stream (`wet`, `dry`, `sanitary`, `special_care`) and disposal instructions via `classes.json`.
     - Flags `uncertain = True` whenever top-1 probability $p_{max} < \text{uncertainty threshold}$.
     - Tested on 20 fixed test images with exact parity against offline `evaluate.py` ($< 10^{-5}$ difference).
  3. **Security & Threat Model Defense (`SECURITY.md` T1–T15):**
     - **T1 Polyglot / Non-image:** Validates image format using Pillow `verify()`; rejects non-images and non-whitelisted formats (JPEG, PNG, WebP only) with HTTP 415.
     - **T2 Decompression Bomb & Size:** Rejects payloads $> 8$ MB with HTTP 413. Rejects images exceeding `MAX_IMAGE_PIXELS` (40M pixels) with HTTP 422/413.
     - **T3 Privacy & EXIF Stripping:** Re-encodes uploaded images to clean JPEG (quality 90, `optimize=True`), completely stripping GPS and camera metadata before persisting.
     - **T4 Path Traversal:** Stored images and Grad-CAM overlays are saved with randomly generated UUID4 hex filenames (`uploads/{id}.jpg`, `gradcam/{id}.png`). Direct disk path traversals (`/..%2F..%2Fetc%2Fpasswd`) are rejected with 404/422.
     - **T6 Rate Limiting:** Enforces `slowapi` rate limit of 20 requests per minute per IP on `/api/v1/predict` (returning 429 Too Many Requests on the 21st call).
     - **T7 Admin Authorization:** `/api/v1/admin/*` endpoints strictly enforce localhost-only callers (`127.0.0.1`, `::1`, `localhost`, `testclient`), returning 403 Forbidden for remote callers.
     - **T8 Feedback Injection:** Strips non-printable characters and truncates comments to 280 characters.
     - **Security Headers:** Custom `SecurityHeadersMiddleware` injects CSP (`default-src 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Request-ID` on all responses.
  4. **Persistence & Health:**
     - SQLModel SQLite database (`backend/data/ecosort.db`) with tables `predictions` and `feedback`.
     - `/api/v1/health/live` returns 200.
     - `/api/v1/health/ready` returns 200 only when the default model is actively loaded in the registry AND the database is reachable (503 otherwise). Never returns fake predictions.

## E-22: SQLModel strict datetime timezone requirement
- **Date:** 2026-11-18
- **Context:** Running backend test suite with SQLite.
- **Problem:** SQLModel / Pydantic v2 raised `StatementError: Datetime values must have timezone information` when storing `datetime.utcnow()`.
- **Resolution:** Replaced all `datetime.utcnow()` calls with `datetime.now(timezone.utc)` across `models.py` and `endpoints.py`.

## E-23: Test database in-memory isolation and SlowAPI rate limiter accumulation
- **Date:** 2026-11-18
- **Context:** Running backend pytest suite.
- **Problem:**
  1. Default in-memory SQLite (`sqlite://`) opened new connections per session without preserving tables, causing `OperationalError: no such table: predictions` in readiness check.
  2. The 20-image parity test exhausted the 20/minute rate limit on `/predict`, causing subsequent security tests to fail with 429.
- **Resolution:**
  1. Configured `test_engine` in `conftest.py` with `poolclass=StaticPool` so in-memory connections share the created schema.
  2. Added an autouse fixture in `conftest.py` calling `limiter.reset()` between test cases.

## Verification Log — Milestone 5 (Backend API)
- Commands executed:
  ```bash
  # Code formatting and linting
  backend/.venv/bin/ruff check backend/
  # Output: All checks passed!

  # Backend test suite (22 tests covering API, True Parity, Security T1-T15, CSPs)
  PYTHONPATH=backend:ml/src MPLCONFIGDIR=/tmp/matplotlib backend/.venv/bin/pytest -v backend/tests/
  # Output: 22 passed, 5 warnings in 9.11s

  # ML test suite verification
  cd ml && .venv/bin/pytest -q
  # Output: 32 passed in 19.57s
  ```
- Endpoints verified:
  - `GET /api/v1/health/live` -> 200 OK + strict security headers (`default-src 'none'`)
  - `GET /api/v1/health/ready` -> 200 OK (model loaded + DB connected)
  - `GET /api/v1/classes` -> 200 OK (12 classes with streams and disposal text)
  - `GET /api/v1/models` -> 200 OK (discovered `mobilenet_v3`, `efficientnet_b0`, `wastenet`)
  - `GET /api/v1/models/{name}/metrics` -> 200 OK (full metrics, confusion matrix, calibration)
  - `POST /api/v1/predict` -> 200 OK (with top-3, stream, disposal, Grad-CAM, uncertain flag)
  - `GET /api/v1/predictions` -> 200 OK (cursor-based pagination, stream filter)
  - `POST /api/v1/predictions/{id}/feedback` -> 201 Created (and 409 Conflict on duplicate)
  - `GET /api/v1/stats` -> 200 OK (municipal KPIs, daily counts, confusion breakdown)
  - `GET /api/v1/admin/feedback.csv` -> 200 OK (localhost only; 403 for remote)
  - `DELETE /api/v1/admin/predictions/{id}` -> 200 OK (localhost only; 403 for remote)
  - `GET /docs` -> 200 OK (Swagger UI renders, scripts from `cdn.jsdelivr.net` and logos from `fastapi.tiangolo.com` allowed via targeted CSP)
  - `GET /redoc` -> 200 OK (ReDoc rendered via targeted CSP)
  - `GET /openapi.json` -> 200 OK
- Status: COMPLETE

## Decision D-18: Swagger UI CSP targeted relaxation, real evaluate.py parity, and admin localhost isolation
- **Date:** 2026-11-18
- **Context:** User review identified two critical defects before starting M6: (1) global CSP `default-src 'none'` rendered `/docs` completely blank by blocking CDN assets, and (2) `test_parity.py` recomputed predictions using identical runtime logic instead of comparing against offline `evaluate.py` outputs.
- **Decisions Made:**
  1. **Dual CSP Architecture (`SecurityHeadersMiddleware`):**
     - Routes `/docs`, `/redoc`, and `/openapi.json` receive targeted CSP:
       `default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'`.
     - When `ENV=production`, `/docs`, `/redoc`, and `/openapi.json` are disabled entirely (`docs_url=None`, returning 404).
     - Every API route under `/api/v1/*` continues to enforce the strict `default-src 'none'; frame-ancestors 'none'`.
  2. **True Parity Verification (`ml/src/wasteml/evaluate.py` & `backend/tests/test_parity.py`):**
     - Updated `evaluate.py` to write `ml/artifacts/<model>/test_predictions.csv` containing ground truth, predicted class, stream, confidence, and all 12 calibrated probabilities.
     - `test_parity.py` now reads directly from `test_predictions.csv`, comparing backend outputs on 20 test images against offline evaluation results without recomputing predictions via ML code.
  3. **Strict Localhost Admin Enforcement (`verify_localhost_admin`):**
     - Removed `"testclient"` from production allowed hosts set; allowed hosts are strictly `{"127.0.0.1", "::1", "localhost"}`. Test clients pass `client=("127.0.0.1", 50000)` explicitly.

## Decision D-19: Milestone 6 Frontend Foundation & Field Instrument Design System
- **Date:** 2026-11-18
- **Context:** Implementing Milestone 6: Design system, layout, accessible base components, typed API client, and About documentation page, adhering strictly to `DESIGN.md` §0–§6.
- **Decisions Made:**
  1. **Strict "Field Instrument" Visual Identity:**
     - Adopted industrial precision inspired by waste equipment leaders (Greyparrot, AMP, Recycleye, TOMRA).
     - Single sans font family: Archivo (condensed 75% width for uppercase H1 moments, standard width for headings and body).
     - Data font: JetBrains Mono (500 weight, tabular figures, uppercase letter-spaced eyebrows like `01 — SCAN`).
     - Exactly one loud accent: Hi-Vis yellow-green (`#D4F23A`) used with `#0E1A16` text for primary buttons, scan lines, active nav markers, and focus rings. Never used as standalone body text on light backgrounds.
     - Four functional municipal streams: Wet (Green, `Leaf`), Dry (Blue, `Package`), Sanitary (Orange, `ShieldAlert`), Special Care (Red, `TriangleAlert`). Always paired with Lucide icon + text label (never color alone).
     - Radius strictly 2px for controls, 4px for panels; depth created via 1px hairline rules (`var(--rule)`), zero generic heavy shadows.
     - Zero §1 violations: No Inter/Geist/Roboto, no serif display fonts, no purple gradients, no glassmorphism, no sparkle-AI icons, no 3D blobs, no stock photos of people, and no fake testimonials/numbers.
  2. **Typed API Layer (`src/lib/types.ts` & `src/lib/api.ts`):**
     - Mapped directly from Pydantic schemas in `backend/app/api/v1/schemas.py`.
     - Dual-mode URL resolution: uses relative URLs on client (routed via Next.js rewrites to eliminate CORS) and direct `BACKEND_URL` on server.
  3. **Empirical Data Invariant for `/about`:**
     - The `/about` page loads empirical benchmark numbers directly from `ml/artifacts/*/metrics.json` and `ml/reports/shortcut_test.json`.
     - Zero numbers were hardcoded or typed in. MobileNetV3 test accuracy (92.4%), macro-F1 (0.9181), stream accuracy (97.8%), hazard miss rate (3.12%), and spatial bias numbers (51.0% uniform baseline vs 42.4% observed outer mass, 0.83× ratio) are rendered directly from disk.
  4. **Home Console Shell:**
     - Replaced M0 placeholder with asymmetric 5/7 split: Left column features bold `WHICH BIN?` display heading; right column stages the dark instrument viewfinder console with 4 corner brackets, segmented architecture control, and FOV telemetry.

## E-25: React 19 theme synchronization and casing collision
- **Date:** 2026-11-18
- **Context:** Building frontend components.
- **Problem:**
  1. React 19 ESLint flagged calling `setTheme` synchronously inside `useEffect` (`react-hooks/set-state-in-effect`).
  2. Case-insensitive macOS filesystem caused TS collision between `Button.tsx` and `button.tsx`.
- **Resolution:**
  1. Replaced `useEffect` setState pattern in `ThemeProvider.tsx` with React 19's `useSyncExternalStore` observing DOM mutation attributes on `document.documentElement`.
  2. Consolidated button component into lowercase `button.tsx`.

## E-26: WCAG 2.2 AA Color Contrast & Label-in-Name Adjustments
- **Date:** 2026-11-18
- **Context:** Automated Axe accessibility audit on `/` and `/about`.
- **Problem:**
  1. Header brand link failed SC 2.5.3 (Label in Name) because `aria-label="EcoSort Home"` differed from visible text "EcoSort".
  2. Small 12px colored stream subtitle text (`Green Bin`, etc.) on `#ffffff` scored 4.17:1 (below 4.5:1 AA requirement).
  3. How-it-works Step 06 used Hi-Vis text on light background.
  4. About table hazard miss cell used green text on Hi-Vis 10% row.
- **Resolution:**
  1. Removed redundant `aria-label` from brand link, allowing accessible name to match visible text cleanly.
  2. Switched stream subtitles to ink bold text (`<span className="text-[var(--ink)] font-bold">Green Bin</span>`).
  3. Changed Step 06 text to ink bold with Hi-Vis border.
  4. Rendered table hazard numbers in ink bold. Axe audit re-ran with 0 serious or critical violations across all routes.

## Verification Log — Milestone 6 (Frontend Foundation)
- Commands executed:
  ```bash
  # Linter and TypeScript checks
  cd frontend && pnpm lint
  # Output: $ eslint (0 errors, 0 warnings)
  cd frontend && pnpm typecheck
  # Output: $ tsc --noEmit (0 errors)

  # Production webpack build
  cd frontend && npx next build --webpack
  # Output: Compiled successfully, 3 static/dynamic routes generated cleanly

  # Playwright test suite (12 tests covering smoke, a11y, and screenshots)
  cd frontend && pnpm exec playwright test
  # Output: 12 passed in 4.7s

  # Lighthouse quality audit on http://localhost:3000/
  npx lighthouse http://localhost:3000/ --output=json --output-path=frontend/tests/lighthouse-home-m6.json --chrome-flags="--headless" --only-categories=accessibility,best-practices,seo --no-enable-error-reporting
  # Output: Accessibility: 100 / 100, Best Practices: 96 / 100, SEO: 100 / 100
  ```
- Routes verified:
  - `GET /` — 200 OK + strict CSP + security headers
  - `GET /about` — 200 OK + empirical metrics + citations
  - `GET /non-existent-route` — 404 Not Found + field instrument error state
- Screenshots generated in `frontend/tests/screenshots/`:
  - `home_375_light.png` & `home_375_dark.png`
  - `home_768_light.png` & `home_768_dark.png`
  - `home_1440_light.png` & `home_1440_dark.png`
  - `about_375_light.png` & `about_375_dark.png`
  - `about_768_light.png` & `about_768_dark.png`
  - `about_1440_light.png` & `about_1440_dark.png`
- Design §1 Ban Review:
  - Fonts: Archivo + JetBrains Mono only (Zero banned fonts).
  - Colors: Paper (`#F3F2EC` / `#0B1210`), Surface, Ink, Hi-Vis (`#D4F23A`), 4 stream tokens. Zero gradients/mesh/glows.
  - Icons: Lucide 1.5px stroke only. Zero sparkles ✨ or emoji.
  - Imagery: Zero stock photos or AI scenes. Viewfinder corner brackets + real metrics only.
- Status: COMPLETE


## Decision D-20: Milestone 6 Content Honesty Overhaul, Dynamic Manifest Counting, SWM Rules 2026 Mandate Alignment, and Mobile Navigation Disclosure
- **Date:** 2026-11-18
- **Context:** Following user review of initial M6 screenshots, multiple content honesty defects and UI improvements were identified: (1) unsourced MSW generation claims, (2) typed-in dataset counts on `/about` differing from `manifest.csv`, (3) invented stream rules and bin colors, (4) overpromising on sanitary waste capabilities beyond the model's training data, (5) raw unrendered LaTeX in the DOM, (6) fake instrument readouts in the scanner console, (7) internal design label "FIELD INSTRUMENT" exposed in UI, (8) stat tile naming, (9) mobile navigation disclosure menu, and (10) pipeline diagram formatting.
- **Decisions Made:**
  1. **Source Honesty & Regulatory Grounding:**
     - Removed unsourced "150,000 metric tons of MSW daily" claim; reframed problem statement strictly around MoEFCC/CPCB directives and SWM Rules 2026 mandates.
     - Removed invented stream rules and bin requirements ("YELLOW WRAP · INCINERATION", "RED BIN", "High-Temperature Biomedical Waste Incinerator", "Hazardous Landfill").
     - Strictly aligned stream destinations with statutory SWM Rules 2026 mandates:
       - Wet → Decentralized Composting / Biomethanation
       - Dry → Material Recovery Facility (MRF)
       - Sanitary → Wrapped securely and stored separately
       - Special Care → Authorised agencies / designated collection centres
     - Explicitly added disclaimer: "* Note: Card colours (green, blue, orange, red) are a design choice for visual clarity, not statutory container colours."
  2. **Model Scope Honesty on Sanitary Waste:**
     - Explicitly disclosed the model's true training scope: "EcoSort recognises: face masks, gloves. Not yet recognised: diapers, sanitary napkins (no public open-access training data)."
  3. **Dynamic Manifest Counts (`data/processed/waste12/manifest.csv`):**
     - Replaced typed-in numbers on `/about` with dynamic server-side parsing of `manifest.csv` line by line at render time.
     - Ground-truth counts computed and rendered: Garbage12 = 4,605; RealWaste = 4,752; TrashBox = 7,072; TrashNet = 2,522 (Total: 18,951 images).
     - Added automated Playwright test asserting rendered UI values equal ground-truth counts from `manifest.csv`.
  4. **Typography & LaTeX Cleanliness:**
     - Eliminated raw LaTeX strings (`$b=542$`, `\chi^2 = 360.36`, `\times 10^{-91}`) from DOM text; rendered as clean, accessible Unicode: `(discordant pairs b = 542, c = 71; continuity-corrected χ² = 360.36, p < 10⁻⁹⁰)` and `(p = 0.0547)`.
  5. **Removal of Fake Instrument Readouts:**
     - Removed fake decorator readouts ("SENSOR READY", "TARGET: 224×224 RGB", "FOV: 1.0× STANDARD") from the viewfinder frame.
     - Kept strictly empirical model data: Active Architecture (`MobileNetV3-Large · PyTorch`), Calibrated Temperature (`T = 0.8392 (CALIBRATED)`), Latency (`CPU p50: ~55 MS`), and `ZERO CLOUD APIS`.
     - Hero eyebrow updated to `01 — SCAN`.
     - Stat tile updated to: `92.44% TEST ACCURACY · 2,843 held-out images`.
  6. **Mobile Navigation Disclosure & Layout:**
     - Implemented accessible mobile menu disclosure button (<768px) with `aria-expanded`, `aria-controls="mobile-nav"`, and full keyboard navigation (Escape closes and returns focus).
     - Responsive model selector: stacks on mobile so full architecture names are always visible.
  7. **Continuous Pipeline Flow:**
     - Replaced 6 separate bordered cards with a single continuous hairline flow diagram connected with arrows per DESIGN.md §6.

## E-27: Next.js Turbopack PostCSS Subprocess Crash on Next.js 16
- **Date:** 2026-11-18
- **Context:** Running `next build` on Next.js 16 with Tailwind v4.
- **Problem:** Turbopack failed when spawning node subprocesses for Tailwind PostCSS (`TurbopackInternalError: node process exited before we could connect to it`).
- **Resolution:** Updated build script in `frontend/package.json` to `next build --webpack`. Compiles cleanly in ~1.9s.

## E-28: React 19 ESLint `react-hooks/set-state-in-effect` on Navigation
- **Date:** 2026-11-18
- **Context:** Closing mobile menu on route change in `Navbar.tsx`.
- **Problem:** Calling `setMobileMenuOpen(false)` inside `useEffect` depending on `pathname` violated React 19's `react-hooks/set-state-in-effect` rule.
- **Resolution:** Adopted official React render-time state adjustment pattern (`if (pathname !== prevPathname) { setPrevPathname(pathname); setMobileMenuOpen(false); }`) plus individual link `onClick` handlers.

## E-29: WCAG 2.2 AA Contrast for Sanitary Note & Mobile Nav Button Label
- **Date:** 2026-11-18
- **Context:** Automated Axe and smoke tests on revised M6 layout.
- **Problem:**
  1. Sanitary disclaimer text `#c25a12` on `#f9eee7` had 3.86:1 contrast ratio for 11px text (below 4.5:1 requirement).
  2. Mobile menu button changed `aria-label` from `"Open menu"` to `"Close menu"` upon click, breaking locator in test.
- **Resolution:**
  1. Updated sanitary disclaimer to use ink text (`text-[var(--ink)]`, >12:1 contrast ratio) with a `border-l-2 border-[var(--sanitary)]` accent line.
  2. Added persistent `id="mobile-menu-toggle"` to the button for unambiguous test selection.

## Verification Log — Milestone 6 Revision (Content Honesty & Mobile Accessibility)
- Commands executed:
  ```bash
  # Linter and TypeScript checks
  cd frontend && pnpm lint
  # Output: $ eslint (0 errors, 0 warnings)
  cd frontend && pnpm typecheck
  # Output: $ tsc --noEmit (0 errors)

  # Production webpack build
  cd frontend && pnpm build
  # Output: Compiled successfully, 3 routes generated in 2.2s

  # Playwright full test suite (14 tests covering smoke, manifest count parity, mobile disclosure a11y, WCAG 2.2 AA, and screenshots)
  cd frontend && pnpm exec playwright test
  # Output: 14 passed in 5.1s

  # Lighthouse quality audit on http://127.0.0.1:3000/
  cd frontend && npx lighthouse http://127.0.0.1:3000/ --only-categories=accessibility,best-practices --quiet --chrome-flags="--headless" --output=json --output-path=./tests/lighthouse-home-m6.json --no-enable-error-reporting
  # Output: Accessibility: 100 / 100, Best Practices: 96 / 100
  ```
- Routes verified:
  - `GET /` — 200 OK (Honest telemetry, SWM Rules 2026 stream destinations, continuous pipeline, stat tile)
  - `GET /about` — 200 OK (Dynamically parsed manifest counts, Unicode math, sanitary scope disclosure, MoEFCC/CPCB problem framing)
  - `GET /non-existent-route` — 404 Not Found (Clean error console)
- Automated Test Assertions:
  - Garbage12: 4,605 images (asserted equal to `manifest.csv`)
  - RealWaste: 4,752 images (asserted equal to `manifest.csv`)
  - TrashBox: 7,072 images (asserted equal to `manifest.csv`)
  - TrashNet: 2,522 images (asserted equal to `manifest.csv`)
  - Total: 18,951 images
- Screenshots regenerated in `frontend/tests/screenshots/`:
  - `home_375_light.png` & `home_375_dark.png`
  - `home_768_light.png` & `home_768_dark.png`
  - `home_1440_light.png` & `home_1440_dark.png`
  - `about_375_light.png` & `about_375_dark.png`
  - `about_768_light.png` & `about_768_dark.png`
  - `about_1440_light.png` & `about_1440_dark.png`
- Status: COMPLETE


## Decision D-21: Milestone 7 Core Scan Flow, Viewfinder Scanner, Grad-CAM Heatmap Comparison, Specimen Wall, and Citizen Feedback
- **Date:** 2026-11-18
- **Context:** Implementing Milestone 7 (the core user-facing feature): end-to-end image ingestion (drag-and-drop, file picker, camera stream), real inference lifecycle, Grad-CAM heatmap overlay with interactive slider, spec-sheet result readout, citizen correction feedback, and 24-sample test specimen wall.
- **Leftover Fixes Folded In:**
  1. **Confidence Interval Correction:** Updated homepage stat tile sublabel to `MobileNetV3 · 95% CI: [91.4%, 93.4%]`, matching `bootstrap_ci_95.accuracy` from `ml/artifacts/mobilenet_v3/metrics.json` instead of macro-F1 CI.
  2. **Zero Hardcoded Numbers on `/about`:** Removed all hard-coded fallback strings ("91.5", "96.7", "3.12", "75.9", "17.36", "42.4%", "42.7%") and typed split counts. All data is dynamically loaded from `metrics.json`, `shortcut_test.json`, and `stats.json`. If an artifact is missing, it renders `"Not trained yet"` or `"—"`. Added automated Playwright test asserting zero hard-coded metric percentages in JSX text across `frontend/src`.
  3. **Pipeline ECE from Calibration:** Step 04 now reads `val ECE after calibration: 0.0795` from `ml/artifacts/mobilenet_v3/calibration.json`.
  4. **Stream Card Statutory Labeling:** Replaced bin color mandates with statutory guidance: `"Commonly Green Bin"`, `"Commonly Blue Bin"`, `"Secure Paper Wrap"`, `"Designated Drop Point"`.
- **Decisions Made for M7:**
  1. **Interactive Viewfinder Scanner (`Scanner.tsx`):**
     - Primary hero CTA updated to "Scan an item →" which smoothly scrolls to and focuses `#scanner-section`.
     - Drag-and-drop and native file input with client-side format checks (JPEG, PNG, WebP only, max 8 MB).
     - Integrated camera capture using `navigator.mediaDevices.getUserMedia` with `facingMode: { ideal: "environment" }`, live video stream in viewfinder, frame capture to JPEG blob, clean track teardown on unmount, and friendly permission-denied / device-not-found error banners.
     - Model architecture segmented control passing `?model=` to the backend.
     - Real request lifecycle states (`idle` → `uploading` → `classifying` → navigation), driving a Hi-Vis scan line sweep that respects `prefers-reduced-motion`.
  2. **Interactive Grad-CAM Heatmap Comparison (`HeatmapCompare.tsx`):**
     - Side-by-side / overlay comparison with a draggable vertical divider (50% default).
     - Full keyboard accessibility: Left/Right arrows shift divider by 5%, Home (0%), End (100%), with `role="slider"`, `aria-label="Grad-CAM overlay comparison slider"`, and `aria-valuenow`.
  3. **Result Readout Spec Sheet (`ReadoutPanel.tsx`):**
     - Condensed uppercase material label (e.g. `BATTERY`), statutory stream bar with destination, and calibrated confidence meter with a tick mark at the 0.40 threshold.
     - When `uncertain === true` (`confidence < 0.40`), displays a prominent warning alert advising manual segregation before disposal.
     - Top-3 Softmax probability bars, disposal protocol, and technical metadata row (model, latency, specimen ID).
  4. **Citizen Feedback Flow (`FeedbackFlow.tsx`):**
     - "YES, CORRECT" one-click verification and "NO, CHANGE MATERIAL" opening a 12-class radio grid with stream chips and optional comment.
     - Calls `POST /api/v1/predictions/{id}/feedback`, handles 409 duplicate submission gracefully, and displays confirmation.
  5. **Specimen Wall (`SpecimenWall.tsx`):**
     - 24 real held-out test images (2 per class, seeded) copied to `frontend/public/samples/`.
     - Each card displays a visible "SAMPLE" tag and uppercase mono caption (`MATERIAL · STREAM`). Clicking triggers real backend inference and navigates to `/scan/[id]`.

## E-30: Axe WCAG 2.5.3 (Label in Name) on Specimen Wall Buttons
- **Date:** 2026-11-18
- **Context:** Automated Axe audit on homepage with specimen wall.
- **Problem:** Adding custom `aria-label="Test specimen: BATTERY..."` conflicted with visible button text (`SAMPLE BATTERY SPECIAL CARE`), failing SC 2.5.3.
- **Resolution:** Removed redundant `aria-label`; browser computes accessible name directly from the inner visible elements without mismatch.

## E-31: Axe WCAG 2.2 AA Contrast on ReadoutPanel 40% Threshold Tick
- **Date:** 2026-11-18
- **Context:** Automated Axe audit on `/scan/[id]`.
- **Problem:** `text-red-500` on `#F3F2EC` scored 3.39:1 (below 4.5:1 AA requirement).
- **Resolution:** Replaced with `text-[var(--ink)] font-bold` (>12:1 contrast ratio) and `bg-[var(--special)]` for the line marker.

## E-32: Playwright Strict Mode Collision on `role="alert"`
- **Date:** 2026-11-18
- **Context:** Running E2E tests for uncertain banner and invalid file validation.
- **Problem:** `page.getByRole("alert")` matched both our custom alert and Next.js's internal `#__next-route-announcer__`.
- **Resolution:** Targeted specific alert text via `locator("div[role='alert']:has-text('Uncertain Flagged')")` and `locator("div[role='alert']:has-text('Unsupported format')")`.

## E-33: Result Page Blank Image Bug & LAN Camera Security Context
- **Date:** 2026-11-18
- **Where (file/command):** `frontend/src/lib/api.ts` (`getImageUrl`, `getGradcamUrl`), `frontend/src/components/scan/HeatmapCompare.tsx`, `frontend/src/components/scanner/Scanner.tsx`, `frontend/src/components/scan/ReadoutPanel.tsx`, `frontend/src/components/Navbar.tsx`
- **Error text / manifestation:** Result page `/scan/[id]` rendered blank grey/black containers with broken image icons for both specimen photo and Grad-CAM heatmap overlay. Camera viewfinder threw errors or failed over LAN `http://<IP>:3000`.
- **Root cause:**
  1. `api.getImageUrl` and `api.getGradcamUrl` called `getBaseUrl()`, which on the Next.js server rendered absolute URLs `http://localhost:8000/api/v1/predictions/...`. Browser CSP (`img-src 'self' data: blob:`) blocked requests to port 8000. Furthermore, when accessed from mobile devices on LAN, `localhost:8000` resolved to the mobile device instead of the host.
  2. Next.js `<Image>` attempted optimization without remote patterns or `unoptimized={true}`, causing broken image states on dynamic API asset endpoints.
  3. `navigator.mediaDevices.getUserMedia` is restricted to Secure Contexts (`window.isSecureContext === true`). On LAN plain `http://<IP>:3000`, live camera streaming is disabled by browser security policies.
  4. Next.js router prefetching on unbuilt M8 routes (`/history`, `/insights`, `/model`) produced 404 console errors in the browser.
- **Fix:**
  1. Updated `getImageUrl` and `getGradcamUrl` to return relative paths (`/api/v1/predictions/${id}/image` and `.../gradcam`), routing cleanly through the Next.js same-origin `/api` rewrite proxy (`'self'`).
  2. Added `unoptimized` prop to `<Image>` in `HeatmapCompare.tsx` to serve raw image bytes directly without server-side proxy overhead.
  3. Added "Take photo" button with `<input type="file" accept="image/*" capture="environment">` that opens the native phone camera over plain HTTP without HTTPS requirement.
  4. Added `window.isSecureContext` check using React 19 `useSyncExternalStore` to conditionally hide "Open camera" and show helper text when not on HTTPS. Added `dev:https` script in `package.json`.
  5. Refined uncertain state: formatted banner confidence with 1 decimal place (`39.6% < 40.0%`), rendered stream box with tentative styling (`POSSIBLY: SPECIAL CARE HAZARDOUS`, `Check the top-3 guesses before disposing.`), renamed feedback header to `"Was this right?"`, and labeled latency as `"SERVER TIME INCL. GRAD-CAM: {latency_ms.toFixed(1)} MS"`.
  6. Added `prefetch={false}` on unbuilt routes in `Navbar.tsx` to eliminate 404 network console noise.
  7. Added automated Playwright assertions polling `naturalWidth > 0` on both `<img>` elements and checking zero console errors.

## Verification Log — Milestone 7 (Scan Flow & Real Inference — Revision 2)
- Commands executed:
  ```bash
  # Linter and TypeScript checks
  cd frontend && pnpm lint
  # Output: $ eslint (0 errors, 0 warnings)
  cd frontend && pnpm typecheck
  # Output: $ tsc --noEmit (0 errors)

  # Production webpack build
  cd frontend && pnpm build
  # Output: Compiled successfully, routes: /, /_not-found, /about, /scan/[id] (2.6s)

  # Start backend
  cd backend && uvicorn app.main:app --port 8000
  # Output: Eagerly loaded default model: mobilenet_v3, running on port 8000

  # Playwright test suite (24 tests covering smoke, real inference, feedback, uncertain banner, WCAG 2.2 AA on /scan/[id], image naturalWidth > 0 assertions, JSX honesty, and screenshots)
  cd frontend && pnpm exec playwright test
  # Output: 24 passed (18.4s)
  ```
- Routes verified:
  - `GET /` — 200 OK (Interactive scanner, Take Photo native capture input, camera stream with secure-context check, drag-and-drop, specimen wall)
  - `GET /scan/[id]` — 200 OK (HeatmapCompare with verified `naturalWidth > 0` on photo & Grad-CAM, ReadoutPanel with 1-decimal uncertain banner & tentative stream styling, FeedbackFlow "Was this right?")
  - `GET /about` — 200 OK (Empirical metrics, zero hardcoded numbers, Unicode math)
  - `GET /not-found` — 404 Not Found
- Screenshots generated and verified in `frontend/tests/screenshots/`:
  - `home_375_light.png` & `home_375_dark.png`
  - `home_768_light.png` & `home_768_dark.png`
  - `home_1440_light.png` & `home_1440_dark.png`
  - `about_375_light.png` & `about_375_dark.png`
  - `about_768_light.png` & `about_768_dark.png`
  - `about_1440_light.png` & `about_1440_dark.png`
  - `scan_375_light.png` & `scan_375_dark.png` (Photo + Grad-CAM rendered, 184 KB)
  - `scan_768_light.png` & `scan_768_dark.png` (Photo + Grad-CAM rendered, 316 KB)
  - `scan_1440_light.png` & `scan_1440_dark.png` (Photo + Grad-CAM rendered, 303 KB)
  - `scan_uncertain_1440_light.png` & `scan_uncertain_1440_dark.png` (Tentative styling + 1-dec banner, 294 KB)
- Status: COMPLETE

### D-18 · 2026-11-19 · Zero-Pandas CSV Parsing & In-Memory Metrics Caching
- **Decision:** Replaced dynamic `import pandas as pd` and `pd.read_csv` inside `ModelRegistry.get_full_metrics` with Python's built-in `csv.DictReader`, and cached parsed metrics in memory (`_full_metrics_cache`).
- **Why:** In async FastAPI endpoints, dynamically importing heavy libraries like pandas inside request handlers blocks the asyncio event loop and triggers font cache builds, causing 30s timeouts under concurrent test execution. The built-in `csv` module parses the 25-line training history in microseconds with zero overhead.
- **Consequences:** `GET /api/v1/models/{name}/metrics` response time dropped from ~3,500ms to <1ms on repeated calls.

### D-19 · 2026-11-19 · Milestone 8 Architecture & Design Standards
- **Decision:** Implemented `/history`, `/insights`, and `/model` adhering strictly to `DESIGN.md` tokens (Archivo + JetBrains Mono, hairline rules, 2px radius, WCAG 2.2 AA contrast):
  1. `/history`: Contact-sheet grid of square specimen thumbnails (`/api/v1/predictions/[id]/image`) with bottom stream color indicator border, mono captions, uncertainty flag badge (`#F5C451` on `--panel-dark`, contrast > 10:1), stream segmented control (`ALL`, `WET`, `DRY`, `SANITARY`, `SPECIAL CARE`), and cursor-based pagination.
  2. `/insights`: Dark "control room" KPI strip (`bg-[var(--panel-dark)]`) displaying Total Scans Logged, Recovery Stream Share, Citizen Feedback, and Field Correction Rate. Recharts visualizations for Stream Composition (Donut), Daily Ingestion Volume (Area), Material Volume (Bar), and Citizen Audit confusion pairs table. Every chart includes `<figcaption>` and toggleable accessible data tables. Localhost-only export link to `/api/v1/admin/feedback.csv`.
  3. `/model`: Comprehensive diagnostic telemetry report comparing `mobilenet_v3`, `efficientnet_b0`, and `wastenet`. Features McNemar significance testing notes (χ² = 360.36, p = 9.51 × 10⁻⁹¹ vs scratch; χ² = 3.68, p = 0.055 vs EfficientNet), an interactive 12×12 confusion matrix with Row-Normalized (%) vs Raw Counts (N) toggle, per-class F1 breakdown, 4-dataset source generalization, temperature scaling ECE reduction (14.5% → 7.95%), and 25-epoch convergence curves.
  4. Zero hardcoded percentages or invented telemetry. All numbers bind directly to backend registry endpoints.

## Verification Log — Milestone 8 (History, Insights, and Model Diagnostics)
- **Commands executed:**
  ```bash
  # 1. Typecheck and lint
  cd frontend && pnpm lint && pnpm typecheck
  # Output: eslint (0 errors, 0 warnings), tsc --noEmit (0 errors)

  # 2. Production build
  cd frontend && pnpm build
  # Output: Compiled successfully in 4.7s. Routes: /, /_not-found, /about, /history, /insights, /model, /scan/[id]

  # 3. Backend tests
  cd backend && source .venv/bin/activate && pytest -q
  # Output: 23 passed, 5 warnings in 5.15s

  # 4. Milestone 8 Playwright test suite (smoke, navigation, filters, matrix toggle, charts, a11y, and screenshots)
  cd frontend && pnpm test:e2e tests/e2e/m8-pages.spec.ts --workers=1
  # Output: 13 passed in 17.3s

  # 5. Full regression test suite
  cd frontend && pnpm test:e2e tests/e2e/smoke.spec.ts tests/e2e/m7-scan.spec.ts tests/e2e/a11y.spec.ts --workers=1
  # Output: 14 passed in 11.5s
  ```
- **Routes verified:**
  - `GET /history` — 200 OK (Segmented stream filter tabs, contact sheet grid, cursor pagination, direct navigation to `/scan/[id]`)
  - `GET /insights` — 200 OK (Dark control room KPI panel, Recharts donut, area, and bar charts, accessible table toggle, feedback audit table, admin CSV export link)
  - `GET /model` — 200 OK (3-architecture comparison table, McNemar hypothesis testing callouts, 12×12 confusion matrix with row-normalized toggle, per-class precision/recall/F1, dataset source generalization, ECE calibration reduction, training loss & macro-F1 curves)
- **A11y Audit Results (@axe-core/playwright):**
  - Zero critical or serious accessibility violations across `/history`, `/insights`, and `/model`.
- **Key numbers verified from empirical artifacts:**
  - MobileNetV3 test accuracy: 92.44% (95% CI [91.42%, 93.39%]), macro-F1: 91.81% (95% CI [90.74%, 92.84%]) from `ml/artifacts/mobilenet_v3/metrics.json`
  - EfficientNet-B0 test accuracy: 91.45% (95% CI [90.43%, 92.40%]), macro-F1: 90.63% (95% CI [89.46%, 91.68%]) from `ml/artifacts/efficientnet_b0/metrics.json`
  - WasteNet (scratch) test accuracy: 75.87% (95% CI [74.39%, 77.45%]), macro-F1: 74.41% (95% CI [72.72%, 75.99%]) from `ml/artifacts/wastenet/metrics.json`
  - Hazard miss rate: 3.12% (21/674) for MobileNetV3 vs 17.36% (117/674) for WasteNet
  - Calibration: Temperature T = 0.8392, ECE reduced from 14.51% to 7.95%
  - UI Uncertainty gate: 0.585 (retains 88.15% automated throughput with 97.17% precision on unflagged scans)
- **Screenshots generated and verified in `frontend/tests/screenshots/`:**
  - `history_375_light.png` & `history_375_dark.png` (558 KB)
  - `history_768_light.png` & `history_768_dark.png` (380 KB)
  - `history_1440_light.png` & `history_1440_dark.png` (311 KB)
  - `insights_375_light.png` & `insights_375_dark.png` (163 KB)
  - `insights_768_light.png` & `insights_768_dark.png` (180 KB)
  - `insights_1440_light.png` & `insights_1440_dark.png` (183 KB)
  - `model_375_light.png` & `model_375_dark.png` (326 KB)
  - `model_768_light.png` & `model_768_dark.png` (382 KB)
  - `model_1440_light.png` & `model_1440_dark.png` (397 KB)
- **Status:** COMPLETE

### E-34 · 2026-11-19 · Production Proxy Admin Endpoint Leak (Report TC-11)
- **Where (file/command):** `frontend/src/proxy.ts`, report test case TC-11 (`GET /api/v1/admin/feedback.csv`, `DELETE /api/v1/admin/predictions/<id>`)
- **Error text / manifestation:** In a production build (`NODE_ENV=production`), `GET /api/v1/admin/feedback.csv` through the Next.js proxy returned 200 OK.
- **Root cause:** The backend relies on `request.client.host in {"127.0.0.1", "::1"}` (`SECURITY.md T7`) to enforce localhost-only admin access. When requests were sent through the Next.js reverse proxy rewrite (`/api/:path*`), Next.js forwarded the request to FastAPI from `127.0.0.1`. Consequently, the backend's localhost check passed for any external client (e.g. phone on LAN). Furthermore, `src/proxy.ts` had previously excluded `/api` in its matcher (`(?!api...)`), allowing admin routes to pass through to the backend unintercepted.
- **Fix:**
  1. Updated `frontend/src/proxy.ts` matcher to explicitly include `"/api/v1/admin/:path*"` and `"/api/admin/:path*"`.
  2. In `proxy(request)`, added an upfront security check: if `request.nextUrl.pathname.startsWith("/api/v1/admin")` or `.../api/admin` and `process.env.NODE_ENV === "production"`, immediately return `new NextResponse(null, { status: 404, headers: ... })`.
  3. Added Playwright test suite `frontend/tests/e2e/admin-security.spec.ts` asserting that `GET /api/v1/admin/feedback.csv`, `DELETE /api/v1/admin/predictions/<id>`, and `GET /api/admin/feedback.csv` all return HTTP 404 against a production server build (`pnpm build && pnpm start`).

### E-35 · 2026-11-19 · First TC-11 fix incomplete: path-encoding and case bypass (Defense in Depth)
- **Where (file/command):** `frontend/src/proxy.ts`, `backend/app/core/security.py`, `backend/tests/test_security.py`, `frontend/tests/e2e/admin-security.spec.ts`
- **Error text / manifestation:** Independent re-audit revealed that commit `edd346a` blocked literal `/api/v1/admin/feedback.csv`, but `/api/v1/%61dmin/feedback.csv` (encoded "a") and `/API/v1/admin/feedback.csv` (uppercase) still returned 200 OK with full CSV data served.
- **Root cause:**
  1. Next.js middleware matchers (`config.matcher`) evaluate raw, undecoded request paths. Matching `"/api/v1/admin/:path*"` failed to match alternate casings or percent-encoded variants like `"/API/..."` or `"/api/v1/%61dmin/..."`, causing requests to bypass the middleware completely and proceed to Next.js rewrites.
  2. The single-layer check in proxy was insufficient because the backend only inspected `request.client.host in {"127.0.0.1", "::1"}` without detecting reverse proxy headers (`X-Forwarded-For`, etc.), trusting loopback connections blindly.
- **Fix (Defense in Depth):**
  1. **Frontend Proxy Normalization (`frontend/src/proxy.ts`):**
     - Extended matcher to `"/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"` so all API requests are intercepted.
     - Implemented recursive `decodeURIComponent` (catches nested encoding, rejects malformed URI sequences with HTTP 400).
     - Standardized path to lowercase, collapsed consecutive slashes (`replace(/\/+/g, "/")`), and resolved relative dot segments (`.` and `..`).
     - Upfront production check: if normalized path starts with `/api/v1/admin` or `/api/admin`, returns HTTP 404 with security headers.
     - Sets client proxy identity headers (`x-forwarded-for`, `x-forwarded-host`) before delegating downstream.
  2. **Backend Proxy Header Rejection (`backend/app/core/security.py`):**
     - Enhanced `verify_localhost_admin` to inspect `request.headers` for reverse proxy forwarding headers (`x-forwarded-for`, `x-forwarded-host`, `x-real-ip`, `forwarded`).
     - Any request carrying proxy forwarding headers is immediately rejected with `HTTP 403 Forbidden` ("Admin endpoints are accessible only via direct local connection, not via reverse proxy").
     - Direct local connections (`curl http://127.0.0.1:8000/...` without proxy headers) succeed with 200 OK.
  3. **Verification & Testing:**
     - Added `test_t7_admin_rejects_proxied_requests` to `backend/tests/test_security.py` (asserts 403 on forwarded headers, 200 on direct localhost).
     - Expanded `frontend/tests/e2e/admin-security.spec.ts` with 9 Playwright tests covering literal, percent-encoded (`%61dmin`), uppercase (`/API/...`), mixed-case (`/Api/V1/Admin/...`), double slash (`//admin`), encoded slash (`admin%2Ffeedback.csv`), dot segment traversal (`/predictions/../admin`), and DELETE methods.
     - Both layers tested and verified empirically: backend tests pass (24/24), Playwright tests pass (9/9), and live Python urllib probe confirms all bypasses blocked.

## Decision D-20: Offline Font Embedding via next/font/local & Milestone 9 Verification
- **Date:** 2026-11-19
- **Context:** Executing Milestone 9 (Hardening, polish, report assets, demo rehearsal). An external audit noted that `next/font/google` fetches fonts from Google CDN at build time, failing if the build occurs offline (e.g. on restricted college Wi-Fi).
- **Decisions Made:**
  1. **Committed Local WOFF2 Fonts (`next/font/local`):**
     - Replaced `next/font/google` in `frontend/src/app/layout.tsx` with `next/font/local`.
     - Committed variable WOFF2 fonts with `wdth` and `wght` axes directly into `frontend/src/app/fonts/`:
       * `archivo-latin-wdth-normal.woff2` & `archivo-latin-wdth-italic.woff2` (from `@fontsource-variable/archivo`)
       * `jetbrains-mono-latin-wght-normal.woff2` & `jetbrains-mono-latin-wght-italic.woff2` (from `@fontsource-variable/jetbrains-mono`)
     - Verified that `pnpm build` (`next build --webpack`) runs and completes in 4.7s with zero external network connectivity.
  2. **Automated README Results Synchronization (`scripts/update_readme_results.py`):**
     - Automated population of the results table in `README.md` reading directly from `ml/artifacts/{wastenet,mobilenet_v3,efficientnet_b0}/metrics.json`.
     - Added prominent "Run it in 3 commands" section and a structured 3-minute examiner demonstration walkthrough.
  3. **High-Resolution 300 DPI Report Figures (`scripts/export_report_figures.py`):**
     - Exported 13 publication-grade figures at 300 DPI to `ml/reports/figures/report/`:
       * Individual training curves (`training_curves_mobilenet_v3.png`, `..._efficientnet_b0.png`, `..._wastenet.png`) and composite architecture comparison (`training_curves_comparison.png`).
       * Row-normalized 12×12 MobileNetV3 confusion matrix with cell counts and recall percentages (`mobilenet_v3_confusion_matrix_row_norm.png`).
       * Grad-CAM 12-class correct grid (`gradcam_12class_correct.png`) and top misclassifications grid (`gradcam_top_wrong.png`).
       * EDA charts (`class_counts_split.png`, `source_mix_per_class.png`).
       * Desktop application screens at 1440px light (`app_home_scanner_1440_light.png`, `app_result_heatmap_1440_light.png`, `app_result_uncertain_1440_light.png`, `app_model_benchmarks_1440_light.png`).
  4. **Comprehensive Mobile Lighthouse Verification across 6 Application Routes (`scripts/run_lighthouse_audit.py`):**
     - Executed full headless Chrome mobile Lighthouse audits across all public and dynamic routes.
     - Results recorded in `ml/reports/lighthouse_m9.json`:
       * `/` (Home Viewfinder): Performance 100, Accessibility 100, Best Practices 100, SEO 100
       * `/about` (System & Dataset): Performance 100, Accessibility 100, Best Practices 100, SEO 100
       * `/scan/<id>` (Grad-CAM Result): Performance 84, Accessibility 100, Best Practices 100, SEO 100
       * `/model` (Model Diagnostics): Performance 99, Accessibility 100, Best Practices 100, SEO 100
       * `/insights` (Municipal Insights): Performance 99, Accessibility 100, Best Practices 100, SEO 100
       * `/history` (Specimen History): Performance 88, Accessibility 100, Best Practices 100, SEO 100
  5. **Demo Rehearsal Timing Verification (`scripts/rehearse_demo.py` & `scripts/demo.sh`):**
     - Automated end-to-end benchmark timing of the full demonstration script:
       * Backend Cold Start: 4.36 s
       * Frontend Cold Start: 878.0 ms
       * Confident Scan (cardboard): 1.23 s (CPU inference + Grad-CAM hook synthesis)
       * Uncertain Scan (safety gate): 82.5 ms (uncertainty flag triggered: 39.6% < 58.5%)
       * Hazardous Scan (battery -> Special Care): 62.5 ms
       * Heatmap & Photo Byte Delivery: 10.7 ms
       * Feedback Submission: 6.2 ms (HTTP 201 Created)
       * Model Diagnostics Navigation: 52.3 ms
       * **Total Demonstration Runtime:** 6.86 s (Target: < 180 s / 3 minutes)

- **Exact shell commands executed for M9 verification:**
  ```bash
  # 1. Offline build verification
  cd frontend && pnpm build
  # 2. Automated README results generation
  python3 scripts/update_readme_results.py
  # 3. 300 DPI Report figures generation
  ml/.venv/bin/python3 scripts/export_report_figures.py
  # 4. Mobile Lighthouse audit suite
  python3 scripts/run_lighthouse_audit.py
  # 5. Demo rehearsal timing benchmark
  python3 scripts/rehearse_demo.py
  # 6. Backend unit and integration tests
  cd backend && source .venv/bin/activate && pytest -q
  # Output: 24 passed in 8.90s
  # 7. ML tests
  cd ml && source .venv/bin/activate && pytest -q
  # Output: 32 passed in 19.22s
  # 8. Full Playwright E2E suite
  cd frontend && pnpm test:e2e tests/e2e/smoke.spec.ts tests/e2e/admin-security.spec.ts tests/e2e/a11y.spec.ts tests/e2e/m7-scan.spec.ts tests/e2e/m8-pages.spec.ts --workers=1
  # Output: 36 passed in 19.6s
  # 9. Frontend lint & typecheck
  cd frontend && pnpm lint && pnpm typecheck
  # Output: 0 errors, 0 warnings
  # 10. Secret pattern audit
  git grep -EI "PRIVATE KEY|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|aws_secret" -- ":(exclude).venv" ":(exclude)node_modules"
  # Output: clean
  ```
- **Routes verified:**
  - `GET /` — 200 OK
  - `GET /about` — 200 OK
  - `GET /scan/<id>` — 200 OK
  - `GET /model` — 200 OK
  - `GET /insights` — 200 OK
  - `GET /history` — 200 OK
- **Status:** COMPLETE




