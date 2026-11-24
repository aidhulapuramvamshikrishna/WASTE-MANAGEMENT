# ARCHITECTURE.md — EcoSort: Municipal Waste Classification using CNN

> Source of truth for structure, interfaces and data flow. If code and this doc disagree, fix one of them **and log it in DECISION_LOG.md**.

## 1. System overview

```
 ┌──────────────┐   image (multipart)   ┌───────────────────────────┐   state_dict   ┌──────────────────────┐
 │  Next.js UI  │ ───────────────────▶ │  FastAPI backend          │ ◀───────────── │ ml/artifacts/<model>/ │
 │ (frontend/)  │ ◀─────────────────── │  PyTorch CPU/MPS inference│                │ best.pt, metrics.json │
 └──────────────┘  JSON + Grad-CAM PNG │  Grad-CAM (manual hooks)  │                │ calibration.json      │
        ▲                              │  SQLite (history/feedback)│                └──────────▲───────────┘
        │ /api/* rewrite (same origin) └───────────┬───────────────┘                           │ train.py / evaluate.py
        │                                          │ shares model code via `pip install -e ml`  │
        └──────────── browser ─────────────────────┴──────────────── ml/ (PyTorch training) ────┘
                                                                         ▲
                                                         data/processed/waste12 (ImageFolder)
```

Three parts, one repo:
1. **`ml/`**: PyTorch package `wasteml`, which handles dataset loading, the models, training, evaluation, calibration, Grad-CAM and export. Each training run writes its artifacts into `ml/artifacts/<model_name>/`.
2. **`backend/`**: a FastAPI service. It loads the trained models from `ml/artifacts`, runs predictions, generates Grad-CAM heatmaps, saves history and feedback in SQLite, and serves model metrics.
3. **`frontend/`**: a Next.js (App Router, TypeScript) app with scanning (upload or camera), results with the heatmap, history, insights and model-comparison pages.

**Hard constraint:** no external AI or ML APIs (OpenAI, Gemini, Roboflow, HF Inference, etc.). Every prediction comes from a model trained in this repo. ImageNet-pretrained *weights* from `torchvision` are allowed for transfer learning (that is standard and gets cited); hosted inference is not.

## 2. Repository layout

```
Waste_management_AI/
├── README.md  PRD.md  ARCHITECTURE.md  SECURITY.md  DESIGN.md
├── DESIGN.md  DATASET.md  DECISION_LOG.md  implementation_plan.md  .gitignore  .env.example
├── .agents/workflows/verify-milestone.md
├── Makefile                                 # ml-train, api, web, test, verify
├── scripts/build_dataset.py                 # already done; rebuilds data/processed/waste12
├── scripts/update_readme_results.py         # copies metrics.json numbers into README (M9)
├── data/                                    # GITIGNORED
│   └── processed/waste12/{train,val,test}/<class>/*.jpg + manifest.csv, classes.json, stats.json
├── ml/
│   ├── pyproject.toml                       # package name: wasteml (editable install)
│   ├── requirements.txt
│   ├── configs/{wastenet.yaml, mobilenet_v3.yaml, efficientnet_b0.yaml}
│   ├── src/wasteml/
│   │   ├── __init__.py
│   │   ├── constants.py      # CLASS_NAMES (sorted, = ImageFolder order), STREAMS, IMAGENET_MEAN/STD, IMG_SIZE=224
│   │   ├── data.py           # build_dataloaders(cfg) -> train/val/test loaders, class weights, WeightedRandomSampler option
│   │   ├── transforms.py     # train_tfms(), eval_tfms()  (eval_tfms is ALSO used by backend)
│   │   ├── models/
│   │   │   ├── wastenet.py   # custom CNN from scratch
│   │   │   └── factory.py    # build_model(name, num_classes, pretrained) + gradcam_target_layer(model, name)
│   │   ├── train.py          # CLI: python -m wasteml.train --config configs/x.yaml
│   │   ├── evaluate.py       # CLI: python -m wasteml.evaluate --model <name>  -> metrics.json, confusion_matrix.json/png
│   │   ├── calibrate.py      # temperature scaling + confidence threshold on VAL -> calibration.json
│   │   ├── gradcam.py        # manual Grad-CAM (forward/backward hooks), returns HxW float map
│   │   └── utils.py          # seed_everything, get_device (cuda > mps > cpu), AverageMeter, timers
│   ├── notebooks/{01_eda.ipynb, 02_results.ipynb}   # analysis/figures for the report; logic lives in src/
│   ├── tests/                # pytest: shapes, transforms, gradcam output range, class order
│   └── artifacts/            # GITIGNORED except */metrics.json, */confusion_matrix.json, */history.csv, */calibration.json, */model_card.json
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # app factory, routers, middleware (security headers, request-id, CORS)
│   │   ├── config.py         # pydantic-settings; reads .env
│   │   ├── schemas.py        # pydantic response/request models (see §5)
│   │   ├── api/v1/{predict.py, predictions.py, models.py, stats.py, classes.py, admin.py, health.py}
│   │   ├── services/
│   │   │   ├── registry.py   # discovers ml/artifacts/*/model_card.json, lazy-loads + caches models
│   │   │   ├── inference.py  # preprocess (wasteml.transforms.eval_tfms) -> logits/T -> softmax -> top3
│   │   │   ├── explain.py    # Grad-CAM overlay PNG via wasteml.gradcam
│   │   │   └── storage.py    # validated image save (uuid names), overlay save
│   │   ├── db/{session.py, models.py}   # SQLModel + SQLite
│   │   └── core/{security.py, ratelimit.py, logging.py, errors.py}
│   ├── tests/                # pytest + httpx TestClient
│   └── storage/{uploads,gradcam}/   # GITIGNORED
├── frontend/
│   ├── package.json  next.config.ts  tailwind / postcss config  components.json (shadcn)
│   ├── src/app/{layout.tsx, page.tsx, scan/[id]/page.tsx, history/page.tsx, insights/page.tsx, model/page.tsx, about/page.tsx, not-found.tsx}
│   ├── src/components/{scanner/, result/, charts/, layout/, ui/(shadcn)}
│   ├── src/lib/{api.ts, types.ts, streams.ts, format.ts}
│   └── tests/e2e/*.spec.ts   # Playwright
└── playwright.config.ts (inside frontend/)
```

## 3. Classes and streams (fixed contract)

Class order **must** equal `torchvision.datasets.ImageFolder` order (alphabetical folder names):

| idx | class | stream |
|---|---|---|
| 0 | battery | special_care |
| 1 | cardboard | dry |
| 2 | e_waste | special_care |
| 3 | glass | dry |
| 4 | mask_glove | sanitary |
| 5 | medicine_syringe | special_care |
| 6 | metal | dry |
| 7 | misc_trash | dry |
| 8 | organic | wet |
| 9 | paper | dry |
| 10 | plastic | dry |
| 11 | textile | dry |

`data/processed/waste12/classes.json` has stream + disposal text, but its `index` field uses a different (insertion) order: **ignore that `index`; always use the alphabetical order above** (`constants.CLASS_NAMES = sorted(os.listdir(train_dir))`, asserted in a test). The backend gets class names from each model's `model_card.json`, never by guessing.

## 4. ML design (`ml/`)

### 4.1 Data
- `ImageFolder` on `data/processed/waste12/{train,val,test}`. Path comes from env `WASTE_DATA_DIR` (default `../data/processed/waste12`).
- **Train transforms:** `RandomResizedCrop(224, scale=(0.6,1.0))`, `RandomHorizontalFlip`, `RandomRotation(15)`, `ColorJitter(0.2,0.2,0.2,0.02)`, `ToTensor`, `Normalize(ImageNet)`, `RandomErasing(p=0.25)`.
- **Eval transforms (shared with the backend):** `Resize(256)`, `CenterCrop(224)`, `ToTensor`, `Normalize(ImageNet)`.
- **Imbalance:** class-weighted `CrossEntropyLoss(weight=w, label_smoothing=0.1)` with `w_c = N / (K * n_c)`. A `WeightedRandomSampler` is optional and set by a config flag; never use both at once.
- DataLoader: `num_workers` from config (default 4; 0 on Windows), `pin_memory` only on CUDA, `persistent_workers=True` when workers > 0.

### 4.2 Models (all trained by us)
| name | type | notes |
|---|---|---|
| `wastenet` | **custom CNN from scratch** | 5 blocks of [Conv3×3-BN-ReLU ×2 → MaxPool] with channels 32-64-128-256-384, with block 1 conv1 using stride 2 for 4× activation memory reduction, then GAP → Dropout(0.4) → Linear(384→12). Exactly 3,391,212 params. Kaiming init. The "built by us" baseline. Grad-CAM target: last conv block (`block5.conv2`). |
| `mobilenet_v3` | transfer learning | `torchvision.models.mobilenet_v3_large(weights=IMAGENET1K_V2)`, classifier[-1] replaced with 12 outputs. Grad-CAM target: `features[-1]`. |
| `efficientnet_b0` | transfer learning | `torchvision.models.efficientnet_b0(weights=IMAGENET1K_V1)`, classifier[1] replaced with 12 outputs. Grad-CAM target: `features[-1]`. |

### 4.3 Training (`train.py`)
- YAML config: model, epochs, batch_size, lr, weight_decay, warmup/freeze epochs, sampler flag, seed, early-stop patience.
- AdamW with cosine LR decay and 1 epoch of linear warmup. AMP on CUDA only; fp32 on MPS and CPU.
- **Transfer models:** phase 1 freezes the backbone and trains the head for `freeze_epochs` (default 3, lr 1e-3); phase 2 unfreezes everything (lr 3e-4, backbone lr ×0.1).
- **wastenet:** lr 1e-3, 40–60 epochs.
- Early stopping on **val macro-F1** (patience 8). Save `best.pt` (state_dict only) and `last.pt`.
- Log every epoch to `history.csv` (epoch, train_loss, train_acc, val_loss, val_acc, val_macro_f1, lr, seconds).
- `seed_everything(42)`; print the device being used.
- Must run on Apple Silicon (MPS), CUDA (Colab) or CPU. For a slow local machine, document a Colab path in README (upload `data/processed/waste12` as a zip).

### 4.4 Evaluation (`evaluate.py`), on TEST, run once per final model
Writes `ml/artifacts/<model>/metrics.json` containing:
`accuracy, macro_f1, weighted_f1, per_class{precision,recall,f1,support}, stream_accuracy` (prediction mapped to its stream), `per_source_accuracy` (joined via `manifest.csv` on the file path), `params, size_mb, cpu_latency_ms_p50/p95` (batch 1, 50 runs after warm-up), `top3_accuracy`, `n_test`, `git_commit`, `timestamp`, `device`.
Also writes `confusion_matrix.json` (12×12 counts + labels), `confusion_matrix.png`, and `misclassified.csv` (top 50 by confidence).

### 4.5 Calibration (`calibrate.py`), on VAL only
- Fit a temperature `T` (LBFGS on val NLL). Report ECE before and after.
- Choose `uncertain_threshold` as the max-softmax value (after T) where val accuracy of kept predictions is ≥ 90%. Clamp to [0.40, 0.85].
- Writes `calibration.json {temperature, uncertain_threshold, ece_before, ece_after, coverage_at_threshold}`.

### 4.6 Model card (`model_card.json`), what the backend reads
`{name, display_name, arch, num_classes, class_names[], img_size, mean[], std[], gradcam_layer, weights_file:"best.pt", trained_from_scratch: bool, created_at}`

### 4.7 Grad-CAM (`gradcam.py`), implemented by hand (no `pytorch-grad-cam` lib)
Register forward and backward hooks on the target layer and backprop the target logit. `weights = grads.mean((H,W))`, `cam = ReLU(Σ w·A)`, upsample to the input size and normalise to [0,1]. Must work with `model.eval()` under `torch.enable_grad()`.

## 5. Backend design (`backend/`)

- Python 3.11+, FastAPI, Uvicorn, SQLModel (SQLite at `backend/storage/ecosort.db`), Pillow, torch/torchvision (CPU or MPS), `wasteml` (editable install from `../ml`), slowapi (rate limits), pydantic-settings.
- **Startup:** `registry` scans `MODEL_DIR` (default `../ml/artifacts`) for `model_card.json` and eagerly loads `DEFAULT_MODEL`; other models load lazily on first use and stay cached. If no model exists, `/health/ready` returns 503 and `/predict` returns 503 with a clear message. **Never fake a prediction.**
- **Inference path:** validate upload → `PIL.Image` → `exif_transpose` → RGB → `eval_tfms` → `logits / T` → softmax → top-3 → map to stream → `uncertain = p_max < threshold`. Then Grad-CAM for the top-1 class → overlay (jet colormap at alpha 0.45) → PNG in `storage/gradcam/{id}.png`.
- **Concurrency:** inference runs in a threadpool (`run_in_threadpool`), with one model lock per model for Grad-CAM (hooks are stateful).

### 5.1 API (all under `/api/v1`, JSON, errors as `{"error": {"code","message","request_id"}}`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/live` | liveness: always 200 if the process is up |
| GET | `/health/ready` | readiness: 200 if the default model is loaded and the DB is reachable, else 503 |
| GET | `/classes` | `[{name, stream, disposal}]` |
| GET | `/models` | `[{name, display_name, trained_from_scratch, metrics_summary{accuracy,macro_f1,params,size_mb,cpu_latency_ms_p50}, is_default}]` from `metrics.json` |
| GET | `/models/{name}/metrics` | full `metrics.json` + `confusion_matrix.json` + `history.csv` parsed + `calibration.json` |
| POST | `/predict?model=<name>&explain=true` | multipart field `file`. Returns `PredictionOut` (below). Rate limit 20/min per client. |
| GET | `/predictions?limit=24&cursor=<id>&stream=<s>` | history, newest first, cursor pagination |
| GET | `/predictions/{id}` | one prediction |
| GET | `/predictions/{id}/image` and `/predictions/{id}/gradcam` | image bytes (served by id, never by path) |
| POST | `/predictions/{id}/feedback` | `{correct_class, comment?}`, one per prediction (409 if one exists) |
| GET | `/stats?days=30` | counts per stream/class, scans per day, feedback count, correction rate, top confused pairs (from feedback) |
| GET | `/admin/feedback.csv` | header `X-Admin-Token`. Exports feedback for retraining. |
| DELETE | `/admin/predictions/{id}` | header `X-Admin-Token` |

`PredictionOut`:
```json
{ "id": "uuid", "created_at": "iso", "model": "efficientnet_b0",
  "label": "plastic", "stream": "dry", "confidence": 0.91, "uncertain": false,
  "top3": [{"label":"plastic","confidence":0.91},{"label":"glass","confidence":0.05},{"label":"paper","confidence":0.02}],
  "disposal": "Rinse, dry and put in the dry-waste bin for the MRF.",
  "image_url": "/api/v1/predictions/<id>/image", "gradcam_url": "/api/v1/predictions/<id>/gradcam",
  "latency_ms": 84 }
```

### 5.2 DB schema (SQLModel)
- `prediction(id UUID pk, created_at, model_name, label, stream, confidence float, top3 JSON, uncertain bool, latency_ms int, image_file str, gradcam_file str null, image_sha256 str index)`
- `feedback(id UUID pk, prediction_id fk unique, correct_class str, comment str null ≤ 280, created_at)`
- No user accounts and no IP or PII stored. EXIF is stripped from saved images.

## 6. Frontend design (`frontend/`)

- Next.js 15 (App Router) + TypeScript (strict) + Tailwind CSS v4 + shadcn/ui + lucide-react + Recharts. Package manager: **pnpm**.
- **API access:** `next.config.ts` rewrites `/api/:path*` → `${BACKEND_URL}/api/:path*`, so the browser only talks to the same origin. That means no CORS in production and a simple CSP.
- Data fetching: server components for read-only pages (`/model`, `/about`, `/insights` with `revalidate: 30`); client components for the scanner and feedback. Typed client in `src/lib/api.ts`; types mirror §5.1 by hand in `src/lib/types.ts`.

| Route | Content |
|---|---|
| `/` | Hero with the **scanner** (drag-drop upload, file picker, camera capture via `getUserMedia` with the rear camera on mobile), model selector, sample images (from the test set, labelled "sample"), a "How it works" strip, and an explanation of the four streams |
| `/scan/[id]` | Result: photo with a Grad-CAM before/after slider; label; stream badge (bin colour + icon); confidence meter; top-3 bars; disposal steps; "uncertain" banner when flagged; feedback ("Correct?" yes / pick the correct class) |
| `/history` | Grid of past scans, stream filter chips, infinite "load more" (cursor) |
| `/insights` | Municipal dashboard: stream share (donut), scans per day (line), class counts (bar), feedback correction rate, most-corrected class pairs. Every number comes from `/stats`, and empty states show when there's no data. |
| `/model` | Model comparison table (accuracy, macro-F1, params, size, CPU latency, from-scratch flag); confusion-matrix heatmap; per-class F1 bars; per-source accuracy; training curves from `history.csv`; calibration info. **Only real numbers from `metrics.json`.** If a model isn't trained yet, show "Not trained yet". |
| `/about` | Problem statement, SWM Rules 2026 four streams, dataset sources + citations (from DATASET.md), method, limitations |

States required on every data view: loading skeleton, empty, error (with retry).

## 7. Configuration: everything runs locally with **zero setup**
All settings have working **defaults in code** (`backend/app/config.py`, `ml/src/wasteml/constants.py`, `frontend/next.config.ts`), so `uvicorn` / `pnpm dev` / `python -m wasteml.train` work straight after cloning, **with no `.env` file**.
A `.env` file is **optional**. It's only for overriding a default on your own machine (e.g. a different port or data path). `.env.example` lists every setting with its default:
```
# backend
MODEL_DIR=../ml/artifacts
DEFAULT_MODEL=mobilenet_v3
DATABASE_URL=sqlite:///./storage/ecosort.db
STORAGE_DIR=./storage
MAX_UPLOAD_MB=8
RATE_LIMIT_PREDICT=20/minute
ALLOWED_ORIGINS=http://localhost:3000
ADMIN_TOKEN=                 # optional; if empty, a random token is generated at startup and printed once in the terminal
TORCH_DEVICE=auto            # auto|cpu|mps|cuda
# frontend
BACKEND_URL=http://localhost:8000
# ml
WASTE_DATA_DIR=../data/processed/waste12
```

## 8. Local run
```bash
# ML
cd ml && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e .
python -m wasteml.train --config configs/efficientnet_b0.yaml
python -m wasteml.calibrate --model efficientnet_b0 && python -m wasteml.evaluate --model efficientnet_b0
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e ../ml
uvicorn app.main:app --reload --port 8000
# Frontend
cd frontend && pnpm install && pnpm dev   # http://localhost:3000
```
